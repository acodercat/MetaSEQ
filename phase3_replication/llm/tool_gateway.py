"""The tool harness's connection to the model: one conversation per agent, with the tools it
is given.

This module is transport and wire format only: the tool harness's agent
(`agents.harness.tool_agent`) owns its tools (:class:`ToolSpec`) and what a call does, and
nothing here imports it. :class:`ToolGateway` holds one client per model and opens one
:class:`Conversation` per agent, in the wire protocol the model's ``provider`` names:

- ``openai_compatible`` -> :class:`ChatConversation`, Chat Completions with ``tools``. An
  assistant message's ``reasoning_content`` is sent back with it: DeepSeek in thinking mode
  requires that inside a tool loop.
- ``openai_responses`` -> :class:`ResponsesConversation`, the Responses API, which GPT-6 Luna
  needs. Output items go back verbatim (reasoning items carry state the next call needs).
- ``anthropic`` -> :class:`AnthropicConversation`, the Messages API through the anthropic SDK,
  which Claude needs. Its content blocks go back as returned (a thinking block's signature is
  checked), and the history carries a prompt-cache breakpoint on its last block.

Each step asks for at most one tool call (``parallel_tool_calls=False``): a code-harness step
runs one block, and the agent holds a step to one execution as well, for endpoints that ignore
the switch. A call's arguments come back as the model wrote them (:class:`ToolCall`), parsed
for the agent, and go back into the history as a JSON object whatever they were. Steps
stream, so a reverse proxy never ends one for silence, and the client's read timeout bounds
each silence. A plain completion (:meth:`ToolGateway.complete`, the coordinator's plan) is one
request, as under the code harness. Sampling options are the code harness's
(`ModelConfig.chat_options`, `responses_options`). The system prompt is replaced before each
run and followed, on the wire only, by the date reminder cave-agent sends. A provider's
failure leaves this module as cave-agent's typed `ModelError` (`raise_model_error`: a prompt
past the window, an endpoint out of credit, else a provider error), and so does a plain
completion's body that is not what the protocol promises; a defect here propagates.

Ported from AirBench (``adapters/tool_gateway.py`` at d5bcc29: the call, the step, the Chat
conversation, the replay and usage rules) and FinBench (``core/tool_gateway.py`` at 520f271:
the Responses conversation; the Messages conversation as of 2026-10-12), where each rule was
settled against a live endpoint.
"""

from __future__ import annotations

import contextlib
import json
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from functools import cached_property
from typing import Any, Protocol

import anthropic
import httpx
import httpx2
import openai
from cave_agent.compaction import default_token_estimate
from cave_agent.models.base import ModelResponse, TokenUsage
from cave_agent.models.errors import ProviderError, raise_model_error

from llm.registry import ModelConfig
from llm.responses import response_finish_reason, response_text, response_usage

# Failures on the provider's side of a request: the SDK wraps those in opening one, and a
# stream that breaks while it is read raises the transport's own.
_PROVIDER_FAILURES = (openai.APIError, anthropic.APIError, httpx.HTTPError, httpx2.HTTPError)
# A plain completion's body that is not what the protocol promises (`choices` empty,
# `output` missing).
_MALFORMED = (AttributeError, IndexError, KeyError, TypeError)
# Final events of a Responses stream: the response, whole, in whichever state it ended.
_FINAL_EVENTS = ("response.completed", "response.incomplete", "response.failed")


@dataclass(frozen=True)
class ToolSpec:
    """A function tool in neither protocol's shape; each conversation renders it in its own."""

    name: str
    description: str
    parameters: dict[str, Any]       # JSON Schema of the arguments object


