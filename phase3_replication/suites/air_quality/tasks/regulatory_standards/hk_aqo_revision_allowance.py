"""Neither half of the 2025 AQO revision bites alone (regulatory_standards).

BASELINE. The interesting error — treating a standard as its concentration limit
and changing only that — is real and produces a specific wrong answer, but the
query has to supply both regimes' numbers for the answer to be unique, and a
reading the query forecloses is not a naive path (Round 9). So the counts are
scored and the insight sits in the CC claims.

Hong Kong replaced its Air Quality Objectives on **11 April 2025**. For PM2.5
over 24 hours the limit went from 50 to 37.5 ug/m3 — a 25 % tightening — while
the exceedances permitted in a calendar year went from **35 to 18**. Screened
over 2025 across all eighteen stations:

    previous objective   50 ug/m3, 35 allowed    0 stations fail
    current objective    37.5 ug/m3, 18 allowed  4 stations fail
                                                 Central 32 days, Tuen Mun 31,
                                                 Causeway Bay 28, Yuen Long 19

**The two halves only bite together, and an earlier version of this docstring
said the allowance did it alone.** That conclusion came from running half the
experiment. Applying the new limit with the OLD allowance — 37.5 with 35 —
leaves 0 stations failing, which is true and was measured; from it this case
concluded that halving the permitted exceedances is what turns the failing stations
non-compliant. Gate B round 3 ran the other cell. Applying the OLD limit with the
new allowance — 50 with 18 — ALSO leaves 0 stations failing, because a 50 ug/m3
limit generates at most seven exceedance days at any station in 2025 and no
allowance of 18 can bind on seven days. The full factorial:

    50 / 35    0 stations      37.5 / 35    0 stations
    50 / 18    0 stations      37.5 / 18    4 stations

So the lower limit is what creates enough exceedance days for the lower
allowance to have anything to bind on, and the lower allowance is what turns
those days into a breach. Crediting either alone is wrong, and the case used to
require the wrong one of the two in its CC claim.

The values were verified against the published standard rather than recalled,
which matters because this corpus has shipped a recalled figure before:

    2014 AQO (from 2014-01-01)   PM2.5 24h  75, 9 allowed
    2022 AQO (from 2022-01-01)   PM2.5 24h  50, 35 allowed
    2025 AQO (from 2025-04-11)   PM2.5 24h  37.5, 18 allowed

Source: EPD, `epd.gov.hk/epd/english/environmentinhk/air/air_quality_objectives/`.
The 2022 revision is worth noting for the same reason: it tightened the limit
from 75 to 50 while RELAXING the allowance from 9 to 35, the opposite trade to
2025's.

**This is a counterfactual screen, not a compliance finding, and the reason is
a date.** The revision took effect on 11 April 2025, inside the year screened,
so neither objective governed the whole of 2025 and applying either to all of it
is a hypothetical. The third turn asks about it directly. An analyst who knows the
effective date could instead judge each day against whatever was in force that
day, and that reading reaches neither 0 nor 4. Counting exceedances of the
applicable limit and comparing the total against 18 gives **two** stations,
Central 24 days and Tuen Mun 19; against a day-weighted blend of the two
allowances, 22.2, **one**, Central; and against 35, **none**. Which allowance to pair a segmented count with is itself
undetermined, which is a second reason the query forecloses the reading rather
than leaving the agent to pick.

Measured degrees of freedom:

- **The valid-day rule is load-bearing, and it is pinned as a standard rather
  than for definiteness.** Re-measured 2026-09-03 after Gate B round 21: no
  minimum, 12 and the stated 18 all return 0 and **4**, while 20 and 24 return
  0 and **3** — Yuen Long, the fourth station at 19 days, loses a day to a
  stricter completeness rule and falls back inside the allowance. An earlier
  version of this list said the answer does not move and gave it as 3; both
  were written before the 2026-08-30 hour-ending re-measurement and neither was
  re-checked against it. 18 of 24 is the 75 % data-capture convention
  air-quality reporting uses, which is what lets it sit on the variables.
- **The rounding of the daily mean matters, and is pinned on the variable.**
  Measured 2026-09-06 after a Gate A review raised it: comparing the daily mean
  as computed gives 4 failing stations, and rounding it to one decimal place —
  which is how EPD publishes daily means — gives **3**. The station that moves
  is Yuen Long, whose 8 January mean is 37.5125: unrounded it clears 37.5, at
  one decimal it becomes exactly 37.5 and does not, and the station drops from
  19 exceedance days to 18, inside the allowance. Three station-days of the year
  sit in [37.45, 37.55) and this is the only one that matters. Rounding to whole
  numbers leaves the answer at 4. An analyst who rounded to the published
  precision was reaching 3 with no surface saying otherwise, against a count
  scored at tolerance 0. A verification pass on 2026-09-07 caught the repair
  half-made: the sentence had gone onto `stations_failing_previous`, the 50
  ug/m3 objective, where rounding changes nothing because no station comes near
  it. The flip lives entirely in `stations_failing_current`, which said only
  "the same 18-of-24 daily completeness rule" — "the same" pointing at
  completeness, not at rounding. Both variables now carry the full sentence.
- **Station scope does matter and is pinned.** All eighteen stations gives 4;
  restricting to the fifteen general ones gives 2, since two of the four
  failures — Central and Causeway Bay — are roadside sites.
- **Ignoring the allowance entirely** — treating any exceedance as failure —
  gives 18 stations under BOTH objectives, so it destroys the comparison rather
  than distorting it. Every station has at least one day over 37.5 and at least
  one over 50.

Relationship to `hk_aqo_station_level_compliance`, which must be stated because
both are AQO cases in this category: that one is about the assessment UNIT — an
ambient standard is met station by station, not on a territory average — and
uses NO2 over six years. This one holds the unit fixed and varies the standard,
using PM2.5 in one year. The shared machinery is a limit plus an allowance; the
lessons do not overlap.

Tolerances. **Neither turn carries one.** Both answers are counts of stations,
integers matched exactly by `compare_numeric(tolerance=0)`, and §4 requires an
exact match to be declared: no near-miss exists because there is nothing between
0 and 1, or between 4 and 5. Turn 1's answer of 0 is not degenerate — reaching
it requires applying the allowance, and the careless reading that skips the
allowance returns 18, not 0.

Both ground truths are recomputed here from the database.

Figures re-measured 2026-08-30 under the hour-ending timestamp convention;
Yuen Long moved from 17 to 19 exceedance days and became the fourth failing
station. EPD's 2025 report lists Yuen Long as compliant (19th-highest daily
mean 37.1): the record's PM2.5 is the real-time feed (see
`hk_pm25_annual_aqo_provisional_record`), and a station within a few tenths
of the limit can sit on either side of it.

**Gate B round 21 (2026-09-03) found this docstring still describing the
result as "0 and 3" in four places** — the completeness sweep, the station
scope, the tolerance discussion and the segmented-count figure — against its
own 2026-08-30 update note recording the fourth station. All four are
re-measured above. The validator and the claims were already on 4; only the
prose was stale, which is P7 exactly.

**Split 2026-09-02 (query length):** turn 1 no longer says "treat it as a
screen rather than a compliance determination: no objective governed all of
2025" — that sentence was the answer to the `screen_not_verdict` claim,
handed over. A third turn now relays the desk's wish to print a breach and
scores the verdict; the claim moved there.
"""

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number
from domains.hk.db import read_frame

