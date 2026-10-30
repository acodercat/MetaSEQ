"""Experiment 2's tables as the paper's scripts read them, from phase3_replication/results/report/.

Two sets of derived tables sit there. `arms.csv`, `contrasts.csv`, `outcomes.csv` and
`failures.csv` are the two-arm report (`metaseq report study`, arms A and D) that the
error analyses, the cases and Fig. 5 read. `study_*.csv` are the six-arm study report
(all backbones; see the README beside them) that the factorial results read.

    accuracy()        one row per backbone and "pooled": A, D (%), tokens_A, tokens_D (per task)
    contrasts()       D - A per backbone and pooled, with the column names the scripts use
    arm_accuracy()    every arm and G, per backbone and pooled (%)
    factorial()       verification and decomposition main effects and their interaction
    core_contrasts()  H1, H2a-c with Holm p; delegation_contrasts() the exploratory ones
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PHASE3 = ROOT / "phase3_replication"
REPORT = PHASE3 / "results" / "report"
A, D = "single_agent_bare", "multi_agent_fixed_roles_verified"
B, C = "single_agent_verified", "multi_agent_fixed_roles"
F, FV = "multi_agent_delegation_planned", "multi_agent_delegation_verified"
G = "single_agent_bare_vote"   # the pre-registered self-consistency baseline: A run three times, outputs voted
CORE = [A, B, C, D]            # the registered 2 x 2: decomposition (C, D) x verification (B, D)
ARMS6 = [A, B, C, D, F, FV]
ARM_LABELS = {A: "A", B: "B", C: "C", D: "D", F: "F", FV: "F+V", G: "G"}
POOLED = "pooled over backbones"   # the aggregate scope label in the study_*.csv files
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


# ---------------- the six-arm study tables ----------------------------------------------------

def study_outcomes() -> pd.DataFrame:
    """One row per run of the six arms (15,984) and one per (backbone, task) for G (888)."""
    o = pd.read_csv(REPORT / "study_outcomes.csv")
    o["ok"] = o.passed.astype(str).str.lower().eq("true").astype(float)
    return o


def study_contrasts() -> pd.DataFrame:
    return pd.read_csv(REPORT / "study_contrasts.csv")


def _scope(frame: pd.DataFrame, scope: str) -> pd.DataFrame:
    return frame[frame.scope == (POOLED if scope == "pooled" else scope)]


def arm_task_means(arm: str) -> pd.DataFrame:
    """Per-task pass rate (repeats averaged) of one arm: rows tasks, columns backbones, plus
    "pooled" (the backbones averaged), the per-task quantity the study's bootstrap resamples."""
    o = study_outcomes()
    m = o[o.arm == arm].groupby(["task", "model"]).ok.mean().unstack(1)[models()]
    m["pooled"] = m.mean(axis=1)
    return m


def arm_accuracy() -> pd.DataFrame:
    """Accuracy (%) of every arm and G per backbone and pooled: runs passed over runs scored,
    the figure `study_arms.csv` reports (pooled over all runs, so each task counts equally)."""
    o = study_outcomes()
    acc = o.groupby(["model", "arm"]).ok.mean().unstack(1)[ARMS6 + [G]]
    out = (100 * acc).loc[models()]
    out.loc["pooled"] = 100 * o.groupby("arm").ok.mean()[ARMS6 + [G]]
    return out


def factorial(scope: str = "pooled") -> pd.DataFrame:
    """The 2 x 2 on per-task means: verification = mean of (B - A, D - C), decomposition = mean of
    (C - A, D - B), interaction = (D - C) - (B - A), and B - C (H2 as registered); percentage
    points with the 95% percentile interval over 10,000 task resamples and the two-sided
    bootstrap p, from `study_factorial.csv`. Index: verification, decomposition, interaction, H2."""
    f = _scope(pd.read_csv(REPORT / "study_factorial.csv"), scope).copy()
    f["effect"] = f.effect.where(~f.effect.str.startswith("H2"), "H2")
    return f.set_index("effect")[["estimate_pp", "lo_pp", "hi_pp", "p"]]


def per_model_effects() -> pd.DataFrame:
    """Verification and decomposition main effects and the interaction per backbone (pp, with
    intervals), rows ordered as models()."""
    rows = {}
    for m in models():
        f = factorial(m)
        rows[m] = {f"{e}_{k}": f.loc[e, c] for e in ("verification", "decomposition", "interaction")
                   for k, c in (("pp", "estimate_pp"), ("lo", "lo_pp"), ("hi", "hi_pp"))}
    return pd.DataFrame(rows).T


