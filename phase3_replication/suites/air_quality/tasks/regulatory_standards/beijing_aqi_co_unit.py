"""Beijing AQI — the CO unit trap (regulatory_standards).

Diagnostic trap. China's AQI (HJ 633-2012) tabulates the CO sub-index against
breakpoints expressed in **mg/m3**, whereas this dataset publishes CO in
**ug/m3** (stated in the domain schema, "CO is ug/m3 throughout"). An agent
that feeds the raw ug/m3 CO values straight into the mg/m3 breakpoint table
inflates the CO sub-index to its ceiling (IAQI 500) on essentially every day,
because typical CO of ~1000-2500 ug/m3 read as "mg/m3" is far above the top
breakpoint of 60. Since the daily AQI is the maximum of the pollutant
sub-indices, the whole month then reads AQI = 500.

- correct path: convert CO ug/m3 -> mg/m3 (divide by 1000) before the CO
  sub-index. January is PM2.5-driven, so the monthly mean of daily AQI is
  72.0645, which the variable's one decimal reports as 72.1.
- wrong path: skip the conversion -> mean daily AQI = 500.

The query names HJ 633-2012 and describes the ozone basis directly ("the maximum
daily 8-hour running mean") rather than citing HJ 663-2013, so the candidate-
window set is formally open. Measured, it does not matter: January is
PM2.5-driven and admitting all 24 trailing windows moves the monthly mean by
0.0000. P1 holds on the data, not on the wording.

The 24-hour means are taken over HJ 663-2013's natural day, which A.1 stamps
1:00 to 24:00. The record's hour h is the hour ending at h:00, so label 0 is the
previous date's 24:00 — the reading the shared MDA8 helper already applies to
the ozone windows — and a January day is its labels 1-23 plus label 0 of the
next date, which takes 31 January's last hour from 1 February. Grouping each
date's labels 0-23 instead reads 72.0000, outside the band by 0.0145 and 72.0
at one decimal, so the agent cannot be left to guess; the domain prompt's
TIMESTAMPS block states what the labels mean.

The query pins the day-completeness convention ("every day of the month, whatever
number of hours it reports") because it is not free.

**The rounding DIRECTION lived only here, where the agent cannot see it, and
an external audit caught that.** Clause 6.2 rounds up; conventional
四舍五入 to the nearest integer is what an analyst who has not read the clause
would do, and it reads **71.5806** against the pinned 72.0645 — ten bands out,
and close to the unrounded 71.64 the case already probes.
Rounding down reads 71.0645, twenty bands. The variable now states the
direction: the case is about the CO unit conversion, and a second hidden
discriminator would make a failure ambiguous — the same reasoning
`beijing_aqi_aggregation_order` applied to its own copy of clause 6.2.

Tolerance +/-0.05 AQI points. There is no rounding for a band to cover: HJ 633
clause 6.2 rounds every sub-index UP to a whole number, so the daily AQI values
are integers and only their mean carries decimals. The +/-2.0 band two earlier
revisions carried existed to absorb an interpolation "rounding" the standard
actually prescribes, and it accepted the unrounded 71.47 that those revisions
also documented as the answer. The correct figure is 72.0645 (72.1 as
reported); the excluded readings are the unrounded 71.64, the label-date day
72.00, the fully-reported-days convention (78.92) and the unconverted CO path
(500). The band is unchanged by the move to the natural day: 72.1 sits 0.0355
inside it.

Both ground truths are recomputed here from the CSV, so the validator never
trusts a hardcoded number.
"""

import math
from typing import List

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn
from domains.beijing.mda8 import frame_to_mda8

# HJ 633-2012 individual air quality index (IAQI) breakpoints.
# PM/SO2/NO2/O3 in ug/m3; CO in mg/m3.
_IAQI = [0, 50, 100, 150, 200, 300, 400, 500]
_BP = {
    "PM2.5": [0, 35, 75, 115, 150, 250, 350, 500],
    "PM10": [0, 50, 150, 250, 350, 420, 500, 600],
    "SO2": [0, 50, 150, 475, 800, 1600, 2100, 2620],
    "NO2": [0, 40, 80, 180, 280, 565, 750, 940],
    "CO": [0, 2, 4, 14, 24, 36, 48, 60],
    "O3": [0, 100, 160, 215, 265, 800],
}


