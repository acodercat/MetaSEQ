"""The six-arm study analysis that wrote results/report/study_*.csv.

It ran in the study repository's layout (run records under results/reliability_tool/, arms under
their working names); on the deposited records, set `settings.results_dir` and the arm names
accordingly. `analysis/bayes.py`, the registered primary model, reads study_outcomes.csv directly.

Original docstring follows.
"""
"""The study's analysis (`reliability_tool`, docs/deviations.md §18), on the frozen verdicts.

    uv run python -m analysis.study            -> results/reliability_tool/report/study.md

(+ CSVs beside it.) Infrastructure comes first: every arm's run and turn statuses, stage stop
reasons, and any stratum (model x arm x category) with no passing run. Then the 2 x 2 of
decomposition x verification (the contrasts of docs/preregistration.md §4-5), per backbone and
pooled, and the planned delegation without and with the verifier.

Contrasts pair runs on (task, repeat) scored in both arms. Intervals resample tasks, so a
task's repeats move together (10,000 draws, seed 20260929, percentile 95%); p is the
bootstrap's two-sided tail at zero, Holm-corrected over the four core contrasts. The
Bayesian model of §5 is fitted separately from `study_outcomes.csv`.
"""

from __future__ import annotations

import json
import math
import re
import sys
import tomllib
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from analysis.failures import cause_table, collect_failures
from analysis.outcomes import collect
from analysis.stats import mcnemar_exact
from domains.beijing import conventions as beijing_conventions
from domains.hk import conventions as hk_conventions
from evaluation.records import Scorecard, read_json
from evaluation.store import PV_FILE, ResultStore
from settings import PROJECT_ROOT, settings

EXPERIMENT = "reliability_tool"
DRAWS, SEED = 10_000, 20260929
A, B, C, D, E = ("single_agent_bare", "single_agent_verified", "neuroair_no_verification",
                 "neuroair", "neuroair_published")
TEXT, CODE, EVIDENCE = ("single_agent_conventions_text", "single_agent_conventions_code",
                        "single_agent_verified_evidence")
G = f"{A}_vote"
# Exploratory, both backbones (docs/deviations.md §13, §17): decomposition made at run time,
# without and with the verifier.
F, FV = "multi_agent_delegation_planned", "multi_agent_delegation_verified"
TWINS = {"single_agent": A, "single_agent_verified_rules": B,
         "neuroair_no_verification_rules": C, "neuroair_rules": D}
REGISTERED = [A, B, C, D, *TWINS, E]
EXPLORATORY = [TEXT, CODE, EVIDENCE]
CORE = [("H1", D, A), ("H2a", B, A), ("H2b", C, A), ("H2c", D, B)]
FLASH = "deepseek-v4-flash"
# The (model, task, repeat) runs whose final outputs the first frozen pass left at infra_error
# and which were rescored before it was archived (docs/deviations.md §8), per store:
# `results/_frozen/<experiment>/`. Pre-registration §5 read strictly would drop their task and
# repeat from every arm of that model.
RESCORED_FILE = "rescored_in_pass1.json"
LIBRARY = [f.__name__ for f in hk_conventions.CONVENTIONS + beijing_conventions.CONVENTIONS]
_CALL = re.compile(r"(?<!def )\b(" + "|".join(LIBRARY) + r")\(")


# --- statistics -------------------------------------------------------------------------

def bootstrap(matrix: np.ndarray, statistic: Callable[[np.ndarray], float],
              draws: int = DRAWS, seed: int = SEED) -> tuple[float, float, float]:
    """95% percentile interval of `statistic` with the rows (tasks) resampled, and the
    two-sided bootstrap p-value at zero."""
    n = len(matrix)
    if n == 0:
        return math.nan, math.nan, math.nan
    rng = np.random.default_rng(seed)
    values = np.array([statistic(matrix[rng.integers(0, n, n)]) for _ in range(draws)])
    lo, hi = np.percentile(values, [2.5, 97.5])
    p = min(1.0, 2 * min((values <= 0).mean(), (values >= 0).mean()))
    return float(lo), float(hi), float(p)


def holm(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted, running = [0.0] * len(p_values), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(p_values) - rank) * p_values[i]))
        adjusted[i] = running
    return adjusted


def _mean_diff(m: np.ndarray) -> float:
    return float(m[:, 0].mean())


def _cost_diff(m: np.ndarray) -> float:
    """Tokens per correct task, treatment minus control; columns tokens_t, correct_t,
    tokens_c, correct_c."""
    return m[:, 0].sum() / m[:, 1].sum() - m[:, 2].sum() / m[:, 3].sum()


# --- pairing ----------------------------------------------------------------------------

