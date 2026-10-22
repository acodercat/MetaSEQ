"""Experiment 2's tables as the paper's scripts read them, from the report that
`metaseq report study` writes (phase3_replication/results/report/).

    accuracy()   one row per backbone and "pooled": A, D (%), tokens_A, tokens_D (per task)
    contrasts()  D - A per backbone and pooled, with the column names the scripts use
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PHASE3 = ROOT / "phase3_replication"
REPORT = PHASE3 / "results" / "report"
A, D = "single_agent_bare", "multi_agent_fixed_roles_verified"
FIRST_THREE = ["deepseek-v4-flash", "gpt-6-luna", "qwen3.8-flash"]   # the backbones run first
LABELS = {"qwen3.8-27b": "Qwen3.8-27B", "qwen3.8-flash": "Qwen3.8-Flash", "gpt-6-luna": "GPT-6 Luna",
          "deepseek-v4-flash": "DeepSeek-V4-Flash", "qwen3.8-27b-thinking": "Qwen3.8-27B (reasoning)",
          "deepseek-v4-flash-thinking": "DeepSeek-V4-Flash (reasoning)",
          "deepseek-v4-pro-0813": "DeepSeek-V4-Pro", "claude-sonnet-5-5": "Claude Sonnet 5.5"}
THINKING_PAIRS = [("qwen3.8-27b", "qwen3.8-27b-thinking"), ("deepseek-v4-flash", "deepseek-v4-flash-thinking")]


def models() -> list[str]:
    """Backbones in the report, ordered by single-agent accuracy."""
    arms_ = pd.read_csv(REPORT / "arms.csv")
    return list(arms_[arms_.arm == A].sort_values("accuracy").model)


MODELS = None  # resolved lazily by models(); kept for callers that import the name


def contrasts() -> pd.DataFrame:
    table = pd.read_csv(REPORT / "contrasts.csv")
    assert set(table.contrast) == {"H1 orchestration vs single"}, set(table.contrast)
    return table.assign(contrast="H1")


def accuracy() -> pd.DataFrame:
    arms = pd.read_csv(REPORT / "arms.csv").set_index(["arm", "model"])
    rows = [{"model": m, "A": 100 * arms.loc[(A, m), "accuracy"],
             "D": 100 * arms.loc[(D, m), "accuracy"],
             "tokens_A": arms.loc[(A, m), "mean_tokens"],
             "tokens_D": arms.loc[(D, m), "mean_tokens"],
             "per_correct_A": arms.loc[(A, m), "tokens_per_correct"],
             "per_correct_D": arms.loc[(D, m), "tokens_per_correct"]} for m in models()]
    pooled = contrasts().set_index("scope").loc["pooled"]
    rows.append({"model": "pooled", "A": 100 * pooled.control_acc, "D": 100 * pooled.treatment_acc,
                 "tokens_A": pooled.control_tokens_per_task,
                 "tokens_D": pooled.treatment_tokens_per_task,
                 "per_correct_A": pooled.control_tokens_per_correct,
                 "per_correct_D": pooled.treatment_tokens_per_correct})
    return pd.DataFrame(rows)


def arms() -> pd.DataFrame:
    return pd.read_csv(REPORT / "arms.csv")


def outcomes() -> pd.DataFrame:
    return pd.read_csv(REPORT / "outcomes.csv")


def categories() -> pd.DataFrame:
    return pd.read_csv(REPORT / "categories.csv")


PREBAND = PHASE3 / "results" / "original_bands"


def preband() -> dict:
    """Pooled A, D (%) and D - A [interval] under the comparison bands in force before three
    were widened (Supplementary Note 2): the verdicts kept from then on the same runs, through the same estimator. Needs the experiment's package
    (`uv run --project phase3_replication`)."""
    import sys

    sys.path.insert(0, str(PHASE3))
    from analysis.report import contrast
    from evaluation.experiment import Contrast
    from evaluation.records import Scorecard, read_json

    passed = {}
    for path in PREBAND.glob("*/*/*/*/*/r*/programmatic_verification.json"):
        card = Scorecard.from_dict(read_json(path))
        task, arm, model, repeat = path.parts[-5], path.parts[-4], path.parts[-3], path.parts[-2]
        passed[(arm, model, task, int(repeat[1:]))] = card.passed
    have = {k[1] for k in passed}
    runs = outcomes()
    runs = runs[runs.model.isin(have)].reset_index(drop=True)   # the backbones run before the bands changed
    assert len(passed) == len(runs), (len(passed), len(runs))
    runs = runs.assign(passed=[passed[(r.arm, r.model, r.task, r.repeat)]
                               for r in runs.itertuples()])
    r = contrast(runs, Contrast(name="H1", treatment=D, control=A))
    return {"A": 100 * r["control_acc"], "D": 100 * r["treatment_acc"],
            "gain": (r["delta_pp"], r["lo_pp"], r["hi_pp"]), "models": sorted(have)}


def sign_test() -> dict:
    """Per-backbone gains: how many positive, exact sign-test p, over all backbones and over
    distinct models (a model run with and without reasoning counted once, by its base run)."""
    from scipy import stats

    c = contrasts(); c = c[c.scope != "pooled"].set_index("scope")
    gains = c.delta_pp
    base = [m for m in gains.index if m not in {t for _, t in THINKING_PAIRS}]
    out = {}
    for name, idx in (("all", list(gains.index)), ("distinct", base)):
        k, n = int((gains[idx] > 0).sum()), len(idx)
        out[name] = dict(positive=k, n=n, p=stats.binomtest(k, n, 0.5).pvalue,
                         significant=int((c.loc[idx].lo_pp > 0).sum()))
    return out


def thinking_pairs() -> pd.DataFrame:
    """For each model run with reasoning off and on: accuracy of A and D in both modes, the
    three gains (reasoning alone, orchestration alone, both) and the paired task-resampled
    difference reasoning-alone minus orchestration-alone."""
    import numpy as np

    o = outcomes(); o["ok"] = o.passed.astype(bool)
    rng = np.random.default_rng(20260929)

    def task_acc(m, arm):
        return o[(o.model == m) & (o.arm == arm)].groupby("task").ok.mean()

    rows = []
    for base, think in THINKING_PAIRS:
        a0, d0, a1, d1 = (100 * task_acc(m, arm).mean() for m, arm in
                          ((base, A), (base, D), (think, A), (think, D)))
        d = (task_acc(think, A) - task_acc(base, D)).values
        bs = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(10000)])
        rows.append(dict(model=base, A=a0, D=d0, A_reasoning=a1, D_reasoning=d1,
                         gain_reasoning=a1 - a0, gain_orchestration=d0 - a0, gain_both=d1 - a0,
                         diff_pp=100 * d.mean(), diff_lo=100 * np.percentile(bs, 2.5),
                         diff_hi=100 * np.percentile(bs, 97.5)))
    return pd.DataFrame(rows).set_index("model")


def cross_model(small: str, large: str) -> tuple[float, float, float]:
    """Task-resampled paired difference: the small backbone under D minus the large under A."""
    import numpy as np

    o = outcomes(); o["ok"] = o.passed.astype(bool)
    rng = np.random.default_rng(20260929)
    x = o[(o.model == small) & (o.arm == D)].groupby("task").ok.mean()
    y = o[(o.model == large) & (o.arm == A)].groupby("task").ok.mean()
    d = (x - y).values
    bs = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(10000)])
    return 100 * d.mean(), 100 * np.percentile(bs, 2.5), 100 * np.percentile(bs, 97.5)


def repeat_consistency() -> pd.DataFrame:
    """Per arm: share of (backbone, task) cells passed in all three repeats, in none, and the
    majority-of-three accuracy."""
    o = outcomes(); o["ok"] = o.passed.astype(bool)
    per = o.groupby(["arm", "model", "task"]).ok.sum().reset_index()
    rows = []
    for arm in (A, D):
        g = per[per.arm == arm].ok
        rows.append(dict(arm=arm, all_three=100 * (g == 3).mean(), none=100 * (g == 0).mean(),
                         majority=100 * (g >= 2).mean()))
    return pd.DataFrame(rows).set_index("arm")


def by_repeat() -> pd.DataFrame:
    """Run pass rate (%) of A and D for each backbone and repeat, the pooled row averaging the
    backbones, and how many of a backbone's repeats D passed more, as many or fewer runs than A."""
    o = outcomes()
    o = o[(o.status == "scored") & o.arm.isin([A, D])]
    n = o.groupby(["model", "arm", "repeat"]).passed.agg(["sum", "count"])
    assert (n["count"] == 111).all(), n[n["count"] != 111]
    rate = (100 * n["sum"] / n["count"]).unstack(["arm", "repeat"])
    wins = n["sum"].unstack("arm")
    diff = (wins[D] - wins[A]).unstack("repeat")
    out = rate.loc[models()].copy()
    out.loc["pooled"] = rate.loc[models()].mean()
    out[("D_vs_A", "higher")] = (diff > 0).sum(axis=1)
    out[("D_vs_A", "equal")] = (diff == 0).sum(axis=1)
    out[("D_vs_A", "lower")] = (diff < 0).sum(axis=1)
    out.loc["pooled", [("D_vs_A", k) for k in ("higher", "equal", "lower")]] = (
        out.loc[models(), [("D_vs_A", k) for k in ("higher", "equal", "lower")]].sum().values)
    return out


