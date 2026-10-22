"""Check every experiment-2 number the manuscript quotes against the report that
`metaseq report study` wrote, and print them.

    uv run --project phase3_replication python scripts/aggregate_replication.py

Exits non-zero when a quoted number no longer matches. The report itself is regenerated from
the stored runs by `cd phase3_replication && uv run metaseq report study`.
"""

from __future__ import annotations

import replication_tables as rt

# The numbers as the manuscript and its SI quote them (one decimal unless stated).
QUOTED = {
    "accuracy": {"qwen3.8-27b": (60.7, 76.9), "qwen3.8-flash": (69.4, 71.8), "gpt-6-luna": (72.7, 82.3),
                 "deepseek-v4-flash": (79.0, 83.8), "qwen3.8-27b-thinking": (79.0, 87.1),
                 "deepseek-v4-flash-thinking": (81.7, 88.6), "deepseek-v4-pro-0813": (84.1, 84.7),
                 "claude-sonnet-5-5": (90.4, 97.9), "pooled": (77.1, 84.1)},
    "gain": {"qwen3.8-27b": (16.2, 9.9, 22.8), "qwen3.8-flash": (2.4, -3.9, 8.7), "gpt-6-luna": (9.6, 4.2, 15.3),
             "deepseek-v4-flash": (4.8, -0.6, 10.5), "qwen3.8-27b-thinking": (8.1, 3.6, 12.9),
             "deepseek-v4-flash-thinking": (6.9, 2.1, 12.0), "deepseek-v4-pro-0813": (0.6, -4.8, 6.6),
             "claude-sonnet-5-5": (7.5, 3.0, 12.3), "pooled": (7.0, 4.7, 9.6)},
    "pooled_p_max": 0.0005,                   # bootstrap p reported as < 10^-3
    "recovered_regressed": (362, 175),
    "sign_test": {"all": (8, 8, 0.0078), "distinct": (6, 6, 0.0313), "significant": 5},
    "tokens_per_task_ratio": (2.4, 4.8),      # D / A, range over backbones
    "tokens_per_correct_ratio": (2.3, 4.4),
    "step_cap_turns": {"qwen3.8-flash": (2, 233), "qwen3.8-27b": (14, 85)},   # A, D
    "runs": 5328,
    "preband": {"A": 72.1, "D": 77.9, "gain": (5.8, 2.1, 9.7),   # the first three backbones only
                "models": ["deepseek-v4-flash", "gpt-6-luna", "qwen3.8-flash"]},
    "multiturn": {"after_failed": (59.2, 80.3), "after_passed": (88.5, 91.9),   # A, D
                  "third": (78.2, 91.7), "n_after_failed": (184, 132)},
    "thinking": {"qwen3.8-27b": dict(gain_reasoning=18.3, gain_orchestration=16.2, gain_both=26.4,
                                     diff=(2.1, -3.6, 7.8)),
                 "deepseek-v4-flash": dict(gain_reasoning=2.7, gain_orchestration=4.8, gain_both=9.6,
                                           diff=(-2.1, -7.8, 3.6))},
    "cross_model": {("qwen3.8-27b-thinking", "deepseek-v4-pro-0813"): (3.0, -3.9, 9.9)},
    "consistency": {"all_three": (62.6, 71.5), "none": (10.9, 5.7)},        # A, D (% of cells)
    "fixed_broken": {"unset": (123, 27), "gross >=50%": (53, 19), "near miss <2%": (83, 48),
                     "mid 2-50%": (73, 49), "other/unparsed": (30, 32)},          # largest reported error; fixed, broken
    "convergent": {"n_tasks": 18, "failed_share": 36, "A_on": 53.5, "D_on": 61.6, "A_off": 81.7, "D_off": 88.5,
                   "families": {2: 10, 3: 8}},        # tasks by number of model families sharing the wrong value
    "mixed_model": {"odds_ratio": 2.09, "or_lo": 1.83, "or_hi": 2.38},   # protocol's primary model, A/D only
    "vote": {"G": 81.1, "D_minus_G": (3.0, 0.3, 6.0), "tokens_ratio": 1.08, "backbones_positive": 6},   # G: A x3 voted
    "final_turn": (81.1, 88.1),               # pooled A, D under the final-turn-only rule
    "per_task": {"higher": 67, "equal": 23, "lower": 21, "top20_share": 69},   # Fig. 4a: D - A over 24 runs per task
    "headroom": (-0.61, 0.016),               # Spearman rho, p over the 15 comparisons of both experiments
    "verifier": {"corrected": 342, "broken": 122, "before": 77.2, "after": 84.1, "delta": (6.9, 5.3, 8.7),
                 "turns": 4080, "label_flips_broken": 22,
                 "before_minus_A": (0.1, -2.6, 2.9), "before_minus_A_range": (-11, 9)},   # the pre-verifier audit (post hoc)
    "cases": {"beijing_olympics_meteorological_adjustment": (3, 8),   # passed of 9, A / D
              "hk_ozone_peak_season_aqo": (0, 7),
              "hk_weekend_ozone_ox_conservation": (9, 6)},
    "cases_turn1": {"hk_ozone_peak_season_aqo": (0, 9)},
    "repeats": {"higher": 21, "equal": 2, "lower": 1},   # backbone-repeat comparisons, D vs A runs passed
}