def paired(outcomes: pd.DataFrame, arms: list[str], tasks=None, exclude=(),
           values=("passed", "total_tokens")) -> pd.DataFrame:
    """One row per (model, task, repeat) scored in every one of `arms`, with `values` per arm;
    `exclude` drops (model, task, repeat) runs from every arm. Runs pair within a model only.
    A per-task figure (`groupby(level="task")`) averages over the repeats and the models, so
    a task's runs move together when tasks are resampled."""
    scored = outcomes[(outcomes.status == "scored") & outcomes.arm.isin(arms)]
    if tasks is not None:
        scored = scored[scored.task.isin(tasks)]
    if exclude:
        dropped = pd.MultiIndex.from_tuples([tuple(e) for e in exclude])
        key = pd.MultiIndex.from_frame(scored[["model", "task", "repeat"]])
        scored = scored[~key.isin(dropped)]
    wide = scored.pivot_table(index=["model", "task", "repeat"], columns="arm",
                              values=list(values), aggfunc="first")
    return wide.dropna().astype(float)


def contrast(outcomes: pd.DataFrame, name: str, treatment: str, control: str,
             tasks=None, exclude=()) -> dict:
    """Treatment minus control: accuracies and their difference weight each task equally."""
    pairs = paired(outcomes, [treatment, control], tasks, exclude)
    t, c = pairs["passed"][treatment], pairs["passed"][control]
    per_task = (t - c).groupby(level="task").mean()
    lo, hi, p = bootstrap(per_task.to_numpy()[:, None], _mean_diff)
    recovered, regressed = int(((c == 0) & (t == 1)).sum()), int(((c == 1) & (t == 0)).sum())
    return {"contrast": name, "treatment": treatment, "control": control,
            "tasks": per_task.size, "pairs": len(pairs),
            "control_acc": c.groupby(level="task").mean().mean(),
            "treatment_acc": t.groupby(level="task").mean().mean(),
            "delta_pp": 100 * per_task.mean(), "lo_pp": 100 * lo, "hi_pp": 100 * hi,
            "p": p, "recovered": recovered, "regressed": regressed,
            "mcnemar_p": mcnemar_exact(recovered, regressed)}


def pooled_contrast(outcomes: pd.DataFrame, name: str, pairs: dict[str, str],
                    tasks=None, exclude=()) -> dict:
    """The mean of several treatment-minus-control differences (each treatment: control in
    `pairs`), on the (task, repeat) pairs scored in every arm involved."""
    rows = paired(outcomes, [*pairs, *pairs.values()], tasks, exclude)
    wide = rows["passed"].groupby(level="task").mean()
    treatments, controls = wide[list(pairs)].mean(axis=1), wide[list(pairs.values())].mean(axis=1)
    per_task = treatments - controls
    lo, hi, p = bootstrap(per_task.to_numpy()[:, None], _mean_diff)
    return {"contrast": name, "treatment": " + ".join(pairs), "control": " + ".join(pairs.values()),
            "tasks": per_task.size, "pairs": len(rows),
            "control_acc": controls.mean(), "treatment_acc": treatments.mean(),
            "delta_pp": 100 * per_task.mean(), "lo_pp": 100 * lo, "hi_pp": 100 * hi,
            "p": p, "recovered": None, "regressed": None, "mcnemar_p": None}


def cost_contrast(outcomes: pd.DataFrame, treatment: str, control: str, tasks=None,
                  exclude=()) -> dict:
    """Tokens per correct task in each arm on their paired runs, and the difference."""
    pairs = paired(outcomes, [treatment, control], tasks, exclude)
    per_task = pd.DataFrame({
        "tokens_t": pairs["total_tokens"][treatment], "correct_t": pairs["passed"][treatment],
        "tokens_c": pairs["total_tokens"][control], "correct_c": pairs["passed"][control],
    }).groupby(level="task").sum()
    m = per_task.to_numpy()
    lo, hi, _ = bootstrap(m, _cost_diff)
    return {"treatment": treatment, "control": control, "tasks": len(m),
            "treatment_per_correct": m[:, 0].sum() / m[:, 1].sum(),
            "control_per_correct": m[:, 2].sum() / m[:, 3].sum(),
            "difference": _cost_diff(m), "lo": lo, "hi": hi}


def factorial(outcomes: pd.DataFrame, tasks=None, exclude=()) -> list[dict]:
    """The 2x2's main effects and interaction, per task on the four arms' paired runs, and
    H2's test: verification's main effect minus decomposition's, which in the balanced 2x2
    is B - C."""
    pairs = paired(outcomes, [A, B, C, D], tasks, exclude)["passed"].groupby(level="task").mean()
    m = pairs[[A, B, C, D]].to_numpy()
    effects = {
        "verification": lambda x: ((x[:, 1] - x[:, 0]) + (x[:, 3] - x[:, 2])).mean() / 2,
        "decomposition": lambda x: ((x[:, 2] - x[:, 0]) + (x[:, 3] - x[:, 1])).mean() / 2,
        "interaction": lambda x: ((x[:, 3] - x[:, 2]) - (x[:, 1] - x[:, 0])).mean(),
        "H2: verification − decomposition (= B − C)": lambda x: (x[:, 1] - x[:, 2]).mean(),
    }
    rows = []
    for name, effect in effects.items():
        lo, hi, p = bootstrap(m, effect)
        rows.append({"effect": name, "tasks": len(m), "estimate_pp": 100 * effect(m),
                     "lo_pp": 100 * lo, "hi_pp": 100 * hi, "p": p})
    return rows


