"""Programmatic verification: validators judge a snapshot of the output variables.

Scoring always reads the snapshot, never the live runtime, so a verdict made
right after a run and one remade later from `run.json` see the same values.

The output follows AirBench's programmatic_verification.json, with one
deliberate difference: an output stored as something JSON cannot hold (a
Timestamp, an array, a frame) fails its turn, where AirBench refuses to score
it. Every output asks for a plain value, so the type is the model's error;
refusing would count the run as missing and drop it from every paired
contrast, hiding the failure.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy.exc import DBAPIError, OperationalError

from errors import InfrastructureError, TaskSpecificationError
from evaluation.records import RunRecord, Scorecard, TurnRecord, Verdict
from tasks import Task, TaskModule, Turn

_DB_RETRIES = 3
_DB_RETRY_SLEEP_S = 2.0


class SnapshotRuntime:
    """The one runtime method validators use, served from a snapshot."""

    def __init__(self, values: dict[str, Any]):
        self._values = values

    def retrieve(self, name: str) -> Any:
        if name not in self._values:
            raise KeyError(f"{name!r} is not in the snapshot; have {sorted(self._values)}")
        return self._values[name]


def unserialisable(values: dict[str, Any]) -> list[str]:
    bad = []
    for name, value in values.items():
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            bad.append(name)
    return bad


async def judge(
    validator: Callable,
    answer: str,
    values: dict[str, Any],
    turn: Turn,
    *,
    conversation: str,
    turn_number: int,
) -> Verdict:
    """Run one validator on a snapshot, retrying only on transient database errors."""
    name = getattr(validator, "__name__", repr(validator))
    for attempt in range(_DB_RETRIES):
        try:
            result = await asyncio.to_thread(validator, answer, SnapshotRuntime(values), turn)
            break
        except Exception as exc:
            if not _transient(exc):
                raise TaskSpecificationError(
                    f"validator {name} crashed: {_root_cause(exc)}"
                ) from exc
            if attempt == _DB_RETRIES - 1:
                raise InfrastructureError(
                    f"validator {name}: database unavailable ({_root_cause(exc)})"
                ) from exc
            await asyncio.sleep(_DB_RETRY_SLEEP_S)
    if not hasattr(result, "success"):
        raise TaskSpecificationError(f"validator {name} returned {type(result).__name__}")
    return Verdict(
        conversation=conversation, turn=turn_number, validator=name, status="scored",
        passed=bool(result.success),
        message=str(result.message),
        runtime_variables=values,
        variables_not_set=bool(getattr(result, "variables_not_set", False)),
    )


def _transient(exc: BaseException) -> bool:
    """A lost connection or a statement timeout, found anywhere in the cause chain.

    The driver error can sit under SQLAlchemy's `DBAPIError` (`.orig`) or, when a
    validator reads through a raw connection, directly under pandas' own
    DatabaseError, so the chain is searched for the driver's error class.

    A statement timeout counts as transient. It was once treated as a validator
    defect ("the same query times out again"), but on the full AirBench run the
    three validators that timed out while four experiment slices were querying
    the database all ran in seconds once the cache was warm.
    """
    for error in _chain(exc):
        if isinstance(error, DBAPIError):
            if error.connection_invalidated or isinstance(error, OperationalError):
                return True
            error = error.orig
        if type(error).__name__ in ("QueryCanceled", "OperationalError"):
            return True
    return False


def _chain(exc: BaseException | None) -> list[BaseException]:
    seen, out = set(), []
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        out.append(exc)
        exc = exc.__cause__ or exc.__context__
    return out


def _root_cause(exc: BaseException) -> str:
    """The innermost error's first line, e.g. the database's own message, which a
    wrapper's first line (pandas: "Execution failed on sql '") does not carry."""
    for error in reversed(_chain(exc)):
        if line := _first_line(error):
            return f"{type(error).__name__}: {line}"
    return type(exc).__name__


def _first_line(exc: BaseException) -> str:
    return str(exc).strip().splitlines()[0][:300] if str(exc).strip() else ""


async def score_run(run: RunRecord, task: Task, module: TaskModule) -> Scorecard:
    """Score a stored run, turn by turn.

    A turn that cannot be judged gets a status saying why (`TURN_STATUSES`)
    instead of a verdict; a run whose conversations no longer match the task
    gets none at all. Neither is ever counted as a failure.
    """
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    if not run.ok:
        return Scorecard(task.name, now, [], status="run_error", reason=run.error)

    specs = {c.id: c for c in task.conversations}
    verdicts = []
    for conversation in run.conversations:
        spec = specs.get(conversation.id)
        if spec is None or len(spec.turns) != len(conversation.turns):
            return Scorecard(task.name, now, [], status="conversation_changed",
                             reason=f"conversation {conversation.id!r} no longer matches the task")
        for turn_spec, turn in zip(spec.turns, conversation.turns, strict=True):
            verdicts.append(await _score_turn(conversation.id, turn_spec, turn, module))
    return Scorecard(task.name, now, verdicts)


async def _score_turn(conversation: str, spec: Turn, turn: TurnRecord,
                      module: TaskModule) -> Verdict:
    response = turn.response
    snapshot, unserialisable_names = turn.runtime_variables, turn.snapshot_unserialisable

    def unjudged(status: str, message: str) -> Verdict:
        return Verdict(conversation, turn.turn, spec.validator, status,
                       message=message, runtime_variables=snapshot)

    # An answer to a different question is not evidence about this validator.
    # (A pre-turn hook may legitimately rewrite the query.)
    if spec.pre_turn_hook is None and turn.query != spec.query:
        return unjudged("query_changed", "the task's query has changed since the run")
    if missing := [name for name in (spec.stores or ()) if name not in snapshot]:
        return unjudged("stale", f"the task now declares {missing}, not in the snapshot")
    if unserialisable_names:
        return Verdict(conversation, turn.turn, spec.validator, "scored", passed=False,
                       message=f"stored {unserialisable_names} as a type JSON cannot"
                               " hold; the task asks for plain values",
                       runtime_variables=snapshot)
    try:
        return await judge(module.validators[spec.validator], response, snapshot, spec,
                           conversation=conversation, turn_number=turn.turn)
    except TaskSpecificationError as exc:
        return unjudged("raised", str(exc))
    except InfrastructureError as exc:
        return unjudged("infra_error", str(exc))
