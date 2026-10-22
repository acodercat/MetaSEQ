"""Audit archived A/D scorecards for the failure and robustness displays.

No model calls or fresh database queries. Reference values are those recorded
by the validators. All new subgroup analyses are exploratory.
"""
from collections import Counter
import json
from pathlib import Path

import numpy as np
import pandas as pd

import replication_tables as rt
from error_messages import NUMERIC_MISMATCH, error_class, ORDER

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript/analysis/failure_evidence"
MODEL_ORDER = ["qwen3.8-27b", "qwen3.8-27b-thinking", "qwen3.8-flash",
               "deepseek-v4-flash", "deepseek-v4-flash-thinking", "deepseek-v4-pro-0813",
               "gpt-6-luna", "claude-sonnet-5-5"]
TASK_LABELS = {
    "beijing_regional_trend_attribution": "Regional trend",
    "beijing_o3_mda8_exceedance": "Ozone exceedance days",
    "beijing_realtime_anomaly_lookahead": "Real-time anomaly",
    "beijing_aqi_co_unit": "CO-to-AQI conversion",
    "beijing_fire_detection_bias": "Fire detection bias",
    "beijing_no3_production_kinetics": "NO₃ production kinetics",
    "beijing_spring_sector_tail": "Spring wind sectors",
    "hk_cny_traffic_quasi_experiment": "Holiday traffic contrast",
    "hk_ozone_probability_skill": "Ozone alert skill",
    "hk_moisture_mixing_ratio_rank": "Moisture mixing ratio",
    "hk_pm25_change_coverage_pushback": "PM₂.₅ coverage",
    "hk_moist_hypsometric_thickness": "Moist-layer thickness",
    "hk_nocturnal_decoupling_morning_fumigation": "Nocturnal decoupling",
    "hk_sunshine_ozone_scale_reversal": "Sunshine–ozone scale",
    "hk_partial_column_water_mass": "Partial-column water",
    "hk_aqo_station_level_compliance": "NO₂ compliance",
    "hk_calm_coded_as_north": "Calm-wind coding",
    "hk_hot_nights_hourly_ceiling": "Hourly cold-day count",
}
CASE_TURNS = [("hk_ozone_peak_season_aqo", 1, "Ozone season"),
              ("hk_aqo_station_level_compliance", 2, "NO₂ compliance")]


def load_turns():
    records = []
    for arm in (rt.A, rt.D):
        for path in sorted((rt.PHASE3 / "results").glob(f"*/*/*/{arm}/*/r*/programmatic_verification.json")):
            domain, category, task, _, model, repeat = path.parts[-7:-1]
            card = json.loads(path.read_text())
            for ci, conversation in enumerate(card["conversations"]):
                for turn in conversation["turns"]:
                    records.append(dict(domain=domain, category=category, task=task, arm=arm,
                        model=model, repeat=int(repeat[1:]), conversation=conversation["id"],
                        conversation_order=ci, turn=turn["turn"], passed=bool(turn["success"]),
                        message=turn.get("message", "") or "", path=str(path.relative_to(ROOT))))
    frame = pd.DataFrame(records)
    assert len(frame) == 8160 and (~frame.passed).sum() == 1138
    keys = ["model", "task", "repeat", "arm"]
    actual = frame.groupby(keys).passed.all().sort_index()
    expected = rt.outcomes().set_index(keys).passed.sort_index()
    pd.testing.assert_series_equal(actual, expected, check_names=False)
    return frame