def verifier_change(outcomes: pd.DataFrame, treatment: str, control: str) -> list[dict]:
    """Turns fixed and broken per run, treatment minus control, on paired runs (E4)."""
    pairs = paired(outcomes, [treatment, control],
                   values=("verifier_fixed_turns", "verifier_broke_turns"))
    rows = []
    for label, column in (("fixed", "verifier_fixed_turns"), ("broken", "verifier_broke_turns")):
        t = pairs[column][treatment].groupby(level="task").mean()
        c = pairs[column][control].groupby(level="task").mean()
        lo, hi, p = bootstrap((t - c).to_numpy()[:, None], _mean_diff)
        rows.append({"measure": f"turns {label} per run", "tasks": t.size, "pairs": len(pairs),
                     "treatment": t.mean(), "control": c.mean(), "difference": (t - c).mean(),
                     "lo": lo, "hi": hi, "p": p})
    return rows


# --- per-run facts the outcome table does not carry -------------------------------------

def run_facts(store: ResultStore) -> pd.DataFrame:
    rows = []
    for key in store.runs():
        run = store.load_run(key)
        card = store.load_scorecard(key)
        before = store.load_scorecard(key, before=True)
        evidence = run.arm.get("verifier") == "evidence"
        stops, agreeing, changed, reported, calls, library_errors = Counter(), 0, 0, 0, 0, 0
        for conversation in run.conversations:
            for turn in conversation.turns:
                stops.update(f"{s.get('role')}:{s.get('stop_reason')}" for s in turn.stages)
                coordination = turn.coordination or {}
                agreeing += coordination.get("issues_agreeing_with_stored", 0)
                changed += len(coordination.get("outputs_changed_by_verifier", []))
                # A usable report with at least one entry, before the entries the stored
                # value agrees with are filtered out.
                reported += evidence and not coordination.get("malformed_reviews") and (
                    len(coordination.get("issues", []))
                    + coordination.get("issues_agreeing_with_stored", 0)) > 0
        if run.arm.get("conventions") == "code":
            calls, library_errors = _library_use(store.path(key))
        turn_statuses = Counter(v.status for v in card.verdicts) if card else Counter()
        before_statuses = Counter(v.status for v in before.verdicts) if before else Counter()
        after = {(v.conversation, v.turn): v.scored for v in card.verdicts} if card else {}
        judged_twice = sum(v.scored and after.get((v.conversation, v.turn), False)
                           for v in (before.verdicts if before else []))
        rows.append({"arm": key.arm, "model": key.model, "task": key.task,
                     "repeat": key.repeat,
                     "evidence_agreeing_entries": agreeing,
                     "outputs_changed_by_verifier": changed,
                     "library_calls": calls, "library_errors": library_errors,
                     "judged_twice": judged_twice, "reported_turns": reported,
                     "stops": dict(stops), "turn_statuses": dict(turn_statuses),
                     "before_statuses": dict(before_statuses),
                     "scorecard_status": card.status if card else "none"})
    return pd.DataFrame(rows)


def _library_use(run_dir: Path) -> tuple[int, int]:
    """Calls of library functions in the agent's code, and execution errors naming one."""
    calls = errors = 0
    for transcript in (run_dir / "transcripts").glob("*.jsonl"):
        for line in transcript.read_text(encoding="utf-8").splitlines():
            message = json.loads(line)
            content = str(message.get("content", ""))
            if message.get("type") == "CodeExecutionMessage":
                calls += len(_CALL.findall(content))
            elif message.get("type") == "ExecutionResultMessage" and (
                    "Error" in content or "Traceback" in content) and _CALL.search(content):
                errors += 1
    return calls, errors


def vote_outcomes(store: ResultStore, outcomes: pd.DataFrame) -> pd.DataFrame:
    """G's rows: its verdict per task; its tokens, the voted repeats' sum."""
    tokens = outcomes[outcomes.arm == A].groupby(["model", "task"]).total_tokens.sum()
    rows = []
    for path in sorted(store.root.glob(f"*/*/*/{G}/*/r1/{PV_FILE}")):
        card = Scorecard.from_dict(read_json(path))
        task, model = path.parents[3].name, path.parents[1].name
        rows.append({"arm": G, "model": model, "domain": path.parents[5].name,
                     "category": path.parents[4].name, "task": task, "repeat": 1,
                     "status": "scored" if card.outcome != "refused" else "refused",
                     "passed": card.passed, "total_tokens": int(tokens.get((model, task), 0)),
                     "turn_statuses": dict(Counter(v.status for v in card.verdicts))})
    return pd.DataFrame(rows)


