"""A stage: one agent run, by one role, inside the shared workspace.

The agent is the harness's (`agents.harness`). A run it ends with `MODEL_ERROR` carries the
agent's :class:`~agents.failure.Failure`: an infrastructure failure raises
`InfrastructureError` and the run is retried; the model's own ends the stage with
`stop_reason = "model_failure:<kind>"`, and the turn goes on and is scored as it stands.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from cave_agent import StopReason

from agents.failure import classify
from agents.harness import Agent
from agents.workspace import Workspace, changed
from domains import cell_time
from errors import InfrastructureError


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
            self.total_tokens + other.total_tokens,
        )

    @classmethod
    def of(cls, usage: Any) -> Usage:
        return cls(
            getattr(usage, "prompt_tokens", 0) or 0,
            getattr(usage, "completion_tokens", 0) or 0,
            getattr(usage, "total_tokens", 0) or 0,
        )


@dataclass
class StageRecord:
    role: str
    task: str            # what the stage was asked (its subtask, or the turn's query)
    budget: int          # steps it was granted
    steps: int
    stop_reason: str
    answer: str
    code: list[str]
    usage: Usage
    elapsed_s: float
    changed: list[str]   # workspace variables it created or modified
    error: str = ""      # "model_failure" stages: what the model's reply was and why
    compactions: int = 0  # times the agent's history was summarised in the stage
    # What this stage added to its agent's history, as transcript lines
    # (`agents.harness.base`); written to the transcript, not to run.json.
    transcript: list[dict[str, Any]] = field(default_factory=list, repr=False)

    def to_dict(self) -> dict[str, Any]:
        record = asdict(self)
        record.pop("transcript")
        record["elapsed_s"] = round(self.elapsed_s, 3)
        return record


async def run_stage(
    agent: Agent,
    workspace: Workspace,
    *,
    role: str,
    query: str,
    task: str,
    budget: int,
) -> StageRecord:
    before = workspace.inventory()
    # Held, not just counted: compaction replaces earlier messages, so what this stage
    # added is what was not there before (by identity, which holding them keeps unique).
    prior = list(agent.messages)
    seen = {id(message) for message in prior}
    try:
        with cell_time.outside_cell():
            response = await agent.run(query)
    except (Exception, cell_time.CellTimeLimit) as exc:
        # A time-limit signal that lands outside a cell (while a traceback is formatted)
        # escapes the runtime; it ends the run as the lab's failure, not the process.
        raise InfrastructureError(f"{role}: agent run raised {type(exc).__name__}: {exc}",
                                  kind=type(exc).__name__) from exc
    stop, error = response.stop_reason.value, ""
    if response.stop_reason in (StopReason.RUNTIME_ERROR, StopReason.INTERNAL_ERROR):
        raise InfrastructureError(f"{role}: stopped with {stop}", kind=stop)
    if response.stop_reason is StopReason.MODEL_ERROR:
        failure = agent.failure or classify(None)
        if not failure.model_fault:
            raise InfrastructureError(f"{role}: {failure.kind}: {failure.detail}",
                                      kind=failure.kind)
        stop, error = f"model_failure:{failure.kind}", failure.detail
    added = [message for message in agent.messages if id(message) not in seen]
    return StageRecord(
        role=role,
        task=task,
        budget=budget,
        steps=response.steps,
        stop_reason=stop,
        answer=response.content or "",
        code=list(response.code_snippets),
        usage=Usage.of(response.usage),
        elapsed_s=response.elapsed,
        changed=changed(before, workspace.inventory()),
        error=error,
        compactions=agent.compactions(added),
        transcript=agent.transcript(added),
    )
