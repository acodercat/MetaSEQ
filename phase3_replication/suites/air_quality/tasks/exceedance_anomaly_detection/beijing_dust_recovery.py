"""Beijing March 2021 dust recovery — first crossing is not the end
(exceedance_anomaly_detection).

Episode anatomy on the 15 March 2021 dust storm's aftermath. Network-mean hourly
PM10 peaked at ~7500 ug/m3 at 09:00 on the 15th, first dipped under the Grade II
daily-limit level of 150 during the following night — and then climbed back over
it, reaching 400 again on the 17th as fresh dust swept through and settled
material resuspended, before subsiding for good. The sustained recovery does not
begin for another 49 hours after that first dip, and 36 of those 49 hours are at
or above the level. (This sentence said 102 hours until a Gate A review on
2026-09-06; no span in the episode is 102 hours, and the case's own turn-2
paragraph and its claim both say 49 and "roughly two days".)

- Turn 1 (first_crossing_time): 2021-03-16 05:00, a transient overnight lull.
- Turn 2 (recovery_time): 2021-03-18 06:00, the first hour from which PM10 held
  below 150 for 24 consecutive hours. The nearest wrong path is turn 1's answer
  — reading the first threshold crossing as the episode's end, which misses the
  recovery by 49 hours.

The sustained-recovery reading is insensitive to every convention within reason:
thresholds 140/150/160 and windows of 18 to 48 hours all give 2021-03-18 06:00,
and strict-vs-inclusive comparison cannot matter (no hour equals 150.0 exactly).
Only a 12-hour window collapses onto the overnight lull. All 313 hours of the
window are present.

Both turns' answers are timestamps matched to the exact hour.

Both ground truths are recomputed here from the CSV.

**Turn 2 rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier query named the 24-consecutive-hours rule; the rebuilt one asks
when the storm was over. The variable says what "over" means — back below
the daily level and staying there for at least a full day — and the
validator matches 2021-03-18 06:00 exactly, which every reading of that
definition returns (thresholds 140 to 160, windows 18 to 48 hours). Gate B
round 21 swept the same grid independently and made the point that decided
it: with no construction disagreeing there is nothing for a tolerance to
absorb, so the six hours either side this validator used to allow were
twelve chances to be wrong about the hour the variable asks for. The
tolerance was removed 2026-09-03. The first crossing, 49 hours earlier, is what the claims are about.
The variable names the run's FIRST hour outright. "The hour from which the
episode can be said to have ended" also reads as the hour by which the end can
be DECLARED, once the full day below the level has been seen — 2021-03-19
05:00, the label of the run's 24th hour, a day after the key. An exact-hour
validator cannot absorb a reading a day away, so the text has to choose, and
the onset of the recovered state is the one the episode's anatomy is about.
Measured and worth knowing: after the recovery hour PM10 is back above 150 by
2021-03-20 10:00 (234.1 ug/m3) and above it again on ten of the month's
remaining days, so "stayed below for the rest of the month" is a different
question with a different answer; the definition on the variable is what keeps
the question posed. (This paragraph named 26 March as the next crossing until a
verification pass on 2026-09-07 recomputed it. The 48-hour invariance sweep is
unaffected — its window closes on 20 March at 06:00, four hours before.)
"""

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult
from tasks import Turn

_THRESHOLD = 150.0
_WINDOW_H = 24
_SPAN = ("2021-03-15", "2021-03-28")


def _series() -> pd.Series:
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    df["dt"] = pd.to_datetime(df[["year", "month", "day", "hour"]])
    sel = df[(df["dt"] >= _SPAN[0]) & (df["dt"] <= _SPAN[1])]
    return sel.groupby("dt")["PM10"].mean()


def _times() -> dict:
    hourly = _series()
    post = hourly[hourly.index > hourly.idxmax()]

    below = post < _THRESHOLD
    first_crossing = post.index[below.argmax()]

    def sustained(threshold: float, window: int):
        flags, index = (post < threshold).values, post.index
        for i in range(len(flags) - window):
            if flags[i:i + window].all():
                return index[i]
        return None

    # "Stayed below for at least a full day" is asserted invariant across the
    # readings an analyst could take of it: thresholds 140/150/160 and windows
    # of 18 to 48 hours all return 2021-03-18 06:00; only a half-day window
    # collapses onto the overnight lull, which is the wrong path.
    readings = {(t, w): sustained(t, w) for t in (140.0, 150.0, 160.0) for w in (18, 24, 36, 48)}
    if len(set(readings.values())) != 1:
        raise RuntimeError(f"the recovery hour is not invariant: {readings}")
    return {"first_crossing": first_crossing, "recovery": readings[(_THRESHOLD, _WINDOW_H)]}


def _parse(val) -> pd.Timestamp:
    return pd.to_datetime(val, errors="coerce")


def validate_first_crossing(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("first_crossing_time")
    if val is None:
        return ValidatorResult(
            False, "first_crossing_time not set", variables_not_set=True
        )
    got = _parse(val)
    if pd.isna(got):
        return ValidatorResult(False, f"first_crossing_time={val!r} is not a timestamp")

    gt = _times()
    if got == gt["first_crossing"]:
        return ValidatorResult(True, f"correct: {got}")
    return ValidatorResult(
        False, f"first_crossing_time={got}, expected {gt['first_crossing']}"
    )


def validate_recovery_time(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("recovery_time")
    if val is None:
        return ValidatorResult(
            False, "recovery_time not set", variables_not_set=True
        )
    got = _parse(val)
    if pd.isna(got):
        return ValidatorResult(False, f"recovery_time={val!r} is not a timestamp")

    gt = _times()
    # Matched exactly. Gate B round 21 swept every start hour for 12, 18, 24, 36
    # and 48 consecutive hours below 140, 150 and 160 ug/m3: every window of 18
    # hours or more begins the sustained run at exactly 06:00 on 18 March, and
    # only the 12-hour window collapses to the transient first crossing 49 hours
    # earlier. With no construction disagreeing there is nothing for a tolerance
    # to absorb, and the six hours either side this used to allow accepted
    # twelve timestamps that are false under the variable's own definition.
    if got == gt["recovery"]:
        return ValidatorResult(True, f"correct: {got}")
    return ValidatorResult(False, f"recovery_time={got}, expected {gt['recovery']}")


tools = []
variables = [
    Variable(
        "first_crossing_time",
        None,
        "Store the first hour after the peak with network-mean PM10 below the "
        "threshold, as a string 'YYYY-MM-DD HH:00' in Beijing local time.",
    ),
    Variable(
        "recovery_time",
        None,
        "Store the hour the episode can be said to have ended: the first hour "
        "of the run in which network-mean PM10 stays below the Grade II daily "
        "level of 150 ug/m3 for at least 24 consecutive hours (the run's first "
        "hour, not the hour by which those 24 hours have elapsed), as a string "
        "'YYYY-MM-DD HH:00' in Beijing local time.",
    ),
]
validators = {
    "validate_first_crossing": validate_first_crossing,
    "validate_recovery_time": validate_recovery_time,
}
