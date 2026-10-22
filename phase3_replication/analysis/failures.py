"""Stored runs -> one row per failed turn, with the most specific cause the record shows.

Causes, checked in this order (the first that applies is reported):

    outputs not set      the validator found required outputs unassigned
    wrong type           an output was stored as a type JSON cannot hold
    model failure        an answering stage ended on a reply the model failed to give
                         (empty, truncated, a prompt past the window;
                         `agents.failure.classify`)
    out of steps         the answering agent stopped at its step limit
    wrong value          anything else: the outputs were set and wrong
"""

from __future__ import annotations

import pandas as pd

from evaluation.records import TurnRecord
from evaluation.store import ResultStore

CAUSES = ["outputs not set", "wrong type", "model failure", "out of steps", "wrong value"]
STEP_LIMITS = {"max_steps", "budget_exhausted"}
MODEL_FAILURE = "model_failure"     # a stage's stop reason starts with it
COLUMNS = ["arm", "model", "domain", "category", "task", "repeat", "conversation", "turn",
           "cause"]


def collect_failures(store: ResultStore) -> pd.DataFrame:
    rows = []
    for key in store.runs():
        card = store.load_scorecard(key)
        if card is None or card.status != "ok":
            continue
        run = store.load_run(key)
        turns = {c.id: c.turns for c in run.conversations}
        for verdict in card.verdicts:
            if not verdict.failed:
                continue
            turn = turns[verdict.conversation][verdict.turn - 1]
            rows.append({
                "arm": key.arm, "model": key.model, "domain": key.domain,
                "category": key.category, "task": key.task, "repeat": key.repeat,
                "conversation": verdict.conversation, "turn": verdict.turn,
                "cause": cause(turn, verdict.variables_not_set),
            })
    return pd.DataFrame(rows, columns=COLUMNS)


def cause(turn: TurnRecord, variables_not_set: bool) -> str:
    if variables_not_set:
        return "outputs not set"
    if turn.snapshot_unserialisable:
        return "wrong type"
    if any(stage.get("stop_reason", "").startswith(MODEL_FAILURE)
           for stage in turn.stages):
        return "model failure"
    if any(stage.get("stop_reason") in STEP_LIMITS
           for stage in turn.stages):
        return "out of steps"
    return "wrong value"


def cause_table(failures: pd.DataFrame) -> pd.DataFrame:
    """Failed turns per arm and cause, causes in the order above."""
    table = pd.crosstab(failures.arm, failures.cause)
    return table.reindex(columns=[c for c in CAUSES if c in table.columns])
