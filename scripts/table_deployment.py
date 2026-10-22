"""Deployment evaluation (117 Hong Kong queries, six backbones, three LLM judges): the
per-query scores as the paper reads them, and Supplementary Table 5 written from them.

    uv run --project phase3_replication python scripts/table_deployment.py

Reads phase1_evaluation/eval_results/hk/<model>/hk_cat_<k>_agent_<model>_judge_<judge>_eval_results.json
(k = 1..6; each file holds the queries of one taxonomy category, each query scored on the
five criteria by that judge). A query's score under a judge is the mean of its five criterion
scores; a backbone's score is the mean over the three judges, then over the 117 queries, with
a t-based 95% confidence interval over queries. Writes manuscript/tex/table_deployment.tex and
asserts the deployment numbers the main text quotes.
"""

from __future__ import annotations

import json
import math
import statistics as st
import re
from scipy.stats import t
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "phase1_evaluation" / "eval_results" / "hk"
OUT = ROOT / "manuscript" / "tex" / "table_deployment.tex"

MODELS = ["gpt5", "gemini", "qwen3", "claude4", "kimi2", "deepseek"]
JUDGES = ["kimi2", "claude4", "qwen3"]                      # the fixed judge panel
BASELINE = "control_group_1"                                # C1: Claude-4-sonnet with a web-search tool only
PRIMARY = "claude4"                                         # C3's backbone in the pairwise comparison
LABELS = {"gpt5": "GPT-5", "claude4": "Claude-4-sonnet", "gemini": "Gemini-2.5-Pro", "kimi2": "Kimi-K2",
          "qwen3": "Qwen3-235B", "deepseek": "DeepSeek-V3", "control_group_1": "Claude-4-sonnet, web only"}
JUDGE_LABELS = {"kimi2": "Kimi-K2", "claude4": "Claude-4-sonnet", "qwen3": "Qwen3-235B"}
# The query taxonomy's six categories, grouped into the three higher-order classes of
# Supplementary Table 1 and Methods (13 + 19, 18, 31 + 14 + 22 queries).
GROUPS = {"Spatial--temporal analysis": [1, 2], "Feature analysis": [3], "Environmental management": [4, 5, 6]}
CRITERIA = ["Methodological Soundness", "Technical Implementation Quality", "Data Integration and Synthesis",
            "Response Alignment", "Faithfulness"]
N_QUERIES = 117
# The baseline's category-3 file also holds an earlier wording of the typhoon query, which the
# final 117-query set replaced; it is not among the backbones' queries and is skipped.
DROPPED = {"Search for the time period of the most recent typhoon affecting Hong Kong this year. "
           "Analyze how the air quality at The University of Hong Kong is affected by the typhoon during that period."}


def load(model: str) -> dict[str, list[dict]]:
    """For each judge, the 117 queries in category order: {"category": k, "criteria": {name: score}}."""
    out = {}
    for judge in JUDGES:
        rows = []
        for k in range(1, 7):
            path = EVAL / model / f"hk_cat_{k}_agent_{model}_judge_{judge}_eval_results.json"
            for case in json.loads(path.read_text())["case_eval_results"]:
                if case["input"].strip() in DROPPED:
                    continue
                crit = {m["metric_name"].replace(" [GEval]", ""): float(m["score"]) for m in case["metrics"]}
                assert set(crit) == set(CRITERIA), (path, sorted(crit))
                query = re.sub(r"^# User query:\s*", "", case["input"].strip())
                rows.append({"query": query, "category": k, "criteria": crit})
        assert len(rows) == N_QUERIES, (model, judge, len(rows))
        out[judge] = rows
    # Some judges export the same queries in a different order. Join by identity,
    # never by row number, before computing per-query means or correlations.
    reference = [row["query"] for row in out[JUDGES[0]]]
    assert len(set(reference)) == N_QUERIES
    for judge, rows in out.items():
        keyed = {row["query"]: row for row in rows}
        assert len(keyed) == N_QUERIES and set(keyed) == set(reference), (model, judge)
        out[judge] = [keyed[query] for query in reference]
        assert all(a["category"] == b["category"] for a, b in zip(out[JUDGES[0]], out[judge]))
    return out