def _iaqi(conc: float, bp: List[float]) -> float:
    """Sub-index, rounded UP per HJ 633-2012 clause 6.2.

    "环境空气质量指数及空气质量分指数的计算结果应全部进位取整数，不保留小数" —
    every index result is a whole number, rounded up. Two revisions of this case
    scored the raw interpolation instead and read 71.47.
    """
    levels = _IAQI[: len(bp)]
    if not np.isfinite(conc):
        return np.nan
    if conc <= bp[0]:
        return 0.0
    if conc >= bp[-1]:
        return float(levels[-1])
    for i in range(1, len(bp)):
        if conc <= bp[i]:
            lo, hi, il, ih = bp[i - 1], bp[i], levels[i - 1], levels[i]
            return float(math.ceil((ih - il) / (hi - lo) * (conc - lo) + il))
    return float(levels[-1])


def _daily_aqi(day_df: pd.DataFrame, o3_mda8: float, *, convert_co: bool) -> float:
    co = day_df["CO"].mean()
    conc = {
        "PM2.5": day_df["PM2.5"].mean(),
        "PM10": day_df["PM10"].mean(),
        "SO2": day_df["SO2"].mean(),
        "NO2": day_df["NO2"].mean(),
        "CO": (co / 1000.0) if convert_co else co,
        "O3": o3_mda8,
    }
    subs = [_iaqi(conc[p], _BP[p]) for p in _BP]
    subs = [s for s in subs if np.isfinite(s)]
    return max(subs) if subs else np.nan


def _mean_daily_aqi(convert_co: bool) -> float:
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    station_year = df[(df["station"] == "Dongsi") & (df["year"] == 2021)]
    # Ozone on the HJ 663 window basis; the whole year feeds the rolling window
    # so 31 January's 24:00 window, labelled 1 February 00:00, is formed.
    mda8 = frame_to_mda8(station_year)
    # HJ 663-2013 A.1: a natural day runs 1:00-24:00, and label 0 is the
    # previous date's 24:00, so each 24-hour mean takes labels 1-23 of the date
    # and label 0 of the next — the same day the ozone windows are owned by.
    ts = pd.to_datetime(station_year[["year", "month", "day", "hour"]])
    natural = (ts - pd.Timedelta(hours=1)).dt.normalize()
    sub = station_year[(natural.dt.year == 2021) & (natural.dt.month == 1)]
    daily = [
        _daily_aqi(g, mda8.get(date), convert_co=convert_co)
        for date, g in sub.groupby(natural[sub.index])
    ]
    return float(np.nanmean(daily))


def validate_mean_daily_aqi(
    response: str, runtime, turn: Turn
) -> ValidatorResult:
    val = runtime.retrieve("mean_daily_aqi")
    if val is None:
        return ValidatorResult(
            False, "mean_daily_aqi not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(False, f"mean_daily_aqi={val!r} is not a number")

    correct = _mean_daily_aqi(convert_co=True)

    if reports_as(val, correct, decimals=1):
        return ValidatorResult(True, f"correct: {val} ~ {correct:.1f}")
    return ValidatorResult(
        False, f"mean_daily_aqi={val}, expected ~{correct:.1f}"
    )


tools = []
variables = [
    Variable(
        "mean_daily_aqi",
        None,
        "Store the arithmetic mean over January 2021 of the daily AQI at "
        "Dongsi (HJ 633-2012), as a float rounded to 1 decimal place. "
        "Round every sub-index UP to a whole number, as clause 6.2 of the "
        "standard requires, so each day's AQI is an integer and only "
        "their mean carries decimals.",
    ),
]
validators = {"validate_mean_daily_aqi": validate_mean_daily_aqi}