def core_contrasts(scope: str = "pooled") -> pd.DataFrame:
    """H1 (D - A), H2a (B - A), H2b (C - A), H2c (D - B): arm accuracies, mean paired difference
    (pp), 95% interval, bootstrap p, Holm-corrected p over the four, task-repeats recovered and
    regressed, exact McNemar p."""
    c = _scope(study_contrasts(), scope)
    c = c[c.analysis == "core"].set_index("contrast")
    return c.loc[["H1", "H2a", "H2b", "H2c"], ["treatment", "control", "control_acc", "treatment_acc",
                                                 "delta_pp", "lo_pp", "hi_pp", "p", "holm_p",
                                                 "recovered", "regressed", "mcnemar_p"]]


DELEGATION = {"F-A": (F, A), "F-C": (F, C), "F-B": (F, B), "FV-F": (FV, F), "FV-B": (FV, B), "FV-D": (FV, D)}


def delegation_contrasts(scope: str = "pooled") -> pd.DataFrame:
    """The exploratory delegation contrasts (no Holm correction, no confirmatory claim), indexed
    by the keys of DELEGATION."""
    c = _scope(study_contrasts(), scope)
    c = c[c.analysis == "delegation"].set_index(["treatment", "control"])
    rows = {k: c.loc[(t, u)] for k, (t, u) in DELEGATION.items()}
    return pd.DataFrame(rows).T[["control_acc", "treatment_acc", "delta_pp", "lo_pp", "hi_pp", "p",
                                 "recovered", "regressed", "mcnemar_p"]].astype(float)


def cost_contrast(scope: str = "pooled") -> dict:
    """Tokens per correct task of D and B and their difference with its 95% task-resampled
    interval (H4), from `study_cost.csv`."""
    r = _scope(pd.read_csv(REPORT / "study_cost.csv"), scope).iloc[0]
    assert (r.treatment, r.control) == (D, B), (r.treatment, r.control)
    return dict(D=r.treatment_per_correct, B=r.control_per_correct, diff=r.difference, lo=r.lo, hi=r.hi)


def tokens_per_correct() -> pd.DataFrame:
    """Tokens per correct task (sum of tokens over sum of passes) for every arm and G, per
    backbone and pooled; G's tokens are the sum of A's three repeats."""
    o = study_outcomes()
    per = o.groupby(["model", "arm"]).apply(lambda g: g.total_tokens.sum() / g.ok.sum()).unstack(1)
    out = per.loc[models(), ARMS6 + [G]]
    out.loc["pooled"] = o.groupby("arm").apply(lambda g: g.total_tokens.sum() / g.ok.sum())[ARMS6 + [G]]
    return out


def tokens_per_task() -> pd.DataFrame:
    """Mean tokens per run for every arm and G (G: per task, three repeats summed)."""
    o = study_outcomes()
    out = o.groupby(["model", "arm"]).total_tokens.mean().unstack(1).loc[models(), ARMS6 + [G]]
    out.loc["pooled"] = o.groupby("arm").total_tokens.mean()[ARMS6 + [G]]
    return out


def verifier_turns() -> pd.DataFrame:
    """Turns the verifier fixed (failed before it, passed after) and broke (the reverse) in the
    three verified arms, per backbone and in total, with the turns verified."""
    o = study_outcomes()
    v = o[o.arm.isin([B, D, FV])].groupby(["model", "arm"])[["verified_turns", "verifier_fixed_turns", "verifier_broke_turns"]].sum()
    v = v.rename(columns={"verified_turns": "verified", "verifier_fixed_turns": "fixed", "verifier_broke_turns": "broken"}).astype(int)
    out = v.unstack(1).swaplevel(axis=1).sort_index(axis=1).loc[models()]
    out.loc["pooled"] = out.sum()
    return out[[(arm, k) for arm in (B, D, FV) for k in ("verified", "fixed", "broken")]]


def turn_accuracy() -> pd.Series:
    """Share of scored turns passed, per arm, pooled over backbones (the six arms; G has no turn record)."""
    o = study_outcomes(); o = o[o.arm.isin(ARMS6)]
    return (100 * o.groupby("arm").turns_passed.sum() / o.groupby("arm").turns.sum()).loc[ARMS6]


def elapsed_per_run() -> pd.Series:
    """Mean wall-clock seconds per run, per arm, pooled over backbones: the stages' elapsed time
    summed, through the relay; descriptive."""
    o = study_outcomes(); o = o[o.arm.isin(ARMS6)]
    return o.groupby("arm").elapsed_s.mean().loc[ARMS6]


def step_cap_by_arm() -> pd.DataFrame:
    """Turns whose answering stage ended at its step cap, per backbone and arm, and the totals."""
    o = study_outcomes()
    out = o[o.arm.isin(ARMS6)].groupby(["model", "arm"]).step_limit_turns.sum().unstack(1).loc[models(), ARMS6].astype(int)
    out.loc["pooled"] = out.sum()
    return out