def multiturn() -> pd.DataFrame:
    """Turn-level pass rates on the multi-turn tasks, per arm: after a failed earlier turn,
    after a passed one, and on the third turn. Rebuilt from outcomes.csv (every run) and
    failures.csv (every failed turn); a turn absent from failures.csv passed."""
    import json

    tasks = {}
    for path in (PHASE3 / "suites" / "air_quality" / "tasks").glob("*/*.json"):
        j = json.loads(path.read_text())
        tasks[j["name"]] = [(c["id"], len(c["turns"])) for c in j["conversations"]]
    fail = pd.read_csv(REPORT / "failures.csv")
    failed = {(r.arm, r.model, r.task, int(r.repeat), r.conversation, int(r.turn))
              for r in fail.itertuples()}
    rows = []
    for r in outcomes().itertuples():
        if r.arm not in (A, D):
            continue
        for conv, n in tasks[r.task]:
            for t in range(1, n + 1):
                rows.append(dict(arm=r.arm, model=r.model, task=r.task, rep=int(r.repeat),
                                 conv=conv, turn=t, n=n,
                                 ok=(r.arm, r.model, r.task, int(r.repeat), conv, t) not in failed))
    turns = pd.DataFrame(rows)
    mt = turns[turns.n > 1]
    key = ["arm", "model", "task", "rep", "conv", "turn"]
    prev = mt[key + ["ok"]].assign(turn=mt.turn + 1).rename(columns={"ok": "prev_ok"})
    m = mt.merge(prev, on=key)
    out = []
    for arm in (A, D):
        g = m[m.arm == arm]
        third = mt[(mt.arm == arm) & (mt.turn == 3)]
        out.append(dict(arm=arm,
                        after_failed=100 * g[~g.prev_ok].ok.mean(), n_after_failed=int((~g.prev_ok).sum()),
                        after_passed=100 * g[g.prev_ok].ok.mean(), n_after_passed=int(g.prev_ok.sum()),
                        third=100 * third.ok.mean(), n_third=len(third), turns=int((turns.arm == arm).sum())))
    return pd.DataFrame(out).set_index("arm")


