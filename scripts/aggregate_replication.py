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
    "step_cap_turns": {"qwen3.8-flash": (2, 233), "qwen3.8-27b": (14, 85)},   # A, D: turns with a stage at its cap
    "step_cap_full": {"qwen3.8-flash": (510, 2, 135)},   # turns per arm; A and D turns that used all 50 steps
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
    "vote": {"G": 81.1, "D_minus_G": (3.0, 0.3, 6.0), "tokens_ratio": 1.08, "backbones_positive": 6},   # G: A x3 voted
    "final_turn": (81.1, 88.1),               # pooled A, D under the final-turn-only rule
    "per_task": {"higher": 67, "equal": 23, "lower": 21, "top20_share": 69},   # Fig. 5a: D - A over 24 runs per task
    "headroom": (-0.61, 0.016),               # Spearman rho, p over the 15 comparisons of both experiments
    "cases": {"beijing_olympics_meteorological_adjustment": (3, 8),   # passed of 9, A / D
              "hk_ozone_peak_season_aqo": (0, 7),
              "hk_weekend_ozone_ox_conservation": (9, 6)},
    "cases_turn1": {"hk_ozone_peak_season_aqo": (0, 9)},
    "repeats": {"higher": 21, "equal": 2, "lower": 1},   # backbone-repeat comparisons, D vs A runs passed
    # ---- the six-arm study (study_*.csv): the registered 2 x 2, G, and the exploratory delegation arms
    "runs6": 15984, "vote_cells": 888, "configurations6": 48,
    # --- where the gain comes from (exploratory; Fig. 5d, Supplementary Tables 27-31) ---
    "by_baseline": {"<=5 of 8": dict(n=34, verification=(9.7, 6.2, 13.6), decomposition=(3.3, -0.3, 7.0)),
                    "6-7 of 8": dict(n=39, verification=(4.7, 2.2, 7.3), decomposition=(-0.6, -3.4, 2.2)),
                    "8 of 8": dict(n=38, verification=(1.4, -0.6, 3.2), decomposition=(0.9, -0.7, 2.5)),
                    "spearman": {"verification": -0.53, "decomposition": -0.33}},   # task-level rho against A
    "by_turns": {"single-turn": dict(n=61, verification=(4.2, 2.4, 6.0), decomposition=(2.0, 0.1, 3.9)),
                 "multi-turn": dict(n=50, verification=(7.0, 4.5, 9.8), decomposition=(1.0, -1.5, 3.5), D_minus_B=(-1.3, -3.4, 0.6))},
    "by_category": {"regulatory_standards": dict(A=67.2, verification=(7.6, 2.6, 12.6)),
                    "spatial_analysis": dict(decomposition=(-2.9, -5.0, -0.8)),
                    "decomposition_excluding_zero": ["spatial_analysis"]},   # the only category whose decomposition interval excludes zero
    "by_kind": {"regulatory": dict(n=23, A=67.2, verification=(9.4, 5.4, 13.4)), "regulatory_minus_others": (5.0, 0.7, 9.4)},
    "consistency_all": {"all_three": {"A": 62.6, "B": 73.1, "C": 67.5, "D": 71.5}, "none": {"A": 10.9, "B": 7.1},
                        "B-A": (10.5, 7.0, 14.1), "D-C": (4.1, 1.1, 7.1), "D-B": (-1.6, -4.1, 0.9)},
    "transitions": {"fixed": 695, "survived": 576, "broke": 231, "kept": 10810,   # outputs of D, before -> after the verifier
                    "fix_rate": {"order of magnitude": 33, "1-10%": 58}},
    "shared_judgements": {("beijing_fire_detection_bias", "fires_shown_not_to_matter"): (20, 5, 2),   # runs, backbones, families
                          ("hk_cloud_enhancement_extreme", "above_constant_is_error"): (14, 4, 2),
                          ("hk_weekend_ozone_ox_conservation", "line_can_be_written"): (7, 4, 2)},
    "prose_credit": {"hit_rate": 66, "unset_numeric": 180, "credited_runs": 46, "failed_runs": 610,
                     "D_minus_A": (7.0, 4.7, 9.6), "D_minus_A_credited": (5.3, 3.0, 7.9), "credit": (1.7, 1.1, 2.4)},
    "per_model_category": {"gpt-6-luna": {"regulatory_standards": (51, 67)}, "claude-sonnet-5-5": {"regulatory_standards": (78, 100)}},   # A, B   # arm x backbone cells with their own runs (six arms, eight backbones)
    "arms6": {"A": 77.1, "B": 84.2, "C": 80.3, "D": 84.1, "F": 78.5, "FV": 84.8, "G": 81.1},   # pooled accuracy (%)
    "factorial": {"verification": (5.4, 3.9, 7.1), "decomposition": (1.6, 0.1, 3.2),
                  "interaction": (-3.2, -6.1, -0.6), "H2": (3.9, 2.0, 5.9)},      # pp, 95% interval
    "core": {"H1": (7.0, 4.7, 9.6), "H2a": (7.1, 4.8, 9.6), "H2b": (3.2, 0.6, 5.9), "H2c": (-0.0, -1.4, 1.2)},
    "core_holm_max": {"H1": 0.001, "H2a": 0.001, "H2c": 1.0},   # H2b's Holm p is quoted exactly below
    "H2b_holm": 0.026,
    "core_pairs": {"H1": (362, 175), "H2a": (343, 155), "H2b": (319, 234), "H2c": (195, 196)},
    "delegation": {"F-A": (1.4, -0.8, 3.8), "FV-F": (6.3, 4.3, 8.3), "FV-B": (0.6, -0.6, 2.0), "FV-D": (0.7, -0.8, 2.1),
                   "F-B": (-5.6, -7.8, -3.5)},
    "tokens_per_correct_k": {"A": 172, "B": 341, "C": 377, "D": 509, "F": 253, "FV": 409, "G": 490},   # pooled, thousands
    "cost_D_minus_B_k": (169, 147, 192),       # tokens per correct task, thousands (H4)
    "verifier_turns": {"B": (427, 149), "D": (342, 122), "FV": (383, 134), "verified": 4080},   # fixed, broken
    "verifier_turns_D_range": {"claude-sonnet-5-5": (6, 0), "deepseek-v4-pro-0813": (45, 27)},   # fewest and most broken
    "verifier_changed_pct": {"B": 14.1, "D": 11.4},        # share of the 4,080 turns whose verdict the verifier changed
    "claude_C_D": (98.5, 97.9),                            # Claude Sonnet 5.5, C against D: a net verifier gain within runs, a lower arm
    "p_values": {"verification": 0.0, "decomposition": 0.044, "interaction": 0.013, "H2c": 0.98,   # bootstrap p at zero;
                 "H1_holm": 0.0, "H2a_holm": 0.0},                                                  # 0.0 is quoted as p < 1e-4
    "D_minus_B_uncapped": {"claude-sonnet-5-5": -1.2, "gpt-6-luna": -0.6, "deepseek-v4-pro-0813": 1.5, "max_D_cap_turns": 11},
    "turn_accuracy": {"A": 83.1, "B": 89.1, "C": 85.9, "D": 89.0},   # per cent of 4,080 turns per arm
    "elapsed_s": {"A": 69, "B": 155, "C": 187, "D": 261},            # mean seconds per run
    "verification_range": (0.8, 9.6),                                  # per-backbone verification effect, min and max
    "step_cap_by_arm_D": {"qwen3.8-flash": 233, "qwen3.8-27b": 85, "deepseek-v4-flash": 36},
    "step_cap_by_arm_B": {"qwen3.8-flash": 40, "qwen3.8-27b": 41, "deepseek-v4-flash": 6},
    "per_model_effects": {"verification_positive": 8, "verification_significant": 6,
                          "decomposition_significant": ["qwen3.8-27b", "claude-sonnet-5-5"],
                          "qwen3.8-27b": (9.0, 7.2), "claude-sonnet-5-5": (4.1, 3.5)},   # verification, decomposition (pp)
    "vote_vs_B": {"B_minus_G": (3.1, 0.4, 6.1), "backbones_positive": 6},
    "D_minus_C": (3.8, 2.2, 5.5), "G_minus_A": (4.0, 2.8, 5.1),
    "by_model": {"qwen3.8-flash": {"H2a": 5.7, "H1": 2.4}, "qwen3.8-27b": {"B": 74.2}},
    "turns6": 24480,
    "sensitivity": {"no_cap": {"cells": 680, "verification": (5.7, 3.9, 7.5), "decomposition": (1.7, -0.0, 3.5), "D_minus_B": (0.6, -0.9, 2.1)},
                    "six_model": {"verification": (5.0, 3.6, 6.6), "decomposition": (1.3, -0.2, 2.8)}},
    "verifier_kinds_D": {"fixed_wrong": 269, "fixed_missing": 73, "broken_wrong": 121, "broken_missing": 1},
    "bayes": {"verification": (5.4, 4.3, 6.6), "decomposition": (1.6, 0.5, 2.7), "interaction": (-3.2, -5.5, -1.0),
              "H2c": (-0.0, -1.6, 1.5)},   # the registered bambi/PyMC model, pooled, probability scale
}