def vote_vs_verified(seed: int = 20260929, resamples: int = 10_000) -> pd.DataFrame:
    """B against G per backbone and pooled: accuracy of both, the mean paired task-level
    difference B - G with its 95% percentile interval, and (pooled row) the backbones on which
    B is ahead."""
    import numpy as np

    b, g = arm_task_means(B), arm_task_means(G)
    rng = np.random.default_rng(seed); n = len(b)
    draws = rng.integers(0, n, (resamples, n))
    rows = []
    for m in models() + ["pooled"]:
        d = (b[m] - g[m]).to_numpy(); bs = d[draws].mean(axis=1)
        rows.append(dict(model=m, B=100 * b[m].mean(), G=100 * g[m].mean(), delta_pp=100 * d.mean(),
                         lo_pp=100 * np.percentile(bs, 2.5), hi_pp=100 * np.percentile(bs, 97.5)))
    out = pd.DataFrame(rows).set_index("model")
    out.loc["pooled", "backbones_positive"] = int((out.drop("pooled").delta_pp > 0).sum())
    return out


def pair_contrast(treatment: str, control: str, seed: int = 20260929, resamples: int = 10_000) -> tuple[float, float, float]:
    """Pooled mean paired difference of per-task pass rates between two arms (pp) with its 95%
    percentile interval over task resamples, the study's estimator."""
    import numpy as np

    d = (arm_task_means(treatment)["pooled"] - arm_task_means(control)["pooled"]).to_numpy()
    rng = np.random.default_rng(seed); n = len(d)
    bs = d[rng.integers(0, n, (resamples, n))].mean(axis=1)
    return 100 * d.mean(), 100 * np.percentile(bs, 2.5), 100 * np.percentile(bs, 97.5)


def factorial_sensitivity(seed: int = 20260929, resamples: int = 10_000) -> pd.DataFrame:
    """The 2 x 2 effects and D - B under three conditions, each with the study's estimator (per-task
    means, task resamples): "all" (every cell; reproduces factorial()), "no_cap" (dropping every
    backbone x task cell in which any core arm ended a turn at its step cap in any repeat) and
    "six_model" (reasoning modes averaged within a model before the six models are averaged).
    Rows: condition; columns: effect_pp/lo/hi and, for no_cap, the cells and tasks kept."""
    import numpy as np

    o = study_outcomes(); core = o[o.arm.isin(CORE)]
    cell = core.groupby(["task", "model", "arm"]).ok.mean().unstack("arm")
    cap = (core.groupby(["task", "model"]).step_limit_turns.sum() > 0).reindex(cell.index)
    base = {t: b for b, t in THINKING_PAIRS}
    cm = cell.reset_index(); cm["base"] = cm.model.map(lambda m: base.get(m, m))
    conditions = {"all": cell.groupby("task").mean(),
                  "no_cap": cell[~cap.values].groupby("task").mean(),
                  "six_model": cm.groupby(["task", "base"])[CORE].mean().groupby("task").mean()}
    rng = np.random.default_rng(seed)
    rows = {}
    for name, per in conditions.items():
        A_, B_, C_, D_ = (per[a] for a in CORE)
        eff = {"verification": ((B_ - A_) + (D_ - C_)) / 2, "decomposition": ((C_ - A_) + (D_ - B_)) / 2,
               "interaction": (D_ - C_) - (B_ - A_), "D_minus_B": D_ - B_}
        n = len(per); draws = rng.integers(0, n, (resamples, n))
        row = {}
        for k, v in eff.items():
            d = v.to_numpy(); bs = d[draws].mean(axis=1)
            row[f"{k}_pp"], row[f"{k}_lo"], row[f"{k}_hi"] = 100 * d.mean(), 100 * np.percentile(bs, 2.5), 100 * np.percentile(bs, 97.5)
        row["cells"] = int(len(cell) - cap.sum()) if name == "no_cap" else int(len(cell))
        row["tasks"] = int(per.shape[0])
        rows[name] = row
    return pd.DataFrame(rows).T


D_BEFORE = f"{D}_before"   # D's outputs as the synthesis worker left them, before the verifier