CASES = [  # the three tasks described in Supplementary Note 4, with their store paths
    ("beijing_olympics_meteorological_adjustment", "beijing/cross_domain_analysis"),
    ("hk_ozone_peak_season_aqo", "hk/regulatory_standards"),
    ("hk_weekend_ozone_ox_conservation", "hk/temporal_pattern_analysis"),
]


def case_counts() -> pd.DataFrame:
    """Runs passed of nine (the first three backbones x three repeats) per arm for the three
    case tasks, per backbone and in total, and the first-turn passes. The cases were read
    from the transcripts of those three backbones (Supplementary Note 3)."""
    out = outcomes()
    fail = pd.read_csv(REPORT / "failures.csv")
    fail = fail[fail.model.isin(FIRST_THREE)]
    rows = []
    for task, _ in CASES:
        sel = out[(out.task == task) & out.arm.isin([A, D]) & out.model.isin(FIRST_THREE)]
        for arm in (A, D):
            s = sel[sel.arm == arm]
            f1 = fail[(fail.task == task) & (fail.arm == arm) & (fail.turn == 1)]
            rows.append(dict(task=task, arm=arm, passed=int(s.passed.sum()), runs=len(s),
                             turn1_passed=len(s) - len(f1),
                             **{m: int(s[s.model == m].passed.sum()) for m in FIRST_THREE}))
    return pd.DataFrame(rows).set_index(["task", "arm"])


