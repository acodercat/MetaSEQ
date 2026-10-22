"""The tool harness's wire: what each protocol sends, and how a reply becomes a step and goes
back into the history. Rules from AirBench (Chat) and FinBench (Responses)."""

from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace as NS

import httpx
import openai
import pytest
from cave_agent.models.errors import PromptTooLongError, ProviderError

from llm import ModelConfig
from llm.tool_gateway import ToolGateway, ToolSpec
from settings import PROJECT_ROOT
from tests.fakes import (
    SDKItem,
    SDKStream,
    call_fragment,
    chat_chunk,
    final_event,
    function_call,
    output_message,
    responses_reply,
)

_TOOL = ToolSpec("run", "Runs it.", {"type": "object", "properties": {"code": {"type": "string"}}})


def _gateway(provider="openai_compatible", **fields) -> ToolGateway:
    config = ModelConfig(name="m", api_model="m-1", api_key="k", provider=provider, **fields)
    return ToolGateway(config, timeout=httpx.Timeout(1200.0), retries=0)


def _refused(message, code=None) -> openai.BadRequestError:
    response = httpx.Response(400, request=httpx.Request("POST", "http://gateway/v1"))
    return openai.BadRequestError(message, response=response,
                                  body={"code": code} if code else None)


# --- Chat Completions -------------------------------------------------------------------------

async def test_a_chat_step_offers_one_tool_one_call_at_a_time_and_streams(endpoint):
    endpoint.replies.append(SDKStream([chat_chunk("hi", finish="stop")]))
    conv = _gateway(temperature=0.3, max_tokens=100,
                    extra_body={"enable_thinking": False}).conversation([_TOOL])
    conv.set_system("S")
    conv.add_user("q")
    await conv.step()
    (params,) = endpoint.sent
    assert params["model"] == "m-1" and params["tool_choice"] == "auto"
    assert params["parallel_tool_calls"] is False and params["stream"] is True
    assert params["tools"] == [{"type": "function", "function": {
        "name": "run", "description": "Runs it.", "parameters": _TOOL.parameters}}]
    assert (params["temperature"], params["max_tokens"], params["extra_body"]) == (
        0.3, 100, {"enable_thinking": False})
    assert params["messages"][0] == {"role": "system", "content": "S"}
    assert "Current date and time" in params["messages"][1]["content"]   # on the wire only
    assert conv.messages[1:] == [{"role": "user", "content": "q"},
                                 {"role": "assistant", "content": "hi"}]
    assert endpoint.client_options["max_retries"] == 0


async def test_temperature_inside_the_raw_body_is_not_sent_twice(endpoint):
    endpoint.replies.append(SDKStream([chat_chunk("hi", finish="stop")]))
    await _gateway(extra_body={"temperature": 0.7}).conversation([_TOOL]).step()
    (params,) = endpoint.sent
    assert "temperature" not in params and params["extra_body"] == {"temperature": 0.7}


async def test_call_fragments_are_put_together_and_reasoning_goes_back_with_the_call(endpoint):
    stream = SDKStream([
        chat_chunk(reasoning="think ", calls=[call_fragment(0, '{"code": "x', "c1", "python")]),
        chat_chunk(reasoning="more", calls=[call_fragment(0, ' = 1"}', "c1", "python")]),
        chat_chunk(finish="tool_calls", usage=NS(prompt_tokens=7, completion_tokens=3,
                                                 total_tokens=10)),
    ])
    endpoint.replies.append(stream)
    conv = _gateway().conversation([_TOOL])
    step = await conv.step()
    assert step.tool_calls[0].arguments == {"code": "x = 1"}
    assert step.finish_reason == "tool_calls"
    assert step.usage.total_tokens == 10 and stream.closed
    (assistant,) = conv.messages[1:]
    assert assistant["reasoning_content"] == "think more"
    assert assistant["tool_calls"][0]["function"] == {"name": "python",
                                                      "arguments": '{"code": "x = 1"}'}
    conv.add_tool_result("c1", "ok")
    assert conv.messages[-1] == {"role": "tool", "tool_call_id": "c1", "content": "ok"}


async def test_arguments_that_are_not_json_go_back_as_an_empty_object(endpoint):
    endpoint.replies.append(SDKStream([chat_chunk(
        calls=[call_fragment(0, '{"code": "cut', "c1", "python")], finish="length")]))
    conv = _gateway().conversation([_TOOL])
    step = await conv.step()
    assert step.tool_calls[0].is_malformed and step.tool_calls[0].raw_arguments == '{"code": "cut'
    assert conv.messages[-1]["tool_calls"][0]["function"]["arguments"] == "{}"


async def test_an_empty_chat_reply_leaves_no_message_and_usage_is_estimated_when_absent(
        endpoint):
    endpoint.replies.append(SDKStream([chat_chunk("", finish="stop")]))
    conv = _gateway().conversation([_TOOL])
    conv.add_user("a question with some words")
    step = await conv.step()
    assert conv.messages[1:] == [{"role": "user", "content": "a question with some words"}]
    assert step.usage.prompt_tokens > 0


async def test_a_chat_stream_cut_before_its_finish_is_a_provider_error_and_after_it_is_not(
        endpoint):
    endpoint.replies += [SDKStream([chat_chunk("par")], httpx.ReadError("x")),
                         SDKStream([chat_chunk("par")]),
                         SDKStream([chat_chunk("done", finish="stop")], httpx.ReadError("x"))]
    gateway = _gateway()
    for _ in range(2):
        with pytest.raises(ProviderError):
            await gateway.conversation([_TOOL]).step()
    assert (await gateway.conversation([_TOOL]).step()).text == "done"


