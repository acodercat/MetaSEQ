"""The tool harness's wire messages, in either protocol, as transcript lines
(`agents.harness.base`): a call as a turn that ran code, written as cave-agent writes one (the
step's text, then the code in a fence), its result as an execution result. Reasoning items
carry state for the next request, not text to read: only their summaries are written. A
Chat reply's reasoning (`reasoning_content`) is written before the reply it led to."""

from __future__ import annotations

from typing import Any

from agents.harness.python_tool import code_of
from llm.tool_gateway import parse_arguments

_PLAIN = {"system": "SystemMessage", "user": "UserMessage", "assistant": "AssistantMessage"}


def _ran(text: str | None, raw_arguments: str) -> str:
    code = code_of(parse_arguments(raw_arguments))
    block = f"```python\n{code}\n```" if code is not None else raw_arguments
    return f"{text}\n{block}" if text else block


def transcript_lines(message: dict[str, Any]) -> list[dict[str, Any]]:
    """One wire message (either protocol's) as transcript lines."""
    kind = message.get("type")
    if kind == "function_call":                                   # Responses
        return [{"type": "CodeExecutionMessage", "role": "assistant",
                 "content": _ran(None, message["arguments"]), "call_id": message["call_id"]}]
    if kind == "function_call_output":
        return [{"type": "ExecutionResultMessage", "role": "user",
                 "content": message["output"], "call_id": message["call_id"]}]
    if kind == "reasoning":
        summary = "\n".join(part.get("text", "") for part in message.get("summary", ()))
        return [{"type": "ReasoningMessage", "role": "assistant", "content": summary}]
    if kind == "message":
        text = "".join(part.get("text") or part.get("refusal") or ""
                       for part in message.get("content", ()))
        return [{"type": "AssistantMessage", "role": "assistant", "content": text,
                 **({"phase": message["phase"]} if message.get("phase") else {})}]
    if message.get("role") == "tool":                             # Chat
        return [{"type": "ExecutionResultMessage", "role": "user",
                 "content": message["content"], "call_id": message["tool_call_id"]}]
    if message.get("reasoning_content"):
        reasoning = {"type": "ReasoningMessage", "role": "assistant",
                     "content": message["reasoning_content"]}
        rest = {k: v for k, v in message.items() if k != "reasoning_content"}
        return [reasoning, *transcript_lines(rest)]
    if message.get("tool_calls"):
        # One line per call; the step's text goes with the first, as it preceded it.
        texts = [message.get("content")] + [None] * (len(message["tool_calls"]) - 1)
        return [{"type": "CodeExecutionMessage", "role": "assistant",
                 "content": _ran(text, call["function"]["arguments"]), "call_id": call["id"]}
                for text, call in zip(texts, message["tool_calls"], strict=True)]
    return [{"type": _PLAIN[message["role"]], "role": message["role"],
             "content": message.get("content") or ""}]
