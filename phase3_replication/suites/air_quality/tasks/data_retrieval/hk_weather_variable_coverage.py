"""What the weather network measures is not what it reports (data_retrieval).

BASELINE, easy, and Hong Kong's only difficulty anchor: one table, three
counts, no join, no aggregation choice, and no domain knowledge needed to
produce them. `hk_cloud_enhancement_extreme` was built alongside it as a
second anchor and Gate B round 7 reclassified that one `medium`, because its
scored interpretation needs radiative reasoning even though its retrieval does
not.

The question is worth asking because the author hit it while building
`hk_visibility_extinction_aggregation` and it decided that case's design. Hong
Kong's hourly weather record carries 51 stations in 2025, but the variables are
not carried uniformly across them:

    stations present in the hourly record        51
    reporting temperature                        39
    reporting wind speed and gust                30 each
    reporting humidity                           28
    reporting pressure                           13
    reporting visibility                          4
    reporting visibility AND humidity              2

The last line is the one that matters. A humidity-and-visibility study reads
like a network-scale question and is in fact a two-site question — Chek Lap Kok
and Waglan Island — because the other two visibility sites carry no humidity at
all. An analyst who joins the two variables without checking gets a result and
no warning that it rests on two locations.

**Convention sweep — two axes, four combinations, all computed.**
Neither moves the
answer. The window endpoint changes nothing because no hourly record falls at
2026-01-01 00:00. What counts as "reports the variable" changes nothing either:
requiring at least one reading in the year and requiring at least a thousand
give the same 39, 28, 4, 13, 30, 30 and 2, because a station in this record
either carries an instrument all year or carries none of it. That invariance is
measured rather than assumed, which is what a case with no live convention owes
a reviewer in place of an empty sweep section.

**Tolerances.** All three scored quantities are counts of stations, matched
exactly; no tolerance applies and none could, since a station either appears in
the record or does not and either reports a variable or does not. The near
misses that exist are the other coverage figures above — 39, 28, 13 and 30 —
and each is a different question correctly answered.

**What this case does not do.** It does not audit the station table, compare
coordinates, or say anything about which sites are well placed; the corpus has
a known defect in the weather stations' recorded positions and nothing here
depends on them. It counts what the hourly record contains.

Ground truth is recomputed from the database at validation time.

**Split 2026-09-02 (query length):** the earlier single turn asked for the
figures and the judgement together; the judgement now has its own turn,
scored as a verdict, with the claims moved to it. The figures' turn keeps
only the deliverable.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult
from domains.hk.db import read_frame

_SPAN = ("2025-01-01", "2026-01-01")


def _per_station() -> pd.DataFrame:
    """One row per weather station, with how many readings it filed of each."""
    return read_frame(text("""
        select h.station_id,
               count(h.visibility) as visibility,
               count(h.humidity)   as humidity
        from hourly_station_weather h
        where h.datetime > :lo and h.datetime <= :hi
        group by 1
    """), {"lo": _SPAN[0], "hi": _SPAN[1]})


def _figures() -> Dict[str, int]:
    """The three scored counts."""
    stations = _per_station()
    reports_visibility = stations["visibility"] > 0
    return {
        "weather_stations_total": int(len(stations)),
        "stations_reporting_visibility": int(reports_visibility.sum()),
        "stations_reporting_visibility_and_humidity":
            int((reports_visibility & (stations["humidity"] > 0)).sum()),
    }


def validate_coverage_counts(response: str, runtime, turn: Turn) -> ValidatorResult:
    total = runtime.retrieve("weather_stations_total")
    visibility = runtime.retrieve("stations_reporting_visibility")
    both = runtime.retrieve("stations_reporting_visibility_and_humidity")

    got = {"weather_stations_total": total,
           "stations_reporting_visibility": visibility,
           "stations_reporting_visibility_and_humidity": both}
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)
    # Counts of stations, matched exactly. `bool` is excluded because it is an
    # `int` subclass and True would otherwise pass as 1.
    for name, val in got.items():
        if not isinstance(val, int) or isinstance(val, bool):
            return ValidatorResult(False, f"{name}={val!r} is not an integer")

    gt = _figures()
    wrong = [f"{name}={val}, expected {gt[name]}"
             for name, val in got.items() if val != gt[name]]
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {total} stations, {visibility} with visibility, "
              f"{both} with both")








tools = []
variables = [
    Variable(
        "weather_stations_total",
        None,
        "Store how many distinct weather stations appear in the hourly weather "
        "record during 2025, as an integer.",
    ),
    Variable(
        "stations_reporting_visibility",
        None,
        "Store how many of those stations file at least one visibility reading "
        "during the year, as an integer.",
    ),
    Variable(
        "stations_reporting_visibility_and_humidity",
        None,
        "Store how many file at least one reading of each of visibility and "
        "humidity during the year, as an integer.",
    ),
]
validators = {
    "validate_coverage_counts": validate_coverage_counts,
}
variables += [
]
