"""Why an agent's run ended without an answer, and whose failure that was.

A run that ends with `MODEL_ERROR` is one of two things, and they are scored differently. A
provider or transport failure (an outage, a timeout, a stalled stream, a gateway error, the
gateway's content check blocking an output) says nothing about the model: the stage raises
`InfrastructureError` and the run is retried. A reply the model gave that cannot serve as one
(empty, truncated beyond recovery, a prompt it grew past the window) is the model's: the stage
ends with `stop_reason = "model_failure:<kind>"`, the turn goes on, and it is scored as it
stands. Every agent reports the cause as a :class:`Failure` (`agents.harness.Agent`).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from cave_agent.models.errors import (
    PromptTooLongError,
    ProviderBillingError,
    ProviderError,
    StreamStalledError,
)


@dataclass(frozen=True)
class Failure:
    kind: str           # empty_answer, truncated, prompt_too_long, content_filter, provider, ...
    model_fault: bool   # the model's own failure (scored), not the infrastructure's (retried)
    detail: str


# The texts are cave-agent's own (cave_agent/agent.py), which names these cases only in the
# message of the `ProviderError` it logs. First the model's replies that cannot serve as one.
EMPTY_ANSWER = Failure("empty_answer", True, "The model completed without returning an answer.")
TRUNCATED = Failure("truncated", True, "Model output was truncated and could not be recovered")
# The provider's filter: with nothing to show for it, or withdrawing what it had sent.
FILTERED = Failure("content_filter", False,
                   "The provider filtered this response and returned no content.")
WITHDRAWN = Failure("content_filter", False,
                    "The provider filtered this response after partially streaming it.")
_MODEL_FAILURES = ((EMPTY_ANSWER.detail, EMPTY_ANSWER), (TRUNCATED.detail, TRUNCATED))
# The gateway's content check blocking an output: a provider rule misfiring on air-quality
# analysis, not a measure of the model, and met more often by arms that make more calls.
_CONTENT_CHECK = ("filtered this response", "inappropriate content")
# A prompt past the window in words cave-agent does not know: DashScope's "Range of input
# length should be [1, N]".
_PROMPT_TOO_LONG = ("Range of input length should be",)


def classify(error: BaseException | None) -> Failure:
    """The failure a model-layer error (cave-agent's typed `ModelError`s) stands for."""
    detail = "no cause recorded" if error is None else f"{type(error).__name__}: {error}"
    if isinstance(error, PromptTooLongError):
        return Failure("prompt_too_long", True, detail)
    if isinstance(error, StreamStalledError):
        return Failure("stream_stalled", False, detail)
    if isinstance(error, ProviderBillingError):
        return Failure("billing", False, detail)
    if isinstance(error, ProviderError):
        text = str(error)
        if any(phrase in text for phrase in _PROMPT_TOO_LONG):
            return Failure("prompt_too_long", True, detail)
        if any(phrase in text for phrase in _CONTENT_CHECK):
            return replace(FILTERED, detail=detail)
        for phrase, failure in _MODEL_FAILURES:
            if phrase in text:
                return replace(failure, detail=detail)
        return Failure("provider", False, detail)
    return Failure("unknown" if error is None else type(error).__name__, False, detail)