def convergent_tasks(min_wrong: int = 8, share: float = 0.5, min_backbones: int = 3) -> dict:
    """Tasks on which wrong answers coincide across backbones: a (task, variable) qualifies
    when at least `share` of its >= `min_wrong` wrong values are one value given by >=
    `min_backbones` backbones. Returns the task set, the share of failed turns on them and
    the per-arm pass rates on and off them. Reads the stored verdicts."""
    import collections, json, re

    NUM = re.compile(r"(\w+)=(-?\d+(?:\.\d+)?),? expected ~?(-?\d+(?:\.\d+)?)")
    vals = collections.defaultdict(list)
    for path in (PHASE3 / "results").glob("*/*/*/*/*/r*/programmatic_verification.json"):
        task, model = path.parts[-5], path.parts[-3]
        if path.parts[-4] not in (A, D):      # skip the voted baseline's cards
            continue
        card = json.loads(path.read_text())
        for conv in card["conversations"]:
            for t in conv["turns"]:
                if t.get("success"):
                    continue
                for var, got, _ in NUM.findall(t.get("message", "") or ""):
                    vals[(task, var)].append((model, round(float(got), 4)))
    tasks = set()
    for (task, _), lst in vals.items():
        if len(lst) < min_wrong:
            continue
        modal, k = collections.Counter(g for _, g in lst).most_common(1)[0]
        if k / len(lst) >= share and len({m for m, g in lst if g == modal}) >= min_backbones:
            tasks.add(task)
    fail = pd.read_csv(REPORT / "failures.csv")
    o = outcomes(); o["ok"] = o.passed.astype(bool); o["conv"] = o.task.isin(tasks)
    rates = o.groupby(["conv", "arm"]).ok.mean() * 100
    families = {t: max(len({FAMILY[m] for m, g in lst if g == modal_of(lst)})
                       for (task, _), lst in vals.items() if task == t and len(lst) >= min_wrong)
                for t in tasks}
    return dict(tasks=sorted(tasks), n_tasks=len(tasks),
                failed_share=100 * fail.task.isin(tasks).mean(),
                A_on=rates[(True, A)], D_on=rates[(True, D)], A_off=rates[(False, A)], D_off=rates[(False, D)],
                families=families)   # per task: model families sharing the modal wrong value


FAMILY = {"qwen3.8-27b": "qwen", "qwen3.8-27b-thinking": "qwen", "qwen3.8-flash": "qwen",
          "deepseek-v4-flash": "deepseek", "deepseek-v4-flash-thinking": "deepseek", "deepseek-v4-pro-0813": "deepseek",
          "gpt-6-luna": "openai", "claude-sonnet-5-5": "anthropic"}


def modal_of(lst) -> float:
    import collections
    return collections.Counter(g for _, g in lst).most_common(1)[0][0]


def mixed_model() -> dict:
    """The protocol's primary model restricted to arms A and D: Bayesian mixed-effects logistic
    regression of a run's correctness on topology with task, backbone and task x backbone random
    intercepts (statsmodels BinomialBayesMixedGLM, variational inference, as in experiment 1).
    Returns the topology coefficient, its posterior sd, the odds ratio with a 95% interval and
    the mean difference on the probability scale over all runs."""
    import math
    import numpy as np
    from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM

    o = outcomes()
    o = o[o.arm.isin([A, D])].copy()
    o["ok"] = o.passed.astype(int)
    o["topology"] = (o.arm == D).astype(int)
    o["tb"] = o.task + ":" + o.model
    fit = BinomialBayesMixedGLM.from_formula(
        "ok ~ topology", {"task": "0 + C(task)", "backbone": "0 + C(model)", "task_backbone": "0 + C(tb)"}, o
    ).fit_vb()
    i = list(fit.model.exog_names).index("topology")
    beta, sd = float(fit.fe_mean[i]), float(fit.fe_sd[i])
    eta = fit.fe_mean[0] + fit.model.exog_vc @ fit.vc_mean
    p1, p0 = 1 / (1 + np.exp(-(eta + beta))), 1 / (1 + np.exp(-eta))
    return dict(beta=beta, sd=sd, odds_ratio=math.exp(beta),
                or_lo=math.exp(beta - 1.96 * sd), or_hi=math.exp(beta + 1.96 * sd),
                marginal_pp=100 * float(np.mean(p1 - p0)), n=len(o))