def verifier_fix_kinds() -> pd.DataFrame:
    """Of the D turns the verifier fixed (failed before it, passed after), how many failed before it
    because a required output was missing and how many because a stored value was wrong, per
    backbone and in total; and of the turns it broke, how many it broke to a wrong value. Reads
    the stored pre-verifier and final cards; the class comes from the validator message
    (error_messages.error_class)."""
    import json
    from error_messages import error_class

    rows = []
    for final_path in (PHASE3 / "results").glob(f"*/*/*/{D}/*/r*/programmatic_verification.json"):
        before_path = Path(str(final_path).replace(f"/{D}/", f"/{D_BEFORE}/"))
        final = json.loads(final_path.read_text()); before = json.loads(before_path.read_text())
        model = final_path.parts[-3]
        fb = {(c["id"], t["turn"]): t for c in before["conversations"] for t in c["turns"]}
        for c in final["conversations"]:
            for t in c["turns"]:
                b = fb[(c["id"], t["turn"])]
                if not b["success"] and t["success"]:
                    rows.append(dict(model=model, kind="fixed", cls="missing" if error_class(b.get("message") or "") == "unset" else "wrong value"))
                elif b["success"] and not t["success"]:
                    rows.append(dict(model=model, kind="broken", cls="missing" if error_class(t.get("message") or "") == "unset" else "wrong value"))
    tr = pd.DataFrame(rows)
    out = tr.groupby(["model", "kind", "cls"]).size().unstack(["kind", "cls"], fill_value=0).reindex(models())
    out.loc["pooled"] = out.sum()
    return out


