"""Scripted models, deterministic and offline, that record what they were asked: one for the
code harness (cave-agent's `Model`) and one for the tool harness (an `llm.tool_gateway.Gateway`),
both driven by the same policies."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable
from types import SimpleNamespace

from cave_agent import Model, ModelResponse
from cave_agent.models.base import StreamResponse, TokenUsage

from agents.harness.python_tool import PYTHON
from llm.tool_gateway import ChatConversation, Step, ToolCall, ToolSpec

Policy = Callable[[list[dict[str, str]]], str]

USAGE = TokenUsage(prompt_tokens=100, completion_tokens=10, total_tokens=110)


class _ScriptedStream(StreamResponse):
    def __init__(self, text: str):
        super().__init__()
        self._text = text

    async def _open_stream(self):
        async def chunks():
            yield SimpleNamespace(usage=None, choices=[SimpleNamespace(
                finish_reason=None,
                delta=SimpleNamespace(content=self._text, reasoning=None, refusal=None),
            )])
            yield SimpleNamespace(usage=USAGE, choices=[SimpleNamespace(
                finish_reason="stop",
                delta=SimpleNamespace(content=None, reasoning=None, refusal=None),
            )])
        return chunks()


class ScriptedModel(Model):
    def __init__(self, policy: Policy):
        super().__init__()
        self.policy = policy
        self.requests: list[list[dict[str, str]]] = []

    async def _complete(self, messages):
        self.requests.append(messages)
        return ModelResponse(content=self.policy(messages), usage=USAGE, finish_reason="stop")

    def stream(self, messages):
        self.requests.append(messages)
        return _ScriptedStream(self.policy(messages))


class ScriptedGateway:
    """The tool harness's gateway under a code-harness policy: the ```python block of a reply
    becomes one call of the `python` tool, the text before it the reply's text. Everything
    else is the real Chat conversation (history, system prompt, tool results)."""

    def __init__(self, policy: Policy):
        self.policy = policy
        self.requests: list[list[dict]] = []

    def conversation(self, tools: list[ToolSpec]) -> ChatConversation:
        return _ScriptedConversation(self, tools)

    async def complete(self, messages: list[dict]) -> ModelResponse:
        self.requests.append(messages)
        return ModelResponse(content=self.policy(messages), usage=USAGE, finish_reason="stop")


class _ScriptedConversation(ChatConversation):
    def __init__(self, gateway: ScriptedGateway, tools: list[ToolSpec]):
        super().__init__(client=None, options={}, tools=tools)
        self._gateway = gateway

    async def _request(self, wire: list[dict]) -> Step:
        await asyncio.sleep(0)      # a request yields to the loop, where a cancel lands
        self._gateway.requests.append(wire)
        reply = self._gateway.policy(wire)
        fence = re.search(r"```python\n(.*?)```", reply, re.S)
        if fence is None:
            self._history.append({"role": "assistant", "content": reply})
            return Step(reply, (), "stop", USAGE)
        text = reply[:fence.start()].strip()
        call = ToolCall(f"call_{len(self._gateway.requests)}", PYTHON.name,
                        json.dumps({"code": fence.group(1)}))
        self._history.append({"role": "assistant", "content": text or None, "tool_calls": [
            {"id": call.id, "type": "function",
             "function": {"name": call.name, "arguments": call.raw_arguments}}]})
        return Step(text, (call,), "tool_calls", USAGE)


DONE_MARKER = "TOY_STEP_DONE"


def fenced(*lines: str) -> str:
    """A reply whose code block runs *lines*, then prints the marker `toy_policy` waits for."""
    return "```python\n" + "\n".join((*lines, f"print('{DONE_MARKER}')")) + "\n```"


# Idempotent across turns: `doubled` set in turn 1 is discarded when turn 2
# registers it, so it only counts when turn 2 sets it again.
CODE = fenced("total = float(readings_df['value'].sum())", "doubled = total * 2")


def toy_policy(messages: list[dict[str, str]]) -> str:
    """Every agent writes the correct code once, then answers."""
    if DONE_MARKER in messages[-1]["content"]:
        return "The total is 42 and doubled it is 84."
    return CODE


# --- The OpenAI SDK, offline: what `llm.tool_gateway` reads from it ---------------------------

class FakeEndpoint:
    """An OpenAI-compatible endpoint: the replies it will give, in order (an exception is
    raised), and the requests it got. Stands in for `openai.AsyncOpenAI` (`endpoint` fixture)."""

    def __init__(self) -> None:
        self.replies: list = []
        self.sent: list[dict] = []
        self.client_options: dict = {}

    def client(self, **options) -> SimpleNamespace:
        self.client_options = options
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=self._create)), responses=SimpleNamespace(create=self._create))

    async def _create(self, **params):
        self.sent.append(params)
        reply = self.replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        return reply


class SDKStream:
    """A streamed reply: its events, then *error* if one is given; records being closed."""

    def __init__(self, events, error: BaseException | None = None):
        self.events, self.error, self.closed = list(events), error, False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.events:
            return self.events.pop(0)
        if self.error is not None:
            error, self.error = self.error, None
            raise error
        raise StopAsyncIteration

    async def close(self) -> None:
        self.closed = True


def chat_chunk(content=None, reasoning=None, calls=(), finish=None, usage=None, refusal=None):
    delta = SimpleNamespace(content=content, refusal=refusal, reasoning_content=reasoning,
                            tool_calls=list(calls))
    return SimpleNamespace(usage=usage, choices=[SimpleNamespace(finish_reason=finish,
                                                                 delta=delta)])


def call_fragment(index, arguments, call_id=None, name=None):
    return SimpleNamespace(index=index, id=call_id,
                           function=SimpleNamespace(name=name, arguments=arguments))


class SDKItem(SimpleNamespace):
    """A Responses output item: attributes to read, `model_dump` to plain data, as the SDK's."""

    def model_dump(self, exclude_none=True):
        return _dump(self, exclude_none)


def _dump(value, exclude_none):
    if isinstance(value, SimpleNamespace):
        return {k: _dump(v, exclude_none) for k, v in vars(value).items()
                if not (exclude_none and v is None)}
    if isinstance(value, list):
        return [_dump(v, exclude_none) for v in value]
    return value


def output_message(text, phase="final_answer"):
    return SDKItem(type="message", phase=phase, role="assistant",
                   content=[SDKItem(type="output_text", text=text)])


def function_call(code, call_id="c1"):
    return SDKItem(type="function_call", call_id=call_id, name=PYTHON.name, id=f"fc_{call_id}",
                   arguments=json.dumps({"code": code}))


def responses_reply(output, status="completed", reason=None):
    return SimpleNamespace(output=output, status=status, error=None,
                           incomplete_details=SimpleNamespace(reason=reason) if reason else None,
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5,
                                                 total_tokens=15))


def final_event(response):
    """The event that closes a Responses stream, carrying the final response."""
    return SimpleNamespace(type=f"response.{response.status}", response=response)

