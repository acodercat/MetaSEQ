"""Summarise a month's AQHI for a health briefing — the mean is the trap
(exposure_assessment).

BASELINE with an unnamed concept at its centre. The AQHI is an ordinal
health-risk index, capped at 10+; the arithmetic mean of its hourly values is
not a risk level and understates exactly the hours a health briefing exists
to surface. Both models STATE this unprompted when asked in plain text
(`docs/v2_measurements.md` §4: "report the daily maximum", "hours per risk
category") — and the HK domain prompt itself taught the naive path in its
example code (`agg({'aqhi': 'mean'})`) until 2026-08-24, when that example
was corrected to `max`. This case asks whether a model DOES what it says,
now that nothing in the prompt pushes either way.

Tuen Mun, April 2025, measured:

    hourly values reported            719
    arithmetic mean                   4.02   "moderate", the naive summary
    median                            3
    maximum                           10
    hours at 7 or above               85

A month whose mean says "about 4" spent 85 hours — three and a half days —
at High risk or worse and touched the top of the scale. A briefing built on
the mean would have said nothing was happening.

Why BASELINE and not trap: the scored variables (hours at or above 7, and
the worst hour) are pinned quantities a mean-minded model still computes
correctly once asked, so there is no numeric naive path to a wrong stored
value — the naive path lives in the PROSE summary, and the claim scores it.
That split is deliberate and is the same PV/CC division
`hk_roadside_index_compression` uses for the same concept on another
question; that case leaves the method open across station classes, this one
asks for the summary itself, which is the purer form.

Why hours >= 7: verified against the record's own `aqhi_level` enum rather
than recalled — 7 is the HIGH band (its only value; 8-10 are VERY HIGH and
the stored 10 with SERIOUS is EPD's 10+), so "7 or above" is exactly "High
or worse", the first step past MODERATE and the line a briefing acts on.
The threshold is stated on the variable, not left to the agent.

Station and month chosen by measurement, not story: over 2025, Tuen Mun in
April is the station-month with the most hours at 7+ (85) among those that
also reach 10, so the mean-vs-episode gap is at its widest.

Pins, each measured.

- HOURS AT OR ABOVE 7, exact. The index is an integer, so the only
  alternative reading — strictly above 7, which is the same as at-or-above
  8 — reads 68, seventeen away, and is a probe.
- THE WORST HOUR is 10 exactly (the record stores EPD's "10+" as 10).
- APRIL 2025 half-open per TIME WINDOWS; 719 reported hours (one short).
  The station's name is unique in `air_quality_station`.

Tolerance 0 on both integers.

Both ground truths are recomputed here from the database.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult
from domains.hk.db import read_frame

_STATION = "Tuen Mun"
_SPAN = ("2025-04-01", "2025-05-01")
_HIGH = 7


def _hours() -> pd.Series:
    frame = read_frame(text("""
        select h.aqhi
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where s.name_en = :station
          and h.datetime > :lo and h.datetime <= :hi
          and h.aqhi is not null
    """), {"station": _STATION, "lo": _SPAN[0], "hi": _SPAN[1]})
    return frame["aqhi"]


def _figures() -> Dict[str, int]:
    hours = _hours()
    return {
        "hours_high_or_worse": int((hours >= _HIGH).sum()),
        "worst_hour_index": int(hours.max()),
    }


def validate_briefing_figures(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = ("hours_high_or_worse", "worst_hour_index")
    got = {name: runtime.retrieve(name) for name in names}
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)
    # `bool` is an `int` subclass; True must not pass as 1.
    for name, val in got.items():
        if not isinstance(val, int) or isinstance(val, bool):
            return ValidatorResult(False, f"{name}={val!r} is not an integer")

    gt = _figures()
    wrong = [f"{name}={val}, expected {gt[name]}"
             for name, val in got.items() if val != gt[name]]
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {gt['hours_high_or_worse']} hours at 7 or above, "
              f"worst hour {gt['worst_hour_index']}")


tools = []
variables = [
    Variable(
        "hours_high_or_worse",
        None,
        "Store how many of the month's hours carried an index of 7 or above "
        "— the High risk band or worse — as an integer.",
    ),
    Variable(
        "worst_hour_index",
        None,
        "Store the worst hourly index value of the month as an integer.",
    ),
]
validators = {
    "validate_briefing_figures": validate_briefing_figures,
}
