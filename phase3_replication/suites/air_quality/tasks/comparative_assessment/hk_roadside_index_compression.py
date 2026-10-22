"""A roadside doubles NO2 and adds 8 % to the risk it carries
(comparative_assessment).

BASELINE. Neither scored quantity has a plausible-but-wrong method behind it —
both are means of named columns over named stations in a pinned set of hours —
so calling this a trap would be dressing up a surprising result as a
methodological one. The surprise is in what the two numbers say together, and
that lives in the CC claims.

Hong Kong classifies three of its eighteen stations as roadside: Causeway Bay,
Central and Mong Kok. Over the 29,468 hours of 2020-2025 in which **all
eighteen** stations reported, 530,424 station-hours in all:

                      NO2        added risk   AQHI mean   AQHI median
    GENERAL (15)     33.91 ug/m3   5.2878       3.3137         3
    ROADSIDE (3)     67.93         5.7238       3.5468         3
    ratio             2.003        1.0824       1.0704         1.00

**A doubling of the pollutant most specific to traffic buys eight per cent more
health risk, and leaves the band the public is shown unchanged — the median AQHI
is 3 at both kinds of site.**

The reason is that the index's other main term moves the opposite way. Ozone at
the roadside runs 0.56 times the general level — 32.02 against 56.96 — and
across the eighteen stations mean NO2 and mean ozone correlate at **-0.95**
(Pearson; -0.89 Spearman): roadside NO2 titrates ozone away, so the sites with
the most NO2 have the least ozone. Ozone is the larger contributor at general
stations, 56.8 % of mean added risk against NO2's 28.5 %, and it still holds
29.6 % at the roadside against NO2's 53.4 %. So the roadside NO2 surplus is
bought back by an ozone deficit before the index is formed. Particulates never
carry the index anywhere: 13.6 % at general stations, 16.0 % roadside.

**Why the scored quantity is the added-risk sum and not the index, which is the
substantive change Gate B round 3 forced.** The index used to be scored, as a
ratio of the two classes' mean AQHI, and it cannot be. Two reasons, and the
second is the one that matters.

The measured reason: the ratio is not separable from a completeness convention
the case forbids. Sweeping all 64 minimum-reporter combinations on the pooled
basis, requiring at least 13 of 15 general stations reads 1.074660, sitting
0.001145 from the ground truth while the correctly reported 1.08 sits 0.004194
from it — the wrong method nearer the truth than the right answer's own
rounding, so no band separates them. Pooled at 2, 3 and 4 decimals; station-first
at 2 and 3; restricted to whole-network hours at 2 and 3; and the two class means
scored separately — every one of them admits a filter that drops as little as
0.1 % of station-hours.

The reason behind that reason: **AQHI is an ordinal scale, and the mean of an
ordinal scale is not a quantity.** Its values are bands — 1 to 10 and then
"10+", where the last is not even a number — so an arithmetic mean of them, and
a ratio of two such means, has no defined unit and no stable meaning. That the
band could not be made to hold was not bad luck; it was the statistic being
ill-formed. The correct ordinal summary is the median, and the median says the
two classes are IDENTICAL, which is the sharpest form of the same fact and needs
no arithmetic at all.

So the case scores the cardinal quantity the index is derived from — the sum of
the four added-risk terms, in per cent of baseline risk, which is a real ratio
scale — and puts the compression of the published index in the CC claims, where
it is stated as direction and magnitude, the only way an ordinal scale should be
summarised. The added-risk columns are also the cleaner provenance: recomputing
them from the table's own concentrations reproduces the stored values on 99.99 %
of rows for the NO2 term and 100 % for the SO2 and particulate terms, and on
99.54 % for ozone — whose shortfall is known and dated, the 2025 coefficient
revision having been applied by converting the stored figures rather than
recomputing them. The `aqhi` column, by contrast, is EPD's published index and
is not recoverable from any concentrations at all.

Conventions. **The comparison is restricted to hours in which all eighteen
stations reported**, which is both what makes the tolerances hold and the better
design: the two classes are then measured in the same hours, and the two ratios
are formed on the same rows, so they can be set beside each other. It keeps
29,468 of the window's 52,396 hours, so it costs 43.8 % of them. Pooling every
reported hour instead reads 2.0396 and 1.0890 — both excluded, and the docstring
records them because they are what the case scored before.

**That restriction introduced a degree of freedom of its own, and a live agent
found it before this docstring did.** "Every station reported" can mean the
table holds a row, or that the row is non-null in the column being averaged, and
the readings do not agree:

    18 rows exist, nulls and all      45,620 h   NO2 2.020   risk 1.0819
    18 non-null NO2                   33,571 h       2.015        1.0815
    18 non-null risk components       38,333 h       1.997        1.0831
    both, which the variables pin     29,468 h       2.003        1.0824

The first is what the live run computed, and it is a fair reading of the
sentence the query used to carry. Both ratio variables now spell the rule out —
a row with a null in any of the five fields does not count — and each names the
single hour set, so neither turn inherits the other's reading of it. All three rivals are then excluded by at least 9.8 band
widths, which is why the restriction is still worth having: it replaced an
unpinnable continuum of completeness filters, whose nearest member sat 1.9 band
widths away, with a four-way choice that one clause settles.

Tolerances, each chosen against the completeness sweep rather than against a
reporting format, and each stated with its margin:

- NO2 ratio, `decimals=3`, deriving +/-0.0006. The answer is 2.003133, so the
  reported 2.003 is 0.000133 away and the nearest combination that reports a
  different three-decimal number is 0.006791 away — **11.3 band widths**. At two
  decimals the margin is 1.1 and the case would be back where it started.
- Added-risk ratio, `decimals=4`, deriving +/-0.00006. The answer is 1.082448,
  the reported 1.0824 is 0.000048 away, and the nearest violating combination is
  0.000522 away — **8.7 band widths**. Three decimals gives 2.2, which is
  survivable but thin, and the fourth decimal costs nothing to ask for.

Further out, both bands exclude the ratio of medians (2.00 and 1.00), roadside
against the whole network including itself (1.74), and the pooled-hours readings
above.

Rejected on measurement, recorded so it is not attempted again, and re-measured
on the whole-network hours this case now uses. The intended scored quantity was
the rank correlation between a station's mean NO2 and its mean index across the
eighteen, on the hypothesis that the index barely orders stations by traffic
exposure. It reads Spearman **+0.60**, which is moderate rather than absent, and
it is not robust: dropping the three roadside stations takes it to +0.35 and
dropping the rural background site at Tap Mun to +0.56.

A second candidate died the same way. Ranking the eighteen by mean index puts
two roadside sites on top — Causeway Bay 3.6218, Mong Kok 3.5401 — and then
**Eastern, a general station, at 3.5120, above roadside Central's 3.4785**. So a
general site does outrank a roadside one, which is the fact such a case would
want; but the margin is 0.034 on an ordinal scale's arithmetic mean, and the
identity of the pair moved when the hour basis changed, which is disqualifying
for a scored answer. (On the previous all-hours basis the same two stations read
3.453659 and 3.454174, a gap of 0.0005 the other way.)

Both ground truths are recomputed here from the database.

**Split 2026-09-02 (query length):** turn 2 asked for the added-risk ratio,
the index comparison and the judgement in one breath; the index comparison
and the judgement are now a third turn, with the four claims moved to it.

**Gate B round 21 (2026-09-03) caught what that split turn scored**, and it
was the mistake this docstring spends four paragraphs arguing against: the
verdict was computed as a ratio of the two classes' MEAN published index
(1.070) against the NO2 ratio, which is a metric ratio of an ordinal
category code. The split reintroduced the exact statistic round 3 removed.
The turn now scores the median band instead — 3 at both kinds of site, on
pooled and station-first medians, over the complete hours and over every
reported hour — which is a comparison the scale supports. The share of hours
above a cut was considered and rejected as a scored quantity because it is
not invariant: the roadside class holds more hours at band 4 or above and
fewer at band 7 or above, so the cut would decide the answer.
"""

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

