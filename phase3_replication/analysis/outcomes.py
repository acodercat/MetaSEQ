"""Stored runs -> one row per (arm, model, task, repeat)."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from analysis.failures import MODEL_FAILURE, STEP_LIMITS
from evaluation.records import RunRecord
from evaluation.store import ResultStore


@dataclass
class Outcome:
    arm: str
    topology: str                 # as the run recorded it
    model: str
    domain: str
    category: str
    task: str
    repeat: int
    # "scored" rows carry a verdict; "unscored" (no verdict file), "refused"
    # (no turn failed and some could not be judged) and "error" rows are
    # reported as missing coverage, never as failures.
    status: str
    passed: bool | None
    turns_passed: int
    turns: int
    steps: int
    total_tokens: int
    elapsed_s: float
    run_turns: int                # turns the run completed (scored or not)
    protocol: str                 # the fingerprint the run was made under
    coordinator_fallback_turns: int   # fixed_roles: turns planned by the default plan
    step_limit_turns: int         # turns where an answering stage hit its step cap
    model_failure_turns: int      # turns where an answering stage ended on a model failure
    compactions: int              # times an agent's history was summarised, all stages
    failed_attempts: int          # attempts that failed before this run (attempts.jsonl)


def collect(store: ResultStore) -> pd.DataFrame:
    rows = []
    for key in store.runs():
        run = store.load_run(key)
        card = store.load_scorecard(key)
        if not run.ok:
            status = "error"
        elif card is None:
            status = "unscored"
        else:
            status = "refused" if card.outcome == "refused" else "scored"
        scored = status == "scored"
        cost = run.cost
        rows.append(Outcome(
            arm=key.arm, topology=run.arm.get("topology", ""), model=key.model,
            domain=key.domain, category=key.category,
            task=key.task, repeat=key.repeat,
            status=status,
            passed=card.passed if scored else None,
            turns_passed=sum(v.scored and v.passed for v in card.verdicts) if scored else 0,
            turns=len(card.verdicts) if scored else 0,
            steps=cost.steps,
            total_tokens=cost.total_tokens,
            elapsed_s=cost.elapsed_s,
            run_turns=sum(len(c.turns) for c in run.conversations),
            protocol=run.protocol or "",
            coordinator_fallback_turns=_sum(run, lambda c: c.get("kind") == "fixed_roles"
                                            and bool(c.get("fallback"))),
            step_limit_turns=sum(any(s["stop_reason"] in STEP_LIMITS for s in t.stages)
                                 for c in run.conversations for t in c.turns),
            model_failure_turns=sum(any(s["stop_reason"].startswith(MODEL_FAILURE)
                                        for s in t.stages)
                                    for c in run.conversations for t in c.turns),
            compactions=sum(s.get("compactions", 0) for c in run.conversations
                            for t in c.turns for s in t.stages),
            failed_attempts=store.attempts(key),
        ))
    columns = list(Outcome.__dataclass_fields__)
    return pd.DataFrame([asdict(r) for r in rows], columns=columns)


def _sum(run: RunRecord, of) -> int:
    """A per-turn coordination figure, summed over the run."""
    return sum(of(t.coordination) for c in run.conversations for t in c.turns if t.coordination)