_YEAR = ("2025-01-01", "2026-01-01")
_MIN_HOURS = 18
_PREVIOUS = (50.0, 35)
_CURRENT = (37.5, 18)


def _daily() -> pd.DataFrame:
    """One row per station-day with at least 18 valid hourly PM2.5 readings."""
    rows = read_frame(text("""
        select q.station_id, date_trunc('day', q.datetime - interval '1 hour') as day,
               avg(q.pm2_5) as pm2_5, count(q.pm2_5) as hours
        from hourly_station_air_quality q
        where q.datetime > :lo and q.datetime <= :hi
        group by 1, 2
    """), {"lo": _YEAR[0], "hi": _YEAR[1]})
    return rows[rows["hours"] >= _MIN_HOURS]


def _failing(limit: float, allowance: int) -> int:
    daily = _daily()
    exceedances = daily[daily["pm2_5"] > limit].groupby("station_id").size()
    return int((exceedances > allowance).sum())


def validate_previous_objective(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("stations_failing_previous")
    if val is None:
        return ValidatorResult(
            False, "stations_failing_previous not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"stations_failing_previous={val!r} is not a number"
        )

    gt = _failing(*_PREVIOUS)
    if compare_numeric(val, gt, tolerance=0):
        return ValidatorResult(True, f"correct: {val} stations")
    return ValidatorResult(False, f"stations_failing_previous={val}, expected {gt}")


def validate_current_objective(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("stations_failing_current")
    if val is None:
        return ValidatorResult(
            False, "stations_failing_current not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"stations_failing_current={val!r} is not a number"
        )

    gt = _failing(*_CURRENT)
    if compare_numeric(val, gt, tolerance=0):
        return ValidatorResult(True, f"correct: {val} stations")
    return ValidatorResult(False, f"stations_failing_current={val}, expected {gt}")




def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_printable(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("printable_as_a_breach")
    if val is None:
        return ValidatorResult(False, "printable_as_a_breach not set", variables_not_set=True)
    # A judgement, not a computation: no single objective governed all of
    # 2025, so a whole-year count against either is a screen, not a breach.
    if not _bool_ok(val, False):
        return ValidatorResult(False, f"printable_as_a_breach={val!r}, expected False")
    return ValidatorResult(True, "correct: a screen, not a breach")


tools = []
variables = [
    Variable(
        "stations_failing_previous",
        None,
        "Store how many stations would not have met the earlier objective over "
        "2025, as an integer between 0 and 18. Judge each of the eighteen "
        "stations separately; count a day at a station only when at least 18 of "
        "its 24 hourly readings are present, and compare the day's mean against "
        "the limit as computed, without rounding it to a reporting precision "
        "first.",
    ),
    Variable(
        "stations_failing_current",
        None,
        "Store how many would not have met the later objective over the same "
        "year, as an integer between 0 and 18. Judge each of the eighteen "
        "stations separately; count a day at a station only when at least 18 of "
        "its 24 hourly readings are present, and compare the day's mean against "
        "the limit as computed, without rounding it to a reporting precision "
        "first.",
    ),
]
variables += [
    Variable("printable_as_a_breach", None,
             "Store True if the desk can print the later count as stations "
             "that breached the objective in 2025, else False."),
]


def validate_evidence_and_conclusion(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "stations_failing_current": runtime.retrieve("stations_failing_current"),
        "printable_as_a_breach": runtime.retrieve("printable_as_a_breach"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, f"{missing} not set", variables_not_set=True)
    result_0 = validate_current_objective(response, runtime, turn)
    if not result_0.success:
        return result_0
    result_1 = validate_printable(response, runtime, turn)
    if not result_1.success:
        return result_1
    return ValidatorResult(True, result_0.message + "; " + result_1.message)

validators = {
    "validate_previous_objective": validate_previous_objective,
    "validate_current_objective": validate_current_objective,
    "validate_printable": validate_printable,
    "validate_evidence_and_conclusion": validate_evidence_and_conclusion,
}
