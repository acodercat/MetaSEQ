"""A stage's outcome: provider failures retried, model failures scored, history kept whole."""

from __future__ import annotations

import pytest
from cave_agent import StopReason
from cave_agent.agent import AgentResponse
from cave_agent.models.errors import (
    PromptTooLongError,
    ProviderBillingError,
    ProviderError,
    StreamStalledError,
)

from agents.failure import classify
from agents.stage import run_stage
from agents.workspace import Workspace
from errors import InfrastructureError
from tests.test_end_to_end import _run


@pytest.mark.parametrize("error,expected", [
    (ProviderError("The model completed without returning an answer."), ("empty_answer", True)),
    (ProviderError("The provider filtered this response and returned no content."),
     ("content_filter", False)),
    (ProviderError("BadRequestError: Output data may contain inappropriate content."),
     ("content_filter", False)),
    (ProviderError("Model output was truncated and could not be recovered"), ("truncated", True)),
    (PromptTooLongError("context_length_exceeded"), ("prompt_too_long", True)),
    (ProviderError("BadRequestError: <400> InternalError.Algo.InvalidParameter: Range of input "
                   "length should be [1, 98304]"), ("prompt_too_long", True)),
    (ProviderError("APIConnectionError: connection reset"), ("provider", False)),
    (ProviderError("BadRequestError: bad_response_status_code"), ("provider", False)),
    (ProviderError("The model stream ended without a terminal finish reason."),
     ("provider", False)),
    (StreamStalledError("no chunk for 600 s"), ("stream_stalled", False)),
    (ProviderBillingError("out of credit"), ("billing", False)),
    (None, ("unknown", False)),
])
def test_a_failure_is_the_models_only_when_the_reply_itself_failed(error, expected):
    failure = classify(error)
    assert (failure.kind, failure.model_fault) == expected


class _Agent:
    """Stands in for either harness's agent: stops with `stop`, its failure from `error`."""

    def __init__(self, error=None, stop=StopReason.MODEL_ERROR, replace_history=False):
        self.messages = ["system", "earlier question", "earlier answer"]
        self.error, self.stop, self.replace_history = error, stop, replace_history
        self.failure = None

    async def run(self, query):
        self.failure = classify(self.error) if self.stop is StopReason.MODEL_ERROR else None
        new = [SummaryMessage(), f"user: {query}", "assistant: done"]
        # Compaction replaces the history it summarises; otherwise messages are appended.
        self.messages = (["system", *new] if self.replace_history else [*self.messages, *new[1:]])
        return AgentResponse(content="done", stop_reason=self.stop, steps=2, elapsed=0.1)

    def transcript(self, messages):
        return [{"type": type(m).__name__, "content": str(m)} for m in messages]

    def compactions(self, messages):
        return sum(isinstance(m, SummaryMessage) for m in messages)


class SummaryMessage:
    pass


async def _stage(agent):
    workspace = Workspace(functions=[], variables=[])
    try:
        return await run_stage(agent, workspace, role="solo", query="q", task="q", budget=5)
    finally:
        workspace.close()


async def test_a_provider_failure_raises_with_its_kind():
    with pytest.raises(InfrastructureError) as caught:
        await _stage(_Agent(ProviderError("APIConnectionError: connection reset")))
    assert caught.value.kind == "provider" and "connection reset" in str(caught.value)


async def test_a_model_failure_ends_the_stage_and_is_recorded():
    record = await _stage(_Agent(ProviderError("The model completed without returning an answer.")))
    assert record.stop_reason == "model_failure:empty_answer"
    assert "without returning an answer" in record.error


async def test_runtime_and_internal_errors_are_the_infrastructures():
    for stop in (StopReason.RUNTIME_ERROR, StopReason.INTERNAL_ERROR):
        with pytest.raises(InfrastructureError):
            await _stage(_Agent(stop=stop))


async def test_the_transcript_keeps_what_the_stage_added_across_a_compaction():
    record = await _stage(_Agent(stop=StopReason.COMPLETED, replace_history=True))
    assert record.transcript[0]["type"] == "SummaryMessage"
    assert [line["content"] for line in record.transcript[1:]] == ["user: q", "assistant: done"]
    assert record.compactions == 1
    plain = await _stage(_Agent(stop=StopReason.COMPLETED))
    assert [line["content"] for line in plain.transcript] == ["user: q", "assistant: done"]
    assert plain.compactions == 0


async def test_an_empty_reply_is_scored_as_the_models_failure(toy_suite):
    result, card, _ = await _run(toy_suite, "single_agent_bare", lambda messages: "")
    assert result.record.ok                         # not an error to retry
    first = result.record.conversations[0].turns[0]
    assert first.stages[0]["stop_reason"] == "model_failure:empty_answer"
    assert card.status == "ok" and not card.passed
