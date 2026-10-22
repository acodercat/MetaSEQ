"""Requiring a co-measured pollutant changes which sites answer
(statistical_characterization).

BASELINE. The variables spell both computations out, so the tempting shortcut
— compute PM2.5 on the rows you kept for a CO analysis and report it as Hong
Kong's PM2.5 — is not reachable as a naive path in the Round 9 sense. What the
case tests is whether the agent, having produced both numbers, reads the gap as
an artefact of which sites report the second pollutant rather than as a fact
about the air.

**Seven of the fifteen general stations report no CO.** Central/Western,
Eastern, Kwai Chung, Kwun Tong, Sha Tin, Sham Shui Po and Tai Po carry zero CO
values in EVERY database year from 2020 to the partial 2026, and EPD's own
station configuration disables the CO tab for exactly those seven while
enabling it for the other eight general stations and all three roadside ones
(Gate B round 4 checked `https://www.aqhi.gov.hk/common/js/menu.js`). The
language here is deliberately "do not report CO", not "carry no CO
instrument": neither the database nor EPD's configuration inventories physical
hardware, and an earlier draft of this docstring asserted the hardware claim
the evidence does not support.

**The shift is predominantly site composition, but not only that.** Decomposed
in two steps over 2025 — first drop the seven zero-CO sites while keeping every
PM2.5 record at the other eight, then impose the same-record CO requirement
within those eight:

    general, every PM2.5 hour                14.871980 ug/m3   126,394 hours
      after dropping the seven sites         15.373720          66,686
      after also requiring CO in the row     15.406852          65,531

    total shift  +0.534872
      site composition   +0.501740   93.806 %
      hours within the surviving sites   +0.033132    6.194 %

The seven sites hold 47.240 % of the general PM2.5 hours; the restriction
removes 48.153 % of them, the extra 0.913 points being CO-less hours at the
eight sites that do report CO. An earlier draft called this "station dropout,
not hour dropout" and "the whole of why", which overstated a 93.8 % effect into
a 100 % one and would have penalised a response that correctly reported both
components. Gate B round 4 measured the decomposition and the claim now asks
for the primary driver while permitting the smaller one.

All three roadside stations report CO on 97.2-97.6 % of their PM2.5 hours, so
the kerb figure barely moves and the roadside-to-general ratio compresses from
1.372659 to 1.327848. That asymmetry is the point: an analyst who needs CO
alongside PM2.5 loses almost nothing at the kerb and nearly half the background
network, and the contrast between the two is what shrinks.

**Convention sweep — six axes, all combinations computed.**
`recipe` is the aggregation order.
`co_rule` is whether an hour counts as reporting CO when the record carries any
number or only when that number exceeds zero: 67 CO values in this year are
exactly 0.0. `pm_rule` is whether the 32 hours whose PM2.5 is exactly 0.0 (29
general, 3 roadside) are readings or absences. `endpoint` is whether the year
ends before or at 2026-01-01 00:00. `screen` is whether an hour needs a
minimum of two CO-reporting general stations to count, and `screen_scope` is
whether that rule applies to both classes or only to the general one.

`endpoint` and `screen` were added after Gate B round 4 found them and
`screen_scope` after round 6, and finding them is the reason the record counts
are scored at all — see below.

**What the tolerances exclude, and what the counts do instead.** The means and
the ratios both use `decimals=3` (+/-0.0006). Those bands
exclude every aggregation-recipe and zero-handling variant; the narrowest is
8.8 bands. They CANNOT exclude the two axes Gate B added, because both move the
means by less than a band:

    day-of-stamp endpoint   gen_all 14.872350   0.0025    4 bands  (the reading before 2026-08-30)
    minimum-two-reporters   gen_co  15.406892   0.00004   0.07 bands ADMITTED

Tightening further would mean asking for PM2.5 means to four or five decimals
to police a one-record difference, which tests arithmetic transcription rather
than analysis. The counts do it exactly instead, with no tolerance at all: the
inclusive endpoint reads 126,409 and 65,539 against 126,394 and 65,531, and the
minimum-two-reporters screen reads 65,530. Both fail on an exact integer match.
This is the general lesson — where a convention changes the SIZE of the sample,
score the size.

`general_stations_without_co` is likewise exact. Both readings of it were
measured rather than assumed and both give 7: the seven report no CO in any row
of the year, with or without an accompanying PM2.5 value.

**Round 6 moved the ratios to three decimals and gave turn 2 its own
denominator count.** Round 5's fix guarded turn 2's roadside side but not its
general side: a completeness screen applied only to the general class leaves
every roadside count untouched and moves the ratio by 3.4e-6, which no reported
precision separates. `co_reporting_hours_behind_the_ratio` is that guard — the
same 65,531 turn 1 reports, declared again as turn 2's own output so the turn
does not inherit an assumption about which recipe produced it. It moves to
65,530 under either screen, 65,539 under an inclusive endpoint and 65,474 under
a positive-CO rule.

Dropping the ratios from four decimals to three retired a different problem
rather than papering over it. At four decimals the ratio computed from the
three-decimal class means reads 1.3726 against 1.3727, so the query had to
forbid that rounding order while the band admitted it anyway — an inconsistency
Gate B round 6 was right to call out. At three decimals both orders read 1.373
and 1.328: the disagreement was an artefact of asking for a digit the data does
not support, not a method choice, and the prohibition is gone from the query.

The direction survives every convention: all recipes raise the mean and
compress the ratio. What the sweep changes is the value, not the finding.

**What Gate B round 4 changed, and what it is still worth attacking.** The
review rejected the first version on three counts, all reproduced by the author
before acting on them: the sweep omitted the endpoint and minimum-reporter axes
(fixed by scoring the counts, above); `restriction_changes_the_network` was
satisfiable by restating the station count the query itself asks for, and
`what_the_comparison_cannot_settle` by restating the year; and the mechanism
was written as wholly site composition when 6.2 % of the shift is timing within
the surviving sites.

The two claims were rewritten to demand what the query does not supply — an
inference the two means support (the departing sites are the lower-reading
ones) and the one limitation the record cannot repair (nothing establishes what
the absent sites would have measured). On the live run that followed, the
rewritten claims scored 0.50 and 0.00 where their predecessors scored 1.00 and
0.00, and the tie is substantive rather than vague: both judges read the same
sentence and disagreed over whether "the surviving hours tend to carry higher
particulates" states that the departing sites are the lower-reading ones. One
of them is right and the case cannot tell which, so the wording of that claim
is the part still most worth attacking.

**What Gate B round 5 changed.** The round-4 fix was wrong in an instructive
way: the record counts were added to turn 1 only, and turn 2 scored just the
two ratios and the station count. Both forbidden readings reproduce turn 2's
ratios inside the band — the inclusive endpoint gives 1.372625 / 1.327815 and
the minimum-two-reporter screen 1.372659 / 1.327904 — so an agent that used one
recipe in turn 1 and another in turn 2 passed turn 2 outright. The sweep could
not see it because it judged one tuple across both turns: a wrong turn-1 count
made the combination "outside" even where every turn-2 output was accepted.

**A benchmark conversation cannot assume the agent used one recipe throughout,
so each turn needs its own guard.** Turn 2 now scores the roadside record
counts as well — 25,687 and 25,019, against 25,690 / 25,022 for the inclusive
endpoint and 25,016 for the screen — and the ratios were later dropped to three
decimals, at which the component-rounding route reads the same 1.373 and 1.328
and stops being a distinct reading at all. The query's prohibition on it,
added in round 5, was removed again in round 6.

That also retires the round-4 refusal. Declining to tighten the ratio band was
defended on the grounds that the adjacent four-decimal values are ordinary
rounding slop; they are not, they are the outputs of two specifically forbidden
conventions, and the framework contract cannot be used to admit a route the
query rules out. The band is unchanged, but it is no longer what carries the
exclusion.

Ground truth is recomputed from the database at validation time.


**Gate A review 2026-09-06 carried out the rewrite the query-surface audit
prescribed for turn 2 and the 2026-09-02 pass missed.** The turn asked the agent
to "count how many general stations contribute no carbon monoxide at all across
the year" — the fact the whole finding rests on, handed over — while the claim
`lower_reading_sites_are_the_ones_that_leave` scores whether the response works
out that the stations dropping out are the cleaner ones. The count is still
scored, because it is the evidence; it is no longer named in the query, so
reaching for it is the agent's move.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

# Half-open under the domain prompt's TIME WINDOWS convention: the record runs
# into 2026 and an inclusive end silently adds the hour at 2026-01-01 00:00.
_SPAN = ("2025-01-01", "2026-01-01")


def _station_totals() -> pd.DataFrame:
    """Per-station PM2.5 sums and counts, whole and restricted to CO hours.

    Aggregated server-side: `domains.HK.db` caps a statement at thirty seconds
    and the year holds ~157k station-hours. Sums and counts are enough for
    every pooled mean the case reports, and carrying them per station is what
    lets the same query answer the station-dropout count.

    A pollutant counts as reported whenever the column holds a number, which
    is what both CO-restricted variables state: 32 of these PM2.5 hours are
    exactly 0.0 and 67 CO
    values are exactly 0.0. Treating either as an absence is a different
    method and the tolerances exclude it — by 9.8 and 8.8 bands respectively.

    `n_both` counts hours carrying BOTH pollutants, and the station-dropout
    count is derived from it. That is one of two readings of "a station with
    no CO", the other being a station with no CO row at all whether or not
    PM2.5 accompanies it. Measured rather than assumed: both give 7.
    """
    return read_frame(text("""
        select s.name_en,
               s.station_type::text as station_type,
               count(a.pm2_5)                                    as n_pm,
               sum(a.pm2_5)                                      as sum_pm,
               count(*) filter (where a.pm2_5 is not null
                                  and a.co is not null)          as n_both,
               sum(a.pm2_5) filter (where a.pm2_5 is not null
                                      and a.co is not null)      as sum_both
        from hourly_station_air_quality a
        join air_quality_station s on s.id = a.station_id
        where a.datetime > :lo and a.datetime <= :hi
        group by 1, 2
    """), {"lo": _SPAN[0], "hi": _SPAN[1]})


def _figures() -> Dict[str, float]:
    """The seven scored quantities, pooled over hourly station readings."""
    t = _station_totals()
    general = t[t["station_type"] == "GENERAL"]
    roadside = t[t["station_type"] == "ROADSIDE"]

    def pooled(rows: pd.DataFrame, restricted: bool) -> float:
        sums, counts = ("sum_both", "n_both") if restricted else ("sum_pm", "n_pm")
        return float(rows[sums].sum() / rows[counts].sum())

    general_all = pooled(general, False)
    general_co = pooled(general, True)
    return {
        "pm25_general_all_records": general_all,
        "pm25_general_co_reporting": general_co,
        "general_pm25_hours": int(general["n_pm"].sum()),
        "general_pm25_co_hours": int(general["n_both"].sum()),
        # Ratios formed from the UNROUNDED class means. Dividing the
        # three-decimal means instead reads 1.372647 and 1.327838, which round
        # to the same 1.373 and 1.328 at the scored precision — the reason
        # round 6 removed the prohibition on that order rather than restating
        # it here.
        "roadside_general_ratio_all": pooled(roadside, False) / general_all,
        "roadside_general_ratio_co_reporting": pooled(roadside, True) / general_co,
        # Turn 2's own endpoint and screen guard. Gate B round 5 showed the
        # turn-1 counts do not protect turn 2: an agent may use one recipe in
        # turn 1 and another in turn 2, and both forbidden readings reproduce
        # turn 2's ratios inside the band. These counts do not.
        "roadside_pm25_hours": int(roadside["n_pm"].sum()),
        "roadside_pm25_co_hours": int(roadside["n_both"].sum()),
        # Deliberately the same number turn 1 reports, declared again as
        # turn 2's own output. A completeness screen applied only to the
        # general class leaves every roadside count untouched and moves the
        # ratio by 3.4e-6, which no reported precision separates; this count
        # moves to 65,530 and is exact. Gate B round 6 found that hole.
        "co_reporting_hours_behind_the_ratio": int(general["n_both"].sum()),
        "general_stations_without_co": int((general["n_both"] == 0).sum()),
    }


def _unusable(name: str, val) -> ValidatorResult:
    """The failure for a variable that is missing or not a number, else None.

    `runtime.retrieve` is called in the validators themselves rather than in
    here: `tests/test_turn_stores.py` reads the variable names out of the
    validator source to check them against the turn's `stores`, and a helper
    that hid the call would take that check away.
    """
    if val is None:
        return ValidatorResult(False, f"{name} not set", variables_not_set=True)
    if not is_finite_number(val):
        return ValidatorResult(False, f"{name}={val!r} is not a number")
    return None


def _not_an_integer(name: str, val) -> ValidatorResult:
    """A count must be an int; `bool` is excluded as an `int` subclass."""
    if val is None:
        return ValidatorResult(False, f"{name} not set", variables_not_set=True)
    if not isinstance(val, int) or isinstance(val, bool):
        return ValidatorResult(False, f"{name}={val!r} is not an integer")
    return None


def validate_general_means(response: str, runtime, turn: Turn) -> ValidatorResult:
    all_records = runtime.retrieve("pm25_general_all_records")
    co_reporting = runtime.retrieve("pm25_general_co_reporting")
    pm_hours = runtime.retrieve("general_pm25_hours")
    co_hours = runtime.retrieve("general_pm25_co_hours")

    means = {"pm25_general_all_records": all_records,
             "pm25_general_co_reporting": co_reporting}
    counts = {"general_pm25_hours": pm_hours, "general_pm25_co_hours": co_hours}
    for name, val in means.items():
        failure = _unusable(name, val)
        if failure is not None:
            return failure
    for name, val in counts.items():
        failure = _not_an_integer(name, val)
        if failure is not None:
            return failure

    gt = _figures()
    wrong = [
        f"{name}={val}, expected ~{gt[name]:.3f}"
        for name, val in means.items()
        if not reports_as(val, gt[name], decimals=3)
    ]
    # Exact: the counts are what exclude the year-endpoint and minimum-reporter
    # readings, which every band wide enough to be reasonable would admit.
    wrong += [f"{name}={val}, expected {gt[name]}"
              for name, val in counts.items() if val != gt[name]]
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True,
        f"correct: {all_records} over {pm_hours} hours, "
        f"{co_reporting} over {co_hours} CO-reporting",
    )


def validate_ratio_shift(response: str, runtime, turn: Turn) -> ValidatorResult:
    ratio_all = runtime.retrieve("roadside_general_ratio_all")
    ratio_co = runtime.retrieve("roadside_general_ratio_co_reporting")
    roadside_hours = runtime.retrieve("roadside_pm25_hours")
    roadside_co_hours = runtime.retrieve("roadside_pm25_co_hours")
    denominator_hours = runtime.retrieve("co_reporting_hours_behind_the_ratio")
    dropped = runtime.retrieve("general_stations_without_co")

    ratios = {"roadside_general_ratio_all": ratio_all,
              "roadside_general_ratio_co_reporting": ratio_co}
    for name, val in ratios.items():
        failure = _unusable(name, val)
        if failure is not None:
            return failure
    counts = {"roadside_pm25_hours": roadside_hours,
              "roadside_pm25_co_hours": roadside_co_hours,
              "co_reporting_hours_behind_the_ratio": denominator_hours,
              "general_stations_without_co": dropped}
    for name, val in counts.items():
        failure = _not_an_integer(name, val)
        if failure is not None:
            return failure

    gt = _figures()
    wrong = [
        f"{name}={val}, expected ~{gt[name]:.3f}"
        for name, val in ratios.items()
        if not reports_as(val, gt[name], decimals=3)
    ]
    wrong += [f"{name}={val}, expected {gt[name]}"
              for name, val in counts.items() if val != gt[name]]
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True,
        f"correct: ratio {gt['roadside_general_ratio_all']:.3f} -> "
        f"{gt['roadside_general_ratio_co_reporting']:.3f}, "
        f"{gt['general_stations_without_co']} stations without CO "
        f"over {roadside_hours}/{roadside_co_hours} roadside hours",
    )


tools = []
variables = [
    Variable(
        "pm25_general_all_records",
        None,
        "Store the mean PM2.5 across the general stations' hourly readings for "
        "2025, over every hour that reports a PM2.5 value, as a float in ug/m3 "
        "to 3 decimal places. Give each hourly station reading EQUAL WEIGHT: "
        "pool the station-hours themselves rather than forming a territory "
        "hourly figure or a per-station mean first, and screen no hour by how "
        "many stations reported in it.",
    ),
    Variable(
        "pm25_general_co_reporting",
        None,
        "Store the same mean over only those hourly readings whose record also "
        "carries a carbon monoxide value at the same station and hour, as a "
        "float in ug/m3 to 3 decimal places. A pollutant counts as reported "
        "whenever its record carries a number, a value of exactly zero "
        "included.",
    ),
    Variable(
        "general_pm25_hours",
        None,
        "Store how many general-station hourly readings the first mean was "
        "taken over, as an integer.",
    ),
    Variable(
        "general_pm25_co_hours",
        None,
        "Store how many of those readings the second mean was taken over, as "
        "an integer.",
    ),
    Variable(
        "roadside_general_ratio_all",
        None,
        "Store the roadside mean PM2.5 divided by the general mean PM2.5 over "
        "2025, over every hour that reports a PM2.5 value, as a float to 3 "
        "decimal places. Each of the two means gives every hourly station "
        "reading EQUAL WEIGHT, pooling the station-hours rather than forming a "
        "territory hourly figure or a per-station mean first, with no minimum "
        "number of reporting stations in an hour.",
    ),
    Variable(
        "roadside_general_ratio_co_reporting",
        None,
        "Store the same ratio computed over only the hourly readings whose "
        "record also carries a carbon monoxide value at the same station and "
        "hour, as a float to 3 decimal places. A pollutant counts as reported "
        "whenever its record carries a number, a value of exactly zero "
        "included.",
    ),
    Variable(
        "roadside_pm25_hours",
        None,
        "Store how many roadside-station hourly readings the roadside mean in "
        "the first ratio was taken over, as an integer.",
    ),
    Variable(
        "roadside_pm25_co_hours",
        None,
        "Store how many of those readings the second ratio's roadside mean was "
        "taken over, as an integer.",
    ),
    Variable(
        "co_reporting_hours_behind_the_ratio",
        None,
        "Store how many general-station hourly readings form the denominator "
        "of the carbon-monoxide-restricted ratio, as an integer.",
    ),
    Variable(
        "general_stations_without_co",
        None,
        "Store how many general stations contribute no CO-reporting hourly "
        "readings at all across 2025, as an integer.",
    ),
]
validators = {
    "validate_general_means": validate_general_means,
    "validate_ratio_shift": validate_ratio_shift,
}
