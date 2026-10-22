"""Beijing AQI primary pollutant — the PM2.5-by-default trap (regulatory_standards).

Diagnostic trap. HJ 633-2012 defines the day's primary pollutant as whichever
pollutant yields the largest IAQI sub-index, which requires computing a sub-index
for all six regulated pollutants on their own averaging bases (24-h mean for
PM2.5, PM10, SO2, NO2 and CO; maximum daily 8-hour running mean for O3).

Guanyuan, 2022-06-21 — a summer photochemical day:

- correct path: O3 (MDA8 basis) gives the largest sub-index, IAQI ~201.
- wrong path: reporting PM2.5, whose sub-index is ~94 and only the second
  largest. Two distinct errors produce it, which is why the trap is wide: (a)
  assuming PM2.5 is always primary without computing the others, and (b)
  computing O3 on a 24-hour mean instead of the MDA8 basis and reading it
  through the 1-hour table, which deflates the ozone sub-index to 61, below
  PM2.5's. (Through the 8-hour table the 24-hour mean, 168.8, still gives 108
  and O3 still leads; that variant is caught by the sub-index, not the name.)

No tolerance applies: the answer is a pollutant name, matched exactly after
case and punctuation normalisation, and the sub-index gap to the runner-up
(~201 against ~94) leaves no marginal case.

The query names HJ 633-2012 but deliberately NOT HJ 663-2013. Naming the latter
would announce that ozone is judged on a running 8-hour maximum, which is half
the trap — error (b) above is exactly the failure to know that. The query
instead pins the completeness rule in neutral terms ("where a pollutant's
sub-index is defined on a running-mean basis"), which secures P6 without
disclosing which pollutant that is.

Leaving the candidate-window set open is safe here, and measured rather than
assumed: admitting all 24 trailing windows leaves both the winner and its IAQI
unchanged, because ozone leads PM2.5 by 201 to 94. P1 holds on that margin.

**THE NAME ALONE WAS GUESSABLE, AND A NO-DATA CONTROL PROVED IT.** Asked this
case's query with the runtime taken away, `deepseek-v4-flash` and
`deepseek-v4-pro-0813` BOTH answered O3 and both passed (2026-08-26,
`scratchpad/no_data_control.py`). That is not surprising in hindsight: the
answer space is six pollutants, a summer day in Beijing has one obvious
candidate, and the wide sub-index margin this case relies on for P1 is exactly
what makes the guess safe. A trap whose correct answer is the prior is not a
trap — the naive path and the recalled answer differ here, but a model that
never computes anything reaches the right one anyway.

The repair scores the winner's SUB-INDEX alongside its name. 200.8645 rounds up
to 201 under clause 6.2 and cannot be produced without computing the ozone MDA8
and running it through the breakpoint table, which is the work the case exists
to test. The six sub-indices on the day, for the record:

    O3 200.8645 -> 201    PM2.5 94.0104 -> 95    PM10 77.3958 -> 78
    CO  40.8333 ->  41    NO2   30.5729 -> 31    SO2   4.9583 ->  5

The day is 01:00 on the 21st to 00:00 on the 22nd, the hour-ending reading
the MDA8 windows already use. Read as the labels 0-23 instead, the 24-hour
sub-indices move by up to 1.4 and ozone's not at all, so neither key does.

Scoring the value makes the ROUNDING DIRECTION load-bearing where it was not
before. This case was measured in discovery round 1 (A1) and found not to need
the pin while only the name was scored — fractional, up and half-up all name
O3. That is no longer true of 201, so the direction is now pinned on the
variable, matching `beijing_aqi_co_unit` and `beijing_aqi_aggregation_order`.

Both ground truths are recomputed here from the CSV.
"""

import math

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, is_finite_number
from tasks import Turn
from domains.beijing.mda8 import frame_to_mda8

_STATION, _DATE = "Guanyuan", "2022-06-21"

