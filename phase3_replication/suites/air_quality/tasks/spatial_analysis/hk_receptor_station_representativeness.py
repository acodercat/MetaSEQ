"""A roadside station represents a kerb, not the district around it (spatial_analysis).

BASELINE, and it was a TRAP until Gate B round 2 ruled that it could not be one.
Both assignments are now scored:

    nearest station of any kind          41.49 ug/m3   `school_no2_nearest_station`
    nearest GENERAL station              35.60         `school_no2_nearest_general`
    difference                            5.88, 16.5 %

**Why the trap framing had to go, because the failure is instructive.** Turn 2
used to ask for one number, at "whichever station you take to describe its
surroundings" — wording that hands the choice to the analyst — while the
validator silently required the general-only answer. A live `deepseek-v4-flash`
run made the all-station choice, reported 41.49, explained the roadside
limitation correctly in prose, and was failed. Worse, turn 1 measures distance
to the nearest of all EIGHTEEN stations, so the case switched station sets
between its own turns without saying so. A reading the query invites is not a
naive path (Round 9); this was ambiguity with a scoring key attached. Scoring
both numbers keeps every bit of the content and removes the guess: what used to
be a hidden pass/fail is now the size of the gap, and it is measured rather than
asserted in a claim.

What the gap means is still the point, and the distances are what settle it.
**823 of the 3,867 schools, 21.3 %, have a roadside station as their nearest**,
and those schools sit a median of **1,541 m** from it, quartiles 1,030 and
2,131, out to 4,094. Exactly **one** school lies within 100 m and six within
200 m. So representing them by a kerbside instrument is not representing a
kerbside school; it is carrying a street-canyon measurement a kilometre and a
half into neighbourhoods that do not have one. Those 823 schools receive 67.10
where the nearest general station reads 39.45.

Hong Kong's own network design says the same: the register classifies stations
into two kinds, and the roadside three are reported separately from the fifteen
general ones because they are not intended to describe anything but the kerb.

**But that does not make the general figure "the right answer", and Gate B round
3 was right to reject the version of this case that said it did.** Scoring both
numbers removed the numeric ambiguity while leaving the CC claim demanding a
universal winner, and the data cannot supply one: it holds no school-road
distance, no traffic intensity, no street-canyon geometry. And the distances cut
both ways. Of the 823 schools that change assignment, the roadside station they
would take is a median 1,541 m off — but their nearest general station is a
median 2,699 m off, **another 940 m farther**. Preferring the general station is
not preferring the nearer instrument.

What settles it is the ESTIMAND, so the query now names one: district-background
nitrogen dioxide, the level typical of the neighbourhood rather than of any
particular kerb. For that quantity the general station is definitional by the
network's own design, and the question has one defensible answer without
pretending distance decided it. The CC claim asks for that reasoning and for the
price it carries — a more remote instrument — rather than for a bare verdict.

Turn 1 remains the control turn, and it is deliberately a question where all
eighteen stations are CORRECT: how far away is the nearest instrument. That is a
different question from which instrument describes a place, and separating them
still isolates a failure to do the spatial join from a failure to think about
representativeness.

Measured degrees of freedom:

- **The distance metric matters, and the HK domain prompt pins it.**
  Nearest-station
  assignment by planar degrees rather than distance over the Earth's surface
  picks a different station for 32 of the 3,867 schools and reads 35.53 — 12
  bands out. Every great-circle variant agrees: PostGIS on the spheroid gives
  35.6020 and haversine 35.6008, and the Earth radius does not enter a
  nearest-neighbour choice at all (6367, 6371 and 6378.137 km give the same
  number to four decimals).
- **Ties: none.** No school has two stations within a metre of each other's
  distance, so no tie-break rule is needed and none is stated.
- **Receptor set: unambiguous.** Every educational institution in the register
  is a POINT; there are no polygon ones to decide about.
- **Which statistic stands for a station had to be pinned, and was not at
  first.** The query originally asked for "a level from the monitoring record",
  which leaves mean and median equally available: assigning each school its
  station's six-year MEDIAN reads 31.19 against the mean's 35.60. The band
  excludes it, but excluding a defensible reading is a uniqueness failure
  wearing a tolerance, not a trap — the same defect Gate B found in
  `hk_inversion_species_response`. The domain prompt's STATION LEVELS convention
  names the mean. Aggregation
  ACROSS schools was already pinned and would have mattered less anyway: their
  median is 35.91 against the mean's 35.60.
- **The station mean's own time weighting is a second degree of freedom, found
  by Gate B round 2, and the same convention pins it.** "Mean level over that
  period" does not say whether the unit is the observed hour, the day or the
  year, and gaps make the three differ. Pooling every valid station-hour, which
  is what STATION LEVELS names, reads 35.601965 general-only and 41.485826
  all-station; collapsing to annual station means first reads 35.618392 and
  41.503188; collapsing to daily means first reads 35.624601 and 41.501916.
  Both alternatives round to 35.62 and 41.50 and both are outside the band, so
  this had to be said rather than tolerated.
- Turn 1's median is reported in kilometres to two decimals because the metric
  variants span 2.9 m — 1432.06 on the spheroid against 1434.99 by haversine at
  the equatorial radius — and all of them are 1.43 km.

Tolerances. `decimals=2` on all three, the repo's idiom for "must round to this
2-decimal number", deriving +/-0.006. On turn 2 it separates the two scored
assignments by 980 bands from each other, and excludes the planar-metric reading
by 12 bands and the two time-weighting variants by 2.7 and 3.8. On turn 1 it
covers the 2.9 m spread between metric variants at twice over.

All three ground truths are recomputed here from the database.

**Turn 2 trimmed 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`):
the query no longer says "twice" and no longer names the two assignments;
the two variables carry them as the two estimates the study can choose
between, and the question stays which estimand fits the district level.


**Gate A review 2026-09-06 removed a gloss that answered a claim.** Turn 2 asked
for "the DISTRICT-BACKGROUND level the schools sit in — the neighbourhood's
typical level rather than any particular kerb's", and the second half of that is
what the claim `roadside_sites_are_not_area_representative` is written to test.
The estimand still has a name; the reason a kerbside site does not describe a
district is the response's to supply.
"""

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

