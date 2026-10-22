"""Whether Southern met the ozone 8-hour AQO in 2025 turns on which day the
hour stamped 00:00 belongs to — and the record's stamps are hour-ending
(regulatory_standards).

BASELINE, hard. EPD's annual report ("Air Quality in Hong Kong 2025", Table
C1) lists Southern as compliant with the ozone 8-hour objective — 160 ug/m3,
nine exceedances allowed — with a tenth-highest daily maximum 8-hour average
of 160, in whole micrograms. On the domain's TIMESTAMPS convention — every air-quality
stamp is the END of its hour, so the row stamped 00:00 is the last hour of
the previous day — the record gives nine exceedance days and a tenth-highest
of 159.5: compliant, as published. Read the other way, with the 00:00 stamp
belonging to the day it falls in, the record gives TEN and 162.4:
non-compliant. The two readings disagree on one window.

**The window.** Ozone at Southern on 21 March 2025 ran 170 / 170 / 176 / 172
/ 166 / 149 / 146 / 151 from 17:00 to the stamp 00:00 of 22 March; the
eight-hour mean is 162.51. Hour-ending, that window is the last of 21 March
— already an exceedance day — and Southern stays at nine. Own-day, it is
22 March's daily maximum and a tenth exceedance day.

**How the convention was established.** This case is where the domain's
timestamp convention came from. Reading every stamp as the end of its hour
and taking daily maxima over the windows that end in each day, with at
least six of the eight hours present, reproduces EPD's 2025 table for all
eighteen stations — every compliance verdict, and the tenth-highest value
to within 1 ug/m3 at seventeen of them — and, for 2024, 125 of the 140
published top-ten values and 12 of 14 exceedance counts at the fourteen
stations whose 2024 table the author transcribed. Under the own-day
reading the same figures are 71 of 140 and 5 of 14. Gate B round 18
recomputed the full 2024 network: hour-ending 158 of 180 values exact,
179 of 180 within 1 ug/m3, 16 of 18 counts; own-day 102, 133 and 8. The
two 2024 counts that still miss by one (Southern 10 against 9, Tuen Mun 16
against 15) are unexplained. No other reading tested
(windows labelled by their first hour, windows confined within the calendar
day, a strict 8-of-8 validity rule) comes close. The same reading reproduces
the report's NO2 24-hour table at all eighteen stations, including Mong
Kok's "exceeded" verdict (ten days above 120 hour-ending, nine own-day) —
the same flip, on a different pollutant, the other way round. Until Gate B
round 18 the prompt said the opposite for the stamp 00:00; the evidence
here is what changed it.

**Turn 1** asks whether Southern complied and scores the convention's count
(9) and tenth-highest (159.5). **Turn 2**, rebuilt 2026-09-02 on the surface
rule (`docs/query_surface_audit.md`), relays a desk note — an earlier
analysis had ten, and the department's table says nine — and asks where the
tenth came from and whether Southern complied. The earlier turn told the
agent to recount with the midnight stamp read as the new day and to find the
window that moved; the query carried the diagnosis. The rebuilt turn scores
the verdict (complied), the source of the extra day ('a timestamp
convention'), and the day the tenth was counted on (2025-03-22 — the only
day the own-day reading adds); the claims carry the judgement: one window
across midnight, not a data error; the stamps are hour-ending and the
verdict is nine; no other rule may be used to close the gap.

**The fix that is not one.** Requiring all eight hours present also gives
nine — by dropping a different day, 21 January, whose exceeding window has
six of its hours missing (11:00 to 16:00) — and an analyst who reaches for
it has "matched" the report by accident: on the same rule seven stations
(Causeway Bay, Kwai Chung, Kwun Tong, Sham Shui Po, Tsuen Wan, Tuen Mun,
Tung Chung) no longer reproduce their published tenth-highest values. The
claims fail a response that closes the gap that way.

**Pins, and where each one goes** (`case_design_standard.md` §3.1). The
8-hour construction — running mean of the hourly values, at least six of
eight present, daily maximum over the windows that end in the day — is on
the turn-1 variables; which day a window ends in is the prompt's
convention. Turn 2's variables state the own-day reading explicitly. The
objective's limit and allowance are in the desk's note in turn 2 and on the
turn-1 variable.

**Readings measured and excluded** (turn-1 count / tenth-highest):

    own-day stamps, six of eight           10 / 162.4
    eight of eight required                 9 / 162.4
    any hour present                       10 / 162.4

Counts and dates are exact. The tenth-highest is asked to ONE decimal:
under the own-day reading its unrounded value is 162.425 — a tie at the
SECOND decimal, and not at the first (the one-decimal boundary is 162.45),
so 162.4 is unambiguous at the asked precision and the guide's tie guard
is not exercised here. The day 2025-01-21, which the eight-of-eight rule
drops instead, is the wrong-path date for turn 2's third variable.

**Overlap, stated.** `hk_aqo_station_level_compliance` is about assessing a
standard station by station rather than on a territory mean (NO2 hourly);
`hk_aqo_revision_allowance` about the 2025 revision's two halves (PM2.5
daily). Neither touches the 8-hour objective or the day boundary.

All ground truths are recomputed from the database at validation time. The
published figures are not scored and appear only in the desk's note.

**The desk's note says "about 160", not "160".** On the convention the record's
tenth-highest is 159.49, which is 159 in whole micrograms, not the 160 the
table prints — the 1 ug/m3 agreement described above, not an exact match.
Quoted as a bare "160" the note put a figure in the agent's hands that no
reading of this record reproduces, and the one thing turn 2 must not do is
reward hunting for a rule that closes a gap; the gap that matters is the
count. "About 160" is what the published value says about this record and
no more. The scored values are unchanged: 159.5 at turn 1, and nothing at
turn 2 depends on the published figure.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, is_finite_number, reports_as
from domains.hk.db import read_frame

_STATION = "Southern"
_LIMIT = 160.0
_MIN_HOURS = 6
_ALLOWED = 9
SOURCE_CONVENTION = "a timestamp convention"


def _hourly() -> pd.Series:
    frame = read_frame(text("""
        select h.datetime, h.o3
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where s.name_en = :station and h.o3 is not null
          and h.datetime >= '2024-12-31' and h.datetime < '2026-01-02'
        order by h.datetime
    """), {"station": _STATION})
    return frame.set_index("datetime")["o3"].asfreq("h")


def _daily_max(rolling: pd.Series, shift_hours: int) -> pd.Series:
    """Daily maximum over windows, each labelled by its end stamp minus
    `shift_hours`: 0 keeps the domain convention (a stamp belongs to the day
    it is in), 1 reads every stamp as the end of its hour."""
    labelled = pd.Series(rolling.values, index=rolling.index - pd.Timedelta(hours=shift_hours))
    year = labelled[(labelled.index >= "2025-01-01") & (labelled.index < "2026-01-01")]
    return year.groupby(year.index.date).max().dropna()


def _figures() -> Dict[str, object]:
    series = _hourly()
    rolling = series.rolling(8, min_periods=_MIN_HOURS).mean()
    convention = _daily_max(rolling, 1)   # hour-ending stamps: the domain convention
    own_day = _daily_max(rolling, 0)      # the stamp 00:00 read as its own day
    exceed_conv = set(convention[convention > _LIMIT].index)
    exceed_own = set(own_day[own_day > _LIMIT].index)
    # The day the own-day reading counts and the convention does not: its
    # daily maximum is the window ending at the stamp 00:00.
    boundary_day = sorted(exceed_own - exceed_conv)[0]
    return {
        "exceedance_days_2025": int(len(exceed_conv)),
        "tenth_highest_daily_max_8h_2025": float(convention.sort_values(ascending=False).iloc[9]),
        "southern_complied": bool(len(exceed_conv) <= _ALLOWED),
        "source_of_the_extra_day": SOURCE_CONVENTION,
        "day_the_tenth_was_counted_on": f"{pd.Timestamp(boundary_day):%Y-%m-%d}",
    }


def _is_int(val) -> bool:
    """`bool` is an `int` subclass; True must not pass as a count of one."""
    return isinstance(val, int) and not isinstance(val, bool)


def validate_convention_count(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "exceedance_days_2025": runtime.retrieve("exceedance_days_2025"),
        "tenth_highest_daily_max_8h_2025": runtime.retrieve("tenth_highest_daily_max_8h_2025"),
    }
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    if not _is_int(got["exceedance_days_2025"]):
        return ValidatorResult(
            False, f"exceedance_days_2025={got['exceedance_days_2025']!r} is not an integer")
    gt = _figures()
    errors = []
    if got["exceedance_days_2025"] != gt["exceedance_days_2025"]:
        errors.append(f"exceedance_days_2025={got['exceedance_days_2025']}, "
                      f"expected {gt['exceedance_days_2025']}")
    tenth = got["tenth_highest_daily_max_8h_2025"]
    if not is_finite_number(tenth):
        errors.append(f"tenth_highest_daily_max_8h_2025={tenth!r} is not a number")
    elif not reports_as(tenth, gt["tenth_highest_daily_max_8h_2025"], decimals=1):
        errors.append(f"tenth_highest_daily_max_8h_2025={tenth}, "
                      f"expected ~{gt['tenth_highest_daily_max_8h_2025']:.1f}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True, f"correct: {gt['exceedance_days_2025']} days, tenth highest "
              f"{gt['tenth_highest_daily_max_8h_2025']:.1f}")


def _normalise(value) -> str:
    return str(value).strip().lower()


def validate_reconciliation(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "southern_complied": runtime.retrieve("southern_complied"),
        "source_of_the_extra_day": runtime.retrieve("source_of_the_extra_day"),
        "day_the_tenth_was_counted_on": runtime.retrieve("day_the_tenth_was_counted_on"),
    }
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    complied = got["southern_complied"]
    if not ((isinstance(complied, bool) and complied == gt["southern_complied"]) or
            (isinstance(complied, str) and _normalise(complied) in
             {str(gt["southern_complied"]).lower(), "yes" if gt["southern_complied"] else "no"})):
        errors.append(f"southern_complied={complied!r}, expected {gt['southern_complied']}")
    if _normalise(got["source_of_the_extra_day"]) != _normalise(gt["source_of_the_extra_day"]):
        errors.append(f"source_of_the_extra_day={got['source_of_the_extra_day']!r}, "
                      f"expected {gt['source_of_the_extra_day']!r}")
    if str(got["day_the_tenth_was_counted_on"]).strip()[:10] != gt["day_the_tenth_was_counted_on"]:
        errors.append(f"day_the_tenth_was_counted_on={got['day_the_tenth_was_counted_on']!r}, "
                      f"expected {gt['day_the_tenth_was_counted_on']}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]!r}" for n in got))


tools = []
variables = [
    Variable(
        "exceedance_days_2025",
        None,
        "Store the number of days of 2025 on which the Southern station's "
        "daily maximum 8-hour ozone exceeded 160 ug/m3, as an integer. The "
        "8-hour value at a stamp is the mean of the hourly ozone values at "
        "that stamp and the seven before it, computed only when at least six "
        "of the eight are present; a day's maximum is the highest such value "
        "among the windows ending in that calendar day, the day of a stamp "
        "being decided by the domain's timestamp convention.",
    ),
    Variable(
        "tenth_highest_daily_max_8h_2025",
        None,
        "Store the tenth-highest of those daily maximum 8-hour values at "
        "Southern in 2025, as a float in ug/m3, 1 decimal place.",
    ),
    Variable(
        "southern_complied",
        None,
        "Store True if Southern complied with the 8-hour ozone objective in "
        "2025, else False.",
    ),
    Variable(
        "source_of_the_extra_day",
        None,
        "Store where the earlier analysis's tenth exceedance day came from, as "
        "one of exactly these strings: 'a timestamp convention', 'a data "
        "fault', 'a different validity rule', 'different data'.",
    ),
    Variable(
        "day_the_tenth_was_counted_on",
        None,
        "Store the calendar day the earlier analysis counted as its tenth "
        "exceedance day, as a string 'YYYY-MM-DD'.",
    ),
]
validators = {
    "validate_convention_count": validate_convention_count,
    "validate_reconciliation": validate_reconciliation,
}
