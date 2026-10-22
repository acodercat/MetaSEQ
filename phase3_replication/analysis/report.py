"""Per-arm accuracy and the paired contrast, written to results/report/.

    uv run metaseq report study

The primary outcome is task-level: a task passes only if every turn passed. A contrast pairs
runs within a backbone on (task, repeat), scored in both arms, and reports the mean of the
per-task differences (each task weighted equally over its repeats and backbones) with the
pre-specified estimator (`analysis.stats.bootstrap`: 10,000 task resamples, seed 20260929,
percentile 95% interval, two-sided p at zero), per backbone and pooled, with the task-repeats
recovered and regressed and the exact McNemar test on them, reported descriptively.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from analysis.failures import cause_table
from analysis.stats import bootstrap, mcnemar_exact, mean_of_first_column, wilson
from evaluation.experiment import Contrast, ExperimentSpec


def paired(outcomes: pd.DataFrame, treatment: str, control: str) -> pd.DataFrame:
    """One row per (model, task, repeat) scored in both arms, with passed and tokens per arm."""
    scored = outcomes[(outcomes.status == "scored") & outcomes.arm.isin([treatment, control])]
    wide = scored.pivot_table(index=["model", "task", "repeat"], columns="arm",
                              values=["passed", "total_tokens"], aggfunc="first")
    return wide.dropna().astype(float)


def contrast(outcomes: pd.DataFrame, c: Contrast, scope: str = "pooled") -> dict:
    """Treatment minus control on paired runs: accuracies and their difference weight each
    task equally."""
    pairs = paired(outcomes, c.treatment, c.control)
    t, ctl = pairs["passed"][c.treatment], pairs["passed"][c.control]
    per_task = (t - ctl).groupby(level="task").mean()
    lo, hi, p = bootstrap(per_task.to_numpy()[:, None], mean_of_first_column)
    recovered, regressed = int(((ctl == 0) & (t == 1)).sum()), int(((ctl == 1) & (t == 0)).sum())
    tokens_t, tokens_c = pairs["total_tokens"][c.treatment], pairs["total_tokens"][c.control]
    return {"contrast": c.name, "scope": scope, "treatment": c.treatment, "control": c.control,
            "tasks": per_task.size, "pairs": len(pairs),
            "control_acc": ctl.groupby(level="task").mean().mean(),
            "treatment_acc": t.groupby(level="task").mean().mean(),
            "delta_pp": 100 * per_task.mean(), "lo_pp": 100 * lo, "hi_pp": 100 * hi, "p": p,
            "recovered": recovered, "regressed": regressed,
            "mcnemar_p": mcnemar_exact(recovered, regressed),
            "control_tokens_per_task": tokens_c.mean(),
            "treatment_tokens_per_task": tokens_t.mean(),
            "control_tokens_per_correct": tokens_c.sum() / ctl.sum() if ctl.sum() else math.nan,
            "treatment_tokens_per_correct": tokens_t.sum() / t.sum() if t.sum() else math.nan}


def arm_table(outcomes: pd.DataFrame, spec: ExperimentSpec) -> pd.DataFrame:
    rows = []
    for arm in spec.arms:
        for model in spec.models:
            cell = outcomes[(outcomes.arm == arm) & (outcomes.model == model)]
            scored = cell[cell.status == "scored"]
            n, k = len(scored), int(scored.passed.sum()) if len(scored) else 0
            lo, hi = wilson(k, n)
            rows.append({
                "arm": arm, "model": model, "scored": n, "missing": len(cell) - n,
                "passed": k,
                # task-level: each task weighted equally over its repeats
                "accuracy": scored.groupby("task").passed.mean().mean() if n else math.nan,
                "wilson_lo": lo, "wilson_hi": hi,
                "mean_steps": scored.steps.mean(), "median_steps": scored.steps.median(),
                "mean_tokens": scored.total_tokens.mean(),
                "tokens_per_correct": scored.total_tokens.sum() / k if k else math.nan,
                "step_limit_turns": int(cell.step_limit_turns.sum()),
                "coordinator_fallback_turns": int(cell.coordinator_fallback_turns.sum()),
            })
    return pd.DataFrame(rows)


def category_table(outcomes: pd.DataFrame) -> pd.DataFrame:
    """Task pass rate per arm and category, all backbones (descriptive)."""
    scored = outcomes[outcomes.status == "scored"]
    per_task = scored.groupby(["arm", "category", "task"]).passed.mean().reset_index()
    table = per_task.groupby(["arm", "category"]).passed.agg(["mean", "count"]).reset_index()
    return table.rename(columns={"mean": "pass_rate", "count": "tasks"})


def render_markdown(spec: ExperimentSpec, arms: pd.DataFrame, contrasts: pd.DataFrame,
                    outcomes: pd.DataFrame, causes: pd.DataFrame | None) -> str:
    coverage = outcomes.status.value_counts()
    lines = [f"# {spec.name}", "", spec.description.strip(), "",
             f"Suite `{spec.suite}` · {len(spec.arms)} arms × {len(spec.models)} models"
             f" ({', '.join(spec.models)})"
             f" · repeats {spec.repeats}", "",
             "Run status counts: " + ", ".join(f"{k} {v}" for k, v in coverage.items()), "",
             "## Accuracy by arm (task-level: every turn must pass)", "",
             "| arm | model | passed / scored | accuracy | missing | median steps | tokens/task |"
             " tokens/correct | turns at step cap |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in arms.itertuples():
        lines.append(f"| {r.arm} | {r.model} | {r.passed}/{r.scored} |"
                     f" {_num(100 * r.accuracy, '.1f')}% | {r.missing} |"
                     f" {_num(r.median_steps, '.0f')} | {_num(r.mean_tokens, ',.0f')} |"
                     f" {_num(r.tokens_per_correct, ',.0f')} | {r.step_limit_turns} |")
    lines += ["", "## Paired contrast", "",
              "| contrast | scope | control → treatment | Δ pp [95% interval] | p |"
              " recovered / regressed | McNemar p |",
              "|---|---|---|---|---|---|---|"]
    for r in contrasts.itertuples():
        lines.append(f"| {r.contrast} | {r.scope} | {100 * r.control_acc:.1f}% →"
                     f" {100 * r.treatment_acc:.1f}% | {r.delta_pp:+.1f} [{r.lo_pp:+.1f},"
                     f" {r.hi_pp:+.1f}] | {r.p:.3g} | {r.recovered}/{r.regressed} |"
                     f" {r.mcnemar_p:.3g} |")
    protocols = outcomes.groupby("arm").protocol.unique()
    lines += ["", "Protocol fingerprints per arm (code, prompts and environment the runs were made"
              " under): " + "; ".join(f"{a}: {', '.join(p or '(none)' for p in ps)}"
                                     for a, ps in protocols.items())]
    if causes is not None and not causes.empty:
        lines += ["", "## Failed turns by cause", "",
                  "| arm | " + " | ".join(causes.columns) + " |",
                  "|---" * (len(causes.columns) + 1) + "|"]
        for arm, counts in causes.iterrows():
            lines.append(f"| {arm} | " + " | ".join(str(n) for n in counts) + " |")
    return "\n".join(lines) + "\n"


def _num(value: float, spec: str) -> str:
    return "—" if math.isnan(value) else format(value, spec)


def write_report(spec: ExperimentSpec, outcomes: pd.DataFrame, out_dir: Path,
                 failures: pd.DataFrame | None = None) -> str:
    """Write the report for this spec's grid; stored runs of other arms/models are ignored."""
    outcomes = outcomes[outcomes.arm.isin(spec.arms) & outcomes.model.isin(spec.models)]
    causes = None
    if failures is not None:
        failures = failures[failures.arm.isin(spec.arms) & failures.model.isin(spec.models)]
        causes = cause_table(failures)
    out_dir.mkdir(parents=True, exist_ok=True)
    arms = arm_table(outcomes, spec)
    contrasts = pd.DataFrame(
        [contrast(outcomes[outcomes.model == m], c, m) for c in spec.contrasts
         for m in spec.models]
        + [contrast(outcomes, c) for c in spec.contrasts])
    outcomes.to_csv(out_dir / "outcomes.csv", index=False)
    arms.to_csv(out_dir / "arms.csv", index=False)
    contrasts.to_csv(out_dir / "contrasts.csv", index=False)
    category_table(outcomes).to_csv(out_dir / "categories.csv", index=False)
    if failures is not None:
        failures.to_csv(out_dir / "failures.csv", index=False)
    markdown = render_markdown(spec, arms, contrasts, outcomes, causes)
    (out_dir / "summary.md").write_text(markdown, encoding="utf-8")
    return markdown