def query_scores(data: dict[str, list[dict]], judges: list[str] | None = None,
                 categories: list[int] | None = None, criterion: str | None = None) -> list[float]:
    """One score per query: the mean over the given judges of the query's criterion mean
    (or of one criterion), restricted to the given taxonomy categories."""
    judges = judges or JUDGES
    idx = [i for i, r in enumerate(data[judges[0]]) if categories is None or r["category"] in categories]
    out = []
    for i in idx:
        per_judge = []
        for j in judges:
            c = data[j][i]["criteria"]
            per_judge.append(c[criterion] if criterion else st.mean(c.values()))
        out.append(st.mean(per_judge))
    return out


def mean_ci(xs: list[float]) -> tuple[float, float]:
    """Mean and the half-width of its t-based 95% interval over queries."""
    n = len(xs)
    return st.mean(xs), float(t.ppf(.975, n - 1)) * st.stdev(xs) / math.sqrt(n) if n > 1 else 0.0


def table5() -> list[list[str]]:
    rows = []
    for m in MODELS:
        d = load(m)
        cells = [LABELS[m]]
        for j in JUDGES:
            mu, hw = mean_ci(query_scores(d, [j]))
            cells.append(f"${mu:.3f}_{{(\\pm {hw:.3f})}}$")
        mu, hw = mean_ci(query_scores(d))
        cells.append(f"${mu:.3f}_{{(\\pm {hw:.3f})}}$")
        rows.append(cells)
    return rows


def checks() -> dict:
    """The deployment numbers the main text quotes, recomputed."""
    means = {m: st.mean(query_scores(load(m))) for m in MODELS}
    excl = {}
    for m in MODELS:
        if m in JUDGES:
            d = load(m)
            excl[m] = st.mean(query_scores(d, [j for j in JUDGES if j != m])) - means[m]
    pooled = {j: [s for m in MODELS for s in query_scores(load(m), [j])] for j in JUDGES}
    r = {}
    for a, b in combinations(JUDGES, 2):
        xa, xb = pooled[a], pooled[b]
        ma, mb = st.mean(xa), st.mean(xb)
        r[(a, b)] = sum((x - ma) * (y - mb) for x, y in zip(xa, xb)) / math.sqrt(
            sum((x - ma) ** 2 for x in xa) * sum((y - mb) ** 2 for y in xb))
    return {"means": means, "self_judge_shift": excl, "pairwise_r": r}


def main() -> None:
    body = [" & ".join(r) + r" \\" for r in table5()]
    tex = r"""\centering
\footnotesize
\begin{tabular}{@{}lccc@{\hspace{14pt}}c@{}}
\toprule
 & \multicolumn{3}{c}{Judge} & \\
\cmidrule(lr){2-4}
Backbone & """ + " & ".join(JUDGE_LABELS[j] for j in JUDGES) + r""" & Three-judge mean \\
\midrule
""" + "\n".join(body) + r"""
\bottomrule
\end{tabular}
"""
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(tex)
    print("written", OUT)

    c = checks()
    lo, hi = min(c["means"].values()), max(c["means"].values())
    print("three-judge means:", {LABELS[m]: round(v, 3) for m, v in c["means"].items()})
    print("shift when the backbone's own judge is excluded:", {LABELS[m]: round(v, 3) for m, v in c["self_judge_shift"].items()})
    print("pairwise judge r:", {k: round(v, 2) for k, v in c["pairwise_r"].items()})
    # as quoted in the main text (Results and Methods, deployment evaluation)
    assert round(lo, 2) == 0.80 and round(hi, 2) == 0.92, (lo, hi)
    assert max(abs(v) for v in c["self_judge_shift"].values()) <= 0.04, c["self_judge_shift"]
    # two judges score their own backbone lower than the panel does (excluding them raises the mean)
    assert sum(v > 0 for v in c["self_judge_shift"].values()) == 2, c["self_judge_shift"]
    rs = list(c["pairwise_r"].values())
    assert round(st.mean(rs), 2) == 0.69 and round(min(rs), 2) == 0.66 and round(max(rs), 2) == 0.71, rs
    # every judge ranks the same backbone first and the same one last
    for j in JUDGES:
        order = sorted(MODELS, key=lambda m: -st.mean(query_scores(load(m), [j])))
        assert order[0] == "gpt5" and order[-1] == "deepseek", (j, order)
    print("all quoted deployment numbers hold")


if __name__ == "__main__":
    main()