def check(name: str, got, expected, tol: float = 0.051) -> None:
    pairs = zip(got, expected, strict=True) if isinstance(expected, tuple) else [(got, expected)]
    for g, e in pairs:
        assert abs(g - e) <= tol, f"{name}: got {got}, quoted {expected}"


def main() -> None:
    acc, con = rt.accuracy().set_index("model"), rt.contrasts().set_index("scope")
    arms = rt.arms().set_index(["arm", "model"])
    models = rt.models()
    assert set(models) == set(QUOTED["accuracy"]) - {"pooled"}, models
    for scope, quoted in QUOTED["accuracy"].items():
        check(f"accuracy {scope}", (acc.loc[scope, "A"], acc.loc[scope, "D"]), quoted)
    for scope, quoted in QUOTED["gain"].items():
        r = con.loc[scope]
        check(f"D - A {scope}", (r.delta_pp, r.lo_pp, r.hi_pp), quoted)
    assert con.loc["pooled", "p"] < QUOTED["pooled_p_max"], con.loc["pooled", "p"]
    check("recovered/regressed", (con.loc["pooled", "recovered"], con.loc["pooled", "regressed"]),
          QUOTED["recovered_regressed"], tol=0)
    st = rt.sign_test()
    for kind in ("all", "distinct"):
        k, n, p = QUOTED["sign_test"][kind]
        check(f"sign test {kind}", (st[kind]["positive"], st[kind]["n"]), (k, n), tol=0)
        check(f"sign test {kind} p", st[kind]["p"], p, tol=0.0005)
    check("backbones significant alone", st["all"]["significant"], QUOTED["sign_test"]["significant"], tol=0)
    per_task = [acc.loc[m, "tokens_D"] / acc.loc[m, "tokens_A"] for m in models]
    per_correct = [acc.loc[m, "per_correct_D"] / acc.loc[m, "per_correct_A"] for m in models]
    check("tokens per task D/A", (min(per_task), max(per_task)), QUOTED["tokens_per_task_ratio"])
    check("tokens per correct D/A", (min(per_correct), max(per_correct)), QUOTED["tokens_per_correct_ratio"])
    for m, quoted in QUOTED["step_cap_turns"].items():
        check(f"step-cap turns {m}", (arms.loc[(rt.A, m), "step_limit_turns"],
                                      arms.loc[(rt.D, m), "step_limit_turns"]), quoted, tol=0)
    check("runs", len(rt.outcomes()), QUOTED["runs"], tol=0)
    mt = rt.multiturn()
    for name, quoted in QUOTED["multiturn"].items():
        check(f"multi-turn {name}", (mt.loc[rt.A, name], mt.loc[rt.D, name]), quoted,
              tol=0 if name.startswith("n_") else 0.051)
    tp = rt.thinking_pairs()
    for m, q in QUOTED["thinking"].items():
        for k in ("gain_reasoning", "gain_orchestration", "gain_both"):
            check(f"thinking {m} {k}", tp.loc[m, k], q[k])
        check(f"thinking {m} diff", (tp.loc[m, "diff_pp"], tp.loc[m, "diff_lo"], tp.loc[m, "diff_hi"]), q["diff"])
    for (small, large), q in QUOTED["cross_model"].items():
        check(f"{small}+D vs {large} A", rt.cross_model(small, large), q)
    rc = rt.repeat_consistency()
    for k, q in QUOTED["consistency"].items():
        check(f"consistency {k}", (rc.loc[rt.A, k], rc.loc[rt.D, k]), q)
    fb = rt.fixed_broken_by_class()
    for cls, q in QUOTED["fixed_broken"].items():
        check(f"fixed/broken {cls}", (fb.loc[cls, "fixed"], fb.loc[cls, "broken"]), q, tol=0)
    cv = rt.convergent_tasks()
    check("convergent tasks", cv["n_tasks"], QUOTED["convergent"]["n_tasks"], tol=0)
    check("convergent failed share", cv["failed_share"], QUOTED["convergent"]["failed_share"], tol=0.51)
    for k in ("A_on", "D_on", "A_off", "D_off"):
        check(f"convergent {k}", cv[k], QUOTED["convergent"][k])
    import collections
    fam = dict(collections.Counter(cv["families"].values()))
    assert fam == QUOTED["convergent"]["families"], fam
    mm = rt.mixed_model()
    check("mixed model OR", (mm["odds_ratio"], mm["or_lo"], mm["or_hi"]),
          (QUOTED["mixed_model"]["odds_ratio"], QUOTED["mixed_model"]["or_lo"], QUOTED["mixed_model"]["or_hi"]), tol=0.011)
    assert mm["or_lo"] > 1, mm
    vb = rt.vote_baseline().set_index("model")
    check("vote G pooled", vb.loc["pooled", "G"], QUOTED["vote"]["G"])
    check("D - G pooled", (vb.loc["pooled", "delta_pp"], vb.loc["pooled", "lo_pp"], vb.loc["pooled", "hi_pp"]),
          QUOTED["vote"]["D_minus_G"])
    check("D/G tokens", vb.loc["pooled", "tokens_ratio"], QUOTED["vote"]["tokens_ratio"], tol=0.006)
    assert int(vb.loc["pooled", "backbones_positive"]) == QUOTED["vote"]["backbones_positive"], vb.backbones_positive
    o = rt.outcomes(); o["ok"] = o.passed.astype(float)
    t = o.groupby(["task", "arm"]).ok.mean().unstack(); d = 100 * (t[rt.D] - t[rt.A])
    q = QUOTED["per_task"]
    assert ((d > 0).sum(), (d == 0).sum(), (d < 0).sum()) == (q["higher"], q["equal"], q["lower"]), d.describe()
    check("top-20 share", 100 * d.sort_values(ascending=False).head(20).sum() / d.sum(), q["top20_share"], tol=0.51)
    import csv
    from scipy.stats import spearmanr
    with open(rt.ROOT / "phase2_benchmark/experiments/metaseq/summary/per_backbone.csv") as f:
        e1 = [(2 * int(r["single"]), 2 * (int(r["multi"]) - int(r["single"]))) for r in csv.DictReader(f)]
    e2 = [(acc.loc[m, "A"], acc.loc[m, "D"] - acc.loc[m, "A"]) for m in models]
    rho, pval = spearmanr(*zip(*(e1 + e2)))
    check("headroom rho, p", (rho, pval), QUOTED["headroom"], tol=0.006)
    va = rt.verifier_audit(); vt = va["table"]; qv = QUOTED["verifier"]
    assert (int(vt.loc["pooled", "corrected"]), int(vt.loc["pooled", "broken"])) == (qv["corrected"], qv["broken"]), vt.loc["pooled"]
    check("verifier pass before/after", (vt.loc["pooled", "pass_before"], vt.loc["pooled", "pass_after"]), (qv["before"], qv["after"]))
    check("verifier delta", (va["delta_pp"], va["lo_pp"], va["hi_pp"]), qv["delta"])
    assert va["turns"] == qv["turns"], va["turns"]
    assert (vt.drop("pooled").corrected > vt.drop("pooled").broken).all(), vt
    assert (va["by_domain"]["corrected"] > va["by_domain"]["broken"]).all(), va["by_domain"]
    import numpy as np
    bA = rt.before_minus_single()
    check("D-before minus A", (bA["delta_pp"], bA["lo_pp"], bA["hi_pp"]), qv["before_minus_A"])
    per = bA["per_backbone"]
    assert (round(per.min()), round(per.max())) == qv["before_minus_A_range"], (per.min(), per.max())
    ft = rt.final_turn_rule()
    check("final-turn rule", (ft["A"], ft["D"]), QUOTED["final_turn"])
    assert ft["n"] == QUOTED["runs"] // 2, ft
    cases = rt.case_counts()
    for task, quoted in QUOTED["cases"].items():
        check(f"case {task}", (cases.loc[(task, rt.A), "passed"], cases.loc[(task, rt.D), "passed"]), quoted, tol=0)
    for task, quoted in QUOTED["cases_turn1"].items():
        check(f"case turn 1 {task}", (cases.loc[(task, rt.A), "turn1_passed"],
                                      cases.loc[(task, rt.D), "turn1_passed"]), quoted, tol=0)
    br = rt.by_repeat().loc["pooled"]
    assert tuple(int(br[("D_vs_A", k)]) for k in ("higher", "equal", "lower")) == tuple(QUOTED["repeats"].values()), br
    before = rt.preband()
    assert before["models"] == QUOTED["preband"]["models"], before["models"]
    check("pre-band A, D", (before["A"], before["D"]), (QUOTED["preband"]["A"], QUOTED["preband"]["D"]))
    check("pre-band D - A", before["gain"], QUOTED["preband"]["gain"])

    print("accuracy (%), A -> D:")
    for scope in [*models, "pooled"]:
        r = con.loc[scope]
        print(f"  {scope:28s} {acc.loc[scope, 'A']:.1f} -> {acc.loc[scope, 'D']:.1f}"
              f"   D - A {r.delta_pp:+.1f} [{r.lo_pp:+.1f}, {r.hi_pp:+.1f}]  p {r.p:.3g}"
              f"  {int(r.recovered)}/{int(r.regressed)}")
    print("sign test:", st)
    print("tokens per task D/A: " + ", ".join(f"{m} {x:.2f}" for m, x in zip(models, per_task, strict=True)))
    print("tokens per correct D/A: " + ", ".join(f"{m} {x:.2f}" for m, x in zip(models, per_correct, strict=True)))
    print("multi-turn (A, D): after failed %.1f/%.1f, after passed %.1f/%.1f, third %.1f/%.1f"
          % (mt.loc[rt.A, "after_failed"], mt.loc[rt.D, "after_failed"],
             mt.loc[rt.A, "after_passed"], mt.loc[rt.D, "after_passed"], mt.loc[rt.A, "third"], mt.loc[rt.D, "third"]))
    print(tp.round(1).to_string()); print(rc.round(1).to_string())
    print("every quoted number matches the report")


if __name__ == "__main__":
    main()