# --- tables -----------------------------------------------------------------------------

def _scored(outcomes: pd.DataFrame) -> pd.DataFrame:
    return outcomes[outcomes.status == "scored"].astype({"passed": bool})


def arm_rows(outcomes: pd.DataFrame, arms: list[str]) -> list[dict]:
    rows = []
    for arm in arms:
        cell = outcomes[outcomes.arm == arm]
        scored = _scored(cell)
        k, n = int(scored.passed.sum()), len(scored)
        lo, hi, _ = bootstrap(scored.groupby("task").passed.mean().to_numpy()[:, None],
                              _mean_diff)
        per_task = scored.groupby("task").passed.agg(["sum", "count"])
        full = per_task[per_task["count"] == 3]
        rows.append({
            "arm": arm, "runs": len(cell), "scored": n, "passed": k,
            "accuracy": k / n if n else math.nan, "acc_lo": lo, "acc_hi": hi,
            "consistent_tasks": int(((full["sum"] == 0) | (full["sum"] == 3)).sum()),
            "tasks_with_3": len(full), "majority_tasks": int((full["sum"] >= 2).sum()),
            "mean_tokens": scored.total_tokens.mean(),
            "tokens_per_correct": scored.total_tokens.sum() / k if k else math.nan,
            "answer_cap_turns": int(cell.step_limit_turns.sum()),
            # Absent from runs recorded before 2026-10-06 (the 20-step archive): 0.
            "model_failure_turns": int(cell.get("model_failure_turns", pd.Series(dtype=int)).sum()),
            "compactions": int(cell.get("compactions", pd.Series(dtype=int)).sum()),
            "failed_attempts": int(cell.get("failed_attempts", pd.Series(dtype=int)).sum()),
        })
    return rows


def _table(rows: list[dict], columns: dict[str, Callable | str]) -> list[str]:
    """Markdown rows; each column is a key of the row or a function of it."""
    head = "| " + " | ".join(columns) + " |"
    rule = "|" + "---|" * len(columns)
    body = []
    for row in rows:
        cells = [f(row) if callable(f) else str(row[f]) for f in columns.values()]
        body.append("| " + " | ".join(cells) + " |")
    return [head, rule, *body, ""]


def _pp(row: dict, key: str = "delta_pp") -> str:
    return f"{row[key]:+.1f} [{row['lo_pp']:+.1f}, {row['hi_pp']:+.1f}]"


def _accuracy(row: dict) -> str:
    return (f"{100 * row['accuracy']:.1f}%"
            f" ({100 * row['acc_lo']:.1f}–{100 * row['acc_hi']:.1f})")


def _p(value: float, floor: float = 2 / DRAWS) -> str:
    """A bootstrap p; zero means no draw fell on the other side, so below its resolution."""
    return f"<{floor:.2g}" if value == 0 else f"{value:.3g}"


def _maybe(value, spec: str) -> str:
    return "—" if value is None else format(value, spec)


CONTRAST_COLUMNS = {
    "contrast": "contrast", "treatment vs control": lambda r: f"{r['treatment']} vs {r['control']}",
    "tasks / pairs": lambda r: f"{r['tasks']} / {r['pairs']}",
    "accuracy c → t": lambda r: f"{100 * r['control_acc']:.1f}% → {100 * r['treatment_acc']:.1f}%",
    "Δ pp [95% CI]": _pp, "p (bootstrap)": lambda r: _p(r["p"]),
    "recovered / regressed": lambda r: f"{_maybe(r['recovered'], 'd')} / "
                                       f"{_maybe(r['regressed'], 'd')}",
    "McNemar p": lambda r: _maybe(r["mcnemar_p"], ".3g"),
}
EFFECT_COLUMNS = {"effect": "effect", "tasks": "tasks",
                  "estimate pp [95% CI]": lambda r: _pp(r, "estimate_pp"),
                  "p (bootstrap)": lambda r: _p(r["p"])}
COST_COLUMNS = {
    "treatment vs control": lambda r: f"{r['treatment']} vs {r['control']}",
    "tasks": "tasks",
    "tokens per correct (t / c)": lambda r: f"{r['treatment_per_correct']:,.0f} / "
                                            f"{r['control_per_correct']:,.0f}",
    "t − c [95% CI]": lambda r: f"{r['difference']:+,.0f} [{r['lo']:+,.0f}, {r['hi']:+,.0f}]",
}


def task_sets() -> dict[str, list[str]]:
    path = PROJECT_ROOT / "configs" / "task_sets" / "convention_audit.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))