def fixed_broken_by_class() -> pd.DataFrame:
    """For every (backbone, task, repeat) cell where exactly one arm passed: the failing arm's
    error class, read from the stored verdict of its first failed turn. Rows: error class;
    columns: cells the single agent failed and MetaSEQ passed ("fixed", classed by A's error)
    and cells MetaSEQ failed and the single agent passed ("broken", classed by D's error)."""
    import json
    from error_messages import error_class as turn_class

    o = outcomes(); o["ok"] = o.passed.astype(bool)
    per = o.pivot_table(index=["model", "task", "repeat"], columns="arm", values="ok", aggfunc="first").astype(bool).reset_index()
    counts = {"fixed": {}, "broken": {}}
    for label, rows, arm in (("fixed", per[~per[A] & per[D]], A), ("broken", per[per[A] & ~per[D]], D)):
        for r in rows.itertuples():
            for path in (PHASE3 / "results").glob(f"*/*/{r.task}/{arm}/{r.model}/r{r.repeat}/programmatic_verification.json"):
                card = json.loads(path.read_text())
                cls = [turn_class(t.get("message", "") or "") for c in card["conversations"] for t in c["turns"] if not t.get("success")]
                if cls:
                    counts[label][cls[0]] = counts[label].get(cls[0], 0) + 1
    return pd.DataFrame(counts).fillna(0).astype(int)


G = "single_agent_bare_vote"   # the pre-registered self-consistency baseline: A run three times, outputs voted


def vote_baseline(seed: int = 20260929, resamples: int = 10_000) -> pd.DataFrame:
    """The protocol's compute-matched single-agent baseline G against A and D. G's verdict for a
    (backbone, task) is the voted snapshot's card under single_agent_bare_vote (analysis/vote.py);
    it passes when every turn passes. One row per backbone and "pooled": accuracy of A, G and D,
    the mean paired difference D - G with its 95% percentile interval over `resamples` task
    resamples, how many backbones D beats G on (pooled row), and D's tokens as a multiple of G's
    (G's tokens are the sum of A's three repeats)."""
    import json
    import numpy as np

    g = {}
    for path in (PHASE3 / "results").glob(f"*/*/*/{G}/*/r1/programmatic_verification.json"):
        task, model = path.parts[-5], path.parts[-3]
        card = json.loads(path.read_text())
        g[(model, task)] = float(all(t.get("success") for c in card["conversations"] for t in c["turns"]))
    o = outcomes(); o["ok"] = o.passed.astype(float)
    tasks = sorted(o.task.unique())
    dm = o[o.arm == D].groupby(["model", "task"]).ok.mean().unstack(0).reindex(tasks)
    am = o[o.arm == A].groupby(["model", "task"]).ok.mean().unstack(0).reindex(tasks)
    gm = pd.DataFrame({m: {t: g[(m, t)] for t in tasks} for m in models()}).reindex(tasks)
    assert gm.notna().all().all(), "a voted card is missing"
    tok = o.groupby(["arm", "model"]).total_tokens.mean().unstack(0)
    rng = np.random.default_rng(seed)
    n = len(tasks)
    draws = rng.integers(0, n, (resamples, n))

    def ci(diff: np.ndarray) -> tuple[float, float, float]:
        bs = diff[draws].mean(axis=1)
        return 100 * diff.mean(), 100 * np.percentile(bs, 2.5), 100 * np.percentile(bs, 97.5)

    rows = []
    for m in models():
        mu, lo, hi = ci((dm[m] - gm[m]).to_numpy())
        rows.append({"model": m, "A": 100 * am[m].mean(), "G": 100 * gm[m].mean(), "D": 100 * dm[m].mean(),
                     "delta_pp": mu, "lo_pp": lo, "hi_pp": hi,
                     "tokens_ratio": tok.loc[m, D] / (3 * tok.loc[m, A])})
    mu, lo, hi = ci((dm[models()] - gm[models()]).mean(axis=1).to_numpy())
    rows.append({"model": "pooled", "A": 100 * am.to_numpy().mean(), "G": 100 * gm.to_numpy().mean(),
                 "D": 100 * dm.to_numpy().mean(), "delta_pp": mu, "lo_pp": lo, "hi_pp": hi,
                 "tokens_ratio": tok[D].mean() / (3 * tok[A].mean()),
                 "backbones_positive": int(sum(r["delta_pp"] > 0 for r in rows))})
    return pd.DataFrame(rows)