def discordant_errors(turns):
    paired = rt.outcomes().pivot(index=["model", "task", "repeat"], columns="arm", values="passed")
    first = turns[~turns.passed].sort_values(["conversation_order", "turn"]).groupby(
        ["model", "task", "repeat", "arm"]).first()
    rows = []
    for direction, mask, arm in [("fixed", ~paired[rt.A] & paired[rt.D], rt.A),
                                  ("broken", paired[rt.A] & ~paired[rt.D], rt.D)]:
        for model, task, repeat in paired[mask].index:
            r = first.loc[(model, task, repeat, arm)]
            rows.append(dict(direction=direction, model=model, task=task, repeat=repeat,
                arm=arm, turn=int(r.turn), error_class=error_class(r.message),
                message=r.message, path=r.path))
    detail = pd.DataFrame(rows)
    counts = pd.crosstab(detail.error_class, detail.direction).reindex(ORDER)
    assert (counts.fixed.sum(), counts.broken.sum()) == (362, 175)
    pd.testing.assert_frame_equal(counts.sort_index(), rt.fixed_broken_by_class().sort_index()[counts.columns],
                                  check_names=False)
    return detail, counts


def shared_values(turns):
    records = []
    for r in turns[~turns.passed].itertuples():
        for variable, got, expected in NUMERIC_MISMATCH.findall(r.message):
            records.append(dict(task=r.task, variable=variable, value=round(float(got), 4),
                reference=float(expected), model=r.model, family=rt.FAMILY[r.model],
                arm=r.arm, repeat=r.repeat, conversation=r.conversation, turn=r.turn,
                message=r.message, path=r.path))
    numeric = pd.DataFrame(records)
    summaries, evidence = [], []
    for (task, variable), group in numeric.groupby(["task", "variable"], sort=True):
        # Explicit deterministic tie break. A tie is recorded, not hidden.
        frequencies = group.value.value_counts()
        maximum = int(frequencies.max())
        modes = sorted(frequencies[frequencies == maximum].index)
        modal = modes[0]
        same = group[group.value == modal]
        if len(group) < 8 or maximum / len(group) < .5 or same.model.nunique() < 3:
            continue
        if same.family.nunique() < 2:
            continue
        reference = sorted(same.reference.unique().tolist())
        row = dict(task=task, variable=variable, wrong_value=float(modal),
                   reference_values=reference, modal_count=maximum, parsed_wrong_count=len(group),
                   modal_tie=len(modes) > 1, n_configurations=same.model.nunique(),
                   n_families=same.family.nunique(), families=",".join(sorted(same.family.unique())),
                   A_count=int(same.arm.eq(rt.A).sum()), D_count=int(same.arm.eq(rt.D).sum()),
                   example_path=same.iloc[0].path,
                   evidence_status="Matched numeric output; causal route not assigned")
        if task == "hk_aqo_station_level_compliance":
            row["evidence_status"] = "Network pooling documented in inspected transcripts; not an intervention"
        summaries.append(row)
        evidence.append(same)
    summary = pd.DataFrame(summaries)
    # One representative output per task: strongest family coverage, then count,
    # then variable name. The full table retains every qualifying output.
    representative = summary.sort_values(
        ["task", "n_families", "modal_count", "variable"], ascending=[True, False, False, True]
    ).drop_duplicates("task")
    representative = representative.sort_values(
        ["n_families", "modal_count", "task"], ascending=[False, False, True]).reset_index(drop=True)
    ids = {t: f"T{i+1:02}" for i, t in enumerate(representative.task)}
    summary["task_id"] = summary.task.map(ids)
    representative["task_id"] = representative.task.map(ids)
    summary = summary.sort_values(["task_id", "variable"]).reset_index(drop=True)
    summary["evidence_id"] = [f"E{i+1:02}" for i in range(len(summary))]
    full = pd.concat(evidence, ignore_index=True).merge(
        summary[["task", "variable", "task_id", "evidence_id"]], on=["task", "variable"], validate="many_to_one")
    matrix = np.zeros((len(representative), 16), dtype=int)
    for i, r in representative.iterrows():
        selected = full[(full.task == r.task) & (full.variable == r.variable)]
        for j, model in enumerate(MODEL_ORDER):
            for k, arm in enumerate((rt.A, rt.D)):
                s = selected[(selected.model == model) & (selected.arm == arm)]
                assert len(s) == s.repeat.nunique(), (r.task, r.variable, model, arm)
                matrix[i, 2*j+k] = len(s)
        assert matrix[i].sum() == r.modal_count
    assert matrix.max() <= 3
    assert set(summary.task) == set(rt.convergent_tasks()["tasks"])
    return summary, representative, full, matrix