# HJ 633-2012 IAQI breakpoints. PM/SO2/NO2/O3 in ug/m3; CO in mg/m3.
_IAQI = [0, 50, 100, 150, 200, 300, 400, 500]
_BP = {
    "PM2.5": [0, 35, 75, 115, 150, 250, 350, 500],
    "PM10": [0, 50, 150, 250, 350, 420, 500, 600],
    "SO2": [0, 50, 150, 475, 800, 1600, 2100, 2620],
    "NO2": [0, 40, 80, 180, 280, 565, 750, 940],
    "CO": [0, 2, 4, 14, 24, 36, 48, 60],
    "O3": [0, 100, 160, 215, 265, 800],
}


def _iaqi(conc: float, bp: list) -> float:
    levels = _IAQI[: len(bp)]
    if not np.isfinite(conc):
        return np.nan
    if conc <= bp[0]:
        return 0.0
    if conc >= bp[-1]:
        return float(levels[-1])
    for i in range(1, len(bp)):
        if conc <= bp[i]:
            lo, hi = bp[i - 1], bp[i]
            il, ih = levels[i - 1], levels[i]
            return (ih - il) / (hi - lo) * (conc - lo) + il
    return float(levels[-1])


def _sub_indices() -> dict:
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    # Hour h is the hour ENDING at h:00, so a day is its hours 1-23 and hour 0
    # of the next date; the MDA8 helper owns its windows the same way.
    df["date"] = (pd.to_datetime(df[["year", "month", "day", "hour"]])
                  - pd.Timedelta(hours=1)).dt.normalize()
    station_year = df[(df["station"] == _STATION) & (df["date"].dt.year == 2022)]
    o3_mda8 = frame_to_mda8(station_year).get(pd.Timestamp(_DATE))
    g = df[(df["station"] == _STATION) & (df["date"] == _DATE)]
    conc = {
        "PM2.5": g["PM2.5"].mean(), "PM10": g["PM10"].mean(),
        "SO2": g["SO2"].mean(), "NO2": g["NO2"].mean(),
        "CO": g["CO"].mean() / 1000.0, "O3": o3_mda8,
    }
    return {p: _iaqi(conc[p], _BP[p]) for p in _BP}


def _norm(value) -> str:
    """Normalise a pollutant name for comparison: 'pm 2.5' -> 'PM2.5'."""
    s = str(value).strip().upper().replace(" ", "").replace("_", "")
    return {"PM25": "PM2.5", "OZONE": "O3", "O₃": "O3"}.get(s, s)


def validate_primary_pollutant(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("primary_pollutant")
    if val is None:
        return ValidatorResult(
            False, "primary_pollutant not set", variables_not_set=True
        )
    got = _norm(val)

    iaqi_val = runtime.retrieve("primary_iaqi")
    if iaqi_val is None:
        return ValidatorResult(
            False, "primary_iaqi not set", variables_not_set=True
        )

    ia = _sub_indices()
    ranked = sorted(ia.items(), key=lambda kv: -kv[1])
    correct = ranked[0]
    expected_iaqi = math.ceil(correct[1])

    errors = []
    if got != _norm(correct[0]):
        errors.append(f"primary_pollutant={val!r}, expected {correct[0]}")
    try:
        if not is_finite_number(iaqi_val) or iaqi_val != expected_iaqi:
            errors.append(f"primary_iaqi={iaqi_val}, expected {expected_iaqi}")
    except (TypeError, ValueError):
        errors.append(f"primary_iaqi={iaqi_val!r} is not an integer")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True, f"correct: {correct[0]} (IAQI {expected_iaqi})"
    )


tools = []
variables = [
    Variable(
        "primary_pollutant",
        None,
        "Store the name of the day's primary pollutant as a string, exactly one of: "
        "PM2.5, PM10, SO2, NO2, CO, O3.",
    ),
    Variable(
        "primary_iaqi",
        None,
        "Store that pollutant's own sub-index as an int. Round the sub-index "
        "UP to a whole number, as clause 6.2 of the standard directs.",
    ),
]
validators = {"validate_primary_pollutant": validate_primary_pollutant}
