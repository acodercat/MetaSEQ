"""Particle-size evidence on Beijing's peak non-heating-season PM2.5 day.

Baseline: determine the peak and its recorded fine fraction; do not turn a
PM2.5/PM10 threshold into a source or haze diagnosis. Haze is not defined by
such a fraction (WMO International Cloud Atlas: https://cloudatlas.wmo.int/en/haze.html).
The fixed non-heating window is 16 March–9 November 2023 inclusive. Independent
raw-data freeze: .codex-review/new_rules_fix_20261008/frozen_answers.json.
Peak 2023-04-13; fine fraction 0.2813233486; 24 reporting network hours.
Reported precision rejects the coarse fraction and adjacent reports; a date
inside the excluded heating period is also rejected. Interpretation is in CC.
"""

import pandas as pd
from cave_agent import Variable
from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as


def _dates():
    frame = pd.read_csv(DATA_DIR / "air_quality.csv")
    frame["stamp"] = pd.to_datetime(frame[["year", "month", "day", "hour"]])
    hourly = frame.groupby("stamp")[["PM2.5", "PM10"]].mean()
    days = (hourly.index-pd.Timedelta(hours=1)).normalize()
    daily = hourly.groupby(days).mean().loc["2023-03-16":"2023-11-09"]
    peak = daily["PM2.5"].idxmax()  # sorted dates: earliest exact tie
    count = hourly.loc[(days == peak), "PM2.5"].notna().sum()
    return {"worst_pm25_day": peak.date(),
            "fine_particle_share": float(daily.loc[peak, "PM2.5"] / daily.loc[peak, "PM10"]),
            "peak_reporting_hours": int(count)}


def validate_worst_haze_date(response: str, runtime, turn: Turn):
    got = {name: runtime.retrieve(name) for name in
           ("worst_pm25_day", "fine_particle_share", "peak_reporting_hours")}
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _dates()
    errors = []
    if got["worst_pm25_day"] != str(gt["worst_pm25_day"]):
        errors.append(f"worst_pm25_day={got['worst_pm25_day']!r}, expected {gt['worst_pm25_day']}")
    for name in ("fine_particle_share", "peak_reporting_hours"):
        value = got[name]
        valid = is_finite_number(value) and (
            reports_as(value, gt[name], decimals=3) if name == "fine_particle_share"
            else compare_numeric(value, gt[name], tolerance=0))
        if not valid:
            errors.append(f"{name}={value!r}, expected {gt[name]}")
    return ValidatorResult(not errors, "; ".join(errors) if errors else "correct particle-size evidence")


tools = []
variables = [
    Variable("worst_pm25_day", None,
             "Store, as a string 'YYYY-MM-DD', the date with highest daily network PM2.5 from "
             "2023-03-16 through 2023-11-09 inclusive, outside Beijing's 2023 "
             "heating periods. Use all twelve stations and the domain's hourly-then-daily "
             "network construction and hour-ending dates, with no extra completeness "
             "filter. Break exact peak ties by earliest date."),
    Variable("fine_particle_share", None,
             "Store that day's daily network PM2.5 divided by daily network PM10, "
             "dimensionless to 3 decimal places. Construct both daily figures "
             "on the same domain convention, using each pollutant's reported "
             "values and unrounded daily means; do not average hourly ratios."),
    Variable("peak_reporting_hours", None,
             "Store the exact integer count of network hours reporting PM2.5 "
             "on the selected day; an hour qualifies when at least one station reports it."),
]
validators = {"validate_worst_haze_date": validate_worst_haze_date}
