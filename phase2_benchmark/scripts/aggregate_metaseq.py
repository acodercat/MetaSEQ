"""Aggregate the metaseq single-vs-multi PV experiment into paper-ready tables.

Usage:
    uv run python -m scripts.aggregate_metaseq
    uv run python -m scripts.aggregate_metaseq --root experiments/metaseq --out experiments/metaseq/summary

Reads the raw PV result JSONs under
    experiments/metaseq/<model>/{single,multi}/run1/HK/<category>/<task>/<model>_<ts>.json
(one file per cell; if several timestamps exist the latest is used), scores them,
runs the paired statistics, and writes every number cited in the manuscript to
CSV + LaTeX fragments under --out.  Nothing here calls an LLM or a database:
the script is a deterministic function of the archived JSONs.

Scoring rules
-------------
primary  (all-turns): a task is scored correct only if EVERY turn's validator
    passed (``metrics.failed_turns == 0``).  This is the strict, conservative
    convention used in PV_findings.md and the manuscript.
sensitivity (final-turn): a task passes iff the final turn's validator passed
    (earlier turns treated as scaffolding).  Reported alongside as a
    scoring-rule sensitivity analysis.

Self-checks
-----------
Asserts full 7x2x50 coverage and reproduces the published headline numbers under
BOTH rules: all-turns pooled 261/350 -> 298/350 (discordant 55/18) and final-turn
pooled 262/350 -> 303/350 (discordant 56/15). If the archive changes, run with
--no-expected to skip the expected counts (coverage asserts always run).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from scipy.stats import binomtest

# Registry directory name -> (public name, API/snapshot identifier)
MODELS: dict[str, tuple[str, str]] = {
    "gpt55": ("GPT-5.5", "gpt-5.5"),
    "deepseek-v4-pro": ("DeepSeek-V4-Pro", "deepseek-v4-pro-260425"),
    "deepseek-v4-flash": ("DeepSeek-V4-Flash", "deepseek-v4-flash-260425"),
    "qwen3.5-397b": ("Qwen3.5-397B-A17B", "qwen/qwen3.5-397b-a17b"),
    "qwen3.6-35b": ("Qwen3.6-35B-A3B", "qwen/qwen3.6-35b-a3b"),
    "qwen3.6-27b": ("Qwen3.6-27B", "qwen/qwen3.6-27b"),
    "qwen-2.5-72b": ("Qwen2.5-72B-Instruct", "qwen/qwen-2.5-72b-instruct"),
}
TOPOLOGIES = ("single", "multi")
N_TASKS = 50

# Publication labels for the LaTeX fragments; CSVs keep the raw slugs.
CATEGORY_LABELS: dict[str, str] = {
    "cross_domain_analysis": "Cross-domain analysis",
    "data_retrieval": "Data retrieval",
    "source_attribution": "Source attribution",
    "statistical_characterization": "Statistical characterization",
    "spatial_analysis": "Spatial analysis",
    "exposure_assessment": "Exposure assessment",
    "comparative_assessment": "Comparative assessment",
    "exceedance_anomaly_detection": "Exceedance \\& anomaly detection",
}

PRIMARY = "all_turns"      # strict rule (PV_findings.md / manuscript)
SENSITIVITY = "final_turn"  # lenient final-answer-only rule
RULES = (PRIMARY, SENSITIVITY)
TAG = {PRIMARY: "", SENSITIVITY: "_finalturn"}

# Expected passes for the archived run1 results: (rule, model, topology) -> passes.
EXPECTED = {
    "all_turns": {
        ("gpt55", "single"): 48, ("gpt55", "multi"): 49,
        ("deepseek-v4-pro", "single"): 44, ("deepseek-v4-pro", "multi"): 47,
        ("qwen3.5-397b", "single"): 40, ("qwen3.5-397b", "multi"): 46,
        ("qwen3.6-35b", "single"): 40, ("qwen3.6-35b", "multi"): 42,
        ("deepseek-v4-flash", "single"): 37, ("deepseek-v4-flash", "multi"): 45,
        ("qwen3.6-27b", "single"): 35, ("qwen3.6-27b", "multi"): 41,
        ("qwen-2.5-72b", "single"): 17, ("qwen-2.5-72b", "multi"): 28,
    },
    "final_turn": {
        ("gpt55", "single"): 48, ("gpt55", "multi"): 49,
        ("deepseek-v4-pro", "single"): 44, ("deepseek-v4-pro", "multi"): 48,
        ("qwen3.5-397b", "single"): 40, ("qwen3.5-397b", "multi"): 47,
        ("qwen3.6-35b", "single"): 40, ("qwen3.6-35b", "multi"): 43,
        ("deepseek-v4-flash", "single"): 37, ("deepseek-v4-flash", "multi"): 45,
        ("qwen3.6-27b", "single"): 35, ("qwen3.6-27b", "multi"): 41,
        ("qwen-2.5-72b", "single"): 18, ("qwen-2.5-72b", "multi"): 30,
    },
}
EXPECTED_POOLED = {
    "all_turns": {"single": 261, "multi": 298, "b": 55, "c": 18},
    "final_turn": {"single": 262, "multi": 303, "b": 56, "c": 15},
}


def wilson_ci(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def mcnemar_exact(b: int, c: int) -> float:
    """Exact McNemar p-value: two-sided binomial test on discordant pairs."""
    if b + c == 0:
        return 1.0
    return binomtest(b, b + c, 0.5).pvalue


def load_cells(root: Path) -> dict[tuple[str, str, str], dict]:
    """(model, topology, task) -> {category, all_turns, final_turn, steps, tokens, ...}."""
    cells: dict[tuple[str, str, str], dict] = {}
    for model in MODELS:
        for topo in TOPOLOGIES:
            base = root / model / topo / "run1" / "HK"
            if not base.is_dir():
                raise SystemExit(f"missing arm directory: {base}")
            for task_dir in sorted(p for p in base.glob("*/*") if p.is_dir()):
                files = sorted(task_dir.glob("*.json"))
                if not files:
                    raise SystemExit(f"no result JSON in {task_dir}")
                # File names end in _YYYYMMDD_HHMMSS.json -> lexical sort = chronological.
                data = json.loads(files[-1].read_text())
                if len(data) != 1:
                    raise SystemExit(f"expected one scenario per file: {files[-1]}")
                scenario = next(iter(data.values()))
                convs = scenario["conversations"]
                if len(convs) != 1:
                    raise SystemExit(f"expected one conversation: {files[-1]}")
                turns = convs[0]["turns"]
                metrics = scenario["metrics"]
                cells[(model, topo, task_dir.name)] = {
                    "category": task_dir.parent.name,
                    "all_turns": metrics["failed_turns"] == 0,
                    "final_turn": bool(turns[-1].get("success")),
                    "n_turns": metrics["total_turns"],
                    "steps": metrics["total_steps"],
                    "tokens": metrics["total_tokens"],
                    "prompt_tokens": metrics["total_prompt_tokens"],
                    "completion_tokens": metrics["total_completion_tokens"],
                }
    return cells


def check_coverage(cells: dict) -> tuple[list[str], dict[str, str]]:
    """Assert 7x2x50 with identical task sets; return (tasks, task->category)."""
    task_sets = {
        (m, t): {k[2] for k in cells if k[0] == m and k[1] == t}
        for m in MODELS for t in TOPOLOGIES
    }
    ref = task_sets[(next(iter(MODELS)), "single")]
    for key, ts in task_sets.items():
        assert len(ts) == N_TASKS, f"{key}: {len(ts)} tasks, expected {N_TASKS}"
        assert ts == ref, f"{key}: task set differs from reference"
    categories = {t: cells[(next(iter(MODELS)), "single", t)]["category"] for t in ref}
    for (m, topo, t), cell in cells.items():
        assert cell["category"] == categories[t], f"category mismatch for {t}"
    return sorted(ref), categories


def aggregate(root: Path, out: Path, check_expected: bool) -> None:
    cells = load_cells(root)
    tasks, categories = check_coverage(cells)
    out.mkdir(parents=True, exist_ok=True)

    def passed(model: str, topo: str, task: str, rule: str) -> bool:
        return cells[(model, topo, task)][rule]

    # ---------------- per-backbone paired table ----------------
    backbone_rows = []
    pooled = {r: {"single": 0, "multi": 0, "b": 0, "c": 0} for r in RULES}
    for model, (public, snapshot) in MODELS.items():
        row: dict = {"model": model, "public_name": public, "snapshot": snapshot}
        for rule in RULES:
            s = sum(passed(model, "single", t, rule) for t in tasks)
            m = sum(passed(model, "multi", t, rule) for t in tasks)
            # discordant pairs: b = single fail & multi pass, c = single pass & multi fail
            b = sum((not passed(model, "single", t, rule)) and passed(model, "multi", t, rule) for t in tasks)
            c = sum(passed(model, "single", t, rule) and (not passed(model, "multi", t, rule)) for t in tasks)
            lo_s, hi_s = wilson_ci(s, N_TASKS)
            lo_m, hi_m = wilson_ci(m, N_TASKS)
            tag = TAG[rule]
            row.update({
                f"single{tag}": s, f"multi{tag}": m, f"delta{tag}": m - s,
                f"single_ci{tag}": f"{100*lo_s:.1f}-{100*hi_s:.1f}",
                f"multi_ci{tag}": f"{100*lo_m:.1f}-{100*hi_m:.1f}",
                f"b{tag}": b, f"c{tag}": c,
                f"mcnemar_p{tag}": mcnemar_exact(b, c),
                f"odds_ratio{tag}": (b / c) if c else float("inf"),
                # recovery rate: share of the single arm's failures that multi fixes
                f"recovery_rate{tag}": b / (N_TASKS - s) if s < N_TASKS else float("nan"),
            })
            pooled[rule]["single"] += s
            pooled[rule]["multi"] += m
            pooled[rule]["b"] += b
            pooled[rule]["c"] += c
        # cost metrics; tokens-per-correct uses the primary (all-turns) counts
        for topo in TOPOLOGIES:
            sel = [cells[(model, topo, t)] for t in tasks]
            row[f"avg_steps_{topo}"] = sum(x["steps"] for x in sel) / N_TASKS
            row[f"avg_tokens_{topo}"] = sum(x["tokens"] for x in sel) / N_TASKS
            n_ok = row["single"] if topo == "single" else row["multi"]
            row[f"tokens_per_correct_{topo}"] = (
                sum(x["tokens"] for x in sel) / n_ok if n_ok else float("inf")
            )
        backbone_rows.append(row)

    if check_expected:
        for rule in RULES:
            tag = TAG[rule]
            for (model, topo), expected in EXPECTED[rule].items():
                got = next(r for r in backbone_rows if r["model"] == model)[f"{topo}{tag}"]
                assert got == expected, f"{rule} {model}/{topo}: {got} != expected {expected}"
            for key, expected in EXPECTED_POOLED[rule].items():
                assert pooled[rule][key] == expected, (rule, key, pooled[rule])

    n_pool = N_TASKS * len(MODELS)
    pooled_stats = {}
    for rule in RULES:
        p = pooled[rule]
        lo_s, hi_s = wilson_ci(p["single"], n_pool)
        lo_m, hi_m = wilson_ci(p["multi"], n_pool)
        pooled_stats[rule] = {
            **p,
            "single_pct": 100 * p["single"] / n_pool,
            "multi_pct": 100 * p["multi"] / n_pool,
            "single_ci": f"{100*lo_s:.1f}-{100*hi_s:.1f}",
            "multi_ci": f"{100*lo_m:.1f}-{100*hi_m:.1f}",
            "mcnemar_p": mcnemar_exact(p["b"], p["c"]),
            "odds_ratio": p["b"] / p["c"] if p["c"] else float("inf"),
        }

    # capability-spread compression under the primary rule (pp of 100).
    # Population SD: the 7 backbones are the full set under study, not a sample.
    singles = [2 * r["single"] for r in backbone_rows]
    multis = [2 * r["multi"] for r in backbone_rows]
    spread = {
        "single_min": min(singles), "single_max": max(singles),
        "single_spread_pp": max(singles) - min(singles),
        "single_sd_pp": statistics.pstdev(singles),
        "multi_min": min(multis), "multi_max": max(multis),
        "multi_spread_pp": max(multis) - min(multis),
        "multi_sd_pp": statistics.pstdev(multis),
    }

    # ---------------- mixed-logistic sensitivity (optional) ----------------
    mixed_note = "not run"
    try:
        import pandas as pd
        from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

        records = [
            {"correct": int(passed(m, topo, t, PRIMARY)),
             "multi": int(topo == "multi"), "task": t, "model": m}
            for m in MODELS for topo in TOPOLOGIES for t in tasks
        ]
        df = pd.DataFrame(records)
        model_fit = BinomialBayesMixedGLM.from_formula(
            "correct ~ multi", {"task": "0 + C(task)", "model": "0 + C(model)"}, df
        ).fit_vb()
        idx = list(model_fit.model.exog_names).index("multi")
        coef = float(model_fit.fe_mean[idx])
        sd = float(model_fit.fe_sd[idx])
        mixed_note = (
            f"BinomialBayesMixedGLM on the primary rule (correct ~ topology + task & "
            f"backbone random intercepts): beta_multi = {coef:.3f} (posterior sd {sd:.3f}), "
            f"OR = {math.exp(coef):.2f}, 95% interval "
            f"{math.exp(coef-1.96*sd):.2f}-{math.exp(coef+1.96*sd):.2f}"
        )
    except Exception as exc:  # statsmodels missing or fit failure: stats above stand alone
        mixed_note = f"skipped ({type(exc).__name__}: {exc})"

    # ---------------- category x topology (pooled over backbones, both rules) ----------------
    cat_rows = []
    for cat in sorted({categories[t] for t in tasks}):
        cat_tasks = [t for t in tasks if categories[t] == cat]
        n_cells = len(cat_tasks) * len(MODELS)
        crow: dict = {"category": cat, "n_tasks": len(cat_tasks), "n_cells": n_cells}
        for rule in RULES:
            tag = TAG[rule]
            s = sum(passed(m, "single", t, rule) for m in MODELS for t in cat_tasks)
            mm = sum(passed(m, "multi", t, rule) for m in MODELS for t in cat_tasks)
            crow.update({
                f"single{tag}": s, f"multi{tag}": mm,
                f"single_pct{tag}": 100 * s / n_cells,
                f"multi_pct{tag}": 100 * mm / n_cells,
                f"delta_pp{tag}": 100 * (mm - s) / n_cells,
            })
        cat_rows.append(crow)
    cat_rows.sort(key=lambda r: -r["delta_pp"])

    # ---------------- transition matrix + task lists (primary rule) ----------------
    trans = {"both_pass": 0, "recovery": 0, "regression": 0, "both_fail": 0}
    recovery_tasks: dict[str, int] = defaultdict(int)
    regression_tasks: dict[str, int] = defaultdict(int)
    multi_fail_tasks: dict[str, int] = defaultdict(int)
    for m in MODELS:
        for t in tasks:
            s = passed(m, "single", t, PRIMARY)
            mu = passed(m, "multi", t, PRIMARY)
            if s and mu:
                trans["both_pass"] += 1
            elif not s and mu:
                trans["recovery"] += 1
                recovery_tasks[t] += 1
            elif s and not mu:
                trans["regression"] += 1
                regression_tasks[t] += 1
            else:
                trans["both_fail"] += 1
            if not mu:
                multi_fail_tasks[t] += 1

    # ---------------- write CSVs ----------------
    def write_csv(name: str, rows: list[dict]) -> None:
        with (out / name).open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    write_csv("per_backbone.csv", backbone_rows)
    write_csv("per_category.csv", cat_rows)
    write_csv("transitions.csv", [
        {"task": t, "category": categories[t],
         "recoveries": recovery_tasks.get(t, 0),
         "regressions": regression_tasks.get(t, 0),
         "multi_failures": multi_fail_tasks.get(t, 0)}
        for t in tasks
    ])
    # per-cell long table (for external re-analysis / the mixed model)
    write_csv("per_cell.csv", [
        {"model": m, "public_name": MODELS[m][0], "topology": topo, "task": t,
         "category": categories[t],
         "all_turns": int(passed(m, topo, t, "all_turns")),
         "final_turn": int(passed(m, topo, t, "final_turn")),
         "steps": cells[(m, topo, t)]["steps"], "tokens": cells[(m, topo, t)]["tokens"]}
        for m in MODELS for topo in TOPOLOGIES for t in tasks
    ])

    # ---------------- LaTeX fragment: ED paired-results table ----------------
    def fmt_p(p: float) -> str:
        if p >= 0.001:
            return f"{p:.3f}"
        exp = math.floor(math.log10(p))
        return f"{p / 10**exp:.1f}\\times10^{{{exp}}}"

    lines = [
        "% Auto-generated by scripts/aggregate_metaseq.py -- do not edit by hand.",
        "% Per-backbone paired results, all-turns rule (final-turn sensitivity in comments).",
        "\\begin{tabular}{@{}l c c c c c c@{}}",
        "\\toprule",
        "\\textbf{Backbone} & \\textbf{Single (95\\% CI)} & \\textbf{Multi (95\\% CI)} & "
        "$\\Delta$ (pp) & \\textbf{Discordant} $b/c$ & \\textbf{OR} & \\textbf{McNemar} $p$ \\\\",
        "\\midrule",
    ]
    for r in sorted(backbone_rows, key=lambda x: -x["single"]):
        orr = "--" if r["c"] == 0 and r["b"] == 0 else (
            f"{r['odds_ratio']:.1f}" if math.isfinite(r["odds_ratio"]) else "$\\infty$")
        lines.append(
            f"{r['public_name']} & {2*r['single']:.0f}\\% ({r['single_ci']}) & "
            f"{2*r['multi']:.0f}\\% ({r['multi_ci']}) & +{2*r['delta']:.0f} & "
            f"{r['b']}/{r['c']} & {orr} & ${fmt_p(r['mcnemar_p'])}$ \\\\"
        )
        lines.append(
            f"%   final-turn sensitivity: single {r['single_finalturn']}/50, "
            f"multi {r['multi_finalturn']}/50"
        )
    pf = pooled_stats[PRIMARY]
    pa = pooled_stats[SENSITIVITY]
    lines += [
        "\\midrule",
        f"\\textbf{{Pooled}} & {pf['single_pct']:.1f}\\% ({pf['single_ci']}) & "
        f"{pf['multi_pct']:.1f}\\% ({pf['multi_ci']}) & "
        f"+{pf['multi_pct']-pf['single_pct']:.1f} & {pf['b']}/{pf['c']} & "
        f"{pf['odds_ratio']:.2f} & ${fmt_p(pf['mcnemar_p'])}$ \\\\",
        f"% pooled final-turn sensitivity: {pa['single']}/{n_pool} -> {pa['multi']}/{n_pool} "
        f"({pa['single_pct']:.1f}% -> {pa['multi_pct']:.1f}%), b/c {pa['b']}/{pa['c']}, "
        f"p {pa['mcnemar_p']:.2e}",
        "\\bottomrule",
        "\\end{tabular}",
        "",
        "% --- cost block (recovery rate + compute), same row order ---",
        "\\begin{tabular}{@{}l c c c c@{}}",
        "\\toprule",
        "\\textbf{Backbone} & \\textbf{Recovery rate} & \\textbf{Steps S$\\to$M} & "
        "\\textbf{Tokens S$\\to$M} & \\textbf{Tokens/correct S$\\to$M} \\\\",
        "\\midrule",
    ]
    for r in sorted(backbone_rows, key=lambda x: -x["single"]):
        lines.append(
            f"{r['public_name']} & {100*r['recovery_rate']:.0f}\\% ({r['b']}/{50-r['single']}) & "
            f"{r['avg_steps_single']:.1f} $\\to$ {r['avg_steps_multi']:.1f} & "
            f"{r['avg_tokens_single']/1e3:.1f}k $\\to$ {r['avg_tokens_multi']/1e3:.1f}k & "
            f"{r['tokens_per_correct_single']/1e3:.0f}k $\\to$ "
            f"{r['tokens_per_correct_multi']/1e3:.0f}k \\\\"
        )
    lines += ["\\bottomrule", "\\end{tabular}"]

    # ---------------- LaTeX fragment: category table ----------------
    cat_lines = [
        "% Auto-generated by scripts/aggregate_metaseq.py -- do not edit by hand.",
        "% Pooled over 7 backbones, all-turns rule.",
        "\\begin{tabular}{@{}l c c c c@{}}",
        "\\toprule",
        "\\textbf{Task category} & $n$ \\textbf{tasks} & \\textbf{Single} & "
        "\\textbf{Multi} & $\\Delta$ (pp) \\\\",
        "\\midrule",
    ]
    for r in cat_rows:
        cat_lines.append(
            f"{CATEGORY_LABELS.get(r['category'], r['category'])} & {r['n_tasks']} & "
            f"{r['single_pct']:.1f}\\% & {r['multi_pct']:.1f}\\% & "
            f"{r['delta_pp']:+.1f} \\\\"
        )
    cat_lines += ["\\bottomrule", "\\end{tabular}"]

    # ---------------- summary report ----------------
    rep = []
    rep.append("# metaseq aggregation summary (auto-generated)\n")
    rep.append(f"Coverage: {len(MODELS)} backbones x 2 topologies x {N_TASKS} tasks "
               f"= {len(cells)} runs; task sets identical across cells.\n")
    rep.append("## Pooled (all-turns rule, primary)")
    rep.append(f"- single {pf['single']}/{n_pool} = {pf['single_pct']:.1f}% (Wilson {pf['single_ci']})")
    rep.append(f"- multi  {pf['multi']}/{n_pool} = {pf['multi_pct']:.1f}% (Wilson {pf['multi_ci']})")
    rep.append(f"- discordant b/c = {pf['b']}/{pf['c']}  (OR {pf['odds_ratio']:.2f}), "
               f"exact McNemar p = {pf['mcnemar_p']:.2e}")
    rep.append(f"- all-positive deltas across {len(MODELS)} backbones: "
               f"exact sign test p = {2 * 0.5**len(MODELS):.3f}")
    rep.append("## Pooled (final-turn rule, sensitivity)")
    rep.append(f"- single {pa['single']}/{n_pool} = {pa['single_pct']:.1f}%, "
               f"multi {pa['multi']}/{n_pool} = {pa['multi_pct']:.1f}%, "
               f"b/c = {pa['b']}/{pa['c']}, p = {pa['mcnemar_p']:.2e}")
    rep.append("## Per-backbone (all-turns; % of 50)")
    for r in sorted(backbone_rows, key=lambda x: -x["single"]):
        rep.append(
            f"- {r['public_name']:>20s}: {2*r['single']:.0f}% -> {2*r['multi']:.0f}% "
            f"(delta +{2*r['delta']:.0f}pp, b/c {r['b']}/{r['c']}, "
            f"McNemar p {r['mcnemar_p']:.3g}, recovery rate {100*r['recovery_rate']:.0f}%; "
            f"steps {r['avg_steps_single']:.1f}->{r['avg_steps_multi']:.1f}, "
            f"tokens {r['avg_tokens_single']/1e3:.1f}k->{r['avg_tokens_multi']/1e3:.1f}k, "
            f"tok/correct {r['tokens_per_correct_single']/1e3:.0f}k->"
            f"{r['tokens_per_correct_multi']/1e3:.0f}k)"
        )
    rep.append(f"## Capability spread (pp of 100): single {spread['single_spread_pp']:.0f} "
               f"(SD {spread['single_sd_pp']:.1f}) -> multi {spread['multi_spread_pp']:.0f} "
               f"(SD {spread['multi_sd_pp']:.1f})")
    rep.append("## Transitions (350 paired cells, all-turns)")
    rep.append(f"- both pass {trans['both_pass']}, recovery (S✗→M✓) {trans['recovery']}, "
               f"regression (S✓→M✗) {trans['regression']}, both fail {trans['both_fail']}")
    rep.append("## Recurring recoveries (task: #backbones with S✗→M✓, top 8)")
    for t, n in sorted(recovery_tasks.items(), key=lambda kv: -kv[1])[:8]:
        rep.append(f"- {t}: {n}")
    rep.append("## Recurring regressions (task: #backbones with S✓→M✗)")
    for t, n in sorted(regression_tasks.items(), key=lambda kv: -kv[1]):
        if n >= 1:
            rep.append(f"- {t}: {n}")
    rep.append("## Hard residue (multi fails in >=3 of 7 backbones)")
    for t, n in sorted(multi_fail_tasks.items(), key=lambda kv: -kv[1]):
        if n >= 3:
            rep.append(f"- {t}: {n}/7 ({categories[t]})")
    rep.append("## Category gains (all-turns; final-turn in parentheses)")
    for r in cat_rows:
        rep.append(f"- {r['category']}: {r['single_pct']:.1f}% -> {r['multi_pct']:.1f}% "
                   f"({r['delta_pp']:+.1f}pp; final-turn {r['delta_pp_finalturn']:+.1f}pp)")
    rep.append(f"## Mixed-logistic sensitivity\n- {mixed_note}")
    (out / "summary.md").write_text("\n".join(rep) + "\n")
    print("\n".join(rep))
    print(f"\nWrote {out}/[per_backbone.csv per_category.csv transitions.csv "
          f"per_cell.csv summary.md]")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--root", type=Path, default=Path("experiments/metaseq"))
    parser.add_argument("--out", type=Path, default=Path("experiments/metaseq/summary"))
    parser.add_argument("--no-expected", action="store_true",
                        help="skip the expected headline-number asserts")
    args = parser.parse_args()
    aggregate(args.root, args.out, check_expected=not args.no_expected)


if __name__ == "__main__":
    main()
