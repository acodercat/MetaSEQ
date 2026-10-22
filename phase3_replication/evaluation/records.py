"""What a run leaves on disk, in AirBench's shapes.

    run.json                          the trajectory: `benchmark`, a `run` block
                                      (experiment, arm, model, repeat, status),
                                      `cost`, then `conversations[].turns[]` with
                                      each turn's query, response, cost, stages and
                                      `runtime_variables` snapshot. States no verdict.
    programmatic_verification.json    the validators' verdicts, shaped like the
                                      run.json they were formed from: `benchmark`,
                                      a `scoring` block, then `conversations[].turns[]`
                                      at the same conversation `id` and 1-based `turn`.
                                      Reproducible from run.json and the task's
                                      validators alone (`metaseq score`), so a
                                      validator fix never costs a model call.

Both carry `schema`; readers refuse a version they do not know.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:       # a record module depends on nothing of the lab's at run time
    from agents.harness import HarnessName

SCHEMA = 2

# A turn's PV status. Only "scored" carries a verdict; the others say why the
# turn could not be judged, and are reported as missing coverage, never as
# failures (AirBench's vocabulary).
#   scored         the validator ran on the snapshot
#   query_changed  the task asks something else now than the agent was asked
#   stale          the task now declares an output the snapshot does not hold
#   raised         the validator crashed (a task defect)
#   infra_error    the validator's database was unavailable (retry with `score`)
TURN_STATUSES = ("scored", "query_changed", "stale", "raised", "infra_error")


@dataclass
class Cost:
    steps: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    elapsed_s: float = 0.0

    def __add__(self, other: Cost) -> Cost:
        return Cost(
            self.steps + other.steps,
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
            self.total_tokens + other.total_tokens,
            self.elapsed_s + other.elapsed_s,
        )

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "elapsed_s": round(self.elapsed_s, 3)}


@dataclass
class TurnRecord:
    turn: int                       # 1-based within its conversation
    query: str
    response: str = ""
    cost: Cost = field(default_factory=Cost)
    # The registered output variables after the turn, as the validators see them.
    runtime_variables: dict[str, Any] = field(default_factory=dict)
    # Names whose value JSON cannot represent; stored as repr, so a rescore
    # from this file would judge a string instead of the object.
    snapshot_unserialisable: list[str] = field(default_factory=list)
    coordination: dict[str, Any] | None = None   # the topology's plan/spec/decisions
    stages: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None        # infrastructure failure; the turn did not complete

    def to_dict(self) -> dict[str, Any]:
        record = asdict(self)
        record["cost"] = self.cost.to_dict()
        record["runtime_variables"] = _string_keys(record["runtime_variables"])
        if isinstance(record.get("coordination"), dict):
            record["coordination"] = _string_keys(record["coordination"])
        return {k: v for k, v in record.items()
                if v not in (None, [], {}) or k == "runtime_variables"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TurnRecord:
        return cls(**{**data, "cost": Cost(**data.get("cost", {}))})


@dataclass
class ConversationRecord:
    id: str
    turns: list[TurnRecord]
    transcript: str | None = None   # path relative to the run directory

    def to_dict(self) -> dict[str, Any]:
        record = {"id": self.id, "turns": [t.to_dict() for t in self.turns]}
        if self.transcript:
            record["transcript"] = self.transcript
        return record

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversationRecord:
        return cls(
            id=data["id"],
            turns=[TurnRecord.from_dict(t) for t in data["turns"]],
            transcript=data.get("transcript"),
        )


@dataclass
class RunRecord:
    experiment: str
    suite: str
    domain: str
    category: str
    task: str
    arm: dict[str, Any]
    model: dict[str, Any]
    repeat: int
    started_at: str
    finished_at: str
    conversations: list[ConversationRecord]
    error: str | None = None
    protocol: str | None = None     # None: made before runs recorded it
    # What failed (`agents.failure.Failure` kinds, or "harness" for a lab error, a name kept
    # from before the `harness` field below, which it has nothing to do with);
    # None when the run is ok or was recorded before kinds were kept.
    error_kind: str | None = None
    code: dict[str, Any] | None = None    # the lab's commit and dirty flag
    harness: HarnessName = "tool"   # how code reached the runtime (`agents.harness`)

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def cost(self) -> Cost:
        total = Cost()
        for conversation in self.conversations:
            for turn in conversation.turns:
                total = total + turn.cost
        return total

    def to_dict(self) -> dict[str, Any]:
        turns = sum(len(c.turns) for c in self.conversations)
        return {
            "schema": SCHEMA,
            "benchmark": self.task,
            "run": {
                "experiment": self.experiment,
                "suite": self.suite,
                "domain": self.domain,
                "category": self.category,
                "arm": self.arm,
                "protocol": self.protocol,
                **({"code": self.code} if self.code else {}),
                "harness": self.harness,
                "model": self.model,
                "repeat": self.repeat,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "status": "ok" if self.ok else "error",
                **({"error": self.error, "error_kind": self.error_kind} if self.error else {}),
            },
            "cost": {"turns": turns, **self.cost.to_dict()},
            "conversations": [c.to_dict() for c in self.conversations],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunRecord:
        _check_schema(data)
        run = data["run"]
        return cls(
            experiment=run["experiment"],
            suite=run["suite"],
            domain=run["domain"],
            category=run["category"],
            task=data["benchmark"],
            arm=run["arm"],
            model=run["model"],
            repeat=run["repeat"],
            started_at=run["started_at"],
            finished_at=run["finished_at"],
            conversations=[ConversationRecord.from_dict(c) for c in data["conversations"]],
            error=run.get("error"),
            protocol=run.get("protocol"),
            error_kind=run.get("error_kind"),
            code=run.get("code"),
            harness=run["harness"],
        )


@dataclass
class Verdict:
    """One turn of programmatic_verification.json."""

    conversation: str
    turn: int
    validator: str
    status: str                     # one of TURN_STATUSES
    passed: bool = False            # meaningful only when status == "scored"
    message: str = ""
    runtime_variables: dict[str, Any] = field(default_factory=dict)
    variables_not_set: bool = False

    @property
    def scored(self) -> bool:
        return self.status == "scored"

    @property
    def failed(self) -> bool:
        return self.scored and not self.passed

    def to_dict(self) -> dict[str, Any]:
        record = {"turn": self.turn, "validator": self.validator,
                  "runtime_variables": self.runtime_variables, "status": self.status}
        if self.scored:
            record["success"] = self.passed
        if self.message:
            record["message"] = self.message
        if self.variables_not_set:
            record["variables_not_set"] = True
        return record


@dataclass
class Scorecard:
    """programmatic_verification.json for one run.

    `status` is the run-level gate: "ok" when the turns could be matched to the
    task (they then carry their own statuses), otherwise the reason none could
    be ("run_error", "conversation_changed") with no turns.
    """

    benchmark: str
    scored_at: str
    verdicts: list[Verdict]
    status: str = "ok"
    reason: str | None = None

    @property
    def passed(self) -> bool:
        """Task-level outcome: every turn scored and passed."""
        return self.outcome == "passed"

    @property
    def outcome(self) -> str:
        """passed / failed / refused.

        A failed scored turn fails the task even if another turn could not be
        judged: that failure is known. Only when nothing failed and some turn
        (or the whole run) could not be judged is the task refused -- reported
        as missing, never as a failure.
        """
        if self.status != "ok" or not self.verdicts:
            return "refused"
        if any(v.failed for v in self.verdicts):
            return "failed"
        return "passed" if all(v.scored for v in self.verdicts) else "refused"

    def to_dict(self) -> dict[str, Any]:
        scoring = {"status": self.status}
        if self.reason:
            scoring["reason"] = self.reason
        scoring.update({
            "scored_at": self.scored_at,
            "outcome": self.outcome,
            "turns": len(self.verdicts),
            "scored": sum(v.scored for v in self.verdicts),
            "passed": sum(v.scored and v.passed for v in self.verdicts),
            "failed": sum(v.failed for v in self.verdicts),
        })
        conversations: dict[str, list[dict[str, Any]]] = {}
        for verdict in self.verdicts:
            conversations.setdefault(verdict.conversation, []).append(verdict.to_dict())
        return {
            "schema": SCHEMA,
            "benchmark": self.benchmark,
            "scoring": scoring,
            "conversations": [{"id": cid, "turns": turns} for cid, turns in conversations.items()],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scorecard:
        _check_schema(data)
        scoring = data["scoring"]
        verdicts = [
            Verdict(
                conversation=conversation["id"],
                turn=turn["turn"],
                validator=turn["validator"],
                status=turn["status"],
                passed=bool(turn.get("success", False)),
                message=turn.get("message", ""),
                runtime_variables=turn.get("runtime_variables", {}),
                variables_not_set=bool(turn.get("variables_not_set", False)),
            )
            for conversation in data["conversations"]
            for turn in conversation["turns"]
        ]
        return cls(
            benchmark=data["benchmark"],
            scored_at=scoring["scored_at"],
            verdicts=verdicts,
            status=scoring["status"],
            reason=scoring.get("reason"),
        )


def _check_schema(data: dict[str, Any]) -> None:
    if data.get("schema") != SCHEMA:
        raise ValueError(f"unsupported record schema {data.get('schema')!r} (expected {SCHEMA})")


def _string_keys(value: Any) -> Any:
    """`value` with every mapping key JSON can hold: a key it cannot (a tuple from a groupby,
    a numpy integer, a Timestamp) is written as its repr; one it can is left for `json` to
    write. Values are left to `write_json`'s fallback."""
    if isinstance(value, dict):
        return {(k if k is None or isinstance(k, (str, int, float)) else repr(k)): _string_keys(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_string_keys(v) for v in value]
    return value


def write_json(path: Path, document: dict[str, Any]) -> None:
    """Atomically: a crash mid-write must not leave a half file that resume trusts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(document, indent=2, ensure_ascii=False, default=_bounded_repr)
                   + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bounded_repr(value: Any) -> str:
    """A value JSON cannot hold, as text (AirBench's `_json_fallback`)."""
    text = repr(value)
    return text if len(text) <= 2000 else text[:2000] + "…[truncated]"
