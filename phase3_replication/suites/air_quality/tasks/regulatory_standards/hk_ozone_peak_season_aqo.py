"""The 2025 ozone peak season sits across the calendar year, and four
stations' verdicts under the new objective depend on letting it
(regulatory_standards).

BASELINE, hard. Hong Kong's Air Quality Objectives were revised on 11 April
2025 and, following the WHO 2021 guidelines, gained an ozone PEAK SEASON
objective: 100 ug/m3 for the average of the daily maximum 8-hour ozone over
the six consecutive months with the highest such average, no exceedances
allowed. EPD's 2025 annual report tabulates it per station (Table C2): for
each month M of 2025 the six-month average from M-2 to M+3, and the peak
season value as the highest of the twelve. Five stations are above 100 in
the published table — Tap Mun 120, Tseung Kwan O 111, Tai Po 107, Sha Tin
104, Southern 103 — Eastern sits at exactly 100 and North at 99.

**The condition in the record.** None of those peak seasons lies inside
2025. Tap Mun's is December 2024 to May 2025 (120.64, against 120.43 for
November-April — the report prints both as 120); Tai Po's, Sha Tin's and
Eastern's are the same six months; Southern's is November 2024 to April
2025; and Tseung Kwan O's is October 2025 to March 2026. Hong Kong's ozone
is highest from late autumn through winter into spring and lowest in the
summer monsoon months, so the six-month window that captures the high
months straddles the calendar year: the assessment labelled 2025 reaches two
months into 2024 and three into 2026 — which is why the report on 2025
could only be finalised in July 2026, and why this record, running to
August 2026, can reproduce it. Reproduction, with stamps read as the end
of their hour (see `hk_ozone_aqo_day_boundary`), at least six of eight
hours per window, and the daily maxima of all days in the six months
averaged together:

    published monthly values matched exactly    156 of 216
    peak-season values within 1 ug/m3           18 of 18
    stations above 100                          record 6, report 5

The sixth is Eastern: the record gives 100.41, which the report prints as
100. Whether Eastern complied is therefore a question about the report's
rounding, which the record does not settle, and the claims ask for that to
be said rather than decided.

**What confining the window to the calendar year does.** Taking only the
six-month windows that lie inside 2025 — January-June through
July-December — Tap Mun reads 111.3 instead of 120.6, and Tseung Kwan O,
Tai Po, Sha Tin and Southern fall to 99.8, 99.6, 95.3 and 94.1: four
stations that exceed the objective are reported as meeting it, and the
territory's non-compliance shrinks from five stations to one. That reading
is foreclosed on the variables — the construction is EPD's, and an
objective is assessed the way its authority assesses it — which is why the
case is a baseline; the CC claims carry the point.

**Turn 1** scores Tap Mun's peak-season value (120.6, one decimal) and the
first and last months of its peak season (2024-12, 2025-05). **Turn 2**
scores how many stations' unrounded record values are above 100 (6) and
their names, and asks what the desk should know before printing them as
the non-compliant stations. Gate B round 18 ruled that a count scored as
"above the objective" cannot include Eastern while a claim requires
Eastern's verdict to be withheld: the scored quantity is now the record
count, named as such on the variable and in the query, and the objective
verdict on Eastern is what the claim asks to be left open.

**Pins, and where each one goes** (`case_design_standard.md` §3.1). The
construction — daily maximum 8-hour ozone with stamps read as hour-ends
and six of eight hours required; the twelve six-month windows labelled by
the month two in from their start; the average over every day in the
window; the highest of the twelve — is on the turn-1 variables in full.
Pooling the days rather than averaging six monthly means is pinned because
the two differ (120.64 against 120.53 at Tap Mun) at the reported
precision. Nothing on the surface says the peak season crosses the year;
that is what an agent has to find by computing it.

**Readings measured and excluded** (Tap Mun value / stations above 100):

    windows confined to calendar 2025                111.3 / 1
    stamps read as belonging to their own day        121.3 / 6
    mean of six monthly means                        120.5 / 6
    the November-April window (the report's tie)     120.4

Months and counts are exact; the value uses `reports_as` at one decimal.

**Overlap, stated.** `hk_aqo_revision_allowance` is about the 2025
revision's PM2.5 limit and allowance; `hk_ozone_aqo_day_boundary` about
which day the midnight stamp belongs to, on the 8-hour objective. This
case uses the latter's reading and is about a different objective and a
different window.

All ground truths are recomputed from the database at validation time. The
published figures are not scored and appear only in the docstring and the
desk's note.
"""

from typing import Dict, List

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, is_finite_number, reports_as
from domains.hk.db import read_frame

_FOCUS = "Tap Mun"
_OBJECTIVE = 100.0
_MIN_HOURS = 6


def _hourly() -> pd.DataFrame:
    return read_frame(text("""
        select h.datetime, s.name_en as station, h.o3
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where h.o3 is not null
          and h.datetime >= '2024-10-01' and h.datetime < '2026-04-02'
    """))


def _daily_max(series: pd.Series) -> pd.Series:
    """Daily maximum 8-hour mean, every stamp read as the end of its hour."""
    rolling = series.asfreq("h").rolling(8, min_periods=_MIN_HOURS).mean()
    ending = pd.Series(rolling.values, index=rolling.index - pd.Timedelta(hours=1))
    daily = ending.groupby(ending.index.date).max().dropna()
    daily.index = pd.to_datetime(daily.index)
    return daily


