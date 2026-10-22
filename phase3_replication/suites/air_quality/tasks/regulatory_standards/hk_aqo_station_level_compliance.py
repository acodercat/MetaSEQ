"""An ambient standard is met station by station, not on average (regulatory_standards).

TRAP, and the naive path produces the cleanest possible wrong answer: **zero**.

Hong Kong's Air Quality Objective for nitrogen dioxide is 200 ug/m3 over an
hour, with 18 exceedances permitted in a calendar year. Forming a territory-wide
hourly mean across the eighteen stations and testing THAT against 200 gives
**0 exceeding hours in every one of the six years 2020-2025**, so Hong Kong
appears to have met the objective throughout. Testing each station against the
objective, which is how an ambient standard works, gives **five failing years**:
2020 through 2024, with 2025 the only clean year in the window. The record does
not reach back before 2020-01-09, so nothing here says 2025 is the first clean
year in Hong Kong's history — only that it is the first in these six.

The averaging is not a defensible alternative reading, which is what makes it a
trap rather than an ambiguity. No jurisdiction assesses an ambient standard on a
spatial mean — the point of a concentration limit is to protect the people at
the worst location, and averaging a roadside peak into fifteen general stations
destroys exactly the signal the limit exists to catch. The failing station-years
are all three roadside sites and only those: Causeway Bay, Central and Mong Kok.
General stations do exceed 200 occasionally — Kwai Chung reaches 8 hours in
2023, Tuen Mun 6 in 2020 — but none ever passes 18.

Turn 1 is the control turn §4 asks for: the highest single hourly reading in the
period, a pure maximum with no aggregation choice in it, so an agent that cannot
query the table at all is separable from one that queries it and then averages
the territory.

Measured degrees of freedom, none of which moves the answer:

- `> 200` against `>= 200`: both give 13 failing station-years and five failing
  years. No reading is hiding in the boundary.
- **Data capture.** Two station-years fall below 75 % hourly capture, North and
  Southern in 2020, and both record zero exceedances, so excluding incomplete
  station-years leaves all five failing years standing. The query therefore does
  not pin a capture rule — measured rather than assumed safe.
- **The margin at the 18 line, which is NOT uniformly comfortable.** Mong Kok
  2021 sits at 19, one exceedance above the allowance, but 2021 also carries
  Central at 36 and Causeway Bay at 33, so no individual station decides a
  failing year: the five failing years clear the line by 12, 18, 23, 25 and 38
  at their worst station. **The passing year is the thin one.** 2025 passes
  because Causeway Bay reached 13, five below the allowance of 18 and six
  below the 19 that would have broken it — so the answer being 5
  rather than 6 rests on a single station's margin of five hours in a year of
  8,459 valid ones. That is stated rather than smoothed over; a reviewer may
  reasonably judge it too thin, and if a later data revision moved that station
  the ground truth would move with it.

Tolerances. **Neither turn carries one**; both validators call
`compare_numeric` with `tolerance=0`, and §4 requires an exact match to be
declared rather than assumed, so: turn 2 is a count of years, an integer between
0 and 6, where no near-miss exists because there is nothing between 5 and 6.
Turn 1 is NOT an integer — it is a single stored reading, 555.2 at Causeway Bay
on 2021-01-14 09:00, and it is matched exactly because it is a value the record
holds rather than a quantity anyone estimates. The nearest other value in the
period is 360.3, so no band between them would change any verdict.

Both ground truths are recomputed here from the database.

**Split 2026-09-02 (query length):** turn 2 asked for the count of failing
years and then where the problem lies; the second half is a third turn that
relays the desk's "city-wide" line and scores whether every breach is a
roadside station's (it is: Causeway Bay, Central and Mong Kok, 2020-2024,
none in 2025), with the three claims moved to it.
"""

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number
from domains.hk.db import read_frame

_SPAN = ("2020-01-01", "2026-01-01")
_LIMIT = 200.0
_ALLOWED = 18


def _peak_no2_row() -> pd.Series:
    """The single highest hourly NO2 reading, with the station and the hour.

    Sorted rather than aggregated so the station and datetime come from the same
    row as the value, and the top two are fetched so the uniqueness the case
    depends on is checked rather than assumed: 555.2 at Causeway Bay on
    2021-01-14 09:00, against 360.3 next. A tie would make "where and when"
    unanswerable and must fail loudly rather than pick one.
    """
    top = read_frame(text("""
        select a.no2, btrim(s.name_en) as station, a.datetime
        from hourly_station_air_quality a
        join air_quality_station s on s.id = a.station_id
        where a.datetime > :lo and a.datetime <= :hi and a.no2 is not null
        order by a.no2 desc
        limit 2
    """), {"lo": _SPAN[0], "hi": _SPAN[1]})
    if len(top) == 2 and top["no2"].iloc[0] == top["no2"].iloc[1]:
        raise AssertionError(
            f"the peak NO2 reading is no longer unique: {top['no2'].iloc[0]} "
            f"occurs at least twice"
        )
    row = top.iloc[0]
    return pd.Series({"no2": float(row["no2"]), "station": str(row["station"]),
                      "datetime": pd.Timestamp(row["datetime"])})