def check(name: str, got, expected, tol: float = 0.051) -> None:
    pairs = zip(got, expected, strict=True) if isinstance(expected, tuple) else [(got, expected)]
    for g, e in pairs:
        assert abs(g - e) <= tol, f"{name}: got {got}, quoted {expected}"


def check_study() -> None:
    """The six-arm study tables: every number of the factorial section."""
    so = rt.study_outcomes()
    check("study runs", int((so.arm != rt.G).sum()), QUOTED["runs6"], tol=0)
    check("vote cells", int((so.arm == rt.G).sum()), QUOTED["vote_cells"], tol=0)
    check("study configurations", int(so[so.arm != rt.G].groupby(["arm", "model"]).ngroups), QUOTED["configurations6"], tol=0)
    key = {"A": rt.A, "B": rt.B, "C": rt.C, "D": rt.D, "F": rt.F, "FV": rt.FV, "G": rt.G}
    acc = rt.arm_accuracy().loc["pooled"]
    for k, q in QUOTED["arms6"].items():
        check(f"arm {k} pooled", acc[key[k]], q)
    check("A and D as in the two-arm report", (acc[rt.A], acc[rt.D]), QUOTED["accuracy"]["pooled"])
    fx = rt.factorial()
    for e, q in QUOTED["factorial"].items():
        check(f"factorial {e}", (fx.loc[e, "estimate_pp"], fx.loc[e, "lo_pp"], fx.loc[e, "hi_pp"]), q)
    assert fx.loc["verification", "estimate_pp"] > fx.loc["decomposition", "hi_pp"], fx   # H2 as registered
    cc = rt.core_contrasts()
    for h, q in QUOTED["core"].items():
        r = cc.loc[h]
        check(f"core {h}", (r.delta_pp, r.lo_pp, r.hi_pp), q)
        check(f"core {h} pairs", (r.recovered, r.regressed), QUOTED["core_pairs"][h], tol=0)
    for h, q in QUOTED["core_holm_max"].items():
        assert cc.loc[h, "holm_p"] <= q, (h, cc.loc[h, "holm_p"])
    check("H2b Holm p", cc.loc["H2b", "holm_p"], QUOTED["H2b_holm"], tol=0.0006)
    check("H1 equals the two-arm contrast", (cc.loc["H1", "delta_pp"], cc.loc["H1", "lo_pp"], cc.loc["H1", "hi_pp"]),
          QUOTED["gain"]["pooled"])
    dc = rt.delegation_contrasts()
    for k, q in QUOTED["delegation"].items():
        check(f"delegation {k}", (dc.loc[k, "delta_pp"], dc.loc[k, "lo_pp"], dc.loc[k, "hi_pp"]), q)
    tpc = rt.tokens_per_correct().loc["pooled"]
    for k, q in QUOTED["tokens_per_correct_k"].items():
        check(f"tokens per correct {k}", tpc[key[k]] / 1e3, q, tol=0.51)
    cost = rt.cost_contrast()
    check("D - B tokens per correct", (cost["diff"] / 1e3, cost["lo"] / 1e3, cost["hi"] / 1e3), QUOTED["cost_D_minus_B_k"], tol=0.51)
    check("D, B tokens per correct", (cost["D"] / 1e3, cost["B"] / 1e3), (QUOTED["tokens_per_correct_k"]["D"], QUOTED["tokens_per_correct_k"]["B"]), tol=0.51)
    vt = rt.verifier_turns().loc["pooled"]
    for k, (fixed, broken) in ((k, v) for k, v in QUOTED["verifier_turns"].items() if k != "verified"):
        check(f"verifier turns {k}", (vt[(key[k], "fixed")], vt[(key[k], "broken")]), (fixed, broken), tol=0)
        check(f"verified turns {k}", vt[(key[k], "verified")], QUOTED["verifier_turns"]["verified"], tol=0)
    sc = rt.step_cap_by_arm()
    for m, q in QUOTED["step_cap_by_arm_D"].items():
        check(f"D turns at cap {m}", sc.loc[m, rt.D], q, tol=0)
    for m, q in QUOTED["step_cap_by_arm_B"].items():
        check(f"B turns at cap {m}", sc.loc[m, rt.B], q, tol=0)
    pm = rt.per_model_effects(); q = QUOTED["per_model_effects"]
    check("verification positive", int((pm.verification_pp > 0).sum()), q["verification_positive"], tol=0)
    check("verification significant", int((pm.verification_lo > 0).sum()), q["verification_significant"], tol=0)
    assert list(pm.index[pm.decomposition_lo > 0]) == q["decomposition_significant"], pm[pm.decomposition_lo > 0]
    for m in q["decomposition_significant"]:
        check(f"effects {m}", (pm.loc[m, "verification_pp"], pm.loc[m, "decomposition_pp"]), q[m])
    vv = rt.vote_vs_verified()
    check("B - G pooled", (vv.loc["pooled", "delta_pp"], vv.loc["pooled", "lo_pp"], vv.loc["pooled", "hi_pp"]), QUOTED["vote_vs_B"]["B_minus_G"])
    check("B ahead of G on", int(vv.loc["pooled", "backbones_positive"]), QUOTED["vote_vs_B"]["backbones_positive"], tol=0)
    check("D - C", rt.pair_contrast(rt.D, rt.C), QUOTED["D_minus_C"])
    check("G - A", rt.pair_contrast(rt.G, rt.A), QUOTED["G_minus_A"])
    check("Qwen3.8-Flash B - A, D - A", (rt.core_contrasts("qwen3.8-flash").loc["H2a", "delta_pp"],
                                        rt.core_contrasts("qwen3.8-flash").loc["H1", "delta_pp"]),
          (QUOTED["by_model"]["qwen3.8-flash"]["H2a"], QUOTED["by_model"]["qwen3.8-flash"]["H1"]))
    check("Qwen3.8-27B B", rt.arm_accuracy().loc["qwen3.8-27b", rt.B], QUOTED["by_model"]["qwen3.8-27b"]["B"])
    check("scored turns", int(so[so.arm != rt.G].turns.sum()), QUOTED["turns6"], tol=0)
    vtb = rt.verifier_turns().drop("pooled")
    for arm in (rt.B, rt.D, rt.FV):
        assert (vtb[(arm, "fixed")] > vtb[(arm, "broken")]).all(), (arm, vtb[arm])   # a net gain on every backbone
    for m, q in QUOTED["verifier_turns_D_range"].items():
        check(f"verifier turns D {m}", (vtb.loc[m, (rt.D, "fixed")], vtb.loc[m, (rt.D, "broken")]), q, tol=0)
    assert vtb[(rt.D, "broken")].idxmin() == "claude-sonnet-5-5" and vtb[(rt.D, "broken")].idxmax() == "deepseek-v4-pro-0813", vtb[rt.D]
    pv = QUOTED["p_values"]; fxp = rt.factorial(); ccp = rt.core_contrasts()
    for k in ("verification", "decomposition", "interaction"):
        check(f"p {k}", fxp.loc[k, "p"], pv[k], tol=0.00051)
    check("p H2c", ccp.loc["H2c", "p"], pv["H2c"], tol=0.0051)
    check("Holm p H1, H2a", (ccp.loc["H1", "holm_p"], ccp.loc["H2a", "holm_p"]), (pv["H1_holm"], pv["H2a_holm"]), tol=0.00051)
    for k, q in QUOTED["verifier_changed_pct"].items():
        fixed, broken = QUOTED["verifier_turns"][k]
        check(f"verifier changed share {k}", 100 * (fixed + broken) / QUOTED["verifier_turns"]["verified"], q)
    acc = rt.arm_accuracy()
    check("Claude C, D", (acc.loc["claude-sonnet-5-5", rt.C], acc.loc["claude-sonnet-5-5", rt.D]), QUOTED["claude_C_D"])
    qu = QUOTED["D_minus_B_uncapped"]
    for m in ("claude-sonnet-5-5", "gpt-6-luna", "deepseek-v4-pro-0813"):
        check(f"D - B {m}", acc.loc[m, rt.D] - acc.loc[m, rt.B], qu[m])
        assert sc.loc[m, rt.D] <= qu["max_D_cap_turns"], (m, sc.loc[m, rt.D])
    assert max(sc.loc[m, rt.D] for m in ("claude-sonnet-5-5", "gpt-6-luna", "deepseek-v4-pro-0813")) == qu["max_D_cap_turns"]
    ta = rt.turn_accuracy(); el = rt.elapsed_per_run()
    for k, q in QUOTED["turn_accuracy"].items():
        check(f"turn accuracy {k}", ta[key[k]], q)
    for k, q in QUOTED["elapsed_s"].items():
        check(f"elapsed {k}", el[key[k]], q, tol=0.51)
    assert int(so[so.arm == rt.D].turns.sum()) == QUOTED["verifier_turns"]["verified"]   # 4,080 turns per arm
    check("verification range", (pm.verification_pp.min(), pm.verification_pp.max()), QUOTED["verification_range"])
    fs = rt.factorial_sensitivity()
    for cond, q in QUOTED["sensitivity"].items():
        for k, v in q.items():
            if k == "cells":
                check(f"sensitivity {cond} cells", fs.loc[cond, "cells"], v, tol=0)
            else:
                check(f"sensitivity {cond} {k}", (fs.loc[cond, f"{k}_pp"], fs.loc[cond, f"{k}_lo"], fs.loc[cond, f"{k}_hi"]), v)
    check("sensitivity all reproduces the factorial", (fs.loc["all", "verification_pp"], fs.loc["all", "decomposition_pp"]),
          (QUOTED["factorial"]["verification"][0], QUOTED["factorial"]["decomposition"][0]))
    vk = rt.verifier_kinds = rt.verifier_fix_kinds().loc["pooled"]; qk = QUOTED["verifier_kinds_D"]
    check("verifier kinds D", (vk[("fixed", "wrong value")], vk[("fixed", "missing")], vk[("broken", "wrong value")], vk[("broken", "missing")]),
          (qk["fixed_wrong"], qk["fixed_missing"], qk["broken_wrong"], qk["broken_missing"]), tol=0)
    check("verifier kinds sum to the audit", (vk[("fixed", "wrong value")] + vk[("fixed", "missing")], vk[("broken", "wrong value")] + vk[("broken", "missing")]),
          QUOTED["verifier_turns"]["D"], tol=0)
    if QUOTED["bayes"] is not None:
        bf = rt.bayes_factorial()
        for e, qv in QUOTED["bayes"].items():
            check(f"bayes {e}", (bf.loc[e, "pp"], bf.loc[e, "lo"], bf.loc[e, "hi"]), qv)
    check_gain_sources()
    print("six-arm study: pooled accuracy", acc[[key[k] for k in "ABCDF"] + [rt.FV, rt.G]].round(1).to_dict())
    print("factorial:\n" + fx.round(1).to_string())
    print("core contrasts:\n" + cc[["delta_pp", "lo_pp", "hi_pp", "p", "holm_p"]].round(3).to_string())