_SPAN = ("2020-01-01", "2026-01-01")


def _means() -> pd.DataFrame:
    """Class means of NO2 and added risk over whole-network hours.

    Aggregated server-side. The table holds over a million station-hours and
    `domains.HK.db` caps a statement at thirty seconds; pulling the rows to
    group them here times out, which is how this helper was first written.

    The station counts are read from the register rather than written as 3 and
    15, so adding or retiring a station cannot silently turn the completeness
    rule into something weaker.
    """
    return read_frame(text("""
        with roster as (
            select count(*) filter (where station_type = 'ROADSIDE') as roadside,
                   count(*) filter (where station_type = 'GENERAL') as general
            from air_quality_station
        ), valid as (
            select q.datetime, s.station_type as station_type, q.no2,
                   q.no2_ar + q.so2_ar + q.o3_ar + q.pm_ar as risk
            from hourly_station_air_quality q
            join air_quality_station s on s.id = q.station_id
            where q.datetime > :lo and q.datetime <= :hi
              and q.no2 is not null and q.no2_ar is not null
              and q.so2_ar is not null and q.o3_ar is not null
              and q.pm_ar is not null
        ), complete as (
            select v.datetime from valid v, roster r
            group by v.datetime, r.roadside, r.general
            having count(*) filter (where v.station_type = 'ROADSIDE') >= r.roadside
               and count(*) filter (where v.station_type = 'GENERAL') >= r.general
        )
        select v.station_type, avg(v.no2) as no2, avg(v.risk) as risk
        from valid v join complete c on c.datetime = v.datetime
        group by 1
    """), {"lo": _SPAN[0], "hi": _SPAN[1]}).set_index("station_type")