def _peak_no2() -> float:
    return float(_peak_no2_row()["no2"])


def _failing() -> pd.DataFrame:
    """Station-years that used up more than the allowance, with the station's type."""
    per_station_year = read_frame(text("""
        select extract(year from h.datetime - interval '1 hour')::int as year,
               s.name_en as station, s.station_type::text as kind,
               count(*) filter (where h.no2 > :limit) as exceedances
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where h.datetime > :lo and h.datetime <= :hi
        group by 1, 2, 3
    """), {"lo": _SPAN[0], "hi": _SPAN[1], "limit": _LIMIT})
    return per_station_year[per_station_year["exceedances"] > _ALLOWED]


def _failing_years() -> int:
    """Years in which at least one station used up more than its allowance."""
    return int(_failing()["year"].nunique())


def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_problem_location(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("failures_are_roadside_only")
    if val is None:
        return ValidatorResult(False, "failures_are_roadside_only not set", variables_not_set=True)
    failing = _failing()
    expected = bool(len(failing) > 0 and (failing["kind"] == "ROADSIDE").all())
    if not _bool_ok(val, expected):
        return ValidatorResult(False, f"failures_are_roadside_only={val!r}, expected {expected}")
    return ValidatorResult(True, f"correct: every breach is a roadside station's "
                                 f"({', '.join(sorted(failing['station'].unique()))})")


def _normalise(name: str) -> str:
    """Station names compared on identity, not on typography."""
    return " ".join(str(name).split()).casefold()


def validate_peak_no2(response: str, runtime, turn: Turn) -> ValidatorResult:
    """All three parts of "what, where and when", in one validator.

    The turn asks for a value, a station and an hour, and for a while scored
    only the value — so an answer pairing the right 555.2 with the wrong station
    passed. A turn carries one validator, so the three are checked together and
    every failure is named rather than only the first.
    """
    gt = _peak_no2_row()
    value = runtime.retrieve("peak_no2")
    station = runtime.retrieve("peak_no2_station")
    stamp = runtime.retrieve("peak_no2_datetime")

    missing = [name for name, val in (("peak_no2", value),
                                      ("peak_no2_station", station),
                                      ("peak_no2_datetime", stamp)) if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)

    wrong = []
    # tolerance=0 rather than `==`: `compare_numeric` is what the standard
    # requires, and it also rejects bool, NaN and non-numeric input, which a
    # bare equality would silently accept for some values.
    if not is_finite_number(value):
        wrong.append(f"peak_no2={value!r} is not a number")
    elif not compare_numeric(value, gt["no2"], tolerance=0):
        wrong.append(f"peak_no2={value}, expected {gt['no2']}")

    if not isinstance(station, str) or not station.strip():
        wrong.append(f"peak_no2_station={station!r} is not a name")
    elif _normalise(station) != _normalise(gt["station"]):
        wrong.append(f"peak_no2_station={station!r}, expected {gt['station']!r}")

    # The text asks for a string; what is scored is the instant, not its
    # spelling, so any form pandas reads as the same hour is accepted.
    try:
        moment = pd.Timestamp(stamp)
        if moment.tz is not None:
            moment = moment.tz_localize(None)
    except (TypeError, ValueError):
        moment = None
    if moment is None or pd.isna(moment):
        wrong.append(f"peak_no2_datetime={stamp!r} is not a timestamp")
    elif moment != gt["datetime"]:
        wrong.append(f"peak_no2_datetime={stamp!r}, "
                     f"expected {gt['datetime']:%Y-%m-%d %H:%M}")

    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {gt['no2']} ug/m3 at {gt['station']}, "
              f"{gt['datetime']:%Y-%m-%d %H:%M}"
    )


def validate_failing_years(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("failing_years")
    if val is None:
        return ValidatorResult(False, "failing_years not set", variables_not_set=True)
    if not is_finite_number(val):
        return ValidatorResult(False, f"failing_years={val!r} is not a number")

    gt = _failing_years()
    if compare_numeric(val, gt, tolerance=0):
        return ValidatorResult(True, f"correct: {val} years")
    return ValidatorResult(False, f"failing_years={val}, expected {gt}")


tools = []
variables = [
    Variable(
        "peak_no2",
        None,
        "Store the highest single hourly nitrogen dioxide reading recorded at "
        "any station between 2020 and 2025, as a float in ug/m3, exactly as the "
        "record holds it.",
    ),
    Variable(
        "peak_no2_station",
        None,
        "Store the name of the station that recorded it, as a string, spelled as "
        "the station register spells it.",
    ),
    Variable(
        "peak_no2_datetime",
        None,
        "Store the hour it was recorded, as a string 'YYYY-MM-DD HH:MM:SS' in "
        "the same local time the record uses.",
    ),
    Variable(
        "failing_years",
        None,
        "Store how many of the six calendar years 2020 through 2025 did not meet "
        "the objective, as an integer between 0 and 6.",
    ),
]
validators = {
    "validate_peak_no2": validate_peak_no2,
    "validate_failing_years": validate_failing_years,
    "validate_problem_location": validate_problem_location,
}
variables += [
    Variable("failures_are_roadside_only", None,
             "Store True if every station-year that breached the objective's "
             "allowance belongs to a roadside station, else False."),
]