def parse_arguments(raw: str) -> dict[str, Any] | None:
    """A call's raw arguments as an object, or ``None`` when they are not a JSON object
    (malformed, or cut at the output cap)."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    # As the model wrote them, which need not be JSON: malformed, or cut at the cap.
    raw_arguments: str

    @cached_property
    def arguments(self) -> dict[str, Any] | None:
        return parse_arguments(self.raw_arguments)

    @property
    def is_malformed(self) -> bool:
        """Its arguments are not a JSON object: malformed, or cut before they ended."""
        return self.arguments is None


@dataclass(frozen=True)
class Step:
    """One model response: its text, the calls it asked for, and why it stopped."""

    text: str
    tool_calls: tuple[ToolCall, ...]
    finish_reason: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    reasoning: str = ""
    # The text is the model's refusal: the answer when it gave no other, as in cave-agent,
    # even under a "content_filter" finish.
    refused: bool = False


async def _typed[T](request: Callable[[], Awaitable[T]]) -> T:
    """*request*, a provider's failure of it as cave-agent's typed `ModelError`."""
    try:
        return await request()
    except _PROVIDER_FAILURES as error:
        raise_model_error(error)


async def _close(stream: Any) -> None:
    """Release a stream; a failure to close never outranks the reply already read."""
    with contextlib.suppress(*_PROVIDER_FAILURES):
        await stream.close()


def _replayable(raw: str) -> str:
    """Arguments as the history replays them: verbatim when they are a JSON object.

    Anything else -- malformed, or cut at the output cap -- goes back as ``{}``. Providers
    reject a history whose tool-call arguments are not valid JSON (DeepSeek: "Assistant tool
    call function.arguments must be valid JSON"), which failed every later request; the agent
    has already told the model that the call was not run.
    """
    return raw if parse_arguments(raw) is not None else "{}"


def _date_reminder() -> dict[str, str]:
    now = datetime.now().strftime("%Y-%m-%d %H:00")
    return {"role": "user",
            "content": f"<system-reminder>\nCurrent date and time: {now}\n</system-reminder>"}


def _chat_usage(usage: Any) -> TokenUsage:
    """A Chat Completions usage block in cave-agent's terms (none when absent)."""
    if usage is None:
        return TokenUsage()
    prompt = getattr(usage, "prompt_tokens", 0) or 0
    completion = getattr(usage, "completion_tokens", 0) or 0
    return TokenUsage(prompt, completion, getattr(usage, "total_tokens", 0) or prompt + completion)


def _message_text(message: dict[str, Any]) -> str:
    """The text a wire message carries: content, reasoning sent back, a tool result, call
    arguments (in either protocol's shape)."""
    parts = [message.get("content"), message.get("reasoning_content"),
             message.get("output"), message.get("arguments")]
    parts += [call["function"]["arguments"] for call in message.get("tool_calls", ())]
    return "".join(part for part in parts if isinstance(part, str))


def _estimated_usage(wire: list[dict[str, Any]], step: Step) -> TokenUsage:
    """Cost a step whose provider reported no usage, with cave-agent's estimator: prompt from
    the messages sent, completion from the answer, its reasoning and the calls' arguments as
    the model wrote them. What is sent includes the reasoning returned to the model, which the
    code harness never sends, so on a thinking model the prompt count is higher, as its
    requests are."""
    prompt = sum(default_token_estimate(_message_text(message)) for message in wire)
    written = [step.text, step.reasoning, *(call.raw_arguments for call in step.tool_calls)]
    completion = sum(default_token_estimate(text) for text in written)
    return TokenUsage(prompt, completion, prompt + completion)


class Conversation(ABC):
    """One agent's history with the model, in one wire protocol."""

    def __init__(self, client: openai.AsyncOpenAI, options: dict[str, Any],
                 tools: Sequence[ToolSpec]):
        self._client = client
        self._options = options
        self._tools = [self._tool_param(tool) for tool in tools]
        self._system = ""
        self._history: list[dict[str, Any]] = []

    @property
    def messages(self) -> list[dict[str, Any]]:
        return [{"role": "system", "content": self._system}, *self._history]

    def set_system(self, prompt: str) -> None:
        self._system = prompt

    def add_user(self, text: str) -> None:
        self._history.append({"role": "user", "content": text})

    @staticmethod
    @abstractmethod
    def _tool_param(tool: ToolSpec) -> dict[str, Any]:
        """*tool* in this protocol's shape."""

    @abstractmethod
    def add_tool_result(self, call_id: str, output: str) -> None:
        """Answer the call *call_id* with the text *output*."""

    async def step(self) -> Step:
        """Send the history, record the model's response in it, and return the response."""
        wire = self._wire()
        step = await _typed(lambda: self._request(wire))
        if step.usage.total_tokens == 0:
            step = replace(step, usage=_estimated_usage(wire, step))
        return step

    def _wire(self) -> list[dict[str, Any]]:
        """The messages a step sends: the system prompt, the date reminder, the history."""
        return [{"role": "system", "content": self._system}, _date_reminder(), *self._history]

    @abstractmethod
    async def _request(self, wire: list[dict[str, Any]]) -> Step:
        """Send *wire* in this protocol, record the response in the history, return it."""


@dataclass
class _StreamedCall:
    id: str = ""
    name: str = ""
    arguments: list[str] = field(default_factory=list)


class _StreamedReply:
    """A streamed Chat Completions reply, put back together.

    Tool calls arrive as fragments keyed by ``index`` (absent on some gateways, which send one
    call; read as 0). ``id`` and ``name`` are assigned rather than appended, since some
    gateways repeat them in every fragment, and ``arguments`` are joined in order.
    """

    def __init__(self) -> None:
        self._text: list[str] = []
        self._refusal: list[str] = []
        self._reasoning: list[str] = []
        self._calls: dict[int, _StreamedCall] = {}
        self._finish_reason: str | None = None
        self._usage = TokenUsage()

    @property
    def finished(self) -> bool:
        return self._finish_reason is not None

    def add(self, chunk: Any) -> None:
        if getattr(chunk, "usage", None):
            self._usage = _chat_usage(chunk.usage)
        for choice in chunk.choices or ():
            self._finish_reason = choice.finish_reason or self._finish_reason
            delta = choice.delta
            if delta is None:
                continue        # metadata such as an asynchronous content-filter verdict
            self._text.append(delta.content or "")
            self._refusal.append(getattr(delta, "refusal", None) or "")
            self._reasoning.append(getattr(delta, "reasoning_content", None)
                                   or getattr(delta, "reasoning", None) or "")
            for fragment in delta.tool_calls or ():
                call = self._calls.setdefault(fragment.index or 0, _StreamedCall())
                call.id = fragment.id or call.id
                if fragment.function:
                    call.name = fragment.function.name or call.name
                    call.arguments.append(fragment.function.arguments or "")

    def finish(self) -> tuple[dict[str, Any] | None, Step]:
        """The assistant message for the history, if any, and the step for the agent.

        A refusal is the answer when there is no other text, as in cave-agent. A reply with
        neither text nor a call leaves no message: several providers reject empty assistant
        content on the next request.
        """
        if self._finish_reason is None:
            # A stream that stops without saying why was cut, not finished.
            raise ProviderError("The model stream ended without a terminal finish reason")
        written, refusal = "".join(self._text), "".join(self._refusal)
        text = written or refusal
        reasoning = "".join(self._reasoning)
        calls, wire = [], []
        for index, streamed in sorted(self._calls.items()):
            # A gateway that sends no id still needs one to answer the call by.
            call = ToolCall(streamed.id or f"call_{index}", streamed.name,
                            "".join(streamed.arguments))
            calls.append(call)
            wire.append({"id": call.id, "type": "function", "function": {
                "name": call.name, "arguments": _replayable(call.raw_arguments)}})
        step = Step(text, tuple(calls), self._finish_reason, self._usage, reasoning,
                    refused=bool(refusal) and not written)
        if not text.strip() and not wire:
            return None, step
        assistant: dict[str, Any] = {"role": "assistant", "content": text or None}
        if wire:
            assistant["tool_calls"] = wire
        if reasoning:
            assistant["reasoning_content"] = reasoning
        return assistant, step


class ChatConversation(Conversation):
    """Chat Completions with function tools."""

    @staticmethod
    def _tool_param(tool: ToolSpec) -> dict[str, Any]:
        return {"type": "function", "function": {
            "name": tool.name, "description": tool.description, "parameters": tool.parameters}}

    def add_tool_result(self, call_id: str, output: str) -> None:
        self._history.append({"role": "tool", "tool_call_id": call_id, "content": output})

    async def _request(self, wire: list[dict[str, Any]]) -> Step:
        stream = await self._client.chat.completions.create(
            messages=wire, tools=self._tools, tool_choice="auto", parallel_tool_calls=False,
            stream=True, stream_options={"include_usage": True}, **self._options)
        reply = _StreamedReply()
        try:
            async for chunk in stream:
                reply.add(chunk)
        except _PROVIDER_FAILURES:
            # After the finish reason only the usage chunk can be lost; the answer is whole.
            if not reply.finished:
                raise
        finally:
            await _close(stream)
        assistant, step = reply.finish()
        if assistant is not None:
            self._history.append(assistant)
        return step


class ResponsesConversation(Conversation):
    """The Responses API with function tools (flat, as that API defines them)."""

    @staticmethod
    def _tool_param(tool: ToolSpec) -> dict[str, Any]:
        return {"type": "function", "name": tool.name, "description": tool.description,
                "parameters": tool.parameters}

    def add_tool_result(self, call_id: str, output: str) -> None:
        self._history.append({"type": "function_call_output", "call_id": call_id,
                              "output": output})

    async def _request(self, wire: list[dict[str, Any]]) -> Step:
        stream = await self._client.responses.create(
            input=wire, tools=self._tools, parallel_tool_calls=False, store=False,
            include=["reasoning.encrypted_content"], stream=True, **self._options)
        response = None
        try:
            async for event in stream:
                if event.type in _FINAL_EVENTS:
                    response = event.response
                    break           # nothing after the final response is needed
                if event.type == "error":
                    raise ProviderError(f"Responses stream error: {event.message}")
        finally:
            await _close(stream)
        if response is None:
            raise ProviderError("Responses stream ended without a final response")
        if response.status == "failed":
            raise ProviderError(f"Responses stream failed: {response.error}")
        return self._record(response)

    def _record(self, response: Any) -> Step:
        """The final response as a step, its items kept for the next request.

        The items go back verbatim -- reasoning items carry state the next call needs --
        unless the response holds neither text nor a call; then it leaves nothing, as an
        empty Chat reply does.
        """
        written, refusal = response_text(response)
        text = written or refusal
        calls = tuple(ToolCall(item.call_id, item.name, item.arguments)
                      for item in response.output if item.type == "function_call")
        if text.strip() or calls:
            self._history.extend(_replayable_item(item) for item in response.output)
        finish = response_finish_reason(response)
        return Step(text=text, tool_calls=calls,
                    finish_reason="tool_calls" if finish == "stop" and calls else finish,
                    usage=response_usage(response), refused=bool(refusal) and not written)


_ANTHROPIC_FINISH = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "tool_use": "tool_calls",
    "max_tokens": "length",
    "refusal": "content_filter",
}