async def test_a_chat_refusal_is_marked_as_one_and_written_text_is_not(endpoint):
    endpoint.replies += [SDKStream([chat_chunk(refusal="I can't.", finish="content_filter")]),
                         SDKStream([chat_chunk("hi", finish="content_filter")])]
    gateway = _gateway()
    step = await gateway.conversation([_TOOL]).step()
    assert (step.text, step.refused, step.finish_reason) == ("I can't.", True, "content_filter")
    assert not (await gateway.conversation([_TOOL]).step()).refused


# --- Responses ----------------------------------------------------------------------------

async def test_a_responses_step_is_stateless_and_carries_the_models_options(endpoint):
    endpoint.replies.append(SDKStream([final_event(responses_reply([output_message("hi")]))]))
    await _gateway("openai_responses", reasoning_effort="none",
                   max_tokens=1000).conversation([_TOOL]).step()
    (params,) = endpoint.sent
    assert params["store"] is False and params["parallel_tool_calls"] is False
    assert params["include"] == ["reasoning.encrypted_content"] and params["stream"] is True
    # Flat, as that API takes a tool.
    assert params["tools"] == [{"type": "function", "name": "run", "description": "Runs it.",
                                "parameters": _TOOL.parameters}]
    assert (params["reasoning"], params["max_output_tokens"]) == ({"effort": "none"}, 1000)


async def test_output_items_go_back_verbatim_and_a_call_is_answered_as_function_output(
        endpoint):
    reasoning = SDKItem(type="reasoning", id="r1", encrypted_content="opaque", summary=[])
    endpoint.replies.append(SDKStream([final_event(responses_reply(
        [reasoning, output_message("plan", "commentary"), function_call("x = 1")]))]))
    conv = _gateway("openai_responses").conversation([_TOOL])
    step = await conv.step()
    assert step.text == "plan" and step.finish_reason == "tool_calls"
    assert step.tool_calls[0].arguments == {"code": "x = 1"} and step.usage.total_tokens == 15
    assert conv.messages[1]["encrypted_content"] == "opaque"
    assert conv.messages[2]["phase"] == "commentary" and conv.messages[3]["call_id"] == "c1"
    conv.add_tool_result("c1", "ok")
    assert conv.messages[-1] == {"type": "function_call_output", "call_id": "c1", "output": "ok"}


async def test_an_empty_responses_reply_is_not_kept_and_a_cut_one_is_a_length_finish(endpoint):
    endpoint.replies += [
        SDKStream([final_event(responses_reply([output_message("")]))]),
        SDKStream([final_event(responses_reply([output_message("part")], "incomplete",
                                               "max_output_tokens"))])]
    gateway = _gateway("openai_responses")
    empty = gateway.conversation([_TOOL])
    assert (await empty.step()).text == "" and empty.messages == [{"role": "system",
                                                                   "content": ""}]
    assert (await gateway.conversation([_TOOL]).step()).finish_reason == "length"


@pytest.mark.parametrize("stream", [
    SDKStream([]),                                              # no final response
    SDKStream([NS(type="error", message="boom")]),
    SDKStream([final_event(responses_reply([], "failed"))]),
])
async def test_a_responses_stream_that_breaks_is_a_provider_error(endpoint, stream):
    endpoint.replies.append(stream)
    with pytest.raises(ProviderError):
        await _gateway("openai_responses").conversation([_TOOL]).step()


# --- Failures and plain completions -------------------------------------------------------

@pytest.mark.parametrize("provider", ["openai_compatible", "openai_responses"])
async def test_a_prompt_past_the_window_is_typed_as_such_and_other_refusals_are_not(
        endpoint, provider):
    endpoint.replies += [_refused("This model's maximum context length is 128000 tokens",
                                  "context_length_exceeded"),
                         _refused("bad_response_status_code")]
    gateway = _gateway(provider)
    with pytest.raises(PromptTooLongError):
        await gateway.conversation([_TOOL]).step()
    with pytest.raises(ProviderError):
        await gateway.conversation([_TOOL]).step()


@pytest.mark.parametrize(("provider", "reply"), [
    ("openai_compatible", NS(choices=[NS(message=NS(content="plan"), finish_reason="stop")],
                             usage=NS(prompt_tokens=3, completion_tokens=1, total_tokens=4))),
    ("openai_responses", responses_reply([output_message("plan")])),
])
async def test_a_plain_completion_offers_no_tool_in_either_protocol(endpoint, provider, reply):
    endpoint.replies.append(reply)
    response = await _gateway(provider).complete([{"role": "user", "content": "q"}])
    assert response.content == "plan" and "tools" not in endpoint.sent[0]
    assert response.usage.total_tokens > 0


@pytest.mark.parametrize(("provider", "body"), [
    ("openai_compatible", NS(choices=[], usage=None)),
    ("openai_responses", NS(status="completed")),
])
async def test_a_malformed_plain_completion_is_a_provider_error_not_a_crash(
        endpoint, provider, body):
    endpoint.replies.append(body)
    with pytest.raises(ProviderError, match="malformed response"):
        await _gateway(provider).complete([{"role": "user", "content": "q"}])


def test_the_gateway_knows_no_tool_and_imports_nothing_of_the_agents():
    loaded = subprocess.run(
        [sys.executable, "-c", "import sys, llm.tool_gateway; "
         "print(sorted(m for m in sys.modules if m.split('.')[0] == 'agents'))"],
        capture_output=True, text=True, cwd=PROJECT_ROOT, check=True)
    assert loaded.stdout.strip() == "[]"
