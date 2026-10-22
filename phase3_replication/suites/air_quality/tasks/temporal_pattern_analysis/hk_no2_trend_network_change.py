"""Half of the NO2 decline since 2020 is two stations joining the network — and
the other comparability axis is the calendar (temporal_pattern_analysis).

BASELINE, with the diagnostic weight in CC. The naive figure here is not a
mistake — it is the domain's own TERRITORY FIGURES convention, applied exactly
as written — and that is the point. A convention that is right for one period
says nothing about whether two periods are comparable, and nothing in the query
names the network, its size, or the year it changed. Finding that the 2020
figure and the 2025 figure stand on different sets of stations — and that the
difference is not a small one — IS the exam.

**The condition in the record.** Sixteen of Hong Kong's eighteen air quality
stations report from the first day of the record, 9 January 2020. North and
Southern begin on 10 July 2020 at 10:00. Both are general stations in cleaner
districts, and in the first full year they share with the others they read
well below the network:

    2021, all hours       NO2 ug/m3
    the other sixteen       42.35
    North and Southern      32.66

So a territory mean built the domain's way — the hourly mean across whichever
sites report, then the mean of those hourly figures — is a sixteen-station
quantity for the first half of 2020 and an eighteen-station quantity from July,
and the two cleaner stations count for all of 2025 and half of 2020.

**What that does to the headline.** Territory annual mean NO2, the domain
convention:

                                2020      2025      change
    every reporting station    38.9332   37.1288    -4.63 %
    the sixteen present from
      the record's first day   39.4325   38.3890    -2.65 %

"NO2 down 4.6 % since 2020" is nearly halved on a consistent network. The
extra two points are not the air: they are two low-NO2 stations weighing on the
2025 mean for twelve months and on the 2020 mean for six.

A control with no composition change confirms the reading. From 2021, when all
eighteen report all year, to 2025: -9.60 % on all eighteen and -8.92 % on the
sixteen, a gap of 0.7 points with no change of membership. Subtracting that
from the 2.0-point gap of the 2020 comparison leaves about 1.3 points. That
subtraction is a difference-in-differences-style sensitivity, not a
decomposition — the two changes have different denominators — and it is read
only as showing that partial-year membership adds more than the station-set
trend gap alone would.

**The second axis: the calendar.** The record's 2020 begins on 9 January, so
the 2020 mean covers 8,585 territory hours against 8,750 in 2025, and the 192
hours of 1-8 January 2025 (territory mean 55.11 ug/m3, a winter week) have no
counterpart. Fixing the station set does not fix this. On the sixteen stations
over the span of the calendar the 2020 record covers — 9 January to 31 December
of both years — 2025 reads 38.0227 and the change is -3.58 %:

                                    2020      2025      change
    sixteen, 2025 full year        39.4325   38.3890    -2.65 %
    sixteen, 2025 from 9 January   39.4325   38.0227    -3.58 %

The network effect survives (all stations on the common span still sit about
two points below the sixteen), but the like-for-like line the
desk can publish is the common-span one, and that is what turn 2 now scores
beside the full-year figures. Gate B round 13 found this.

**Why the naive figure cannot be marked wrong in PV, and is scored as correct.**
The prompt's convention says every reporting site, no minimum. An agent that
follows it has done what the domain asked; scoring that as a failure would be
the corpus contradicting its own prompt, which Gate B round 9 refused on the
calm-wind case for the same reason. So turn 1 scores the convention's figures,
turn 2 scores the consistent-network figures beside the facts that expose the
change, and the claims carry the judgement: which of the figures the desk may
put a "since 2020" on.

**The July-to-December comparison.** Starting 2020 on 10 July so that both
years sit on eighteen stations, against the same months of 2025, reads
-7.60 % (from 1 July, about -7.2 %). Because the same calendar segment is used at
both ends the seasonal cycle is controlled, not confounded; the result is a
legitimate within-season sensitivity that answers a different estimand — a
July-to-December change, not an annual one. The claims permit it as a labelled
secondary comparison and forbid only presenting it as the annual trend. It is
pinned as a wrong assignment for the full-year variables, which is what it is.
Round 13 corrected an earlier reading that called it seasonal noise.

**Pins, and where each one goes** (`case_design_standard.md` §3.1). The annual
construction — hourly territory mean, then the mean of those — is the prompt's
TERRITORY FIGURES convention and is restated on the variables because pooling
every station-hour instead reads 39.0662 / 37.3215 / -4.47 % and
39.5694 / 38.5853 / -2.49 %. "Stations reporting from the record's first day"
is stated on the turn-2 variables as the definition of the consistent set: it
is one query against the data and every one of the sixteen satisfies it; the
alternative "at least one value in every month of both years" gives the same
sixteen (round 13 checked). The date of network completion is defined over the
stations reporting NO2 in 2025 — a fixed population — rather than "today",
which is a live word the validator could not implement. Every percentage is
"computed from the unrounded means": two Gate C runs took
37.13 / 38.93 - 1 = -4.62 % from the displayed figures against -4.63 from the
means, and the contract refuses the former. Nothing states how many stations
there are, when any joined, that the network changed, or that the record does
not begin on 1 January. The years are in the query because the comparison is
the question.

**Readings measured and excluded.**

    pooled station-hours, all stations           39.07 / 37.32 / -4.47 %
    pooled station-hours, the sixteen            39.57 / 38.59 / -2.49 %
    change from the rounded means                -4.62 % (turn 1)
    hours with at least two reporters            38.93 / 37.13 / -4.64 %
                                                 39.43 / 38.39 / -2.65 %
    2020 taken from 10 July, against the same
      months of 2025, all eighteen               38.93 / 35.97 / -7.60 %
    2025 full year given as the common span      38.39 / -2.65 %
    the day-of-stamp reading used before
      2026-08-30                                 -2.64 / 37.98 / -3.69
    the network was the same all along           16 / 16 stations, no date

Every mean and percentage uses `reports_as` at two decimals — the hours-with-
two-reporters route (-4.64) sat inside the old +/-0.006 band once the
convention moved the truth to -4.6347, and is refused by the report rule. The station
counts and the date are exact.

**Overlap, stated.** `hk_ventilation_evidence_span` is the same shape in the
time dimension — one series starting years after the other — and this is the
shape in the station dimension. `hk_roadside_index_compression` restricts
itself to hours in which all eighteen stations report, for its own tolerances
and so that its two ratios sit on the same rows; it does not name the July 2020
join and does not compare years. Neither tests what this case tests.

All ground truths are recomputed from the database at validation time.


Figures re-measured 2026-08-30 under the hour-ending timestamp convention
(see the prompt's TIMESTAMPS section and `hk_ozone_aqo_day_boundary`).

**Turn 2 rebuilt 2026-09-01 on the surface rule.** The query now asks only
whether the two figures are comparable and what the line can say. PV scores
the verdict (not as they stand), how many stations first appear during 2020
(two: North and Southern, both on 2020-07-10), and whether the fixed-network
change is a decline (it is, -2.65 %, under both hour conventions).
`_comparability_verdicts()` checks both. The fixed-network means and the
common-span figures remain in this docstring as the reference route.


**Gate A review 2026-09-06 made the comparability verdict a computation.** It
was the literal `False`, written inside the loop over the two hour conventions,
so the invariance guard two lines below was comparing a constant with itself and
this docstring's claim that all three verdicts are recomputed was true of two of
them. It is now derived from the join count: the two years are comparable as
they stand only if no station joined the record after its first day. The value
is unchanged, because two did.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, is_finite_number, reports_as
from domains.hk.db import read_frame


def _hourly() -> pd.DataFrame:
    """Every NO2 station-hour of the two years, with the station's first NO2
    hour in the record beside it."""
    frame = read_frame(text("""
        with first_hour as (
            select station_id, min(datetime) as first_no2
            from hourly_station_air_quality where no2 is not null
            group by station_id
        )
        select a.datetime, a.station_id, a.no2, f.first_no2
        from hourly_station_air_quality a
        join first_hour f on f.station_id = a.station_id
        where a.no2 is not null
          and ((a.datetime > '2020-01-01' and a.datetime <= '2021-01-01')
            or (a.datetime > '2025-01-01' and a.datetime <= '2026-01-01'))
    """))
    frame["hour_start"] = frame["datetime"] - pd.Timedelta(hours=1)  # stamps are hour-ending
    frame["year"] = frame["hour_start"].dt.year
    return frame


def _territory_annual(frame: pd.DataFrame) -> Dict[int, float]:
    """TERRITORY FIGURES: the hourly mean across reporting sites, then the
    mean of those hourly figures over the year."""
    hourly = frame.groupby(["year", "datetime"])["no2"].mean()
    return hourly.groupby(level="year").mean().to_dict()


def _pct(later: float, earlier: float) -> float:
    return float((later / earlier - 1) * 100)


def _figures() -> Dict[str, object]:
    frame = _hourly()
    record_start = frame["first_no2"].min()
    from_start = frame[frame["first_no2"] == record_start]
    all_stations = _territory_annual(frame)
    fixed = _territory_annual(from_start)
    # The span of the calendar the 2020 record covers, applied to both years.
    start_2020 = frame.loc[frame["year"] == 2020, "hour_start"].min()
    common = from_start[
        (from_start["hour_start"].dt.month > start_2020.month)
        | ((from_start["hour_start"].dt.month == start_2020.month)
           & (from_start["hour_start"].dt.day >= start_2020.day))]
    common_span = _territory_annual(common)
    in_2020 = frame[frame["year"] == 2020]
    jan = in_2020[in_2020["hour_start"].dt.month == 1]["station_id"].nunique()
    dec = in_2020[in_2020["hour_start"].dt.month == 12]["station_id"].nunique()
    complete = frame.loc[frame["year"] == 2025, "first_no2"].max()
    return {
        "no2_territory_2020": float(all_stations[2020]),
        "no2_territory_2025": float(all_stations[2025]),
        "no2_change_pct": _pct(all_stations[2025], all_stations[2020]),
        "stations_reporting_jan_2020": int(jan),
        "stations_reporting_dec_2020": int(dec),
        "network_complete_date": str(complete.date()),
        "no2_fixed_network_2020": float(fixed[2020]),
        "no2_fixed_network_2025": float(fixed[2025]),
        "no2_fixed_network_change_pct": _pct(fixed[2025], fixed[2020]),
        "no2_fixed_network_2025_common_span": float(common_span[2025]),
        "no2_fixed_network_common_span_change_pct":
            _pct(common_span[2025], common_span[2020]),
    }


def _read(runtime, names):
    got = {name: runtime.retrieve(name) for name in names}
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return got, ValidatorResult(
            False, f"{', '.join(missing)} not set", variables_not_set=True)
    return got, None


def _is_int(val) -> bool:
    """`bool` is an `int` subclass; True must not pass as a count of one."""
    return isinstance(val, int) and not isinstance(val, bool)


def _numeric_errors(got, gt, names) -> list:
    errors = []
    for name in names:
        if not is_finite_number(got[name]):
            errors.append(f"{name}={got[name]!r} is not a number")
        elif not reports_as(got[name], gt[name], decimals=2):
            errors.append(f"{name}={got[name]}, expected ~{gt[name]:.2f}")
    return errors


def validate_convention_change(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = ("no2_territory_2020", "no2_territory_2025", "no2_change_pct")
    got, failure = _read(runtime, names)
    if failure is not None:
        return failure
    gt = _figures()
    errors = _numeric_errors(got, gt, names)
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(
        True, f"correct: {gt['no2_territory_2020']:.2f} to "
              f"{gt['no2_territory_2025']:.2f}, {gt['no2_change_pct']:+.2f} %")




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


def _comparability_verdicts() -> Dict[str, object]:
    frame = read_frame(text("""
        select a.datetime, s.name_en as station, a.no2
        from hourly_station_air_quality a
        join air_quality_station s on s.id = a.station_id
        where a.no2 is not null
          and (a.datetime <= '2021-01-01' or a.datetime > '2025-01-01')
          and a.datetime <= '2026-01-01'
    """))
    first = frame.groupby("station")["datetime"].min()
    joined = first[first > first.min() + pd.Timedelta(days=1)]
    fixed = frame[~frame["station"].isin(joined.index)]
    results = []
    for origin in (fixed["datetime"] - pd.Timedelta(hours=1), fixed["datetime"]):
        year = origin.dt.year
        annual = fixed.groupby([year, fixed["datetime"]])["no2"].mean().groupby(level=0).mean()
        joining = int((joined.dt.year == 2020).sum())
        results.append({
            # Derived, not asserted: the two years are comparable as they stand
            # only if the network they are measured on did not change between
            # them. A record in which no station joined after the first day
            # would score the other way, which is what P4a asks of a verdict.
            "figures_comparable_as_they_stand": joining == 0,
            "stations_joining_during_2020": joining,
            "fixed_network_change_is_negative": bool(annual[2025] < annual[2020]),
        })
    for key in results[0]:
        if len({r[key] for r in results}) != 1:
            raise RuntimeError(f"{key} is not invariant to the hour convention")
    return results[0]


def validate_comparability(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "figures_comparable_as_they_stand": runtime.retrieve("figures_comparable_as_they_stand"),
        "stations_joining_during_2020": runtime.retrieve("stations_joining_during_2020"),
        "fixed_network_change_is_negative": runtime.retrieve("fixed_network_change_is_negative"),
    }
    return _verdict_check(got, _comparability_verdicts())

tools = []
variables = [
    Variable(
        "no2_territory_2020",
        None,
        "Store the territory annual mean nitrogen dioxide for 2020 as a float "
        "in ug/m3, 2 decimal places: for each hour, the mean across whichever "
        "stations report a value in that hour, and then the mean of those "
        "hourly figures over the year.",
    ),
    Variable(
        "no2_territory_2025",
        None,
        "Store the same for 2025, as a float in ug/m3, 2 decimal places.",
    ),
    Variable(
        "no2_change_pct",
        None,
        "Store the change from the 2020 figure to the 2025 figure as a "
        "percentage of the 2020 figure, computed from the unrounded means, "
        "as a float, 2 decimal places, negative for a fall.",
    ),
    Variable("figures_comparable_as_they_stand", None,
             "Store True if the 2020 and 2025 territory annual means can be "
             "compared as they stand, else False."),
    Variable("stations_joining_during_2020", None,
             "Store how many stations first appear in the NO2 record during 2020 "
             "after its first day, as an integer."),
    Variable("fixed_network_change_is_negative", None,
             "Store True if, over only the stations reporting since the record's "
             "first day, the 2025 territory annual mean NO2 is below the 2020 "
             "one, else False."),
]
validators = {
    "validate_convention_change": validate_convention_change,
    "validate_comparability": validate_comparability,
}
