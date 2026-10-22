"""The Messages API (`provider = "anthropic"`, which Claude needs): what a step sends, and how
a reply becomes a step and goes back into the history. Offline, through a stand-in for the
anthropic SDK's client."""

from __future__ import annotations

from types import SimpleNamespace as NS

import anthropic
import httpx
import pytest
from anthropic.types import Message
from cave_agent.models.errors import PromptTooLongError, ProviderError

from llm import ModelConfig
from llm.tool_gateway import AnthropicConversation, ToolGateway, ToolSpec

_TOOL = ToolSpec("run", "Runs it.", {"type": "object", "properties": {"code": {"type": "string"}}})


def _config(**fields) -> ModelConfig:
    return ModelConfig(name="claude", api_model="claude-x", api_key="k", provider="anthropic",
                       **fields)


def _message(content, stop_reason="end_turn", **usage) -> Message:
    return Message.model_validate({
        "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-x",
        "content": content, "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5, **usage}})


class _Stream:
    """`client.messages.stream(...)`: an async context manager over the events, whose
    `current_message_snapshot` is the reply."""

    def __init__(self, events, message, error=None):
        self.events, self.current_message_snapshot, self.error = events, message, error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for event in self.events:
            yield event
        if self.error is not None:
            raise self.error


class _Client:
    def __init__(self, *replies, created=None):
        self.replies, self.created, self.sent = list(replies), created, []
        self.messages = NS(stream=self._stream, create=self._create)

    def _stream(self, **kwargs):
        self.sent.append(kwargs)
        return self.replies.pop(0)

    async def _create(self, **kwargs):
        self.sent.append(kwargs)
        return self.created


def _conversation(*replies, **fields):
    gateway = ToolGateway(_config(**fields), timeout=httpx.Timeout(600.0), retries=0)
    client = _Client(*replies)
    conversation = gateway.conversation([_TOOL])
    conversation._client = client
    conversation.set_system("You are an analyst.")
    conversation.add_user("Compute it.")
    return conversation, client


def _json_delta(index, text):
    return NS(type="content_block_delta", index=index,
              delta=NS(type="input_json_delta", partial_json=text))


def test_options_carry_the_cap_and_put_temperature_and_effort_in_the_raw_body():
    config = _config(temperature=1.0, max_tokens=64000, reasoning_effort="low",
                     extra_body={"thinking": {"type": "disabled"}})
    assert config.anthropic_options() == {
        "max_tokens": 64000,
        "extra_body": {"thinking": {"type": "disabled"}, "temperature": 1.0,
                       "output_config": {"effort": "low"}}}
    assert _config().anthropic_options()["max_tokens"] == 8192
    assert _config().fingerprint()["provider"] == "anthropic"


def test_the_gateway_speaks_the_messages_api_with_the_tool_in_its_shape():
    gateway = ToolGateway(_config(), timeout=httpx.Timeout(600.0), retries=0)
    conversation = gateway.conversation([_TOOL])
    assert isinstance(conversation, AnthropicConversation)
    assert isinstance(gateway._client, anthropic.AsyncAnthropic)
    assert conversation._tools == [{"name": "run", "description": "Runs it.",
                                    "input_schema": _TOOL.parameters}]


async def test_a_step_sends_the_system_apart_one_call_at_a_time_and_marks_the_last_block():
    reply = _message([{"type": "text", "text": "Running."},
                      {"type": "tool_use", "id": "t1", "name": "run", "input": {"code": "1"}}],
                     stop_reason="tool_use", cache_read_input_tokens=100,
                     cache_creation_input_tokens=7)
    conversation, client = _conversation(
        _Stream([_json_delta(1, '{"code": '), _json_delta(1, '"1+1"}')], reply))
    step = await conversation.step()

    sent = client.sent[0]
    assert sent["system"] == "You are an analyst."
    assert sent["model"] == "claude-x"
    assert sent["tool_choice"] == {"type": "auto", "disable_parallel_tool_use": True}
    assert [m["role"] for m in sent["messages"]] == ["user", "user"]   # date reminder, task
    assert sent["messages"][-1]["content"] == [
        {"type": "text", "text": "Compute it.", "cache_control": {"type": "ephemeral"}}]
    # The breakpoint is set in a copy: the history keeps the text as it was added.
    assert conversation._history[0] == {"role": "user", "content": "Compute it."}

    # The call's input as the model wrote it, not the SDK's parse.
    assert [(c.id, c.name, c.raw_arguments) for c in step.tool_calls] == [
        ("t1", "run", '{"code": "1+1"}')]
    assert step.text == "Running." and step.finish_reason == "tool_calls"
    assert (step.usage.prompt_tokens, step.usage.completion_tokens) == (117, 5)
    assert conversation._history[-1]["role"] == "assistant"
    assert conversation._history[-1]["content"][1]["input"] == {"code": "1+1"}


async def test_the_results_of_one_reply_go_back_in_one_user_turn():
    conversation, _ = _conversation()
    conversation._history.append({"role": "assistant", "content": [{"type": "text", "text": "x"}]})
    conversation.add_tool_result("t1", "2")
    conversation.add_tool_result("t2", "3")
    assert conversation._history[-1] == {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "2"},
        {"type": "tool_result", "tool_use_id": "t2", "content": "3"}]}
    last = conversation._wire()[-1]["content"]
    assert last[-1]["cache_control"] == {"type": "ephemeral"} and "cache_control" not in last[0]


async def test_a_refusal_is_the_content_filter_and_keeps_its_text():
    conversation, _ = _conversation(
        _Stream([], _message([{"type": "text", "text": "I can't help."}], stop_reason="refusal")))
    step = await conversation.step()
    assert (step.finish_reason, step.refused, step.text) == ("content_filter", True,
                                                             "I can't help.")


@pytest.mark.parametrize(("stop_reason", "error"), [
    (None, ProviderError), ("pause_turn", ProviderError),
    ("model_context_window_exceeded", PromptTooLongError)])
async def test_a_reply_without_a_usable_stop_reason_is_an_error(stop_reason, error):
    conversation, _ = _conversation(
        _Stream([], _message([{"type": "text", "text": "partial"}], stop_reason=stop_reason)))
    with pytest.raises(error):
        await conversation.step()


async def test_a_dropped_closing_event_after_the_stop_reason_keeps_the_reply():
    dropped = httpx.ReadError("closed")
    reply = _message([{"type": "text", "text": "Done."}])
    conversation, _ = _conversation(_Stream([], reply, error=dropped))
    assert (await conversation.step()).text == "Done."
    unfinished = _message([{"type": "text", "text": "Do"}], stop_reason=None)
    conversation, _ = _conversation(_Stream([], unfinished, error=httpx.ReadError("closed")))
    with pytest.raises(ProviderError):
        await conversation.step()


async def test_a_plain_completion_sends_the_system_messages_as_its_system():
    gateway = ToolGateway(_config(), timeout=httpx.Timeout(600.0), retries=0)
    gateway._client = _Client(created=_message([{"type": "text", "text": "ok"}],
                                               cache_read_input_tokens=4))
    response = await gateway.complete([{"role": "system", "content": "Be brief."},
                                       {"role": "system", "content": "One word."},
                                       {"role": "user", "content": "Say ok."}])
    sent = gateway._client.sent[0]
    assert sent["system"] == "Be brief.\n\nOne word."
    assert sent["messages"] == [{"role": "user", "content": "Say ok."}]
    assert (response.content, response.finish_reason) == ("ok", "stop")
    assert response.usage.prompt_tokens == 14
