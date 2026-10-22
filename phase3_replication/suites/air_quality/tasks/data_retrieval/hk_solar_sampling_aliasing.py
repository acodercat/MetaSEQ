"""hk_solar_sampling_aliasing — hard baseline.

Decision: Decide whether sampled irradiance can substitute for measured day-level radiation in an ozone analysis.
Source concept: https://data.gov.hk/en-data/dataset/hk-hko-rss-daily-global-solar-radiation
Plausible wrong paths: Treating instantaneous samples as hourly means, summing W/m² without seconds/megajoule conversion, including repeated/missing hours, or reading correlation as agreement.

Raw-data values were frozen before authoring in
.codex-review/new_cases_20261006/frozen_answers.json.
Reported answers: {'solar_paired_complete_days': 26, 'sample_integral_daily_r': 0.998, 'sample_integral_mae_mj_m2': 0.247, 'sample_relative_error_p95_pct': 7.73, 'worst_sampling_day': '2025-01-26', 'worst_sample_integral_mj_m2': 2.164, 'worst_measured_integral_mj_m2': 2.51}

Each declared numeric precision rejects adjacent reported answers; all integer
counts use tolerance zero and finite-number guards. Runtime ground truth is
recomputed from the source files/database. No causal judgement is PV-scored.
Author-selected quadrature/cohort conventions make this an execution turn.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

def _ground_truth():
    samples = pd.read_csv(DATA_DIR / "radiation_1min_hko.csv",parse_dates=["observed"])
    samples = samples[samples.station.eq("King's Park") & samples.observed.ge("2025-01-01") & samples.observed.lt("2026-01-01")].copy()
    samples["date"] = samples.observed.dt.normalize()
    samples["finite"] = np.isfinite(samples.global_radiation_wm2)
    sums = samples.groupby("date").agg(n=("hour","size"),hours=("hour","nunique"),valid=("finite","sum"),integral=("global_radiation_wm2","sum"))
    sums = sums[(sums.n==24)&(sums.hours==24)&(sums.valid==24)]
    actual = pd.read_csv(DATA_DIR / "radiation_hko.csv",parse_dates=["date"]).set_index("date")
    actual = actual[actual.global_solar_radiation_mj_m2_completeness.eq("C") & actual.global_solar_radiation_mj_m2.gt(0)]
    paired = sums.join(actual[["global_solar_radiation_mj_m2"]],how="inner")
    estimate = paired.integral*.0036
    measured = paired.global_solar_radiation_mj_m2
    relative = (estimate-measured).abs()/measured*100
    worst = relative.sort_values(ascending=False,kind="stable").index[0]
    return dict(solar_paired_complete_days=len(paired), sample_integral_daily_r=float(estimate.corr(measured)), sample_integral_mae_mj_m2=float((estimate-measured).abs().mean()), sample_relative_error_p95_pct=float(relative.quantile(.95,interpolation="linear")), worst_sampling_day=f"{worst:%Y-%m-%d}", worst_sample_integral_mj_m2=float(estimate.loc[worst]), worst_measured_integral_mj_m2=float(measured.loc[worst]))


tools = []
variables = [
    Variable('solar_paired_complete_days', None, "Store the exact integer number of paired King's Park dates in calendar 2025 with exactly 24 sampled rows, all 24 distinct local hours, 24 finite global irradiances, and a strictly positive daily measured exposure flagged complete by HKO. Do not fill absent samples or aggregate duplicated hours."),
    Variable('sample_integral_daily_r', None, 'Store the Pearson correlation of sampled versus measured daily solar exposure on that cohort to 4 decimal places. Use the zero-order hourly quadrature approximation: each of the 24 instantaneous one-minute global irradiance samples represents a 3600-second interval. Keep sample-time calendar dates, since this feed is instantaneous, rather than shifting them as hourly means.'),
    Variable('sample_integral_mae_mj_m2', None, 'Store MAE of those sampled exposure approximations against measured daily exposures, in MJ/m² to 3 decimal places.'),
    Variable('sample_relative_error_p95_pct', None, 'Store the 95th percentile of absolute relative sampled-exposure errors on those paired days, in percent to 2 decimal places, using linear quantile interpolation and measured daily exposure as denominator.'),
    Variable('worst_sampling_day', None, 'Store, as a string YYYY-MM-DD, the date with largest absolute relative exposure error in that same cohort; break exact ties by earliest date.'),
    Variable('worst_sample_integral_mj_m2', None, 'Store the sampled exposure approximation on that worst day in MJ/m² to 3 decimal places.'),
    Variable('worst_measured_integral_mj_m2', None, 'Store the independent daily HKO exposure on that same worst day in MJ/m² to 3 decimal places.'),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "solar_paired_complete_days": runtime.retrieve("solar_paired_complete_days"),
        "sample_integral_daily_r": runtime.retrieve("sample_integral_daily_r"),
        "sample_integral_mae_mj_m2": runtime.retrieve("sample_integral_mae_mj_m2"),
        "sample_relative_error_p95_pct": runtime.retrieve("sample_relative_error_p95_pct"),
        "worst_sampling_day": runtime.retrieve("worst_sampling_day"),
        "worst_sample_integral_mj_m2": runtime.retrieve("worst_sample_integral_mj_m2"),
        "worst_measured_integral_mj_m2": runtime.retrieve("worst_measured_integral_mj_m2"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    if not (is_finite_number(got["solar_paired_complete_days"]) and compare_numeric(got["solar_paired_complete_days"], expected["solar_paired_complete_days"], tolerance=0)):
        errors.append("solar_paired_complete_days="+repr(got["solar_paired_complete_days"])+", expected "+repr(expected["solar_paired_complete_days"]))
    if not (is_finite_number(got["sample_integral_daily_r"]) and reports_as(got["sample_integral_daily_r"], expected["sample_integral_daily_r"], decimals=4)):
        errors.append("sample_integral_daily_r="+repr(got["sample_integral_daily_r"])+", expected "+repr(expected["sample_integral_daily_r"]))
    if not (is_finite_number(got["sample_integral_mae_mj_m2"]) and reports_as(got["sample_integral_mae_mj_m2"], expected["sample_integral_mae_mj_m2"], decimals=3)):
        errors.append("sample_integral_mae_mj_m2="+repr(got["sample_integral_mae_mj_m2"])+", expected "+repr(expected["sample_integral_mae_mj_m2"]))
    if not (is_finite_number(got["sample_relative_error_p95_pct"]) and reports_as(got["sample_relative_error_p95_pct"], expected["sample_relative_error_p95_pct"], decimals=2)):
        errors.append("sample_relative_error_p95_pct="+repr(got["sample_relative_error_p95_pct"])+", expected "+repr(expected["sample_relative_error_p95_pct"]))
    try:
        parsed = pd.Timestamp(got["worst_sampling_day"])
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("Asia/Hong_Kong")
        valid = not pd.isna(parsed) and parsed.strftime("%Y-%m-%d") == expected["worst_sampling_day"]
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not (valid):
        errors.append("worst_sampling_day="+repr(got["worst_sampling_day"])+", expected "+repr(expected["worst_sampling_day"]))
    if not (is_finite_number(got["worst_sample_integral_mj_m2"]) and reports_as(got["worst_sample_integral_mj_m2"], expected["worst_sample_integral_mj_m2"], decimals=3)):
        errors.append("worst_sample_integral_mj_m2="+repr(got["worst_sample_integral_mj_m2"])+", expected "+repr(expected["worst_sample_integral_mj_m2"]))
    if not (is_finite_number(got["worst_measured_integral_mj_m2"]) and reports_as(got["worst_measured_integral_mj_m2"], expected["worst_measured_integral_mj_m2"], decimals=3)):
        errors.append("worst_measured_integral_mj_m2="+repr(got["worst_measured_integral_mj_m2"])+", expected "+repr(expected["worst_measured_integral_mj_m2"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
