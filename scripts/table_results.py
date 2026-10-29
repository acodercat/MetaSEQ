"""Write manuscript/tex/table_results.tex: the paper's Table 1, single agent against MetaSEQ
on every backbone of both controlled experiments, from the same derived tables the text and
figures read (phase2 summary CSV; phase3 report through replication_tables).

    uv run --project phase3_replication python scripts/table_results.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

import replication_tables as rt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript" / "tex" / "table_results.tex"
EXP1 = ROOT / "phase2_benchmark" / "experiments" / "metaseq" / "summary" / "per_backbone.csv"
CELLS = EXP1.with_name("per_cell.csv")


def exp1_intervals(resamples: int = 10_000, seed: int = 20260929) -> dict[str, tuple[float, float]]:
    """95% percentile interval of the gain (MetaSEQ - single agent, pp) per backbone and pooled, from
    task resamples of the paired per-task differences: the estimator of experiment 2 (seed as there)."""
    with open(CELLS, newline="") as f:
        cells = list(csv.DictReader(f))
    diff: dict[str, dict[str, int]] = {}
    for c in cells:
        diff.setdefault(c["public_name"], {}).setdefault(c["task"], {})[c["topology"]] = int(c["all_turns"])
    tasks = sorted({c["task"] for c in cells})
    per = {m: np.array([diff[m][t]["multi"] - diff[m][t]["single"] for t in tasks], dtype=float) for m in diff}
    draws = np.random.default_rng(seed).integers(0, len(tasks), (resamples, len(tasks)))
    out = {}
    for m, d in per.items():
        bs = 100 * d[draws].mean(axis=1)
        out[m] = (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))
    pooled = np.mean(list(per.values()), axis=0)          # per-task mean over the seven backbones
    bs = 100 * pooled[draws].mean(axis=1)
    out["Pooled"] = (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))
    return out


def exp1_rows() -> list[list[str]]:
    with open(EXP1, newline="") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: int(r["single"]))
    ci = exp1_intervals()
    out = []
    for r in rows:
        a, d = 2 * int(r["single"]), 2 * int(r["multi"])         # 50 tasks -> percent
        ratio = float(r["avg_tokens_multi"]) / float(r["avg_tokens_single"])
        lo, hi = ci[r["public_name"]]
        out.append([r["public_name"], f"{a:.0f}", f"{d:.0f}", f"{d - a:+.0f}", f"[{lo:+.0f}, {hi:+.0f}]", f"{ratio:.1f}"])
    ks = sum(int(r["single"]) for r in rows); km = sum(int(r["multi"]) for r in rows); n = 50 * len(rows)
    tok_a = sum(float(r["avg_tokens_single"]) for r in rows) / len(rows)
    tok_d = sum(float(r["avg_tokens_multi"]) for r in rows) / len(rows)
    lo, hi = ci["Pooled"]
    out.append([r"\textbf{Pooled}", f"{100 * ks / n:.1f}", f"{100 * km / n:.1f}", f"{100 * (km - ks) / n:+.1f}",
                f"[{lo:+.1f}, {hi:+.1f}]", f"{tok_d / tok_a:.1f}"])
    return out


def exp2_rows() -> list[list[str]]:
    acc = rt.accuracy().set_index("model")
    con = rt.contrasts().set_index("scope")
    out = []
    for m in rt.models():
        r = con.loc[m]
        out.append([rt.LABELS[m], f"{acc.loc[m, 'A']:.1f}", f"{acc.loc[m, 'D']:.1f}", f"{r.delta_pp:+.1f}",
                    f"[{r.lo_pp:+.1f}, {r.hi_pp:+.1f}]", f"{acc.loc[m, 'tokens_D'] / acc.loc[m, 'tokens_A']:.1f}"])
    r = con.loc["pooled"]
    out.append([r"\textbf{Pooled}", f"{acc.loc['pooled', 'A']:.1f}", f"{acc.loc['pooled', 'D']:.1f}",
                f"{r.delta_pp:+.1f}", f"[{r.lo_pp:+.1f}, {r.hi_pp:+.1f}]",
                f"{acc.loc['pooled', 'tokens_D'] / acc.loc['pooled', 'tokens_A']:.1f}"])
    return out


def main() -> None:
    body = []
    body.append(r"\multicolumn{6}{@{}l}{\textbf{Experiment 1} | 50 tasks; one run; analysis rules included; 20 steps} \\")
    body.append(r"\addlinespace[3pt]")
    body += [" & ".join(r) + r" \\" for r in exp1_rows()]
    body.append(r"\midrule")
    body.append(r"\multicolumn{6}{@{}l}{\textbf{Experiment 2} | 111 tasks; three repeats; analysis rules removed; 50 steps} \\")
    body.append(r"\addlinespace[3pt]")
    body += [" & ".join(r) + r" \\" for r in exp2_rows()]
    tex = r"""\begin{table}[!ht]
\centering
\fontsize{8.5}{11}\selectfont
\caption{\textbf{Single agent and MetaSEQ on every backbone of both experiments.} Validated accuracy, per cent. Gain: experiment 1, difference of single runs on 50 tasks; experiment 2, mean paired difference over three repeats; 95\% intervals from 10,000 task resamples in both (tests in Supplementary Table~7). Tokens: MetaSEQ's mean tokens per task as a multiple of the single agent's. Experiment 1 runs the deployed prompts, which carry the analysis rules, with a verifier that checks staged intermediates; experiment 2 runs the prompts with the rules removed and a verifier that recomputes every output (Table~\ref{tab:experiments}).}
\label{tab:results}
\setlength{\tabcolsep}{4pt}\renewcommand{\arraystretch}{1.12}
\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}lrrrrr@{}}
\toprule
Backbone & \shortstack[r]{Single agent\\(\%)} & \shortstack[r]{MetaSEQ\\(\%)} & \shortstack[r]{Gain\\(pp)} & 95\% interval & \shortstack[r]{Tokens\\D / A} \\
\midrule
""" + "\n".join(body) + r"""
\bottomrule
\end{tabular*}
\par\smallskip\raggedright\fontsize{8}{10}\selectfont
Experiment 1 pooled McNemar $p=1.7\times10^{-5}$; its per-backbone gains are descriptive (Methods).
\end{table}
"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(tex)
    print("written", OUT)


if __name__ == "__main__":
    main()
