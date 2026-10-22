"""beijing_w126_vegetation_exposure — hard baseline.

Decision: Select an exposure screening priority using a vegetation-relevant metric rather than annual-average ambient concentration.
Source concept: https://www.epa.gov/sites/default/files/2015-12/documents/ozone_max4_w126_data_handling.pdf
Plausible wrong paths: Selecting the annual-mean leader, using µg/m³ directly as ppm, or omitting EPA missing-hour adjustment.

Raw-data values were frozen before authoring in
.codex-review/new_cases_20261006/frozen_answers.json.
Reported answers: {'w126_leading_station': 'Dongsi', 'w126_start_month': '2025-05', 'annual_w126_ppm_hours': 52.94, 'w126_observed_hours': 1021, 'annual_mean_leading_station': 'Dingling', 'w126_station_annual_mean_o3': 73.27}

Each declared numeric precision rejects adjacent reported answers; all integer
counts use tolerance zero and finite-number guards. Runtime ground truth is
recomputed from the source files/database. No causal judgement is PV-scored.
The target is a named published metric or an identified reported observation.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable
from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

def _ground_truth():
    frame = pd.read_csv(DATA_DIR / "air_quality.csv")
    stamp = pd.to_datetime(frame[["year", "month", "day", "hour"]])
    frame["date"] = (stamp-pd.Timedelta(hours=1)).dt.normalize()
    frame = frame[frame.date.dt.year.eq(2025)].copy()
    mean = frame.groupby("station").O3.mean().sort_values(ascending=False)
    daylight = frame[frame.hour.isin(range(9,21))].copy()
    daylight["month"] = daylight.date.dt.month
    ppm = daylight.O3*24.45/48000
    daylight["weighted"] = ppm/(1+4403*np.exp(-126*ppm))
    months = daylight.groupby(["station", "month"]).agg(total=("weighted", "sum"), count=("O3", "count"))
    possible = np.array([pd.Period(f"2025-{m:02d}").days_in_month*12 for _,m in months.index])
    months["adjusted"] = months.total*possible/months["count"]
    months = months[months["count"].to_numpy() >= .75*possible]
    windows = []
    for station, values in months.groupby(level="station"):
        values = values.droplevel("station")
        for start in range(1,11):
            block = values.reindex(range(start,start+3))
            if block.adjusted.notna().all():
                windows.append((station,start,float(block.adjusted.sum()),int(block["count"].sum())))
    rank = pd.DataFrame(windows, columns=["station","start","value","n"]).sort_values(["value","station","start"],ascending=[False,True,True])
    best = rank.iloc[0]
    return dict(w126_leading_station=best.station, w126_start_month=f"2025-{best.start:02d}", annual_w126_ppm_hours=float(best.value), w126_observed_hours=int(best.n), annual_mean_leading_station=mean.index[0], w126_station_annual_mean_o3=float(mean.loc[best.station]))


tools = []
variables = [
    Variable('w126_leading_station', None, "Store the station with the largest annual 2025 W126 index, using EPA's 2015 W126 monthly missing-data adjustment and annual maximum three-month construction. This is a one-year screening index, not a three-year design value. Use the 12 local daytime hours starting 08:00 through 19:00, whose air-quality hour-ending labels are 09,10,11,12,13,14,15,16,17,18,19,20. Use ozone molar mass 48 g/mol and molar volume 24.45 L/mol; retain unrounded ppm values. Break exact station ties alphabetically."),
    Variable('w126_start_month', None, "Store the starting month, YYYY-MM, of the leading site's maximum three-consecutive-calendar-month W126 period wholly within 2025. Follow EPA 2015's minimum 75% daytime-hour monthly coverage and inverse-coverage monthly adjustment. Break exact window ties by earliest starting month."),
    Variable('annual_w126_ppm_hours', None, "Store that leading site's annual W126 in ppm-hours to 2 decimal places, summing its three adjusted monthly indices without intermediate rounding."),
    Variable('w126_observed_hours', None, 'Store the exact integer count of valid observed daytime O3 station-hours in that winning three-month window before coverage adjustment.'),
    Variable('annual_mean_leading_station', None, "Store the station with the largest mean of all its valid hourly O3 readings in calendar year 2025, using the domain's hour-ending convention and alphabetic exact-tie rule."),
    Variable('w126_station_annual_mean_o3', None, "Store the W126-leading station's calendar-2025 mean hourly O3 concentration in µg/m³ to 2 decimal places, using all its reported hours, not just daytime or the winning window."),
]

def validate_evidence(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "w126_leading_station": runtime.retrieve("w126_leading_station"),
        "w126_start_month": runtime.retrieve("w126_start_month"),
        "annual_w126_ppm_hours": runtime.retrieve("annual_w126_ppm_hours"),
        "w126_observed_hours": runtime.retrieve("w126_observed_hours"),
        "annual_mean_leading_station": runtime.retrieve("annual_mean_leading_station"),
        "w126_station_annual_mean_o3": runtime.retrieve("w126_station_annual_mean_o3"),
    }
    missing = [name for name,value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    expected = _ground_truth()
    errors = []
    if not (isinstance(got["w126_leading_station"], str) and got["w126_leading_station"].strip().casefold() == expected["w126_leading_station"].casefold()):
        errors.append("w126_leading_station="+repr(got["w126_leading_station"])+", expected "+repr(expected["w126_leading_station"]))
    try:
        parsed = pd.Timestamp(got["w126_start_month"])
        if parsed.tzinfo is not None:
            parsed = parsed.tz_convert("Asia/Hong_Kong")
        valid = not pd.isna(parsed) and parsed.strftime("%Y-%m") == expected["w126_start_month"]
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not (valid):
        errors.append("w126_start_month="+repr(got["w126_start_month"])+", expected "+repr(expected["w126_start_month"]))
    if not (is_finite_number(got["annual_w126_ppm_hours"]) and reports_as(got["annual_w126_ppm_hours"], expected["annual_w126_ppm_hours"], decimals=2)):
        errors.append("annual_w126_ppm_hours="+repr(got["annual_w126_ppm_hours"])+", expected "+repr(expected["annual_w126_ppm_hours"]))
    if not (is_finite_number(got["w126_observed_hours"]) and compare_numeric(got["w126_observed_hours"], expected["w126_observed_hours"], tolerance=0)):
        errors.append("w126_observed_hours="+repr(got["w126_observed_hours"])+", expected "+repr(expected["w126_observed_hours"]))
    if not (isinstance(got["annual_mean_leading_station"], str) and got["annual_mean_leading_station"].strip().casefold() == expected["annual_mean_leading_station"].casefold()):
        errors.append("annual_mean_leading_station="+repr(got["annual_mean_leading_station"])+", expected "+repr(expected["annual_mean_leading_station"]))
    if not (is_finite_number(got["w126_station_annual_mean_o3"]) and reports_as(got["w126_station_annual_mean_o3"], expected["w126_station_annual_mean_o3"], decimals=2)):
        errors.append("w126_station_annual_mean_o3="+repr(got["w126_station_annual_mean_o3"])+", expected "+repr(expected["w126_station_annual_mean_o3"]))
    return ValidatorResult(not errors, "; ".join(errors) if errors else "all objective evidence accepted")

validators = {"validate_evidence": validate_evidence}