class AnthropicConversation(Conversation):
    """The Messages API with one function tool, through the anthropic SDK.

    The system prompt is a request parameter, not a message; the content blocks of a response
    go back as returned, a call's input as the model wrote it (``{}`` when it is not a JSON
    object, as on the other protocols); the results for one response's calls go back in one
    user turn. Each request carries a prompt-cache breakpoint on its last block, set in a copy
    (the external platform drops the request-level ``cache_control``), so each step reads the
    previous step's prefix from the cache.
    """

    @staticmethod
    def _tool_param(tool: ToolSpec) -> dict[str, Any]:
        return {"name": tool.name, "description": tool.description,
                "input_schema": tool.parameters}

    def add_tool_result(self, call_id: str, output: str) -> None:
        result = {"type": "tool_result", "tool_use_id": call_id, "content": output}
        last = self._history[-1] if self._history else None
        if last is not None and last["role"] == "user" and isinstance(last["content"], list):
            last["content"].append(result)
        else:
            self._history.append({"role": "user", "content": [result]})

    def _wire(self) -> list[dict[str, Any]]:
        *earlier, last = [_date_reminder(), *self._history]
        content = last["content"]
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content
        marked = [*blocks[:-1], {**blocks[-1], "cache_control": {"type": "ephemeral"}}]
        return [*earlier, {**last, "content": marked}]

    async def _request(self, wire: list[dict[str, Any]]) -> Step:
        # Each call's input as the model wrote it, by block index: the SDK's own ``input`` is
        # parsed leniently and keeps a call cut at the cap.
        written: dict[int, str] = {}
        async with self._client.messages.stream(
            messages=wire, system=self._system, tools=self._tools,
            tool_choice={"type": "auto", "disable_parallel_tool_use": True}, **self._options,
        ) as stream:
            try:
                async for event in stream:
                    if (event.type == "content_block_delta"
                            and event.delta.type == "input_json_delta"):
                        written[event.index] = (written.get(event.index, "")
                                                + event.delta.partial_json)
            except _PROVIDER_FAILURES:
                # After the stop reason only the closing event can be lost.
                if stream.current_message_snapshot.stop_reason is None:
                    raise
            message = stream.current_message_snapshot
        return self._record(message, written)

    def _record(self, message: Any, written: dict[int, str]) -> Step:
        if message.stop_reason is None:
            raise ProviderError("The model stream ended without a terminal stop reason")
        if message.stop_reason == "model_context_window_exceeded":
            from cave_agent.models.errors import PromptTooLongError
            raise PromptTooLongError("Claude's reply reached the end of its context window")
        finish = _ANTHROPIC_FINISH.get(message.stop_reason)
        if finish is None:
            raise ProviderError(f"Claude ended the response with {message.stop_reason}")
        blocks, calls = [], []
        for index, block in enumerate(message.content):
            dumped = block.model_dump(mode="json", exclude_none=True)
            if block.type == "tool_use":
                raw = written.get(index) or json.dumps(block.input)
                calls.append(ToolCall(block.id, block.name, raw))
                dumped["input"] = parse_arguments(raw) or {}
            blocks.append(dumped)
        text = "".join(block.text for block in message.content if block.type == "text")
        reasoning = "".join(block.thinking for block in message.content
                            if block.type == "thinking")
        if text.strip() or calls:
            self._history.append({"role": "assistant", "content": blocks})
        usage = message.usage
        prompt = (usage.input_tokens + (usage.cache_read_input_tokens or 0)
                  + (usage.cache_creation_input_tokens or 0))
        return Step(text=text, tool_calls=tuple(calls),
                    finish_reason="tool_calls" if finish == "stop" and calls else finish,
                    usage=TokenUsage(prompt, usage.output_tokens, prompt + usage.output_tokens),
                    reasoning=reasoning, refused=message.stop_reason == "refusal")