def task_contrast(frame, weighting="configuration"):
    per = frame.groupby(["task", "model", "arm"]).passed.mean().unstack("arm")
    if weighting == "model":
        per = per.reset_index()
        per["base_model"] = per.model.str.removesuffix("-thinking")
        per = per.groupby(["task", "base_model"])[[rt.A, rt.D]].mean()
    task = per.groupby("task")[[rt.A, rt.D]].mean().sort_index()
    diff = (task[rt.D] - task[rt.A]).to_numpy()
    rng = np.random.default_rng(20260929)
    samples = diff[rng.integers(0, len(diff), (10000, len(diff)))].mean(axis=1) * 100
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return dict(tasks=len(task), configurations=frame.model.nunique(),
                A=float(task[rt.A].mean()*100), D=float(task[rt.D].mean()*100),
                delta=float(diff.mean()*100), lo=float(lo), hi=float(hi))


def robustness():
    runs = rt.outcomes()
    revised = ["beijing_wind_sector_pm25", "hk_ozone_burden_year_on_year", "hk_sunshine_ozone_scale_reversal"]
    rows = []
    specs = [("Reference", "All tasks; eight configurations", runs, "configuration"),
             ("City", "Hong Kong", runs[runs.domain == "hk"], "configuration"),
             ("City", "Beijing", runs[runs.domain == "beijing"], "configuration")]
    specs += [("Task length", f"{n}-turn tasks", runs[runs.turns == n], "configuration") for n in (1, 2, 3)]
    specs += [("Sensitivity", "Exclude three revised-band tasks", runs[~runs.task.isin(revised)], "configuration"),
              ("Sensitivity", "Six models; modes averaged", runs, "model"),
              ("Sensitivity", "Six models; base modes only", runs[~runs.model.str.endswith("-thinking")], "configuration")]
    for group, label, frame, weighting in specs:
        rows.append(dict(group=group, label=label, weighting=weighting, **task_contrast(frame, weighting)))
    result = pd.DataFrame(rows)
    reference = rt.contrasts().query("scope == 'pooled'").iloc[0]
    assert np.allclose(result.iloc[0][["delta", "lo", "hi"]].astype(float),
                       [reference.delta_pp, reference.lo_pp, reference.hi_pp], atol=1e-7)
    return result


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    turns = load_turns()
    discordant, counts = discordant_errors(turns)
    shared, representative, records, matrix = shared_values(turns)
    robust = robustness()
    cases = pd.concat([turns[(turns.task == task) & (turns.turn == turn)] for task, turn, _ in CASE_TURNS])
    case_counts = cases.groupby(["task", "model", "arm"]).passed.agg(["sum", "count"]).reset_index()
    assert case_counts["count"].eq(3).all()
    summary = dict(scope="Post hoc archived-record analysis; no fresh reference recomputation or causal intervention",
                   error_counts=counts.to_dict(), qualifying_tasks=shared.task.nunique(),
                   qualifying_outputs=len(shared), failed_turns_on_selected_tasks=int(
                       ((~turns.passed) & turns.task.isin(shared.task)).sum()),
                   total_failed_turns=int((~turns.passed).sum()),
                   selection="At least 8 parsed wrong outputs; modal share >= 0.5; >= 3 configurations and >= 2 families; values rounded to 4 decimals",
                   cases=cases.groupby(["task", "arm"]).passed.agg(["sum", "count"]).reset_index().to_dict("records"))
    for name, frame in [("discordant_records", discordant), ("error_counts", counts.reset_index()),
                        ("shared_outputs", shared), ("representative_outputs", representative),
                        ("shared_output_records", records), ("robustness", robust), ("case_counts", case_counts)]:
        frame.to_csv(OUT / f"{name}.csv", index=False)
    np.savetxt(OUT / "shared_error_matrix.csv", matrix, delimiter=",", fmt="%d")
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return counts, shared, representative, records, matrix, robust, case_counts


if __name__ == "__main__":
    build()