def check_gain_sources() -> None:
    """The exploratory subgroup and per-output analyses (Fig. 5d; Supplementary Tables 27-31)."""
    def check_effects(frame, quoted, label):
        for group, q in quoted.items():
            if not isinstance(q, dict) or group == "spearman":
                continue
            r = frame.loc[group]
            if "n" in q:
                check(f"{label} {group} tasks", r.tasks, q["n"], tol=0)
            if "A" in q:
                check(f"{label} {group} A", r.A_pp, q["A"])
            for e in ("verification", "decomposition", "D_minus_B"):
                if e in q:
                    check(f"{label} {group} {e}", (r[f"{e}_pp"], r[f"{e}_lo"], r[f"{e}_hi"]), q[e])
    bb = rt.effects_by_baseline()
    check_effects(bb, QUOTED["by_baseline"], "baseline")
    for e, q in QUOTED["by_baseline"]["spearman"].items():
        check(f"baseline spearman {e}", bb.attrs["spearman"][e][0], q, tol=0.006)
    assert bb.attrs["spearman"]["verification"][1] < 1e-6 and bb.attrs["spearman"]["decomposition"][1] < 0.001
    check_effects(rt.effects_by_turns(), QUOTED["by_turns"], "turns")
    bc = rt.effects_by_category()
    check_effects(bc, QUOTED["by_category"], "category")
    excl = sorted(bc.drop("all").index[(bc.drop("all").decomposition_lo > 0) | (bc.drop("all").decomposition_hi < 0)])
    assert excl == QUOTED["by_category"]["decomposition_excluding_zero"], excl
    assert bc.drop("all").A_pp.idxmin() == "regulatory_standards", bc.A_pp.idxmin()
    bk = rt.effects_by_kind()
    check_effects(bk, QUOTED["by_kind"], "kind")
    r = bk.loc["regulatory minus others"]
    check("regulatory minus others verification", (r.verification_pp, r.verification_lo, r.verification_hi), QUOTED["by_kind"]["regulatory_minus_others"])
    shares, contrasts = rt.repeat_consistency_all(); qc = QUOTED["consistency_all"]
    key = {"A": rt.A, "B": rt.B, "C": rt.C, "D": rt.D}
    for k, q in qc["all_three"].items():
        check(f"consistency all three {k}", shares.loc[key[k], "all_three"], q)
    for k, q in qc["none"].items():
        check(f"consistency none {k}", shares.loc[key[k], "none"], q)
    for k in ("B-A", "D-C", "D-B"):
        check(f"consistency {k}", (contrasts.loc[k, "delta_pp"], contrasts.loc[k, "lo_pp"], contrasts.loc[k, "hi_pp"]), qc[k])
    check("consistency A, D as before", (shares.loc[rt.A, "all_three"], shares.loc[rt.D, "all_three"]), QUOTED["consistency"]["all_three"])
    tr = rt.verifier_transitions(); qt = QUOTED["transitions"]
    for k in ("fixed", "survived", "broke", "kept"):
        check(f"transitions {k}", tr["totals"][k], qt[k], tol=0)
    for k, q in qt["fix_rate"].items():
        check(f"fix rate {k}", tr["by_magnitude"].loc[k, "fix_rate"], q, tol=0.51)
    fr = tr["by_magnitude"].fix_rate
    assert fr["order of magnitude"] < fr[">=50%"] < fr["10-50%"] < fr["1-10%"], fr   # the gradient the text describes
    sj = rt.shared_judgements().set_index(["task", "var"])
    for (task, var), q in QUOTED["shared_judgements"].items():
        r = sj.loc[(task, var)]
        check(f"shared judgement {var}", (r.runs, r.backbones, r.families), q, tol=0)
    assert sj.loc[("hk_weekend_ozone_ox_conservation", "line_can_be_written"), "A"] == 0
    pc = rt.prose_credit(); qp = QUOTED["prose_credit"]; r = pc["pooled"]
    check("prose hit rate", pc["hit_rate"]["pooled"], qp["hit_rate"], tol=0.51)
    check("prose unset numeric", pc["unset_numeric"], qp["unset_numeric"], tol=0)
    check("prose credited runs", (pc["credited_runs"], pc["failed_runs"]), (qp["credited_runs"], qp["failed_runs"]), tol=0)
    check("prose D - A", (r.D_minus_A_pp, r.D_minus_A_lo, r.D_minus_A_hi), qp["D_minus_A"])
    check("prose D - A credited", (r.D_minus_A_credited_pp, r.D_minus_A_credited_lo, r.D_minus_A_credited_hi), qp["D_minus_A_credited"])
    check("prose credit", (r.credit_pp, r.credit_lo, r.credit_hi), qp["credit"])
    pmc = rt.per_model_category()
    for m, q in QUOTED["per_model_category"].items():
        for cat, (a, b) in q.items():
            check(f"{m} {cat} A, B", (pmc.loc[(m, "A"), cat], pmc.loc[(m, "B"), cat]), (a, b), tol=0.51)


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
    for m, (turns, a_full, d_full) in QUOTED["step_cap_full"].items():
        detail = rt.step_cap_detail(m)
        check(f"turns per arm {m}", (detail[rt.A][0], detail[rt.D][0]), (turns, turns), tol=0)
        check(f"stage-cap turns from records {m}", (detail[rt.A][1], detail[rt.D][1]), QUOTED["step_cap_turns"][m], tol=0)
        check(f"full-budget turns {m}", (detail[rt.A][2], detail[rt.D][2]), (a_full, d_full), tol=0)
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
    check_study()

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