def _ratios() -> dict:
    m = _means()
    return {
        "no2": float(m.loc["ROADSIDE", "no2"] / m.loc["GENERAL", "no2"]),
        "risk": float(m.loc["ROADSIDE", "risk"] / m.loc["GENERAL", "risk"]),
    }


def _median_bands() -> dict:
    """The two classes' MEDIAN published index, under four constructions.

    The median, not a mean and not a ratio of means: the index is an ordinal
    band scale whose top value is "10+", so its arithmetic mean has no unit and
    a ratio of two such means has no measurement-scale interpretation. That is
    why Gate B round 3 took the index out of the scored quantities, and round 21
    caught the split turn putting a ratio of index means back in.

    A share-of-hours comparison is not usable either, because the answer depends
    on where the cut is put: the roadside class holds MORE hours at band 4 or
    above (46.8 % against 39.5 %) and FEWER at band 7 or above (1.65 % against
    1.76 %). The median is the one summary that is not a cut chosen after seeing
    which way it falls, and it reads 3 for both classes on all four
    constructions below.
    """
    # The index is an integer band, so the station-hours collapse to a
    # histogram in the database — about 360 rows of (class, station, band,
    # in a complete hour, count) instead of every station-hour since 2020,
    # which took longer to transfer than the 30 s statement limit allows under
    # load. Expanding the counts back gives the very rows the medians were
    # always taken over, so the medians below are pandas' own, unchanged.
    counts = read_frame(text("""
        with valid as (
            select q.datetime, q.station_id, s.station_type as station_type, q.aqhi,
                   (q.no2 is not null and q.no2_ar is not null and q.so2_ar is not null
                    and q.o3_ar is not null and q.pm_ar is not null) as complete_row
            from hourly_station_air_quality q
            join air_quality_station s on s.id = q.station_id
            where q.datetime > :lo and q.datetime <= :hi and q.aqhi is not null
        ), complete as (
            select datetime from valid group by datetime
            having count(*) filter (where complete_row) = count(*) and count(*) >= 18
        )
        select v.station_type, v.station_id, v.aqhi,
               (c.datetime is not null) as in_complete_hour, count(*) as n
        from valid v left join complete c on c.datetime = v.datetime
        group by 1, 2, 3, 4
    """), {"lo": _SPAN[0], "hi": _SPAN[1]})
    rows = counts.loc[counts.index.repeat(counts["n"])].drop(columns="n").reset_index(drop=True)
    out = {}
    for label, frame in (("complete hours", rows[rows["in_complete_hour"]]),
                         ("every reported hour", rows)):
        pooled = frame.groupby("station_type")["aqhi"].median()
        first = (frame.groupby(["station_type", "station_id"])["aqhi"].median()
                 .groupby("station_type").median())
        out[f"{label}, pooled"] = (float(pooled["ROADSIDE"]), float(pooled["GENERAL"]))
        out[f"{label}, station first"] = (float(first["ROADSIDE"]), float(first["GENERAL"]))
    return out