def _replayable_item(item: Any) -> dict[str, Any]:
    dumped = item.model_dump(exclude_none=True)
    if item.type == "function_call":
        dumped["arguments"] = _replayable(item.arguments)
    return dumped


def _malformed(error: Exception) -> ProviderError:
    return ProviderError(f"malformed response: {type(error).__name__}: {error}")


async def _chat_complete(client: openai.AsyncOpenAI, options: dict[str, Any],
                         messages: list[dict[str, str]]) -> ModelResponse:
    response = await client.chat.completions.create(messages=messages, **options)
    try:
        choice = response.choices[0]
        content = choice.message.content or getattr(choice.message, "refusal", None) or ""
        finish_reason = choice.finish_reason or "stop"
    except _MALFORMED as error:
        raise _malformed(error) from error
    return ModelResponse(content=content, usage=_chat_usage(getattr(response, "usage", None)),
                         finish_reason=finish_reason)


async def _responses_complete(client: openai.AsyncOpenAI, options: dict[str, Any],
                              messages: list[dict[str, str]]) -> ModelResponse:
    response = await client.responses.create(input=messages, store=False, **options)
    try:
        written, refusal = response_text(response)
        finish_reason = response_finish_reason(response)
    except _MALFORMED as error:
        raise _malformed(error) from error
    return ModelResponse(content=written or refusal, usage=response_usage(response),
                         finish_reason=finish_reason)


