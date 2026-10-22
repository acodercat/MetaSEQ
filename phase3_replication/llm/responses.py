"""Reading a reply of OpenAI's Responses API (`provider = "openai_responses"`), used by the
tool gateway (`llm.tool_gateway`).

GPT-6 Luna writes each step of an agent turn as its own output message, in a ``commentary``
phase, and only the closing message in the ``final_answer`` phase. Chat Completions returns
the final phase alone; the Responses API returns every phase, and each output message is
started on a new line here; nothing else about the text changes.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from cave_agent.models.base import TokenUsage

_REASONING_EVENTS = ("response.reasoning_text.delta", "response.reasoning_summary_text.delta")
# Responses ``incomplete_details.reason`` -> the chat finish reason cave-agent reads.
_INCOMPLETE_REASON = {"max_output_tokens": "length", "content_filter": "content_filter"}


def _separator(previous: str) -> str:
    """What goes before the next output message: a newline unless one ended the last."""
    return "" if not previous or previous.endswith("\n") else "\n"


def _join(messages: Iterable[str]) -> str:
    text = ""
    for message in messages:
        text += _separator(text) + message
    return text


def response_text(response: Any) -> tuple[str, str]:
    """A final response's text (its output messages, each on a new line) and its refusal."""
    items = [item for item in response.output if item.type == "message"]
    text = _join("".join(part.text for part in item.content if part.type == "output_text")
                 for item in items)
    refusal = "".join(part.refusal for item in items for part in item.content
                      if part.type == "refusal")
    return text, refusal


def _part(event: Any) -> tuple[int, int]:
    return (getattr(event, "output_index", 0), getattr(event, "content_index", 0))


def response_usage(response: Any) -> TokenUsage:
    """A Responses API response's token usage in cave-agent's terms."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return TokenUsage()
    prompt = usage.input_tokens or 0
    completion = usage.output_tokens or 0
    return TokenUsage(prompt, completion, usage.total_tokens or prompt + completion)


def response_finish_reason(response: Any) -> str:
    """The Chat Completions finish reason equivalent to a Responses API outcome."""
    if response.status != "incomplete":
        return "stop"
    reason = getattr(response.incomplete_details, "reason", None)
    return _INCOMPLETE_REASON.get(reason, "length")
