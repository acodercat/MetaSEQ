"""The same hourly record that floors the very-hot-day count puts a CEILING on
the hot-night count — 61 against the Observatory's 54
(statistical_characterization).

BASELINE, and the mirror of `hk_very_hot_days_hourly_floor`. That case
shows an hourly-mean record undercounting a statistic built on daily
maxima: each row is the hourly mean of ten-minute readings, a mean cannot
exceed the readings in it, so the highest hourly value is at or below the
true peak, and 33 record very hot days stand against the Observatory's 53.
A hot night is built on the daily MINIMUM — the Observatory counts a day
whose minimum at headquarters is 28.0 degrees or higher — and the same
averaging runs the other way: the lowest hourly mean is at or ABOVE the
true trough, and a day whose real minimum dipped to 27.8 for twenty
minutes can show a lowest hourly value of 28.1. The record therefore
OVERCOUNTS hot nights. The nesting is exact: against HKO's published 2025
daily extremes the record's daily minimum is at or above the published one
on 365 of 365 days (hour-ending days; see the mirror for the reading that
breaks it). For 2025 the Observatory published 54
(third highest on record; 13 in September and 7 in October, both monthly
records); the record's headquarters station gives 61, with 9 in October.

A third statistic closes the argument. A cold day is a minimum at or BELOW
12.0: the same upward bias in the hourly minimum now hides qualifying days,
and the record gives 5 against the published 6 — a floor again. So the
direction of the bias is set by two things the analyst has to read off the
definition: whether the statistic uses the day's maximum or minimum, and
which way the inequality points. Max-and-above: floor. Min-and-above:
ceiling. Min-and-below: floor.

**The near-miss pools.** 32 days of 2025 have a lowest hourly value in
[28.0, 28.5) — the pool from which the seven record hot nights that the
Observatory did not count come. 4 days have a lowest hourly value in
(12.0, 12.5] — where the one missing cold day sits. (31 and 3 under the
own-day reading of the stamp; this is the one scored value in the pair the
day convention moves.)

**Other quantities, each with a number** (answers to different questions,
as in the mirror). The domain's TERRITORY FIGURES
convention — mean across the thirty-nine temperature stations, then the
threshold — gives 5 hot nights; requiring every station to stay at or above
28 gives 0. Reading "night" as the 18:00-06:00 window instead of the
Observatory's calendar day gives 78. A strict inequality gives 60. And the
path this case is built for is a reasoning error, not a computation: an
analyst who has just learned that hourly records undercount extremes, and
applies that to a statistic whose bias runs the other way — explaining 61
against 54 as the Observatory having missed nights, or as a data fault, or
by tightening the threshold until the record reproduces 54.

**Turn 1** asks the count and scores 61. **Turn 2** relays the desk with
the Observatory's 54 hot nights and 6 cold days and the fact that this time
the record has MORE; an earlier design scored the two near-miss pools' companions — the
[28.0, 28.5) days (32) and the record's cold-day count (5) — and the claims
carry the reasoning: 61 is a ceiling and 5 is a floor for the same reason;
publish 54 and 6; do not move either threshold.

**Pins, and where each one goes** (`case_design_standard.md` §3.1). As in
the mirror, turn 1's variable names the Observatory's definition by
reference and nothing else; that a hot night is a headquarters daily
minimum, on a calendar day, is the exam. Turn 2's query states both
definitions in the desk's words. Days are the domain's hour-ending days; a
day's minimum is the lowest hourly value stored for it.

**Readings measured and excluded:**

    hot nights, territory-mean convention              5
    hot nights, every station at or above 28           0
    hot nights, 18:00-06:00 window                    78
    hot nights, strict > 28.0                         60
    near-miss band read as [28, 29)                   54
    near-miss band read as [27.5, 28)                 21
    cold days, strict < 12.0                           5 (same)
    cold days read from the near-miss band             3

All counts are exact.

**Overlap, stated.** `hk_very_hot_days_hourly_floor` is the mirror and the
two are meant to be read together: one record, one mechanism, opposite
signs. Neither is complete without the other, because a model can pass the
first by learning "hourly undercounts" and fail this one by applying it.

All ground truths are recomputed from the database at validation time. The
published 54 and 6 are not scored — they are not in the record — and appear
only in the desk's note.

**Turn 2 rebuilt 2026-09-01 on the surface rule.** The desk's objection
stays; the near-miss and cold-day computations are no longer dictated. PV
scores which figures to publish (the Observatory's), what our hot-night count
is (a ceiling) and what our cold-day count is (a floor).
`_reconciliation_verdicts()` re-derives both directions from the record —
the hourly hot-night count must not fall below the published 54, the
cold-day count must not exceed the published 6.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult
from domains.hk.db import read_frame

_STATION = "HK Observatory"
_HOT_NIGHT = 28.0
_HOT_NIGHT_NEAR_MISS_HIGH = 28.5
_COLD_DAY = 12.0


def _hko_daily_min() -> pd.Series:
    frame = read_frame(text("""
        select date(h.datetime - interval '1 hour') as day, min(h.temperature) as tmin
        from hourly_station_weather h
        join weather_station s on s.id = h.station_id
        where s.name_en = :station and h.temperature is not null
          and h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
        group by 1
    """), {"station": _STATION})
    return frame["tmin"]


def _figures() -> Dict[str, int]:
    tmin = _hko_daily_min()
    return {
        "hot_nights_2025": int((tmin >= _HOT_NIGHT).sum()),
        "hot_night_near_miss_days_2025": int(
            ((tmin >= _HOT_NIGHT) & (tmin < _HOT_NIGHT_NEAR_MISS_HIGH)).sum()),
        "cold_days_2025": int((tmin <= _COLD_DAY).sum()),
    }


def _is_int(val) -> bool:
    """`bool` is an `int` subclass; True must not pass as a count of one."""
    return isinstance(val, int) and not isinstance(val, bool)


def _check_counts(got: Dict[str, object]) -> ValidatorResult:
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    for name, val in got.items():
        if not _is_int(val):
            return ValidatorResult(False, f"{name}={val!r} is not an integer")
    gt = _figures()
    errors = [f"{name}={val}, expected {gt[name]}" for name, val in got.items() if val != gt[name]]
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{name}={gt[name]}" for name in got))


def validate_count(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check_counts({"hot_nights_2025": runtime.retrieve("hot_nights_2025"),
                          "cold_days_2025": runtime.retrieve("cold_days_2025")})



_DAY = ("A day is the calendar day the stored hours BELONG to on the "
        "domain's hour-ending convention")


def _normalise_verdict(value) -> str:
    return str(value).strip().lower().replace("_", " ").replace("\u2019", "'")


def _verdict_check(got, gt) -> ValidatorResult:
    """Score enumerated conclusions, booleans and exact strings or integers."""
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    errors = []
    for name, val in got.items():
        expected = gt[name]
        if isinstance(expected, bool):
            ok = (isinstance(val, bool) and val == expected) or (
                isinstance(val, str) and _normalise_verdict(val) in {str(expected).lower(),
                                                                      "yes" if expected else "no"})
        elif isinstance(expected, int):
            ok = isinstance(val, int) and not isinstance(val, bool) and val == expected
        else:
            ok = _normalise_verdict(val) == _normalise_verdict(expected)
        if not ok:
            errors.append(f"{name}={val!r}, expected {expected!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


def _reconciliation_verdicts() -> Dict[str, object]:
    figures = _figures()
    if figures["hot_nights_2025"] < 54 or figures["cold_days_2025"] > 6:
        raise RuntimeError("the record contradicts the ceiling/floor argument")
    return {"figure_to_publish": "the Observatory's figures",
            "our_hot_night_count_is": "a ceiling",
            "our_cold_day_count_is": "a floor"}


def validate_reconciliation(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "figure_to_publish": runtime.retrieve("figure_to_publish"),
        "our_hot_night_count_is": runtime.retrieve("our_hot_night_count_is"),
        "our_cold_day_count_is": runtime.retrieve("our_cold_day_count_is"),
    }
    return _verdict_check(got, _reconciliation_verdicts())

tools = []
variables = [
    Variable(
        "hot_nights_2025",
        None,
        "Store the number of hot nights in 2025, as the Hong Kong Observatory "
        "defines a hot night, that this record's hourly temperatures support, "
        "as an integer. " + _DAY + " and its minimum is the lowest hourly "
        "value stored for it.",
    ),
    Variable("cold_days_2025", None,
             "Store the number of cold days supported by the Observatory's hourly "
             "temperatures in 2025, using HKO's cold-day definition, as an integer. "
             + _DAY + "; its minimum is the lowest hourly value stored for it."),
    Variable("figure_to_publish", None,
             "Store whose counts the desk should publish, as one of exactly these "
             "strings: 'the Observatory's figures', 'our figures', 'neither'."),
    Variable("our_hot_night_count_is", None,
             "Store what this record's hot-night count is, relative to the true "
             "statistic, as one of exactly these strings: 'a floor', 'a "
             "ceiling', 'an estimate'."),
    Variable("our_cold_day_count_is", None,
             "Store the same for this record's cold-day count, as one of exactly "
             "these strings: 'a floor', 'a ceiling', 'an estimate'."),
]


def validate_evidence_and_conclusion(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "hot_nights_2025": runtime.retrieve("hot_nights_2025"),
        "cold_days_2025": runtime.retrieve("cold_days_2025"),
        "figure_to_publish": runtime.retrieve("figure_to_publish"),
        "our_hot_night_count_is": runtime.retrieve("our_hot_night_count_is"),
        "our_cold_day_count_is": runtime.retrieve("our_cold_day_count_is"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, f"{missing} not set", variables_not_set=True)
    result_0 = validate_count(response, runtime, turn)
    if not result_0.success:
        return result_0
    result_1 = validate_reconciliation(response, runtime, turn)
    if not result_1.success:
        return result_1
    return ValidatorResult(True, result_0.message + "; " + result_1.message)

validators = {
    "validate_count": validate_count,
    "validate_reconciliation": validate_reconciliation,
    "validate_evidence_and_conclusion": validate_evidence_and_conclusion,
}