_SPAN = ("2020-01-01", "2026-01-01")
_RECEPTOR = "EDUCATIONAL_INSTITUTION"


def _median_distance_km() -> float:
    """Median distance from a school to the nearest station of any kind."""
    nearest = read_frame(text("""
        with receptor as (
            select id, geometry::geography as g from sensitive_area
            where category = :cat and geometry_type = 'POINT'
        ), station as (
            select id, coordinate::geography as g from air_quality_station
        )
        select min(st_distance(receptor.g, station.g)) as d
        from receptor cross join station
        group by receptor.id
    """), {"cat": _RECEPTOR})
    return float(nearest["d"].median() / 1000.0)


def _assigned_no2(general_only: bool) -> float:
    """Mean over schools of the nearest station's mean NO2.

    `general_only` selects between the two assignments the turn scores. The
    station mean pools every valid hourly reading in the window — `avg(no2)`
    over the rows — rather than collapsing to daily or annual means first, which
    the domain prompt pins because the three differ in the second decimal.
    """
    assigned = read_frame(text(f"""
        with receptor as (
            select id, geometry::geography as g from sensitive_area
            where category = :cat and geometry_type = 'POINT'
        ), station as (
            select s.id, s.coordinate::geography as g, m.no2
            from air_quality_station s
            join (
                select station_id, avg(no2) as no2
                from hourly_station_air_quality
                where datetime > :lo and datetime <= :hi
                group by station_id
            ) m on m.station_id = s.id
            {"where s.station_type = 'GENERAL'" if general_only else ""}
        )
        select (array_agg(station.no2 order by st_distance(receptor.g, station.g)))[1] as no2
        from receptor cross join station
        group by receptor.id
    """), {"cat": _RECEPTOR, "lo": _SPAN[0], "hi": _SPAN[1]})
    return float(assigned["no2"].mean())


def validate_median_station_distance_km(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("median_station_distance_km")
    if val is None:
        return ValidatorResult(
            False, "median_station_distance_km not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"median_station_distance_km={val!r} is not a number"
        )

    gt = _median_distance_km()
    if reports_as(val, gt, decimals=2):
        return ValidatorResult(True, f"correct: {val} ~ {gt:.2f} km")
    return ValidatorResult(
        False, f"median_station_distance_km={val}, expected ~{gt:.2f}"
    )


def validate_school_no2(response: str, runtime, turn: Turn) -> ValidatorResult:
    """Both assignments, scored together — the turn asks for both numbers."""
    # Retrieved by literal name, not through a loop over a table of names:
    # `tests/test_turn_stores.py` reads these calls statically to check that a
    # turn declares every variable its validator scores.
    any_station = runtime.retrieve("school_no2_nearest_station")
    general = runtime.retrieve("school_no2_nearest_general")

    missing = [name for name, val in (("school_no2_nearest_station", any_station),
                                      ("school_no2_nearest_general", general))
               if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)

    wrong = []
    for name, val, general_only in (
        ("school_no2_nearest_station", any_station, False),
        ("school_no2_nearest_general", general, True),
    ):
        if not is_finite_number(val):
            wrong.append(f"{name}={val!r} is not a number")
            continue
        gt = _assigned_no2(general_only)
        if not reports_as(val, gt, decimals=2):
            wrong.append(f"{name}={val}, expected ~{gt:.2f}")

    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {any_station} all-station, {general} general-only"
    )


tools = []
variables = [
    Variable(
        "median_station_distance_km",
        None,
        "Store the median over the schools of the distance to the nearest air "
        "quality monitoring station, as a float in kilometres, 2 decimal places.",
    ),
    Variable(
        "school_no2_nearest_station",
        None,
        "Store the mean over the schools of the assigned nitrogen dioxide level "
        "when each school takes the nearest station of any kind, as a float in "
        "ug/m3, 2 decimal places.",
    ),
    Variable(
        "school_no2_nearest_general",
        None,
        "Store the same mean when each school takes the nearest general "
        "(non-roadside) station "
        "instead, as a float in ug/m3, 2 decimal places.",
    ),
]
validators = {
    "validate_median_station_distance_km": validate_median_station_distance_km,
    "validate_school_no2": validate_school_no2,
}