ARM_COLUMNS = {
    "arm": "arm", "passed / scored": lambda r: f"{r['passed']}/{r['scored']}",
    "accuracy [95% CI, tasks resampled]": _accuracy,
    "same outcome ×3": lambda r: f"{r['consistent_tasks']}/{r['tasks_with_3']}",
    "majority of 3": lambda r: f"{r['majority_tasks']}/{r['tasks_with_3']}",
    "mean tokens": lambda r: f"{r['mean_tokens']:,.0f}",
    "tokens per correct": lambda r: f"{r['tokens_per_correct']:,.0f}",
    "answering stage at step cap (turns)": "answer_cap_turns",
    "model failure (turns)": "model_failure_turns", "history compactions": "compactions",
    "failed attempts before success": "failed_attempts"}


def _core_block(outcomes: pd.DataFrame, votes: pd.DataFrame, title: str,
                exclude=()) -> tuple[list[str], list[dict], list[dict], dict]:
    """Core contrasts (Holm over the four), the 2x2 and H4 for the runs given."""
    lines = [f"### {title}", ""]
    core = [contrast(outcomes, name, t, c, exclude=exclude) for name, t, c in CORE]
    for row, adjusted in zip(core, holm([r["p"] for r in core]), strict=True):
        row["holm_p"] = adjusted
    lines += _table(core, {**CONTRAST_COLUMNS,
                           "Holm p": lambda r: _p(r["holm_p"], len(CORE) * 2 / DRAWS)})
    effects = factorial(outcomes, exclude=exclude)
    lines += ["2 × 2 (H2 holds if verification's main effect exceeds decomposition's: the last"
              " row):", ""] + _table(effects, EFFECT_COLUMNS)
    cost = cost_contrast(outcomes, D, B, exclude=exclude)
    lines += ["Cost (H4): tokens per correct task, D vs B:", ""] + _table([cost], COST_COLUMNS)
    voted = _scored(votes) if len(votes) else votes
    if len(voted):
        k, n = int(voted.passed.sum()), len(voted)
        lo, hi, _ = bootstrap(voted.groupby("task").passed.mean().to_numpy()[:, None],
                              _mean_diff)
        lines += [f"Self-consistency baseline G (A's three runs voted per output, then scored):"
                  f" {k}/{n} = {100 * k / n:.1f}% ({100 * lo:.1f}–{100 * hi:.1f}); tokens"
                  f" per task {voted.total_tokens.mean():,.0f}, per correct task"
                  f" {voted.total_tokens.sum() / k:,.0f}.", ""]
    return lines, core, effects, cost


