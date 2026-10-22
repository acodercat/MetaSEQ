"""The tool harness's one tool, ``python``: its schema, the code a call carries, and what the
model is told an execution did, in CaveAgent's words (cave-agent's internals, pinned at 0.8.0:
``_placeholders`` for empty output, persisted output and lost runtime state)."""

from __future__ import annotations

from typing import Any

from cave_agent._placeholders import (
    EMPTY_OUTPUT_PLACEHOLDER,
    PERSISTED_OUTPUT_PREFIX,
    RUNTIME_STATE_LOST_NOTICE,
    build_persist_marker,
)
from cave_agent.prompts import SECURITY_ERROR_PROMPT
from cave_agent.runtime import ExecutionResult, Runtime
from cave_agent.security import SecurityError
from cave_agent.utils import sanitize_surrogates

from llm.tool_gateway import ToolSpec

_CODE = "code"

PYTHON = ToolSpec(
    name="python",
    description=(
        "Run Python in the task's persistent runtime and return what it printed or displayed, "
        "or the error it raised. Every call runs in the same session: variables, imports and "
        "loaded tables from earlier calls remain available."
    ),
    parameters={
        "type": "object",
        "properties": {_CODE: {"type": "string", "description": "The Python code to execute."}},
        "required": [_CODE],
        "additionalProperties": False,
    },
)

# The reply to a call whose arguments hold no code to run. It says so, so that the model
# cannot read an unexecuted call as a silent success.
BAD_ARGUMENTS = "The arguments were not a JSON object with a string `code` field. Nothing ran."


def code_of(arguments: dict[str, Any] | None) -> str | None:
    """The code a call's parsed *arguments* carry; ``None`` when they carry none."""
    value = (arguments or {}).get(_CODE)
    return value if isinstance(value, str) else None


async def execution_output(runtime: Runtime, result: ExecutionResult, *, max_chars: int,
                           preview_chars: int) -> str:
    """The tool result for a finished execution, in CaveAgent's words. Output longer than
    *max_chars* is kept in a runtime variable and previewed."""
    if not result.success and isinstance(result.error, SecurityError):
        return SECURITY_ERROR_PROMPT.format(error=result.error.message)
    if not result.success and not result.stdout and result.error is not None:
        output = f"{type(result.error).__name__}: {result.error}"
    else:
        output = result.stdout or EMPTY_OUTPUT_PLACEHOLDER
    output = sanitize_surrogates(output)
    if len(output) > max_chars:
        variable = await runtime.bind_unique(PERSISTED_OUTPUT_PREFIX, output)
        output = build_persist_marker(output, preview_chars, variable)
    return f"{output}\n\n{RUNTIME_STATE_LOST_NOTICE}" if result.state_lost else output
