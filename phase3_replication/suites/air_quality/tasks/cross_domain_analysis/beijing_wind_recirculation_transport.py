"""beijing_wind_recirculation_transport — hard baseline.

Decision: Decide whether wind-speed-only evidence is sufficient for a ventilation statement.
Source concept: https://www.sciencedirect.com/science/article/pii/1352231094900485
Plausible wrong paths: Wind run treated as net displacement or used alone to select the best-ventilated day.

Raw-data values were frozen before authoring in
.codex-review/new_cases_20261006/frozen_answers.json.
Reported answers: {'most_recirculating_day': '2025-10-22', 'recirculation_factor': 0.9595, 'wind_run_km': 122.36, 'resultant_displacement_km': 4.95, 'complete_wind_days': 365}

Each declared numeric precision rejects adjacent reported answers; all integer
counts use tolerance zero and finite-number guards. Runtime ground truth is
recomputed from the source files/database. No causal judgement is PV-scored.
Author-selected quadrature/cohort conventions make this an execution turn.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

def _ground_truth():
    frame = pd.read_csv(DATA_DIR / "met_era5.csv", parse_dates=["datetime"])
    frame = frame[frame.station.eq("Dongsi") & frame.datetime.ge("2025-01-01") & frame.datetime.lt("2026-01-01")].copy()
    frame["day"] = frame.datetime.dt.normalize()
    rows = []
    for day, group in frame.groupby("day"):
        if len(group) != 24 or group.datetime.dt.hour.nunique() != 24 or not np.isfinite(group[["wind_speed_ms", "wind_dir_deg"]]).all().all():
            continue
        speeds = group.wind_speed_ms.to_numpy()
        bearings = np.deg2rad(group.wind_dir_deg.to_numpy())
        wind_run = float(speeds.sum()*3.6)
        vector = np.array([-np.dot(speeds, np.sin(bearings)), -np.dot(speeds, np.cos(bearings))])*3.6
        displacement = float(np.linalg.norm(vector))
        if wind_run > 0:
            rows.append((day, 1-displacement/wind_run, wind_run, displacement))
    result = pd.DataFrame(rows, columns=["day", "factor", "run", "displacement"]).sort_values(["factor", "day"], ascending=[False, True])
    best = result.iloc[0]
    return dict(most_recirculating_day=f"{best.day:%Y-%m-%d}", recirculation_factor=float(best.factor), wind_run_km=float(best.run), resultant_displacement_km=float(best.displacement), complete_wind_days=len(result))


tools = []
variables = [
    Variable('most_recirculating_day', None, 'Store the date, YYYY-MM-DD, of the largest 24-hour Allwine-Whiteman recirculation factor at Dongsi during 2025. Use the 24 instantaneous ERA5 samples stamped 00,01,02,03,04,05,06,07,08,09,10,11,12,13,14,15,16,17,18,19,20,21,22,23 as one-hour constant-wind intervals; retain only days with all 24 distinct hours and finite speed/direction. Break exact factor ties by earliest date.'),
    Variable('recirculation_factor', None, "Store that day's dimensionless Allwine-Whiteman recirculation factor to 4 decimal places, using unrounded hourly wind vectors and a 24-hour period."),
    Variable('wind_run_km', None, "Store that day's scalar wind run in km to 2 decimal places, from the same 24 hourly intervals."),
    Variable('resultant_displacement_km', None, "Store the length of that day's integrated horizontal wind vector in km to 2 decimal places, using the same interval approximation."),
    Variable('complete_wind_days', None, 'Store the exact integer count of 2025 Dongsi days meeting that complete wind-data definition with positive wind run.'),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "most_recirculating_day": runtime.retrieve("most_recirculating_day"),
        "recirculation_factor": runtime.retrieve("recirculation_factor"),
        "wind_run_km": runtime.retrieve("wind_run_km"),
        "resultant_displacement_km": runtime.retrieve("resultant_displacement_km"),
        "complete_wind_days": runtime.retrieve("complete_wind_days"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    try:
        parsed = pd.Timestamp(got["most_recirculating_day"])
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("Asia/Hong_Kong")
        valid = not pd.isna(parsed) and parsed.strftime("%Y-%m-%d") == expected["most_recirculating_day"]
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not (valid):
        errors.append("most_recirculating_day="+repr(got["most_recirculating_day"])+", expected "+repr(expected["most_recirculating_day"]))
    if not (is_finite_number(got["recirculation_factor"]) and reports_as(got["recirculation_factor"], expected["recirculation_factor"], decimals=4)):
        errors.append("recirculation_factor="+repr(got["recirculation_factor"])+", expected "+repr(expected["recirculation_factor"]))
    if not (is_finite_number(got["wind_run_km"]) and reports_as(got["wind_run_km"], expected["wind_run_km"], decimals=2)):
        errors.append("wind_run_km="+repr(got["wind_run_km"])+", expected "+repr(expected["wind_run_km"]))
    if not (is_finite_number(got["resultant_displacement_km"]) and reports_as(got["resultant_displacement_km"], expected["resultant_displacement_km"], decimals=2)):
        errors.append("resultant_displacement_km="+repr(got["resultant_displacement_km"])+", expected "+repr(expected["resultant_displacement_km"]))
    if not (is_finite_number(got["complete_wind_days"]) and compare_numeric(got["complete_wind_days"], expected["complete_wind_days"], tolerance=0)):
        errors.append("complete_wind_days="+repr(got["complete_wind_days"])+", expected "+repr(expected["complete_wind_days"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