def report(store: ResultStore) -> tuple[str, dict[str, pd.DataFrame]]:
    outcomes = collect(store)
    facts = run_facts(store)
    votes = vote_outcomes(store, outcomes)
    everything = pd.concat([outcomes, votes.drop(columns="turn_statuses", errors="ignore")],
                           ignore_index=True)
    models = [FLASH, *sorted(set(outcomes.model) - {FLASH})]
    flash = outcomes[outcomes.model == FLASH]
    sets = task_sets()
    all_tasks = sorted(outcomes.task.unique())
    separate = set(sets["key_departs"]) | set(sets["record_semantics"])
    uncovered = [t for t in all_tasks if t not in set(sets["covered"]) | separate]
    rescored_path = settings.results_dir / "_frozen" / store.root.name / RESCORED_FILE
    rescored = [tuple(r) for r in json.loads(rescored_path.read_text())] \
        if rescored_path.exists() else []
    lines = [f"# Reliability study ({store.root.name}): frozen analysis", "",
             f"{len(all_tasks)} tasks; backbones: {', '.join(models)}. Bootstrap: {DRAWS:,}"
             f" draws over tasks, seed {SEED}.", ""]

    # 0. Infrastructure
    lines += ["## 0. Coverage and infrastructure", ""]
    status = outcomes.pivot_table(index=["model", "arm"], columns="status", values="task",
                                  aggfunc="count", fill_value=0)
    turn_status, stops = Counter(), Counter()
    for row in facts.itertuples():
        for s_, n in row.turn_statuses.items():
            turn_status[(row.model, row.arm, s_)] += n
        for stop, n in row.stops.items():
            stops[(row.model, row.arm, stop)] += n
    rows = []
    for model, arm in status.index:
        rows.append({"model": model, "arm": arm,
                     **{s_: int(status.loc[(model, arm), s_]) if s_ in status.columns else 0
                        for s_ in ("scored", "refused", "unscored", "error")},
                     "turn statuses": ", ".join(f"{s_} {n}" for (m, a, s_), n in
                                                sorted(turn_status.items())
                                                if (m, a) == (model, arm))})
    lines += _table(rows, {"model": "model", "arm": "arm", "scored": "scored",
                           "refused": "refused", "unscored": "unscored", "error": "error",
                           "turn statuses (final)": "turn statuses"})
    lines += ["Stage stop reasons (role:reason count):", ""]
    for model, arm in status.index:
        lines.append(f"- {model} · {arm}: " + ", ".join(
            f"{s_} {n}" for (m, a, s_), n in sorted(stops.items()) if (m, a) == (model, arm)))
    # Pre-registration §5 would drop a turn left raised or at infra_error from every arm
    # for its task and repeat; that is not implemented, because the frozen scoring leaves
    # none. "absent" marks a turn no verifier ran on, which has no before-verifier verdict.
    unjudged = [(f"{row.model} {row.arm} {row.task} r{row.repeat}", kind, statuses)
                for row in facts.itertuples()
                for kind, counts, allowed in (("final", row.turn_statuses, {"scored"}),
                                              ("before", row.before_statuses,
                                               {"scored", "absent"}))
                if (statuses := {s_: n for s_, n in counts.items() if s_ not in allowed})]
    unjudged += [(f"{row.model} {G} {row.task}", "final", statuses) for row in votes.itertuples()
                 if (statuses := {s_: n for s_, n in row.turn_statuses.items()
                                  if s_ != "scored"})]
    if unjudged:
        raise SystemExit(f"turns left unjudged, rescore them first: {unjudged}")
    absent = sum(row.before_statuses.get("absent", 0) for row in facts.itertuples())
    lines += ["", "Every turn is judged: the final outputs of every run and of G, and the outputs"
              f" before each verifier ({absent} turns had no verifier run, so no such"
              " verdict). " + (f"{len(rescored)} runs whose turns the first frozen pass left at"
              " infra_error were rescored before it was archived (docs/deviations.md §8);"
              " dropping their task and repeat, as pre-registration §5 reads strictly, is a"
              " sensitivity analysis in §1." if rescored else "The first frozen pass left no"
              " turn at infra_error."), ""]
    strata = _scored(outcomes).groupby(["model", "arm", "category"]) \
        .passed.agg(passing="sum", runs="count").reset_index()
    zero = strata[(strata.passing == 0) & (strata.runs >= 3)]
    lines += [f"Strata (model × arm × category) with no passing run: {len(zero)}", ""]
    lines += [f"- {r.model} · {r.arm} · {r.category}: 0/{r.runs}" for r in zero.itertuples()]
    lines.append("")

    # 1. Registered
    lines += ["## 1. Decomposition × verification", "", "### Accuracy by arm, per backbone", ""]
    arm_tables = []
    for model in models:
        cell = outcomes[outcomes.model == model]
        arms = [a for a in REGISTERED if a in set(cell.arm)]
        table = arm_rows(cell, arms)
        arm_tables += [dict(r, model=model) for r in table]
        lines += [f"{model}:", ""] + _table(table, ARM_COLUMNS)
    lines += ["An answering stage is one that can set the turn's outputs: every stage except a"
              " reviewer, a sub-agent and the evidence verifier (which works in a copy).", ""]
    core_rows, effect_rows, cost_rows = [], [], []
    blocks = [(model, outcomes[outcomes.model == model], votes[votes.model == model]
               if len(votes) else votes) for model in models]
    if len(models) > 1:
        blocks.append(("pooled over backbones", outcomes, votes))
    for label, cell, cell_votes in blocks:
        block, core, effects, cost = _core_block(
            cell, cell_votes, f"Core contrasts (H1, H2, H4): {label}")
        lines += block
        core_rows += [dict(r, scope=label) for r in core]
        effect_rows += [dict(r, scope=label) for r in effects]
        cost_rows.append(dict(cost, scope=label))
    if rescored:
        block, core, effects, cost = _core_block(
            outcomes, votes.iloc[0:0], "Sensitivity: the registered exclusion rule read strictly"
            f" ({len(rescored)} rescored runs' task and repeat dropped)", exclude=rescored)
        lines += block
        core_rows += [dict(r, scope="strict exclusion") for r in core]
        effect_rows += [dict(r, scope="strict exclusion") for r in effects]

    # The delegation, knowledge and exploratory arms are reported only when their runs are in
    # the store (the knowledge and exploratory arms are kept in results/_supplementary).
    present = set(outcomes.arm)
    knowledge, exploratory, changes, delegation = [], [], [], []
    if F in present:
        lines += ["### Delegation (every backbone; docs/deviations.md §13)", "",
                  "A lead that splits each turn into pieces and hands every piece to a"
                  " sub-agent, allotting their steps (lead 10 steps, sub-agents 40; with a"
                  " verifier, sub-agents 25 and the verifier 15): the decomposition made at run"
                  " time, against the fixed roles of C, against A and against B.", ""]
        arms = [a for a in (F, FV) if a in present]
        for model in models:
            table = arm_rows(outcomes[outcomes.model == model], arms)
            arm_tables += [dict(r, model=model) for r in table]
            lines += [f"{model}:", ""] + _table(table, ARM_COLUMNS)
        pairs = [(F, A), (F, C), (F, B)] + ([(FV, F), (FV, B), (FV, D)] if FV in present else [])
        for label, cell, _ in blocks:
            rows = [contrast(cell, f"{t} vs {c}", t, c) for t, c in pairs]
            delegation += [dict(r, scope=label) for r in rows]
            lines += [f"{label}:", ""] + _table(rows, CONTRAST_COLUMNS)
    if {E, *TWINS} <= present:
        lines += [f"### Knowledge (H3): {FLASH}", ""]
        knowledge = [contrast(flash, "H3 published prompts", E, D)]
        knowledge += [contrast(flash, f"H3 rules: {twin}", twin, bare)
                      for twin, bare in TWINS.items()]
        knowledge += [pooled_contrast(flash, "H3 knowledge factor: the four rules arms pooled",
                                      TWINS)]
        lines += _table(knowledge, CONTRAST_COLUMNS)

    lines += ["### Verifiers: turns fixed and broken", "",
              "Turns judged both on the outputs before the verifier ran and after it.", ""]
    verifier_rows = []
    for model in models:
        for arm in [B, D, FV, "single_agent_verified_rules", "neuroair_rules", E, EVIDENCE]:
            cell = outcomes[(outcomes.model == model) & (outcomes.arm == arm)]
            if cell.empty:
                continue
            twice = int(facts[(facts.model == model) & (facts.arm == arm)].judged_twice.sum())
            verifier_rows.append({
                "model": model, "arm": arm, "verified": int(cell.verified_turns.sum()),
                "twice": twice,
                "fixed": int(cell.verifier_fixed_turns.sum()) if twice else "—",
                "broken": int(cell.verifier_broke_turns.sum()) if twice else "—"})
    lines += _table(verifier_rows, {"model": "model", "arm": "arm", "turns verified": "verified",
                                    "judged before and after": "twice",
                                    "fixed": "fixed", "broken": "broken"})
    failures = collect_failures(store)
    lines += ["### Failed turns by cause", ""]
    for model in models:
        causes = cause_table(failures[failures.model == model])
        lines += [f"{model}:", "", "| arm | " + " | ".join(causes.columns) + " |",
                  "|---" * (len(causes.columns) + 1) + "|"]
        lines += [f"| {arm} | " + " | ".join(str(n) for n in causes.loc[arm]) + " |"
                  for arm in [*REGISTERED, F, FV, *EXPLORATORY] if arm in causes.index]
        lines.append("")
    fallback = outcomes[outcomes.topology == "neuroair"].groupby(["model", "arm"]) \
        .coordinator_fallback_turns.sum()
    lines += ["Coordinator fallbacks (turns planned by the default plan): "
              + ", ".join(f"{m} {a} {int(n)}" for (m, a), n in fallback.items()), ""]
    lines += ["### Accuracy by category (descriptive; no per-category inference)", ""]
    tasks_per_category = outcomes.groupby("category").task.nunique()
    for model in models:
        cell = _scored(outcomes[outcomes.model == model]).astype({"passed": float})
        by_category = cell.pivot_table(index="category", columns="arm", values="passed",
                                       aggfunc="mean")
        shown = [a for a in [*REGISTERED, F, FV, *EXPLORATORY] if a in by_category.columns]
        lines += [f"{model}:", "", "| category | tasks | " + " | ".join(shown) + " |",
                  "|---" * (len(shown) + 2) + "|"]
        lines += [f"| {c} | {tasks_per_category[c]} | "
                  + " | ".join(f"{100 * by_category.loc[c, a]:.0f}%" for a in shown) + " |"
                  for c in by_category.index]
        lines.append("")

    if set(EXPLORATORY) <= present:
        # 2. Exploratory (Flash only)
        lines += [f"## 2. Exploratory (docs/deviations.md; {FLASH} only)", "",
                  f"### E1–E4 (covered subset: {len(sets['covered'])} tasks;"
                  f" uncovered control: {len(uncovered)})", ""]
        exploratory = [
            contrast(flash, "E1 code − A (covered)", CODE, A, sets["covered"]),
            contrast(flash, "E1 text − A (covered)", TEXT, A, sets["covered"]),
            contrast(flash, "E2 code − text (covered)", CODE, TEXT, sets["covered"]),
            contrast(flash, "E3 code − D (covered)", CODE, D, sets["covered"]),
            contrast(flash, "control: code − A (uncovered)", CODE, A, uncovered),
            contrast(flash, "control: text − A (uncovered)", TEXT, A, uncovered),
            contrast(flash, "E3 code − D (all tasks)", CODE, D),
            contrast(flash, "E4 evidence − B (all tasks)", EVIDENCE, B),
        ]
        lines += _table(exploratory, CONTRAST_COLUMNS)
        exploratory_cost = [cost_contrast(flash, CODE, D, sets["covered"]),
                            cost_contrast(flash, CODE, D)]
        lines += ["E3 cost: tokens per correct task, code vs D (covered subset, then all"
                  " tasks)", ""]
        lines += _table(exploratory_cost, COST_COLUMNS)
        changes = verifier_change(flash, EVIDENCE, B)
        lines += ["E4: turns the verifier fixed and broke per run, evidence vs B (paired runs)", ""]
        lines += _table(changes, {
            "measure": "measure", "tasks / pairs": lambda r: f"{r['tasks']} / {r['pairs']}",
            "evidence / B": lambda r: f"{r['treatment']:.3f} / {r['control']:.3f}",
            "evidence − B [95% CI]": lambda r: f"{r['difference']:+.3f}"
                                               f" [{r['lo']:+.3f}, {r['hi']:+.3f}]",
            "p (bootstrap)": lambda r: _p(r["p"])})

        lines += ["### Reported separately: the four natural-day tasks (D3) and record"
                  " semantics", "",
                  "Outside the covered subset, as fixed before the runs. Passing runs / scored"
                  " runs.",
                  ""]
        shown = [A, TEXT, CODE, B, D]
        separate_rows = []
        for task in [*sets["key_departs"], *sets["record_semantics"]]:
            cell = _scored(flash[flash.task == task])
            separate_rows.append({"task": task, **{
                arm: f"{int(cell[cell.arm == arm].passed.sum())}/{int((cell.arm == arm).sum())}"
                for arm in shown}})
        lines += _table(separate_rows, {"task": "task", **{arm: arm for arm in shown}})

        lines += ["### Exploratory arms: cost and process", ""]
        lines += _table(arm_rows(flash, EXPLORATORY), {
            "arm": "arm", "passed / scored": lambda r: f"{r['passed']}/{r['scored']}",
            "accuracy": lambda r: f"{100 * r['accuracy']:.1f}%",
            "mean tokens": lambda r: f"{r['mean_tokens']:,.0f}",
            "tokens per correct": lambda r: f"{r['tokens_per_correct']:,.0f}",
            "answering stage at step cap (turns)": "answer_cap_turns"})
        evidence = flash[flash.arm == EVIDENCE]
        evidence_facts = facts[(facts.model == FLASH) & (facts.arm == EVIDENCE)]
        turns = int(evidence.run_turns.sum())
        verifier_caps = sum(n for row in evidence_facts.stops for s_, n in row.items()
                            if s_ == "verification:max_steps")
        revise_caps = sum(n for row in evidence_facts.stops for s_, n in row.items()
                          if s_ == "revise:max_steps")
        lines += [f"Evidence verifier: {turns} turns; a usable report with at least one entry in"
                  f" {int(evidence_facts.reported_turns.sum())}; a discrepancy relayed to the agent"
                  f" (who then revised) in {int(evidence.reviewed_with_issues.sum())}; malformed"
                  f" {int(evidence.malformed_review_turns.sum())}; entries the stored value already"
                  " agreed with (not relayed)"
                  f" {int(evidence_facts.evidence_agreeing_entries.sum())};"
                  f" outputs changed while the verifier ran"
                  f" {int(evidence_facts.outputs_changed_by_verifier.sum())}; verifier stages at"
                  f" their step cap {verifier_caps}; revisions at their step cap"
                  f" {revise_caps}.", ""]
        code_facts = facts[(facts.model == FLASH) & (facts.arm == CODE)]
        covered_runs = code_facts[code_facts.task.isin(sets["covered"])]
        other_runs = code_facts[~code_facts.task.isin(sets["covered"])]
        lines += [f"Convention code: runs whose code called the library —"
                  f" covered {int((covered_runs.library_calls > 0).sum())}/{len(covered_runs)},"
                  f" other tasks {int((other_runs.library_calls > 0).sum())}/{len(other_runs)};"
                  f" execution errors naming a library function"
                  f" {int(code_facts.library_errors.sum())}.", ""]

    tables = {"outcomes": everything,
              "facts": facts.drop(columns=["stops", "turn_statuses", "before_statuses"]),
              "contrasts": pd.concat([pd.DataFrame(rows).assign(analysis=name) for name, rows in (
                  ("core", core_rows), ("delegation", delegation), ("knowledge", knowledge),
                  ("exploratory", exploratory))],
                  ignore_index=True),
              "factorial": pd.DataFrame(effect_rows), "cost": pd.DataFrame(cost_rows),
              "verifier_change": pd.DataFrame(changes), "arms": pd.DataFrame(arm_tables)}
    return "\n".join(lines) + "\n", tables


def main(argv: list[str]) -> None:
    if len(argv) > 1:
        raise SystemExit(__doc__)
    store = ResultStore(settings.results_dir, argv[0] if argv else EXPERIMENT)
    markdown, tables = report(store)
    out = store.report_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "study.md").write_text(markdown, encoding="utf-8")
    for name, table in tables.items():
        table.to_csv(out / f"study_{name}.csv", index=False)
    print(f"written to {out / 'study.md'}")


if __name__ == "__main__":
    main(sys.argv[1:])