def bayes_factorial() -> pd.DataFrame:
    """The registered primary model (bambi/PyMC, `analysis/bayes.py` of the study repository)
    fitted on the four core arms of all backbones: posterior mean and 95% interval on the
    probability scale (pp) of verification, decomposition, the interaction and the four
    contrasts, read from the pooled section of `study_bayes.md`."""
    import re

    text = (REPORT / "study_bayes.md").read_text()
    sec = text.split("## pooled over backbones", 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in sec.splitlines():
        m = re.match(r"\|\s*([^|]+?)\s*\|\s*([+-]?[\d.]+)\s*\|\s*\[([+-]?[\d.]+),\s*([+-]?[\d.]+)\]\s*\|", line)
        if m:
            label = m.group(1)
            key = next((k for k in ("verification", "decomposition", "interaction") if label.startswith(k)), None)
            key = key or {"H1": "H1", "H2:": "H2", "H2a": "H2a", "H2b": "H2b", "H2c": "H2c"}.get(label.split()[0], label)
            rows[key] = dict(pp=float(m.group(2)), lo=float(m.group(3)), hi=float(m.group(4)))
    assert {"verification", "decomposition", "interaction"} <= set(rows), rows.keys()
    return pd.DataFrame(rows).T


# --------------------------------------------------------------------------- where the gain comes from
# Exploratory subgroup and per-output analyses of experiment 2 (Fig. 5d; Supplementary Tables
# 27-31). All use the study's estimator: per-task means, 10,000 task resamples, seed 20260929.

def task_meta() -> pd.DataFrame:
    """One row per task of the suite: category, difficulty, case type, city, number of turns and
    the required outputs of each turn (a list of lists), from the released task files."""
    rows = []
    for p in sorted((PHASE3 / "suites" / "air_quality" / "tasks").glob("*/*.json")):
        j = json.loads(p.read_text())
        turns = [t for c in j["conversations"] for t in c["turns"]]
        rows.append(dict(task=j["name"], category=j["category"], difficulty=j["difficulty"], case_type=j["case_type"],
                         domain=j["domain"], turns=len(turns), stores=[t["stores"] for t in turns]))
    return pd.DataFrame(rows).set_index("task")


def _effect_row(per: pd.DataFrame, rng, resamples: int) -> dict:
    """Arm accuracies, the two main effects, D - B and D - A on per-task means (rows tasks,
    columns the four core arms), each with its percentile interval over task resamples."""
    import numpy as np

    a, b, c, d = (per[x] for x in CORE)
    eff = {"A": a, "B": b, "C": c, "D": d, "verification": ((b - a) + (d - c)) / 2,
           "decomposition": ((c - a) + (d - b)) / 2, "D_minus_B": d - b, "D_minus_A": d - a}
    n = len(per); draws = rng.integers(0, n, (resamples, n))
    row = {"tasks": n}
    for k, v in eff.items():
        x = v.to_numpy(); bs = x[draws].mean(axis=1)
        row[f"{k}_pp"], row[f"{k}_lo"], row[f"{k}_hi"] = 100 * x.mean(), 100 * np.percentile(bs, 2.5), 100 * np.percentile(bs, 97.5)
    return row


def _core_task_means(repeats=None) -> pd.DataFrame:
    """Per-task pass rate of the four core arms, pooled over backbones (and over the given
    repeats, default all three)."""
    o = study_outcomes(); core = o[o.arm.isin(CORE)]
    if repeats is not None:
        core = core[core.repeat.isin(repeats)]
    return core.groupby(["task", "arm"]).ok.mean().unstack("arm")[CORE]


def effects_by_group(groups: pd.Series, repeats=None, seed: int = 20260929, resamples: int = 10_000) -> pd.DataFrame:
    """The factorial within each group of tasks (`groups`: task -> label). Rows: group labels in
    first-seen order, then "all"."""
    import numpy as np

    per = _core_task_means(repeats)
    rng = np.random.default_rng(seed)
    rows = {}
    for label in dict.fromkeys(groups):
        rows[label] = _effect_row(per[groups.loc[per.index] == label], rng, resamples)
    rows["all"] = _effect_row(per, rng, resamples)
    return pd.DataFrame(rows).T


# Single-agent pass rate on repeat 1, pooled over the eight backbones, is a multiple of 1/8: the
# bins are "5 or fewer of the eight passed", "6 or 7" and "all eight".
BASELINE_BINS = [(0.0, 0.70, "<=5 of 8"), (0.70, 0.92, "6-7 of 8"), (0.92, 1.01, "8 of 8")]


def effects_by_baseline(seed: int = 20260929, resamples: int = 10_000) -> pd.DataFrame:
    """The factorial by how well the single agent did on the task. Tasks are binned by how many
    of the eight single agents passed them on repeat 1 (five or fewer, six or seven, all eight)
    and the effects are estimated on repeats 2 and 3 only, so the binning variable and the
    outcome never share a run. Rows: the three bins and
    "all" (repeats 2-3). The frame's `attrs["spearman"]` holds the task-level Spearman rho and p
    of each main effect against single-agent accuracy over all repeats (descriptive)."""
    from scipy.stats import spearmanr

    first = _core_task_means([1])[A]
    label = pd.Series({t: next(l for lo, hi, l in BASELINE_BINS if lo <= v < hi or (v >= 1 and hi > 1)) for t, v in first.items()})
    label = label.loc[sorted(label.index, key=lambda t: [l for _, _, l in BASELINE_BINS].index(label[t]))]
    out = effects_by_group(label, repeats=[2, 3], seed=seed, resamples=resamples)
    out["first_repeat_A_pp"] = [100 * first[label == l].mean() if l != "all" else 100 * first.mean() for l in out.index]
    per = _core_task_means()
    ver = ((per[B] - per[A]) + (per[D] - per[C])) / 2; dec = ((per[C] - per[A]) + (per[D] - per[B])) / 2
    out.attrs["spearman"] = {"verification": tuple(spearmanr(per[A], ver)), "decomposition": tuple(spearmanr(per[A], dec))}
    return out


def effects_by_turns(seed: int = 20260929, resamples: int = 10_000) -> pd.DataFrame:
    """The factorial on single-turn and on multi-turn tasks (all repeats)."""
    meta = task_meta()
    groups = pd.Series({t: "single-turn" if n == 1 else "multi-turn" for t, n in meta.turns.items()})
    groups = groups.sort_values(ascending=False)   # single-turn first
    return effects_by_group(groups, seed=seed, resamples=resamples)


def effects_by_category(seed: int = 20260929, resamples: int = 10_000) -> pd.DataFrame:
    """The factorial within each of the suite's eleven expert-defined categories (all repeats),
    rows in alphabetical order then "all"."""
    meta = task_meta()
    return effects_by_group(meta.category.sort_values(), seed=seed, resamples=resamples)


def effects_by_kind(seed: int = 20260929, resamples: int = 10_000) -> pd.DataFrame:
    """The factorial within each kind of knowledge (scripts/knowledge_kinds.py, a post hoc
    grouping), plus a row "regulatory minus others": the difference in each effect between the
    regulatory tasks and all other tasks, with an interval from independent resampling of the
    two groups."""
    import numpy as np
    from knowledge_kinds import KIND_OF, KIND_ORDER

    groups = pd.Series(KIND_OF)
    groups = groups.loc[sorted(groups.index, key=lambda t: KIND_ORDER.index(groups[t]))]
    out = effects_by_group(groups, seed=seed, resamples=resamples)
    per = _core_task_means()
    reg, rest = per[groups.loc[per.index] == "regulatory"], per[groups.loc[per.index] != "regulatory"]
    rng = np.random.default_rng(seed)
    row = {"tasks": len(reg)}
    for k, f in (("verification", lambda p: ((p[B] - p[A]) + (p[D] - p[C])) / 2),
                 ("decomposition", lambda p: ((p[C] - p[A]) + (p[D] - p[B])) / 2)):
        r, s = f(reg).to_numpy(), f(rest).to_numpy()
        bs = (r[rng.integers(0, len(r), (resamples, len(r)))].mean(axis=1)
              - s[rng.integers(0, len(s), (resamples, len(s)))].mean(axis=1))
        row[f"{k}_pp"], row[f"{k}_lo"], row[f"{k}_hi"] = 100 * (r.mean() - s.mean()), 100 * np.percentile(bs, 2.5), 100 * np.percentile(bs, 97.5)
    out.loc["regulatory minus others"] = pd.Series(row)
    return out


def repeat_consistency_all(seed: int = 20260929, resamples: int = 10_000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """For each of the six arms: the share of the 888 backbone x task cells passed in all three
    repeats, in none, and in one or two ("mixed"); and, for the contrasts B - A, D - C, C - A and
    D - B, the difference in the all-three share with its task-resampled interval (cells of a
    task resampled together)."""
    import numpy as np

    o = study_outcomes(); o = o[o.arm.isin(ARMS6)]
    per = o.groupby(["arm", "task", "model"]).ok.sum().unstack("arm")
    shares = pd.DataFrame({"all_three": 100 * (per == 3).mean(), "none": 100 * (per == 0).mean(),
                           "mixed": 100 * per.isin([1, 2]).mean()}).loc[ARMS6]
    all3 = (per == 3).astype(float).groupby("task").mean()   # per task, averaged over backbones
    rng = np.random.default_rng(seed); n = len(all3); draws = rng.integers(0, n, (resamples, n))
    rows = {}
    for name, (t, c) in {"B-A": (B, A), "D-C": (D, C), "C-A": (C, A), "D-B": (D, B)}.items():
        d = (all3[t] - all3[c]).to_numpy(); bs = d[draws].mean(axis=1)
        rows[name] = dict(delta_pp=100 * d.mean(), lo_pp=100 * np.percentile(bs, 2.5), hi_pp=100 * np.percentile(bs, 97.5))
    return shares, pd.DataFrame(rows).T


MAGNITUDE_BINS = ["order of magnitude", ">=50%", "10-50%", "1-10%", "<1%"]


def _magnitude(got: str, expected: str):
    """Bin a numeric mismatch by its size: a ratio of 10 or more either way, else by relative
    error. None when either side is not a finite number or the reference is zero."""
    try:
        g, e = float(got), float(expected)
    except (TypeError, ValueError):
        return None
    if e == 0 or not (abs(g) < float("inf") and abs(e) < float("inf")):
        return None
    if g / e >= 10 or abs(g / e) <= 0.1 or g / e < 0 and abs(g / e) >= 10:
        return MAGNITUDE_BINS[0]
    rel = abs(g - e) / abs(e)
    return MAGNITUDE_BINS[1] if rel >= .5 else MAGNITUDE_BINS[2] if rel >= .1 else MAGNITUDE_BINS[3] if rel >= .01 else MAGNITUDE_BINS[4]


def _variables(card: dict, stores: list[list[str]]) -> dict:
    """For every required output of every turn of a card: ("ok", None, None) in a passed turn; in
    a failed turn the parse of the validator message ("unset"/"type"/"mismatch", got, expected)
    for the outputs it names and ("undetermined", None, None) for the rest. Keys (turn, variable)."""
    from error_messages import parse_variables

    out = {}
    for c in card["conversations"]:
        for t in c["turns"]:
            if t.get("success"):
                wrong, default = {}, ("ok", None, None)
            else:
                # a failed turn: only the outputs its message names are known to be wrong; a
                # validator may stop at its first failed check, so the rest are undetermined
                wrong, default = parse_variables(t.get("message") or ""), ("undetermined", None, None)
            for v in stores[t["turn"] - 1]:
                out[(t["turn"], v)] = wrong.get(v, default)
    return out


def verifier_transitions() -> dict:
    """Every required output of every D turn, before and after the verifier (the stored
    pre-verifier and final cards): kept (right before and after), fixed (wrong or missing before,
    right after), broke (right before, wrong after) and survived (wrong before and after).
    Returns {"totals": Series, "by_type": frame (numeric / string / boolean, from the expected
    value), "by_magnitude": frame (numeric mismatches before the verifier, by size), "by_category":
    frame}, each with fixed, survived, broke, kept counts and the fix rate (fixed over fixed +
    survived) in per cent, and "undetermined": the outputs left out because a failed turn's
    validator message, before or after the verifier, does not name them (a validator may stop at
    its first failed check)."""
    meta = task_meta(); stores = meta.stores.to_dict()
    rows, expected, undetermined = [], {}, {"before": 0, "after": 0}
    for final_path in (PHASE3 / "results").glob(f"*/*/*/{D}/*/r*/programmatic_verification.json"):
        before_path = Path(str(final_path).replace(f"/{D}/", f"/{D_BEFORE}/"))
        task, category = final_path.parts[-5], final_path.parts[-6]
        final_card = json.loads(final_path.read_text())
        fin = _variables(final_card, stores[task])
        bef = _variables(json.loads(before_path.read_text()), stores[task])
        for c in final_card["conversations"]:      # the expected value of an output: a passing turn's stored value
            for t in c["turns"]:
                if t.get("success"):
                    for var, val in (t.get("runtime_variables") or {}).items():
                        if val is not None:
                            expected.setdefault((task, var), str(val))
        for key, (kb, gb, eb) in bef.items():
            ka = fin[key][0]
            if kb == "undetermined" or ka == "undetermined":
                undetermined["before" if kb == "undetermined" else "after"] += 1
                continue
            trans = ("kept" if kb == "ok" and ka == "ok" else "fixed" if kb != "ok" and ka == "ok"
                     else "broke" if kb == "ok" else "survived")
            exp = eb if eb is not None else fin[key][2]
            if exp is not None:                    # or a mismatch message's reference
                expected.setdefault((task, key[1]), exp)
            rows.append(dict(task=task, category=category, var=key[1], kind_before=kb, trans=trans,
                             magnitude=_magnitude(gb, eb) if kb == "mismatch" else None))
    tr = pd.DataFrame(rows)
    tr["expected"] = [expected.get((t, v)) for t, v in zip(tr.task, tr["var"])]

    def vtype(e):
        if e is None:
            return "unknown"
        if str(e).lower() in ("true", "false"):
            return "boolean"
        return "numeric" if _is_number(e) else "string"
    tr["vtype"] = tr.expected.map(vtype)

    def summarise(by):
        t = tr.groupby([by, "trans"]).size().unstack(fill_value=0).reindex(columns=["fixed", "survived", "broke", "kept"], fill_value=0)
        t["fix_rate"] = 100 * t.fixed / (t.fixed + t.survived)
        return t
    totals = tr.trans.value_counts().reindex(["fixed", "survived", "broke", "kept"], fill_value=0)
    return {"totals": totals, "undetermined": undetermined, "by_type": summarise("vtype"),
            "by_magnitude": summarise("magnitude").reindex(MAGNITUDE_BINS),
            "by_category": summarise("category"), "frame": tr}


def shared_judgements(min_backbones: int = 3, min_families: int = 2) -> pd.DataFrame:
    """Boolean outputs on which the same wrong value was returned by at least `min_backbones`
    backbones from `min_families` model families, counted over the A and D cards: runs, backbones,
    families, and the A and D counts. Exploratory; coincidence does not establish a mechanism."""
    meta = task_meta(); stores = meta.stores.to_dict()
    rows = []
    for arm in (A, D):
        for path in (PHASE3 / "results").glob(f"*/*/*/{arm}/*/r*/programmatic_verification.json"):
            task, model = path.parts[-5], path.parts[-3]
            for (turn, var), (kind, got, exp) in _variables(json.loads(path.read_text()), stores[task]).items():
                if kind == "mismatch" and str(got).lower() in ("true", "false"):
                    rows.append(dict(task=task, var=var, got=str(got).capitalize(), expected=str(exp).capitalize(), arm=ARM_LABELS[arm], model=model))
    f = pd.DataFrame(rows); f["family"] = f.model.map(FAMILY)
    g = f.groupby(["task", "var", "got", "expected"]).agg(runs=("model", "size"), backbones=("model", "nunique"), families=("family", "nunique"),
                                                        A=("arm", lambda s: int((s == "A").sum())), D=("arm", lambda s: int((s == "D").sum()))).reset_index()
    return g[(g.backbones >= min_backbones) & (g.families >= min_families)].sort_values("runs", ascending=False).reset_index(drop=True)


_NUMBER_IN_TEXT = re.compile(r"(?<![\w.])-?\d+(?:,\d{3})*(?:\.\d+)?(?![\w.])")
_LABEL_BEFORE = re.compile(r"(?:table|tables|fig\.?|figure|figures|note|notes|step|steps|supplementary|section|no\.|station|stations|site|sites|turn|repeat|version|option|case)\s*$", re.I)


def _in_prose(text: str, expected) -> bool:
    """Whether an expected value appears in an answer's text as a free-standing number within
    0.1% of it (or within 0.005), or a string as a substring. A number that is part of a larger
    token (a year, an identifier, a scientific-notation mantissa) or that follows a label such
    as "Table" or "Fig." does not count. Booleans never match."""
    if expected is None or str(expected).lower() in ("true", "false"):
        return False
    try:
        r = float(expected)
    except ValueError:
        return str(expected).strip("'\"") in text
    tol = max(abs(r) * 0.001, 0.005)
    for m in _NUMBER_IN_TEXT.finditer(text):
        if _LABEL_BEFORE.search(text[max(0, m.start() - 16):m.start()]):
            continue
        if abs(float(m.group().replace(",", "")) - r) <= tol:
            return True
    return False


def _is_number(x) -> bool:
    try:
        float(x); return x is not None
    except (TypeError, ValueError):
        return False


def prose_credit(seed: int = 20260929, resamples: int = 10_000) -> dict:
    """How much of D - A is output delivery rather than wrong values. A single-agent run that
    failed only because required outputs were not set, and whose text answer states the expected
    value of every unset output (numeric within 0.5%, strings as substrings; booleans never
    credited), is credited as passed. Returns {"pooled": Series (A, A_credited, D, D_minus_A,
    D_minus_A_credited, credit_pp, each with lo/hi), "by_model": frame, "hit_rate": Series (share
    of unset numeric outputs whose value appears in the text, pooled and per backbone),
    "unset_numeric": int}. Reads the A cards and run records; the expected value of an unset
    output comes from any mismatch message naming it or from a passing run's stored value."""
    import numpy as np
    from error_messages import parse_variables

    meta = task_meta(); stores = meta.stores.to_dict()
    cards, responses, expected = {}, {}, {}
    for arm in (A, D):
        for path in (PHASE3 / "results").glob(f"*/*/*/{arm}/*/r*/programmatic_verification.json"):
            task, model, rep = path.parts[-5], path.parts[-3], int(path.parts[-2][1:])
            card = json.loads(path.read_text())
            vars_ = _variables(card, stores[task])
            for (turn, var), (kind, got, exp) in vars_.items():
                if kind == "mismatch" and exp is not None:
                    expected.setdefault((task, var), exp)
            for c in card["conversations"]:
                for t in c["turns"]:
                    if t.get("success"):
                        for var, val in (t.get("runtime_variables") or {}).items():
                            if val is not None and (task, var) not in expected:
                                expected[(task, var)] = str(val)
            if arm == A:
                # per failing turn: the parsed message, or None when nothing could be parsed
                cards[(task, model, rep)] = {t["turn"]: (parse_variables(t.get("message") or "") or None)
                                             for c in card["conversations"] for t in c["turns"] if not t.get("success")}
                run = json.loads((path.parent / "run.json").read_text())
                responses[(task, model, rep)] = {t["turn"]: t.get("response") or "" for c in run["conversations"] for t in c["turns"]}
    o = study_outcomes(); a = o[o.arm == A].copy()
    credited, hits = [], []
    for r in a.itertuples():
        key = (r.task, r.model, int(r.repeat))
        if r.ok:
            credited.append(1.0); continue
        turns = cards[key]
        if any(w is None or any(k != "unset" for k, _, _ in w.values()) for w in turns.values()):
            credited.append(0.0); continue   # a wrong value, or a failure the message does not itemise
        ok = True
        for turn, wrong in turns.items():
            for var in wrong:
                exp = expected.get((r.task, var)); hit = _in_prose(responses[key].get(turn, ""), exp)
                if _is_number(exp):
                    hits.append(dict(model=r.model, hit=hit))
                ok &= hit
        credited.append(float(ok))
    a["ok_credit"] = credited
    d = o[o.arm == D]
    per = pd.DataFrame({"A": a.groupby("task").ok.mean(), "A_credit": a.groupby("task").ok_credit.mean(), "D": d.groupby("task").ok.mean()})
    rng = np.random.default_rng(seed); n = len(per); draws = rng.integers(0, n, (resamples, n))

    def summary(p):
        row = {}
        for k, v in (("A", p.A), ("A_credited", p.A_credit), ("D", p.D), ("D_minus_A", p.D - p.A),
                     ("D_minus_A_credited", p.D - p.A_credit), ("credit", p.A_credit - p.A)):
            x = v.to_numpy(); bs = x[draws].mean(axis=1)
            row[f"{k}_pp"], row[f"{k}_lo"], row[f"{k}_hi"] = 100 * x.mean(), 100 * np.percentile(bs, 2.5), 100 * np.percentile(bs, 97.5)
        return pd.Series(row)
    by_model = {}
    for m in models():
        pm = pd.DataFrame({"A": a[a.model == m].groupby("task").ok.mean(), "A_credit": a[a.model == m].groupby("task").ok_credit.mean(),
                           "D": d[d.model == m].groupby("task").ok.mean()})
        by_model[m] = summary(pm)
    h = pd.DataFrame(hits)
    hit_rate = (100 * h.groupby("model").hit.mean()).reindex(models()); hit_rate["pooled"] = 100 * h.hit.mean()
    return {"pooled": summary(per), "by_model": pd.DataFrame(by_model).T, "hit_rate": hit_rate, "unset_numeric": int(len(h)),
            "credited_runs": int(sum(1 for c, k in zip(credited, a.ok) if c and not k)), "failed_runs": int((a.ok == 0).sum())}


def per_model_category() -> pd.DataFrame:
    """Task pass rate (%) of every backbone in each category under A and B, rows (model, arm)."""
    o = study_outcomes(); o = o[o.arm.isin([A, B])]
    t = o.groupby(["model", "arm", "category"]).ok.mean().unstack("category") * 100
    return t.rename(index=ARM_LABELS, level="arm")
