"""Beijing 2023 attainment days — the headline policy metric (regulatory_standards).

"优良天数" (days rated excellent-or-good, daily AQI <= 100) is the number by
which Chinese cities' air quality is publicly judged. Computing it correctly
requires the full HJ 633-2012 daily-AQI machinery: daily-average concentrations
per pollutant (24-h means; for ozone the daily maximum 8-hour average on the
HJ 663-2013 window basis; CO already in mg/m3 in this file), per-pollutant IAQI
by piecewise-linear interpolation, the day's AQI as the maximum sub-index — and
only then the count of days at or below 100.

The record hands the agent an hourly `AQI` column, which is a different,
real-time product. Reading the yearly count off it is the trap, and it misses in
both directions:

- correct path: 271 days.
- wrong path: counting days whose MEAN hourly AQI <= 100 gives 317 — the
  diurnal averaging hides exceedance afternoons.
- wrong path: counting days whose EVERY hour (equivalently the day's max hourly
  AQI) is <= 100 gives 250 — a single bad hour disqualifies a day the daily
  basis rates as attainment.

Every daily figure sits on HJ 663-2013's natural day, which A.1 stamps 1:00 to
24:00. The record's hour h is the hour ending at h:00, so label 0 is the
previous date's 24:00 — the shared MDA8 helper already owns the 00:00 window to
the previous date, and CNEMC's own `O3_8h` restarts at label 1 — and a date's
24-hour means take its labels 1-23 and label 0 of the next date; 31 December
takes its 24:00 from 1 January 2024. Grouping each date's labels 0-23 instead
puts the 24-hour means and the ozone sub-index on different days and counts
269. The schema says only "hour of day", so the variable states what the
labels mean.

External reference point, NOT a validation: Beijing officially reported 271
attainment days for 2023, the count computed here. The label-date grouping's
269 was two short of it. Of 2022-2024, 2023 is the only year the two day
definitions separate (2022 reads 286 both ways, as published); in 2024 both
read 292 against an official 290, a gap neither reading closes and plausibly
the difference between real-time and audited data. Agreement in one
year is not evidence that this pipeline reproduces the official method, and
nothing here should be read as corroboration.

Robustness, and the one reading it does NOT cover. The count is unchanged
whether the day-completeness rule is none or >=18 hours (the query still pins
"every day"), and whether the sub-indices are left fractional or rounded up as
clause 6.2 prescribes — 271 either way, and conventional 四舍五入 also gives
271. Half-up was NOT measured until a live run returned it on the label-date
day: `deepseek-v4-pro-0813` rounded half-up, read 270 against 269 there, and
failed against a tolerance of 0. Half-up is what an analyst who has not read 6.2
does, so the direction sits on the variable, where `beijing_aqi_co_unit` and
`beijing_aqi_aggregation_order` had already put it after an external audit; it
stays there although the natural day makes it indifferent here. The ozone
sub-index uses the shared HJ 663 implementation, whose window basis is itself
load-bearing: taking each day's maximum over all 24 windows of the supplied
running-mean column instead gives 270.

Tolerance 0, and the reason is not fussiness. Nothing measured moves this
count: it is unchanged by the day-completeness rule and by AQI rounding, so
there is no variance for a band to absorb, and the nearest wrong path, the
supplied running-mean column, sits one day out. The label-date day sits two
out, the hourly-AQI paths 46 and 21.

The band was first removed because a band of 2 reached 271, Beijing's published
figure, and an agent recalling the headline would have passed without
computing anything. On the natural day the key IS 271, so this PV check can no
longer tell a recalled headline from a computed one. No tolerance can fix that;
the evidence the answer was computed has to come from the stored code and the
CC channel, and a pass here should be read with that in mind.

Both ground truths are recomputed here from the CSV.
"""

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number
from tasks import Turn
from domains.beijing.mda8 import frame_to_mda8

_CITY, _YEAR = "北京", 2023

_IAQI = [0, 50, 100, 150, 200, 300, 400, 500]
_BP = {
    "PM2.5": [0, 35, 75, 115, 150, 250, 350, 500],
    "PM10": [0, 50, 150, 250, 350, 420, 500, 600],
    "SO2": [0, 50, 150, 475, 800, 1600, 2100, 2620],
    "NO2": [0, 40, 80, 180, 280, 565, 750, 940],
    "CO": [0, 2, 4, 14, 24, 36, 48, 60],       # mg/m3
    "O3": [0, 100, 160, 215, 265, 800],        # daily max 8-h mean
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


def _counts() -> dict:
    cities = pd.read_csv(DATA_DIR / "region_cities.csv")
    # HJ 663-2013 A.1: a natural day runs 1:00-24:00, and label h is the hour
    # ending at h:00, so label 0 is the previous date's 24:00. Selecting and
    # grouping on that day puts the 24-hour means on the same day the ozone
    # windows are owned by, and gives 31 December its 24:00 window.
    ts = pd.to_datetime(cities[["year", "month", "day", "hour"]])
    natural = (ts - pd.Timedelta(hours=1)).dt.normalize()
    keep = (cities["city"] == _CITY) & (natural.dt.year == _YEAR)
    sel = cities[keep]
    by_day = sel.groupby([natural[keep].dt.month, natural[keep].dt.day])

    # Ozone sub-index on the HJ 663 window basis, keyed by (month, day).
    mda8 = frame_to_mda8(sel)
    mda8 = mda8[mda8.index.year == _YEAR]
    o3_by_day = {(t.month, t.day): v for t, v in mda8.items()}

    def attainment(o3_source) -> int:
        n = 0
        for key, day in by_day:
            conc = {
                "PM2.5": day["PM2.5"].mean(), "PM10": day["PM10"].mean(),
                "SO2": day["SO2"].mean(), "NO2": day["NO2"].mean(),
                "CO": day["CO_mg_m3"].mean(), "O3": o3_source(key, day),
            }
            subs = [_iaqi(conc[p], _BP[p]) for p in _BP]
            subs = [s for s in subs if np.isfinite(s)]
            if subs and max(subs) <= 100:
                n += 1
        return n

    return {
        "correct": attainment(lambda k, d: o3_by_day.get(k, np.nan)),
    }


def validate_attainment_days(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("attainment_days")
    if val is None:
        return ValidatorResult(
            False, "attainment_days not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"attainment_days={val!r} is not a number"
        )

    gt = _counts()
    if compare_numeric(val, gt["correct"], tolerance=0):
        return ValidatorResult(
            True, f"correct: {val} ~ {gt['correct']} days"
        )
    return ValidatorResult(
        False, f"attainment_days={val}, expected ~{gt['correct']}"
    )


tools = []
variables = [
    Variable(
        "attainment_days",
        None,
        "Store the number of 2023 days whose daily AQI is at or below 100, "
        "as an integer. Round each sub-index UP to a whole number, as clause "
        "6.2 of HJ 633-2012 requires. "
        "A day's maximum 8-hour ozone is the largest of the "
        "8-hour running means whose window ENDS between 08:00 and 24:00 "
        "of that day. The record labels hours by their ending time, so "
        "hour 0 is the midnight that closes the previous date; a day's "
        "24-hour means take its hours 1-23 and hour 0 of the following "
        "date, the same day its ozone windows belong to.",
    ),
]
validators = {"validate_attainment_days": validate_attainment_days}