def _index_separates() -> bool:
    """Whether the published index puts the two classes in different bands."""
    table = _median_bands()
    verdicts = {roadside != general for roadside, general in table.values()}
    if len(verdicts) != 1:
        raise RuntimeError("the median band comparison is not invariant: "
                           + "; ".join(f"{n}={v}" for n, v in table.items()))
    return verdicts.pop()


def validate_roadside_no2_ratio(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("roadside_no2_ratio")
    if val is None:
        return ValidatorResult(
            False, "roadside_no2_ratio not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(False, f"roadside_no2_ratio={val!r} is not a number")

    gt = _ratios()["no2"]
    # decimals=3, justified in the docstring against a 64-combination sweep of
    # minimum-reporter rules: margin 11.3 band widths, against 1.1 at two.
    if reports_as(val, gt, decimals=3):
        return ValidatorResult(True, f"correct: {val} ~ {gt:.3f}")
    return ValidatorResult(False, f"roadside_no2_ratio={val}, expected ~{gt:.3f}")


def validate_roadside_risk_ratio(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("roadside_added_risk_ratio")
    if val is None:
        return ValidatorResult(
            False, "roadside_added_risk_ratio not set", variables_not_set=True
        )
    if not is_finite_number(val):
        return ValidatorResult(
            False, f"roadside_added_risk_ratio={val!r} is not a number"
        )

    gt = _ratios()["risk"]
    # decimals=4: margin 8.7 band widths, against 2.2 at three.
    if reports_as(val, gt, decimals=4):
        return ValidatorResult(True, f"correct: {val} ~ {gt:.4f}")
    return ValidatorResult(
        False, f"roadside_added_risk_ratio={val}, expected ~{gt:.4f}"
    )




def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_index_separation(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("index_separates_the_two_classes")
    if val is None:
        return ValidatorResult(False, "index_separates_the_two_classes not set",
                               variables_not_set=True)
    expected = _index_separates()
    if not _bool_ok(val, expected):
        return ValidatorResult(False,
                               f"index_separates_the_two_classes={val!r}, expected {expected}")
    return ValidatorResult(True, "correct: the median published band is 3 at both kinds "
                                 "of site, while NO2 doubles")


tools = []
variables = [
    Variable(
        "roadside_no2_ratio",
        None,
        "Store the mean nitrogen dioxide at the roadside stations divided by "
        "the mean at the general stations, as a float, 3 decimal places. Work "
        "only in the hours where all eighteen stations carry BOTH a nitrogen "
        "dioxide value AND all four of their added-risk values — an hour in "
        "which any station has a row but a null in any of those five fields "
        "does not qualify — and inside them pool every station-hour with equal "
        "weight, applying no further filter.",
    ),
    Variable(
        "roadside_added_risk_ratio",
        None,
        "Store the same ratio formed from the total added health risk each "
        "station-hour carries — the sum of its four per-pollutant added-risk "
        "terms — as a float, 4 decimal places. Same hours as before, those in "
        "which all eighteen stations carry a nitrogen dioxide value and all "
        "four added-risk values, and the same equal-weight pooling of "
        "station-hours, so that the two ratios are measured on the same rows.",
    ),
]
validators = {
    "validate_roadside_no2_ratio": validate_roadside_no2_ratio,
    "validate_roadside_risk_ratio": validate_roadside_risk_ratio,
    "validate_index_separation": validate_index_separation,
}
variables += [
    Variable("index_separates_the_two_classes", None,
             "Store True if the published Air Quality Health Index puts "
             "roadside station-hours in a different median band from general "
             "ones over the same hours, else False. The index is a band scale, "
             "so compare the classes on it as one."),
]