async def _anthropic_complete(client: anthropic.AsyncAnthropic, options: dict[str, Any],
                              messages: list[dict[str, str]]) -> ModelResponse:
    """A plain completion on the Messages API: the system messages become its ``system``."""
    system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
    rest = [m for m in messages if m["role"] != "system"]
    response = await client.messages.create(messages=rest, system=system, **options)
    try:
        content = "".join(block.text for block in response.content if block.type == "text")
        finish_reason = _ANTHROPIC_FINISH.get(response.stop_reason, "stop")
        usage = response.usage
        prompt = (usage.input_tokens + (usage.cache_read_input_tokens or 0)
                  + (usage.cache_creation_input_tokens or 0))
    except _MALFORMED as error:
        raise _malformed(error) from error
    return ModelResponse(content=content, finish_reason=finish_reason,
                         usage=TokenUsage(prompt, usage.output_tokens,
                                          prompt + usage.output_tokens))


class Gateway(Protocol):
    """What the tool harness's agent and harness ask of their connection to the model."""

    def conversation(self, tools: Sequence[ToolSpec]) -> Conversation: ...

    async def complete(self, messages: list[dict[str, str]]) -> ModelResponse: ...


class ToolGateway:
    """One client per model; each agent opens its own :meth:`conversation`, and a plain
    completion without tools, nothing kept, is :meth:`complete`."""

    def __init__(self, config: ModelConfig, *, timeout: httpx.Timeout, retries: int):
        """*timeout* bounds each phase of a request (a stream's read: its longest silence);
        *retries* are the transport's, as the code harness's (`llm.TRANSPORT_RETRIES`)."""
        if config.provider == "anthropic":
            self._protocol: type[Conversation] = AnthropicConversation
            self._complete = _anthropic_complete
            self._options = {"model": config.api_model, **config.anthropic_options()}
            # The anthropic SDK speaks httpx2, whose Timeout is its own type.
            self._client = anthropic.AsyncAnthropic(
                api_key=config.api_key, base_url=config.base_url, max_retries=retries,
                timeout=httpx2.Timeout(timeout.read, connect=timeout.connect,
                                       write=timeout.write, pool=timeout.pool))
            return
        responses = config.provider == "openai_responses"
        self._protocol = ResponsesConversation if responses else ChatConversation
        self._complete = _responses_complete if responses else _chat_complete
        options = config.responses_options() if responses else config.chat_options()
        self._options = {"model": config.api_model, **options}
        self._client = openai.AsyncOpenAI(api_key=config.api_key, base_url=config.base_url,
                                          timeout=timeout, max_retries=retries)

    def conversation(self, tools: Sequence[ToolSpec]) -> Conversation:
        """A new history in which the model is offered *tools*."""
        return self._protocol(self._client, self._options, tools)

    async def complete(self, messages: list[dict[str, str]]) -> ModelResponse:
        return await _typed(lambda: self._complete(self._client, self._options, messages))