def step_cap_detail(model: str) -> dict:
    """Per arm, for one backbone: turns, turns in which a stage hit its step cap, and turns that
    used the whole per-turn budget. Reads the run records (on disk; on Zenodo for a clone)."""
    try:
        from analysis.failures import STEP_LIMITS   # the harness's own set
    except ImportError:
        STEP_LIMITS = {"max_steps", "budget_exhausted"}
    out = {}
    for arm in (A, D):
        turns = capped = full = 0
        for path in (PHASE3 / "results").glob(f"*/*/*/{arm}/{model}/r*/run.json"):
            run = json.loads(path.read_text())
            for conversation in run["conversations"]:
                for turn in conversation["turns"]:
                    stages = turn["stages"]
                    turns += 1
                    capped += any(s["stop_reason"] in STEP_LIMITS for s in stages)
                    full += sum(s.get("steps", 0) for s in stages) >= 50
        out[arm] = (turns, capped, full)
    return out


def final_turn_rule() -> dict:
    """Pooled accuracy of A and D when a run counts as correct if its last turn passed
    (the lenient rule), from the stored verdicts."""
    import json
    acc = {A: [], D: []}
    for arm in (A, D):
        for path in (PHASE3 / "results").glob(f"*/*/*/{arm}/*/r*/programmatic_verification.json"):
            card = json.loads(path.read_text())
            last = [c["turns"][-1] for c in card["conversations"] if c["turns"]]
            acc[arm].append(float(all(t.get("success") for t in last)))
    return {"A": 100 * sum(acc[A]) / len(acc[A]), "D": 100 * sum(acc[D]) / len(acc[D]), "n": len(acc[A])}


def backbone_settings() -> pd.DataFrame:
    """One row per backbone from its stored run records: the API model name, temperature,
    reasoning setting, how it was reached, and the dates of its first and last run."""
    import json
    rows = {}
    for path in (PHASE3 / "results").glob(f"*/*/*/{A}/*/r*/run.json"):
        d = json.loads(path.read_text())["run"]
        m = d["model"]; cfg = m["config"]
        day = d["started_at"][:10]
        if cfg not in rows:
            extra = m.get("extra_body") or {}
            if "reasoning_effort" in m:
                reasoning = "off" if m["reasoning_effort"] == "none" else m["reasoning_effort"]
            elif "thinking" in extra:
                reasoning = "off" if extra["thinking"].get("type") == "disabled" else "on"
            elif "chat_template_kwargs" in extra:
                k = extra["chat_template_kwargs"]; reasoning = "on" if k.get("thinking") or k.get("enable_thinking") else "off"
            elif "enable_thinking" in extra:
                reasoning = "on" if extra["enable_thinking"] else "off"
            else:
                reasoning = "off"
            provider = {"anthropic": "Anthropic Messages API", "openai_responses": "OpenAI Responses API via relay"}.get(
                m.get("provider"), "OpenAI-compatible relay")
            rows[cfg] = {"model": cfg, "api_model": m["api_model"], "temperature": m.get("temperature"),
                         "reasoning": reasoning, "access": provider, "first": day, "last": day}
        rows[cfg]["first"] = min(rows[cfg]["first"], day); rows[cfg]["last"] = max(rows[cfg]["last"], day)
    for path in (PHASE3 / "results").glob(f"*/*/*/{D}/*/r*/run.json"):
        d = json.loads(path.read_text())["run"]; cfg = d["model"]["config"]; day = d["started_at"][:10]
        rows[cfg]["first"] = min(rows[cfg]["first"], day); rows[cfg]["last"] = max(rows[cfg]["last"], day)
    return pd.DataFrame([rows[m] for m in models()])


D_BEFORE = f"{D}_before"   # D's outputs as the synthesis worker left them, before the verifier


