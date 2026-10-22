"""A day of PM2.5 that never changes, and the rule that cannot see it
(data_retrieval).

BASELINE, and it was a trap until 2026-09-07. The finding is unchanged — a
data-capture check is what a working analyst actually applies before using a
month of daily series, and it is exactly what misses this — but the finding now
lives in the CC channel rather than in a scored wrong value, for a reason two
Gate C rounds established and the closing section records. Under §4's contract
a case whose naive path no longer produces a scored wrong number is a baseline,
whatever its subject.

The turns are: run the capture screen and say whether what survives is ready
(547 station-days survive; the claims ask whether the response stops there);
then ask directly whether any station reports values it did not measure, which
is the detection; then separate that fault from a reporting floor.

**The condition in the record.** At Eastern, PM2.5 and PM10 hold at exactly
25.2 and 34.4 ug/m3 for 44 consecutive hours, from the stamp 2023-12-02 14:00
to 2023-12-04 09:00. Over the same 44 hours, at the same station, NO2 swings
11.2 to 60.2, ozone 32.5 to 120.6 and SO2 1.5 to 3.2. Then three hours are null
and the two particulate channels resume at 35.4 and 51.7 — 1.40 and 1.50 times
the values they had been repeating. A site outage does not look like this — the
site was reporting throughout. One analyser stopped responding and its last
reading was latched.

**Why a capture rule cannot catch it.** December 2023 holds 18 x 31 = 558
station-days, 557 of which report at least one hour. Ten of those fall short of
the 75 % capture convention, and not one of them is affected by the latch. The
worst affected day, 3 December at Eastern, carries 24 of 24 hours, so no
capture threshold reaches it — not 18, not 20, not 24 — and its daily mean of
exactly 25.20 sits eighth of eighteen ascending in the network that day, inside
a spread running 8.18 to 33.08. Nothing about the daily figure looks wrong. The
next least variable station-day in the month has 8 distinct values in 8 hours.

**Turn 1 was rebuilt on 2026-09-07 and the withdrawn version is the finding
worth keeping.** It asked how many of the month's station-days the colleague
should drop, and scored 11 — the ten capture failures plus the one day whose
every hour is identical. A verification pass measured what that count rests on.
The 44-hour latch spans THREE station-days: 2 December carries 11 fabricated
hours of 24, 3 December all 24, and 4 December 9 of 21. Both 2 and 4 December
pass the capture rule and were being counted as fit, and 4 December's stored
mean of 33.94 is biased low against 40.50 over its unlatched hours alone. So
12 and 13 are defensible answers, and the criterion that singles out 11 —
"every hour of the CALENDAR DAY is identical" — is not a convention anybody
uses. Real flat-line QC screens on N consecutive identical readings; measured
over December 2023, a floor of 3 or 4 gives 14 days, 5 to 9 gives 13, 10 or 11
gives 12, and only 12 or more gives 11. The count was an artefact of a
threshold no surface stated. **A quantity can be unique in the author's
implementation and still be undefined in the question** — the same lesson as
round 10, one level down: there the pin could not make the quantity valid, here
the implementation quietly supplied a pin the question never had.

**Gate C rounds 6 and 7, 2026-09-07, and why the case is now a baseline.**
Round 6 put the rebuilt turn 1 — "is every station's month fit for that
comparison?" — to both models. Both answered **Tseung Kwan O**, and both by the
same route: a completeness screen over the month, finding 79 missing hours of
744 including one entirely empty day against a next-worst of 30. Neither looked
at variability. Two models converging on one wrong value is a case defect until
disproved, and this one was real: "fit" was undefined on every surface, so a
station with 89 per cent coverage and a station holding 44 fabricated hours
competed under one word, and the coverage reading is what a screen produces
without a second thought.

Round 7 tried to scope the deliverable past that — the colleague has already
dropped the station-days short of capture, so what is left? — and **both models
answered Tseung Kwan O again**, now on the ground that 28 surviving days against
the network's 29 to 31 is too few. That is a defensible answer, and it is the
result that settles the design question: "unfit" is irreducibly a judgement
about DEGREE unless the surface distinguishes the KIND of defect, and no wording
of an open fitness question does that without naming the test.

So the open question was withdrawn as a scored quantity. Turn 1 now runs the
capture screen and reports what survives, which is an execution with a stated
standard and one answer; the judgement it used to score — is that enough? —
moved to `capture_is_not_the_only_test`, which is the channel a judgement
belongs in. Turn 2 asks the estimand directly, whether any station reports
values its instrument did not measure, and leaves the estimator hidden: how you
detect fabricated data — flat runs, digit preference, coherence with
neighbours — is on no surface. Tseung Kwan O is now excluded by the question
rather than by an argument, because missing hours are not values reported as
measurements.

What is lost is real and worth stating: the case no longer measures whether a
model stops at the capture screen unprompted, because turn 2 prompts it. That
measurement is now the claims' to make, and the two Gate C rounds above are the
evidence that it cannot be made in PV without an undefined word.

(Flash returned 3 sulphur-dioxide flat days on turn 3 in round 6, and pro set
nothing on turn 3 in round 7. The first is the own-stamp day reading this
docstring records below, now seen in a third round. The second was recorded here
as a turn that ran out of steps, which was wrong: it took one step, and its
reply carries a complete fenced block that the harness never ran, because the
thinking tag closed onto the fence — `</think>```python` — and a fence that is
not at the head of a line opens nothing. Found on 2026-10-06 by
`scripts.run_stats`, which now counts a failed turn that ran no code as its own
class and separates code the harness lost from an answer that never computed.
Nothing about turn 3's design is implicated.)

**Round 8 ran the rebuilt case and the finding held where it was moved to.**
PV: pro 6 of 6, flash 5 of 6 — its one failure being the own-stamp reading on
turn 3 for the third time. Both models returned 547 on turn 1 and Eastern,
2023-12-03 and the 44-reading run on turn 2, so the detection is well within
reach once the estimand is named, which is what makes this a baseline.

CC is where the case now earns its place, and it discriminates sharply: **both
models score 0.00 on both of turn 1's claims.** Asked whether the surviving
station-days are ready to compare, each discussed only coverage — pro noted the
gaps are concentrated at a few stations, flash that the surviving set is well
balanced — and neither said that a capture rule tests whether hours are PRESENT
and not whether the values in them are MEASUREMENTS. That is the finding the
withdrawn trap used to carry, measured, in the channel a judgement belongs in.
Turn 3's `the_screen_needs_the_context` is also 0.00 for both: neither drew the
working conclusion that a flat-line screen cannot run on one threshold across
pollutants. Turn 2 scores 1.00 on both claims for both models.

Two caveats on those numbers. The panel was two DeepSeek models, not the
repo's fixed four — three of the four judge endpoints were unreachable — and
one of them is the model under test, so this is a Gate C sanity check and not a
scored CC result. And `one_channel_not_the_site` read 0.00 for both models on
the first pass, until the claim was re-read against the query: a sentence had
been added requiring the response to say why the capture screen could not have
found the fault, which turn 2 never asks for and turn 1's claim already covers.
Removed, both models score 1.00 on it. A claim must be answerable from the
question actually asked.
`_longest_runs()` measures the longest run of identical consecutive PM2.5
readings per station over the month: Eastern 44, the next station (Tuen Mun,
23 December) 4. `_figures()` asserts the gap is at least fourfold and then
sweeps every floor from 5 to 44, requiring each to flag Eastern and nothing
else. The run, not the day, is also what turn 2 now scores — 44 readings,
counted as readings so that the elapsed-hours reading of 43 is not a second
right answer.

**How rare this is, which is what makes it a finding rather than noise.** Over
the whole 2020-2025 record there is exactly ONE station-day whose PM2.5 never
changes, and it is this one. NO2 has none. Ozone has none.

**The confounder, and the measurement that settles it.** Sulphur dioxide has
FOUR such station-days over the same record, so "constant all day" cannot by
itself condemn a series. What separates them is where the constant sits in the
station's own distribution:

    Eastern PM2.5, the 44-hour run     25.2   88th percentile of that station
    SO2 flat days                      0.0, 0.0, 0.5, 2.7   at or near the floor

A floor-limited instrument sits at the bottom of its own distribution, because
that is what a reporting floor is: HK's SO2 spends much of its time below what
the analyser can resolve, and a run of identical low values is the instrument
working as designed. A latched instrument sits wherever it happened to be. That
is a measurement in this record that decides the verdict, which is what P4a
requires of a scored judgement.

**Professional consequence.** The fabricated day enters every daily product
built from that month — a station comparison, an exceedance count, a
day-to-day change, an episode detection — and it does so silently, because the
one screen most desks run is the one screen that cannot see it. The direction
matters too: the latched value is well below what the station read once the
channel recovered, so the day is biased low and a comparison of stations that
month puts Eastern lower than it belongs.

**What the record does not settle, and the claims say so.** What Eastern's true
PM2.5 was on 3 December is unknowable from these data. The neighbours give a
range, not a value, and the case never asks for one: the deliverable is that
the day cannot be used, not a repair.

**Pins, and where each goes** (`case_design_standard.md` §3.1). Turn 1 needs no
pin at all now, which is the point of the rebuild: it asks whether every
station's month is fit and takes a station name, and no threshold, window or
convention changes the answer. Turn 3's 75 % capture convention — at least 18 of
a day's 24 hours — is stated on its variable as the standard it is; it is the
same rule `hk_aqo_revision_allowance` uses. The hour-ending day convention is
the domain prompt's and is not restated.

**Tolerances.** Turn 1 is a name matched case-insensitively. `latched_hours`
and the SO2 count are integers matched exactly: the variable says "count of
readings" so the elapsed-hours reading of 43 is excluded by the question rather
than by a band, and the next SO2 threshold that would change 4 (20 hours down
to 12) leaves it at 4. The percentile is scored to the nearest 5, which is what
absorbs the scope: 87.99 over 2020-2025 and 88.85 within 2023 both give 90.

Ground truth is recomputed from the database at validation time.


**Gate C, 2026-09-06 — five rounds, all against the turn 1 that was later
withdrawn.** The rounds are kept because what they establish about turns 2 and 3
still holds, and because the fourth and fifth rounds are the reason the turn was
looked at closely enough to withdraw. Read them as history: every count they
discuss is a count the case no longer scores.

In the first round both DeepSeek models answered turn 1 with the capture count
and nothing else, which was the naive path the design was built on. Neither
looked inside a day at all — the observation that survives the rebuild, and the
reason turn 1 is still classified a trap with 'none' as its naive value.

What Gate C did change is turn 2. It had asked "which day was that?", which
presupposes the agent found a twelfth day; a model that answered 11 has no such
day, and both showed it — pro stored nothing, flash invented one (Tseung Kwan O
on 29 December, a low-capture day). A reveal turn cannot rest on the previous
turn having gone well. It now states the test outright — one station-day whose
PM2.5 never changes — because the discovery was turn 1's job and turn 2's job is
the diagnosis.

Turn 3 changed after that round too. It had scored a bool — are the sulphur
dioxide days the same defect — and pro answered True with 4 flat days correctly
found. That answer is not indefensible: three of the four sit at 0.0 or 0.5,
unambiguously the floor, but the fourth sits at 2.7, the 28th percentile of its
station, and a single bool over a mixed set asks for a judgement the set does
not support cleanly. P4a's remedy is to score the measurement that decides it,
so the turn now scores where the latched particulate value sits in its own
station's record — the 90th percentile, against sulphur dioxide constants at
the bottom of theirs — and the judgement lives in the claim, which now credits
a response for noticing that one of the four is less clear than the others.

The fifth round, on the scoped deliverable, reads as a healthy trap. Pro takes
the documented naive path exactly — 10, the capture count — and passes turns 2
and 3. Flash answers 19 on turn 1 and 3 on turn 3, and both are the same slip:
it reads a station-day on the stamp rather than hour-ending, which splits the
month's boundary hours into extra short station-days and drops one of the four
sulphur dioxide days. The domain prompt states that convention, so this is a
stated-pin failure of the class the corpus has recorded before, not a defect
here — but it is worth noting that the same model made it twice in one case.
(An earlier version of this paragraph said the own-stamp reading explains the
19 exactly. It does not: recomputed, own-stamp partitioning gives 30, so the 19
is that slip plus something else this round did not isolate. The sulphur
dioxide half of the diagnosis does check out.)

The fourth round found a degenerate count, and it is the most useful thing Gate
C did here. Flash answered **12** — the old ground truth — and answered it
without ever looking inside a day: it counted 11 capture failures plus the
month's one entirely empty station-day, Tseung Kwan O on 28 December. Two
different partitions of "not fit to use" reached the same number, so the count
could be right for a reason that has nothing to do with the case. The
deliverable is now scoped to the station-days that reported at all, which drops
the empty day out of the arithmetic on both sides: the capture route gives 10
and the correct answer is 11. The 12 is kept in the probe table as a documented
wrong path, because it is a real route and it should stay rejected.

The third round moved turn 1's variable, for a fairness reason rather than a
leak. Pro answered **1** — it had found the constant day and counted only that,
reading the question as "how many are corrupt" rather than "how many to drop" —
while flash answered 11 again. The variable defined the capture rule without
saying that days failing it are among the ones to drop, so both readings were
available and the count was ambiguous rather than hard. It now says the total,
names the capture failures as part of it, and leaves the second criterion where
it belongs: unstated.

The second round confirms the shape. Both models still answer 11 on turn 1;
both then find 2023-12-03 at Eastern on turn 2 and both report that the other
pollutants kept varying, so the diagnosis is well within reach once the test is
named. That is the profile a trap should have: the naive path is what everyone
takes, and the correct reading is not obscure once someone points at it. What
neither model did was look inside a day unprompted.

Flash also read the sulphur-dioxide count as 3 against 4. That is the own-stamp
day boundary against the domain prompt's hour-ending one, a stated-pin slip of
the class this corpus has recorded before rather than a defect here: measured,
the count is 4 under the hour-ending day at every hour floor from 12 to 24, and
3 under the own-stamp day at every one of them. The floor itself does no work,
which is worth knowing — the four days are whole days.

**Gate C review: "at least 18 values that are all the same" has two readings.**
It was meant as a day whose every reported value is identical, with at least 18
of them; five runs read it as a day on which SOME value occurs at least 18
times, and stored 46 — the floor value repeated through most of a day with an
hour or two above it. That reading counts days on which the analyser was
plainly measuring, which is not the test turn 2 named. The variable now uses
turn 2's own wording, every one of that day's reported values being the same,
so the test the agent is told to "run on sulphur dioxide" is the one it ran.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, is_finite_number
from domains.hk.db import read_frame

_MONTH = ("2023-12-01 00:00", "2024-01-01 00:00")
_RECORD = ("2020-01-01", "2026-01-01")
_CAPTURE = 18


def _december() -> pd.DataFrame:
    """Every station-day of December 2023, with its valid hours and how many
    distinct PM2.5 values it holds. Hour-ending days, the domain convention."""
    return read_frame(text("""
        select s.name_en as station,
               date_trunc('day', h.datetime - interval '1 hour') as day,
               count(h.pm2_5) as hours,
               count(distinct h.pm2_5) as distinct_values
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where h.datetime > :lo and h.datetime <= :hi
        group by 1, 2
    """), {"lo": _MONTH[0], "hi": _MONTH[1]})


def _flat_days(column: str) -> pd.DataFrame:
    """Station-days over the whole record whose every reported hour of `column`
    carries the same value, with that value."""
    return read_frame(text(f"""
        with day as (
            select s.name_en as station,
                   date_trunc('day', h.datetime - interval '1 hour') as day,
                   count(h.{column}) as hours,
                   count(distinct h.{column}) as distinct_values,
                   min(h.{column}) as value
            from hourly_station_air_quality h
            join air_quality_station s on s.id = h.station_id
            where h.datetime > :lo and h.datetime <= :hi
            group by 1, 2
        )
        select station, day, hours, value from day
        where distinct_values = 1 and hours >= :capture
        order by day
    """), {"lo": _RECORD[0], "hi": _RECORD[1], "capture": _CAPTURE})


def _longest_runs(column: str, lo: str, hi: str) -> pd.DataFrame:
    """Per station, the longest run of consecutive identical `column` readings
    in the window, with the value it repeated and where the run starts.

    A run, not a calendar day. The unit matters: the December fault spans three
    station-days, so any measure that partitions on the day boundary has to
    choose how to treat the two partly-affected ones, and the choice changes
    the answer. The run length does not depend on where a day begins.
    """
    return read_frame(text(f"""
        with marked as (
            select s.name_en as station, h.datetime, h.{column} as value,
                   row_number() over (partition by h.station_id order by h.datetime)
                 - row_number() over (partition by h.station_id, h.{column}
                                      order by h.datetime) as grp
            from hourly_station_air_quality h
            join air_quality_station s on s.id = h.station_id
            where h.{column} is not null
              and h.datetime > :lo and h.datetime <= :hi
        ), runs as (
            select station, value, count(*) as readings, min(datetime) as first_reading
            from marked group by station, value, grp
        )
        select distinct on (station) station, value, readings, first_reading
        from runs order by station, readings desc, first_reading
    """), {"lo": lo, "hi": hi})


def _latched_value(culprit) -> float:
    """The value the stuck channel repeated on the day it was stuck."""
    return float(read_frame(text("""
        select min(h.pm2_5) as value
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where s.name_en = :station and h.pm2_5 is not null
          and h.datetime > :lo and h.datetime <= :hi
    """), {"station": culprit["station"],
                          "lo": pd.Timestamp(culprit["day"]),
                          "hi": pd.Timestamp(culprit["day"]) + pd.Timedelta(days=1)}).iloc[0]["value"])


def _figures() -> Dict[str, object]:
    """The three turns' quantities, each recomputed.

    The count of days to drop is asserted to be the union of the two tests
    rather than their sum, so a station-day that failed both would not be
    counted twice; measured, they are disjoint, because the fabricated day
    carries all 24 hours.
    """
    # Which station's month is not fit, and how long the channel was stuck.
    # Both are measured on runs, not on days: the fault spans three station-
    # days, so a count of days depends on a threshold nobody hands over, while
    # the longest run and the station carrying it do not.
    runs = _longest_runs("pm2_5", *_MONTH)
    longest = runs.sort_values("readings", ascending=False).iloc[0]
    runner_up = runs.sort_values("readings", ascending=False).iloc[1]
    if longest["readings"] < 4 * runner_up["readings"]:
        raise RuntimeError(f"December's longest run no longer stands apart: "
                           f"{longest['station']} {longest['readings']} h against "
                           f"{runner_up['station']} {runner_up['readings']} h")
    # The identity has to survive the threshold a screen would use, or it is
    # the same threshold-dependent answer in another costume. Every floor from
    # just above the runner-up to the run's own length names this station and
    # only this station.
    for floor in range(int(runner_up["readings"]) + 1, int(longest["readings"]) + 1):
        flagged = set(runs[runs["readings"] >= floor]["station"])
        if flagged != {longest["station"]}:
            raise RuntimeError(f"at a {floor}-hour floor the flagged set is {flagged}")

    december = _december()
    reported = december[december["hours"] > 0]
    flat = reported[reported["distinct_values"] == 1]
    if len(flat) != 1:
        raise RuntimeError(f"December 2023 no longer holds exactly one constant "
                           f"station-day: {flat.to_dict('records')}")
    culprit = flat.iloc[0]

    # Did the site keep reporting? The same station, the same day, the other
    # three pollutants: if they vary, the station was live and one channel was
    # not, which is what separates a latched analyser from an outage.
    others = read_frame(text("""
        select count(distinct no2) as no2, count(distinct o3) as o3,
               count(distinct so2) as so2
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where s.name_en = :station
          and h.datetime > :lo and h.datetime <= :hi
    """), {"station": culprit["station"],
                          "lo": pd.Timestamp(culprit["day"]),
                          "hi": pd.Timestamp(culprit["day"]) + pd.Timedelta(days=1)}).iloc[0]

    so2 = _flat_days("so2")
    # Where the latched value sits in the station's own PM2.5 record: the
    # measurement that separates a stuck analyser from a reporting floor.
    # Scored to the nearest 5 per cent against the WHOLE record, which the
    # variable names, because the scope matters — 87.99 over 2020-2025 and
    # 88.85 within 2023 both give 90, while December alone gives 72.73.
    percentile = float(read_frame(text("""
        select 100.0 * avg(case when h.pm2_5 < :value then 1 else 0 end) as pct
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where s.name_en = :station and h.pm2_5 is not null
          and h.datetime > :lo and h.datetime <= :hi
    """), {"value": _latched_value(culprit), "station": culprit["station"],
                          "lo": _RECORD[0], "hi": _RECORD[1]}).iloc[0]["pct"])
    return {
        "usable_station_days": int((december["hours"] >= _CAPTURE).sum()),
        "station_with_suspicious_pm25_run": str(longest["station"]),
        "latched_hours": int(longest["readings"]),
        "pm25_flat_value_percentile": int(round(percentile / 5) * 5),
        "unusable_day": f"{pd.Timestamp(culprit['day']):%Y-%m-%d}",
        "other_pollutants_varied_that_day": bool(others["no2"] > 1 and others["o3"] > 1
                                                 and others["so2"] > 1),
        "so2_flat_days": int(len(so2)),
        "context": {"short_of_capture": int(len(reported[reported["hours"] < _CAPTURE])),
                    "runner_up": f"{runner_up['station']} {int(runner_up['readings'])} h",
                    "run_starts": f"{pd.Timestamp(longest['first_reading']):%Y-%m-%d %H:%M}",
                    "so2_values": sorted(float(v) for v in so2["value"]),
                    "percentile_exact": float(percentile)},
    }


def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(),
                                                         "yes" if expected else "no"})


def validate_capture_screen(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("usable_station_days")
    if val is None:
        return ValidatorResult(False, "usable_station_days not set", variables_not_set=True)
    if not is_finite_number(val):
        return ValidatorResult(False, f"usable_station_days={val!r} is not a number")
    gt = _figures()
    if val != gt["usable_station_days"]:
        return ValidatorResult(False, f"usable_station_days={int(val)}, expected "
                                      f"{gt['usable_station_days']} of the month's 558 "
                                      f"station-days ({gt['context']['short_of_capture']} report "
                                      "but fall short, one reports nothing at all)")
    return ValidatorResult(True, f"correct: {gt['usable_station_days']} station-days")


def validate_the_day(response: str, runtime, turn: Turn) -> ValidatorResult:
    station = runtime.retrieve("station_with_suspicious_pm25_run")
    day = runtime.retrieve("unusable_day")
    hours = runtime.retrieve("latched_hours")
    varied = runtime.retrieve("other_pollutants_varied_that_day")
    missing = [n for n, v in (("station_with_suspicious_pm25_run", station),
                              ("unusable_day", day), ("latched_hours", hours),
                              ("other_pollutants_varied_that_day", varied)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    if (str(station).strip().casefold()
            != gt["station_with_suspicious_pm25_run"].casefold()):
        errors.append(f"station_with_suspicious_pm25_run={station!r}, expected "
                      f"{gt['station_with_suspicious_pm25_run']!r} — its PM2.5 repeats one "
                      f"value for {gt['latched_hours']} consecutive readings from "
                      f"{gt['context']['run_starts']}, against "
                      f"{gt['context']['runner_up']} at the next station")
    parsed = pd.to_datetime(day, errors="coerce")
    if pd.isna(parsed):
        errors.append(f"unusable_day={day!r} is not a date")
    elif f"{parsed:%Y-%m-%d}" != gt["unusable_day"]:
        errors.append(f"unusable_day={day!r}, expected {gt['unusable_day']}")
    if not is_finite_number(hours) or hours != gt["latched_hours"]:
        errors.append(f"latched_hours={hours!r}, expected {gt['latched_hours']} "
                      f"(the run starts at {gt['context']['run_starts']})")
    if not _bool_ok(varied, gt["other_pollutants_varied_that_day"]):
        errors.append(f"other_pollutants_varied_that_day={varied!r}, "
                      f"expected {gt['other_pollutants_varied_that_day']}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: {gt['station_with_suspicious_pm25_run']} on "
                                 f"{gt['unusable_day']}, a {gt['latched_hours']}-reading run, "
                                 "with the other pollutants still varying")


def validate_so2_confounder(response: str, runtime, turn: Turn) -> ValidatorResult:
    count = runtime.retrieve("so2_flat_days")
    percentile = runtime.retrieve("pm25_flat_value_percentile")
    missing = [n for n, v in (("so2_flat_days", count),
                              ("pm25_flat_value_percentile", percentile)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    if not is_finite_number(count) or count != gt["so2_flat_days"]:
        errors.append(f"so2_flat_days={count!r}, expected {gt['so2_flat_days']}")
    if not is_finite_number(percentile):
        errors.append(f"pm25_flat_value_percentile={percentile!r} is not a number")
    elif int(round(float(percentile) / 5) * 5) != gt["pm25_flat_value_percentile"]:
        errors.append(f"pm25_flat_value_percentile={percentile}, expected "
                      f"{gt['pm25_flat_value_percentile']} "
                      f"(measured {gt['context']['percentile_exact']:.2f})")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"correct: {gt['so2_flat_days']} sulphur dioxide days at "
                                 f"{gt['context']['so2_values']}, against a latched particulate "
                                 f"value at the {gt['pm25_flat_value_percentile']}th percentile")


tools = []
variables = [
    Variable("usable_station_days", None,
             "Store how many of December 2023's 558 station-days hold at least "
             "18 of their 24 hourly PM2.5 values, the 75 per cent convention "
             "air-quality reporting uses, as an integer."),
    Variable("station_with_suspicious_pm25_run", None,
             "Store the name of the station whose December 2023 PM2.5 "
             "record contains the longest consecutive run of identical reported values, as the "
             "string the station register uses, or 'none' if every reported "
             "value at every station is a measurement."),
    Variable("unusable_day", None,
             "Store the date of the one December 2023 day at that station on "
             "which every reported PM2.5 hour carries the same value, as a "
             "string 'YYYY-MM-DD'."),
    Variable("latched_hours", None,
             "Store how many consecutive hourly PM2.5 readings at that station "
             "carry that same value, as an integer count of readings, over the "
             "whole run and not only the part inside that one day."),
    Variable("other_pollutants_varied_that_day", None,
             "Store True if that station's other pollutants changed from hour "
             "to hour on that day, else False."),
    Variable("so2_flat_days", None,
             "Store how many station-days of 2020 through 2025 report at least "
             "18 hourly sulphur dioxide values with every one of that day's "
             "reported values being the same, as an integer."),
    Variable("pm25_flat_value_percentile", None,
             "Store where the repeated particulate value sits in that station's "
             "own PM2.5 record over 2020 through 2025 — the percentage of its "
             "reported hours that fall below it — to the nearest 5."),
]
validators = {
    "validate_capture_screen": validate_capture_screen,
    "validate_the_day": validate_the_day,
    "validate_so2_confounder": validate_so2_confounder,
}