def _windows(daily: pd.Series) -> pd.Series:
    """The twelve six-month averages labelled by the months of 2025: the
    window for month M runs from M-2 to M+3, every day pooled."""
    months = daily.index.to_period("M")
    out = {}
    for label in pd.period_range("2025-01", "2025-12", freq="M"):
        out[label] = daily[(months >= label - 2) & (months <= label + 3)].mean()
    return pd.Series(out)


def _figures() -> Dict[str, object]:
    frame = _hourly()
    peaks: Dict[str, float] = {}
    focus_windows = None
    for station, group in frame.groupby("station"):
        windows = _windows(_daily_max(group.set_index("datetime")["o3"]))
        peaks[station] = float(windows.max())
        if station == _FOCUS:
            focus_windows = windows
    label = focus_windows.idxmax()
    above: List[str] = sorted(s for s, v in peaks.items() if v > _OBJECTIVE)
    return {
        "tap_mun_peak_season_o3_2025": peaks[_FOCUS],
        "tap_mun_peak_season_first_month": str(label - 2),
        "tap_mun_peak_season_last_month": str(label + 3),
        "stations_above_100_on_record_2025": len(above),
        "stations_above_100_on_record_names": above,
    }


def _is_int(val) -> bool:
    """`bool` is an `int` subclass; True must not pass as a count of one."""
    return isinstance(val, int) and not isinstance(val, bool)


def validate_peak_season(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "tap_mun_peak_season_o3_2025": runtime.retrieve("tap_mun_peak_season_o3_2025"),
        "tap_mun_peak_season_first_month": runtime.retrieve("tap_mun_peak_season_first_month"),
        "tap_mun_peak_season_last_month": runtime.retrieve("tap_mun_peak_season_last_month"),
    }
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    value = got["tap_mun_peak_season_o3_2025"]
    if not is_finite_number(value):
        errors.append(f"tap_mun_peak_season_o3_2025={value!r} is not a number")
    elif not reports_as(value, gt["tap_mun_peak_season_o3_2025"], decimals=1):
        errors.append(f"tap_mun_peak_season_o3_2025={value}, "
                      f"expected ~{gt['tap_mun_peak_season_o3_2025']:.1f}")
    for key in ("tap_mun_peak_season_first_month", "tap_mun_peak_season_last_month"):
        if str(got[key])[:7] != gt[key]:
            errors.append(f"{key}={got[key]!r}, expected {gt[key]}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True, f"correct: {gt['tap_mun_peak_season_o3_2025']:.1f} over "
              f"{gt['tap_mun_peak_season_first_month']} to {gt['tap_mun_peak_season_last_month']}")


def validate_stations_above(response: str, runtime, turn: Turn) -> ValidatorResult:
    count = runtime.retrieve("stations_above_100_on_record_2025")
    names = runtime.retrieve("stations_above_100_on_record_names")
    missing = [n for n, v in (("stations_above_100_on_record_2025", count),
                              ("stations_above_100_on_record_names", names)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    if not _is_int(count):
        return ValidatorResult(
            False, f"stations_above_100_on_record_2025={count!r} is not an integer")
    if not isinstance(names, (list, tuple)) or not all(isinstance(n, str) for n in names):
        return ValidatorResult(
            False, f"stations_above_100_on_record_names={names!r} is not a list of strings")
    gt = _figures()
    errors = []
    if count != gt["stations_above_100_on_record_2025"]:
        errors.append(f"stations_above_100_on_record_2025={count}, "
                      f"expected {gt['stations_above_100_on_record_2025']}")
    if sorted(n.strip().lower() for n in names) != [n.lower() for n in gt["stations_above_100_on_record_names"]]:
        errors.append(f"stations_above_100_on_record_names={list(names)!r}, "
                      f"expected {gt['stations_above_100_on_record_names']}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True, f"correct: {count} stations ({', '.join(gt['stations_above_100_on_record_names'])})")


tools = []
variables = [
    Variable(
        "tap_mun_peak_season_o3_2025",
        None,
        "Store Tap Mun's 2025 peak-season ozone value as a float in ug/m3, "
        "1 decimal place, built the way the objective is assessed: the daily "
        "maximum 8-hour mean ozone (8-hour means of the hourly values with at "
        "least six of the eight hours present; every timestamp is the end of "
        "its hour, per the domain's convention, so the value stamped 00:00 is "
        "the last hour of the previous day; a day's maximum over the windows "
        "ending in it); "
        "then, for each month M of 2025, the average of the daily maxima of "
        "every day from month M-2 to month M+3 inclusive; the peak-season "
        "value is the highest of those twelve six-month averages.",
    ),
    Variable(
        "tap_mun_peak_season_first_month",
        None,
        "Store the first month of the six-month window that gives Tap Mun's "
        "peak-season value, as a string in YYYY-MM form.",
    ),
    Variable(
        "tap_mun_peak_season_last_month",
        None,
        "Store the last month of that window, as a string in YYYY-MM form.",
    ),
    Variable(
        "stations_above_100_on_record_2025",
        None,
        "Store how many of the eighteen stations have a 2025 peak-season "
        "ozone value, built the same way and left unrounded, strictly above "
        "100.0 ug/m3, as an integer. This is the record count, not a "
        "compliance verdict.",
    ),
    Variable(
        "stations_above_100_on_record_names",
        None,
        "Store the names of those stations, as a list of strings, spelt as the "
        "station records spell them.",
    ),
]
validators = {
    "validate_peak_season": validate_peak_season,
    "validate_stations_above": validate_stations_above,
}