def verifier_audit(seed: int = 20260929, resamples: int = 10_000) -> dict:
    """Pair every D turn's pre-verifier verdict (pseudo-arm D_BEFORE, scored by
    analysis/before_verifier.py) with its stored final verdict. Returns per-backbone and pooled
    counts of turns corrected (fail -> pass), broken (pass -> fail) and unchanged, the task-level
    pass rate before and after the verifier, and the mean paired task-level change with its 95%
    percentile interval over `resamples` task resamples."""
    import json
    import numpy as np

    turns = []
    for final_path in (PHASE3 / "results").glob(f"*/*/*/{D}/*/r*/programmatic_verification.json"):
        before_path = Path(str(final_path).replace(f"/{D}/", f"/{D_BEFORE}/"))
        if not before_path.exists():
            raise FileNotFoundError(f"no pre-verifier card for {final_path}; run analysis/before_verifier.py")
        final = json.loads(final_path.read_text()); before = json.loads(before_path.read_text())
        task, model, repeat = final_path.parts[-5], final_path.parts[-3], int(final_path.parts[-2][1:])
        fb = {(c["id"], t["turn"]): t for c in before["conversations"] for t in c["turns"]}
        for c in final["conversations"]:
            for t in c["turns"]:
                b = fb[(c["id"], t["turn"])]
                turns.append(dict(domain=final_path.parts[-7], task=task, model=model, repeat=repeat,
                                  before=bool(b["success"]), after=bool(t["success"])))
    tr = pd.DataFrame(turns)
    tr["kind"] = np.select([~tr.before & tr.after, tr.before & ~tr.after, tr.before & tr.after],
                           ["corrected", "broken", "unchanged_pass"], "unchanged_fail")
    counts = tr.groupby(["model", "kind"]).size().unstack(fill_value=0)
    counts = counts.reindex(columns=["corrected", "broken", "unchanged_pass", "unchanged_fail"], fill_value=0)
    counts.loc["pooled"] = counts.sum()
    runs = tr.groupby(["model", "task", "repeat"]).agg(before=("before", "all"), after=("after", "all")).reset_index()
    per = runs.groupby(["model", "task"]).agg(before=("before", "mean"), after=("after", "mean"))
    rate = per.groupby("model").mean() * 100
    rate.loc["pooled"] = per.mean() * 100
    diff = (per.after - per.before).unstack(0)[models()]
    rng = np.random.default_rng(seed); n = len(diff)
    draws = rng.integers(0, n, (resamples, n))
    pooled = diff.mean(axis=1).to_numpy()
    bs = pooled[draws].mean(axis=1)
    out = counts.join(rate.rename(columns={"before": "pass_before", "after": "pass_after"}))
    out["delta_pp"] = out.pass_after - out.pass_before
    out = out.reindex(models() + ["pooled"])
    return {"table": out, "delta_pp": 100 * pooled.mean(),
            "lo_pp": 100 * np.percentile(bs, 2.5), "hi_pp": 100 * np.percentile(bs, 97.5),
            "turns": len(tr), "runs": len(runs),
            "by_domain": tr.groupby(["domain", "kind"]).size().unstack(fill_value=0)}


def before_minus_single(seed: int = 20260929, resamples: int = 10_000) -> dict:
    """MetaSEQ before its verifier against the single agent: mean paired task-level difference
    with its 95% percentile interval over task resamples, and the per-backbone differences."""
    import json
    import numpy as np

    o = outcomes(); o["ok"] = o.passed.astype(float)
    a = o[o.arm == A].groupby(["model", "task"]).ok.mean().unstack(0)
    rows = []
    for f in (PHASE3 / "results").glob(f"*/*/*/{D_BEFORE}/*/r*/programmatic_verification.json"):
        c = json.loads(f.read_text())
        rows.append(dict(model=f.parts[-3], task=f.parts[-5],
                         ok=float(all(t["success"] for cv in c["conversations"] for t in cv["turns"]))))
    b = pd.DataFrame(rows).groupby(["model", "task"]).ok.mean().unstack(0)
    ms = models(); tasks = a.index
    diff = (b.loc[tasks, ms] - a.loc[tasks, ms])
    pooled = diff.mean(axis=1).to_numpy()
    rng = np.random.default_rng(seed); n = len(pooled)
    bs = pooled[rng.integers(0, n, (resamples, n))].mean(axis=1)
    return {"delta_pp": 100 * pooled.mean(), "lo_pp": 100 * np.percentile(bs, 2.5),
            "hi_pp": 100 * np.percentile(bs, 97.5), "per_backbone": 100 * diff.mean()}
