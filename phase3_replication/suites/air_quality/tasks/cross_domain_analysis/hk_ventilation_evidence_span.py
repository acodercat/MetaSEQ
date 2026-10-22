"""A wind-speed contrast measured over three quarters of nothing
(cross_domain_analysis).

BASELINE, and built as the first case in the corpus to score a CROSS-TURN identity, a design
withdrawn later with the variable that carried it (see the end of this docstring)
(`v2_design.md` R5). Nothing here names coverage, join asymmetry, or sample
span: the query asks the question an operations desk would ask, and knowing
that a joint analysis is bounded by its scarcest input — and going to look
which input that is — IS the exam.

**The condition in the record.** Sha Tin's PM2.5 series runs from 2020-01-09.
The wind speed it has to be conditioned on runs from 2024-12-19 — every weather
station in the territory starts there — so the paired series covers 559 days of
a 2,366-day record:

    Sha Tin PM2.5, valid hours          54,852    2020-01-08 onward
    Sha Tin wind speed, valid hours     13,372    2024-12-19 onward
    hours carrying both                 12,646
    PM2.5 hours with no wind to pair    42,206    76.9 % of the record

An inner join answers the question asked and silently discards three quarters
of the record. Nothing errors, nothing warns, and the figure that comes back
is a real figure — for the last 559 days.

**The ventilation signal itself is genuine and strong.** Over the paired hours,
taking the tenth and ninetieth percentiles of wind speed as the two edges:

    wind speed at or below 1.17 km/h,  1,371 hours      16.79 ug/m3
    wind speed at or above 12.67 km/h, 1,303 hours      10.13
    ratio                                                1.66

Sixty-six per cent more fine particulate in the calmest tenth of hours than in
the windiest. That is not in dispute and the case does not ask the agent to
doubt it. What the case asks is what it is evidence ABOUT.

**Why little in the numbers gives the truncation away, which is the point.**
The obvious check — is the covered window representative? — comes back nearly
clean:

    mean PM2.5 over the 12,646 paired hours      13.6179 ug/m3
    mean PM2.5 over all 54,852 hours             13.3195
    difference                                   -0.2984

Three tenths of a microgram, 2.2 % of the level. An analyst who wondered
whether the joined sample was biased would find no symptom worth acting on,
conclude the window was fine, and be right about the level while still holding
559 days of evidence for a six-year claim. The shortfall is not visible in the
quantities the analysis produces, which is why it has to be looked for rather
than noticed.

**The professional consequence, and it is turn 2.** The deliverable this
supports is a statement about how Hong Kong's air responds to ventilation. The
559 covered days open on 19 December 2024 — four months BEFORE the 2025 AQO
revision took effect on 11 April 2025, so they straddle it rather than follow
it, a correction Gate B round 12 made to an earlier draft of this sentence —
and sit entirely outside the pandemic years the record opens with; whether the same
ratio held in 2020 or 2022 is not knowable from this database, and a report
presenting 1.66 as a property of the record rather than of its last eighteen
months has overstated its evidence fourfold in span. The honest deliverable
states the ratio, states the window it rests on, and says what would extend it.

**The cross-turn identity, which the first version scored and the rebuild
withdrew (see the end of this docstring).** Turn 1's paired-hour count
and turn 2's unpaired count must sum to 54,852 — the two turns partition one
series. `docs/v2_measurements.md` §8 records four cases in which a model got a
base quantity wrong, its turn failed, and the next turn passed anyway while the
wrong figure sat in the runtime; in one, an agent carried a gust of 1,148 km/h
into its account of a storm's scale. R5 was written for that and no case had
used it. Here the identity costs one comparison and it is the difference
between two turns that are separately correct and two that are jointly
coherent.

**Pins, and where each one goes** (`case_design_standard.md` §3.1). The station
pair is specific to this question and lives on the variables: Sha Tin's air
quality station and the Sha Tin weather station (`station_code` SHA), which
share a name and a district so no distance argument is needed. The deciles are
stated because ten equal-count groups is an arbitrary framing rather than the
exam. THE START OF THE WINDOW IS NOT PINNED ANYWHERE — the query says "the
record", which is the whole point. Its END is pinned at 2026-07-01 because the
database is live and the scored counts are exact: `hk_extreme_wind_corroboration`
records the same lesson, and this case read 13,858 paired hours and then
13,859 within one session, before the end was pinned, as new rows arrived.

**Why percentile EDGES and not ten equal-count groups, which is what this case
first asked for and what Gate C rejected.** Wind speed here takes 266 distinct
values over 12,646 hours; the calm edge, 1.17 km/h, is shared by 158 of them.
An equal-count split must therefore decide which of those 158 hours falls in
the first group and which in the second, and the question supplies no second
key to decide it with. Measured over four orderings a competent implementer
might choose:

    ordered by (wind speed, hour)             17.05 / 10.17
    ordered by (wind speed, PM2.5 ascending)  16.57 / 10.28
    ordered by (wind speed, PM2.5 descending) 17.44 / 10.06
    ordered by wind speed alone, stable sort  17.05 / 10.16

A spread of 0.86 on the calm figure against a two-decimal report — the
equal-count reading has NO unique answer, so P1 could not hold. The percentile edges do:
pandas `qcut`, `numpy.percentile` under all five interpolation methods, and
PostgreSQL `percentile_cont` all return 1.17 and 12.67, and the calm figure
varies by 0.0000 across the seven.

**Readings measured and excluded.**

    territory-mean wind instead of the Sha Tin station   15.86 / 9.55
    calm hours (wind speed exactly 0) dropped            16.71 / 10.13
    the windy edge excluded from the group it bounds     16.79 / 10.17
    BOTH edges excluded                                  17.03 / 10.17
    ten equal-count groups, ties broken by hour          17.06 / 10.17

Each is separated on at least one of the two scored figures at the reported
precision, and both are scored (`reports_as` at two decimals since Gate B
round 19; it replaced a +/-0.02 band, and it is stricter — every reading in
the table above still differs on at least one figure's second decimal). The first is out by 0.93 and 0.58. The second returns the windy figure
IDENTICALLY — the 100 calm hours all sit below the calm edge — and is separated
on the calm figure by 0.081. The third and fourth are the two ways of dropping
a boundary: the 158 hours at 1.17 km/h and the 59 at 12.67. Dropping only the
windy edge moves that figure by 0.031 and leaves the calm one untouched;
dropping both moves the calm figure by 0.24 as well. Figures re-measured
2026-08-30 under the hour-ending weather convention, which adds one hour at
each end of both records. Gate B round 10 found this
table listing the windy-edge-only pair under a label that said both, which is
why both now appear. The fifth is the equal-count reading Gate C found. The
variables say "at or below" and "at or above" so the edges are not left to
the reader.

**What is NOT claimed, and a Gate C run showed why it has to be said twice.**
That the covered window is unrepresentative. In level it is very nearly
representative — 13.62 against 13.32 — and the docstring says so above with the
number.

The first version of the second claim required the response to STATE that the
truncation is undetectable from the output, which meant computing a comparison
the query gives no reason to compute. `deepseek-v4-flash` did not compute it
and instead asserted the opposite from intuition: "it is not a representative
18-month window". That is the failure worth scoring and it is not the one the
claim was written for, so the claim now forbids the unevidenced assertion
rather than demanding an unprompted calculation. A response that computes the
comparison and reports it, in either direction, satisfies it.

The distinction is a real one in practice: knowing a sample is truncated and
concluding it is biased are two different steps, and only the first is
supported here.

**Turn 2 rebuilt 2026-09-02 on the surface rule** (`docs/query_surface_audit.md`).
The earlier turn asked for the count of PM2.5 hours that could not enter the
comparison and the date the paired record opens — the query named the
truncation it exists to test. The rebuilt turn asks whether the desk can
publish, and scores the verdict (False) and the date the evidence opens
(2024-12-19); the cross-turn identity on the unpaired count is withdrawn
with the variable that carried it, because keeping the count on any surface
keeps the hint. Turn 1's query now asks the desk's question alone; its
variables carry the decile construction as before.

All ground truths are recomputed from the database at validation time.

**Gate C on the rebuilt turn 2 (2026-09-02, `gate_c_t1c`):** flash found the
19 December 2024 start, wrote that the desk "cannot say the full record
shows this", and stored `publishable_as_the_record` True ("yes, but they
need to be precise"). The variable had asked whether the contrast could be
published "as what the record shows"; it now asks whether it is a property
of the record as a whole, its full span, which is the sentence the desk
wants to print and the one flash itself said was not available.
"""

from typing import Dict

import numpy as np
import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, is_finite_number, reports_as
from domains.hk.db import read_frame

_AQ_STATION = "Sha Tin"
_CUTOFF = "2026-07-01"   # the record is live; exact counts need a fixed end
_WX_STATION = "SHA"


def _series() -> Dict[str, pd.DataFrame]:
    """Sha Tin's PM2.5 hours and the wind speed hours available to pair them."""
    pm = read_frame(text("""
        select a.datetime, a.pm2_5 as pm
        from hourly_station_air_quality a
        join air_quality_station s on s.id = a.station_id
        where s.name_en = :st and a.pm2_5 is not null
          and a.datetime <= :cut
    """), {"st": _AQ_STATION, "cut": _CUTOFF})
    wx = read_frame(text("""
        select h.datetime, h.wind_speed as ws
        from hourly_station_weather h
        join weather_station w on w.id = h.station_id
        where w.station_code = :code and h.wind_speed is not null
          and h.datetime <= :cut
    """), {"code": _WX_STATION, "cut": _CUTOFF})
    return {"pm": pm, "wx": wx}


def _figures() -> Dict[str, object]:
    s = _series()
    pm, wx = s["pm"], s["wx"]
    paired = pm.merge(wx, on="datetime")
    # The tenth and ninetieth percentiles of wind speed, boundary hours
    # included in the group they bound. Deliberately NOT ten equal-count
    # groups: see the docstring — with 266 distinct wind speeds over 12,646
    # hours the boundaries are heavily tied, and an equal-count split has to
    # break those ties on a second key the question cannot supply.
    lo = float(np.percentile(paired["ws"], 10))
    hi = float(np.percentile(paired["ws"], 90))
    return {
        "calm_decile_pm25": float(paired.loc[paired["ws"] <= lo, "pm"].mean()),
        "windy_decile_pm25": float(paired.loc[paired["ws"] >= hi, "pm"].mean()),
        "paired_hours": int(len(paired)),
        "first_paired_date": str(paired["datetime"].min().date()),
        # Publishable as what the record shows only if the paired hours are
        # essentially the record: 12,646 of 54,852 is 23 %, and any share
        # below nine tenths reads False.
        "publishable_as_the_record": bool(len(paired) >= 0.9 * len(pm)),
    }


def _read(runtime, names) -> tuple:
    got = {name: runtime.retrieve(name) for name in names}
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return got, ValidatorResult(
            False, f"{', '.join(missing)} not set", variables_not_set=True)
    return got, None


def validate_ventilation_contrast(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = ("calm_decile_pm25", "windy_decile_pm25", "paired_hours")
    got, failure = _read(runtime, names)
    if failure is not None:
        return failure
    # The loop variable is `key`, not `name`: tests/test_turn_stores.py reads
    # this source and would take a loop over a SUBSET of the variables as the
    # declaration, hiding paired_hours from the contract check.
    for key in ("calm_decile_pm25", "windy_decile_pm25"):
        if not is_finite_number(got[key]):
            return ValidatorResult(False, f"{key}={got[key]!r} is not a number")
    # `bool` is an `int` subclass; True must not pass as a count of one.
    if not isinstance(got["paired_hours"], int) or isinstance(got["paired_hours"], bool):
        return ValidatorResult(
            False, f"paired_hours={got['paired_hours']!r} is not an integer count")

    gt = _figures()
    wrong = [f"{key}={got[key]}, expected ~{gt[key]:.2f}"
             for key in ("calm_decile_pm25", "windy_decile_pm25")
             if not reports_as(got[key], gt[key], decimals=2)]
    if got["paired_hours"] != gt["paired_hours"]:
        wrong.append(f"paired_hours={got['paired_hours']}, "
                     f"expected {gt['paired_hours']}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: calmest decile {gt['calm_decile_pm25']:.2f} against "
              f"windiest {gt['windy_decile_pm25']:.2f} ug/m3 over "
              f"{gt['paired_hours']} paired hours")


def validate_evidence_span(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = ("publishable_as_the_record", "first_paired_date")
    got, failure = _read(runtime, names)
    if failure is not None:
        return failure
    gt = _figures()
    wrong = []
    verdict = got["publishable_as_the_record"]
    if not ((isinstance(verdict, bool) and verdict == gt["publishable_as_the_record"]) or
            (isinstance(verdict, str) and verdict.strip().lower() in
             {str(gt["publishable_as_the_record"]).lower(),
              "yes" if gt["publishable_as_the_record"] else "no"})):
        wrong.append(f"publishable_as_the_record={verdict!r}, "
                     f"expected {gt['publishable_as_the_record']}")
    if str(got["first_paired_date"])[:10] != gt["first_paired_date"]:
        wrong.append(f"first_paired_date={got['first_paired_date']!r}, "
                     f"expected {gt['first_paired_date']}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: not publishable as the record; the paired record opens "
              f"on {gt['first_paired_date']}")


tools = []
variables = [
    Variable(
        "calm_decile_pm25",
        None,
        "Store the mean PM2.5 of the calmest tenth of hours as a float in "
        "ug/m3, 2 decimal places. Take the hours that carry both a PM2.5 "
        "reading at the Sha Tin air quality station and a wind speed at the "
        "Sha Tin weather station, code SHA, for that same hour, and "
        "count an hour as calmest-tenth when its wind speed is at or below "
        "the tenth percentile of wind speed over those hours.",
    ),
    Variable(
        "windy_decile_pm25",
        None,
        "Store the mean PM2.5 of the windiest tenth of those same hours as a "
        "float in ug/m3, 2 decimal places — the hours whose wind speed is at "
        "or above the ninetieth percentile of wind speed over those hours.",
    ),
    Variable(
        "paired_hours",
        None,
        "Store the number of hours the two figures above are computed over — "
        "the hours carrying both readings — as an integer.",
    ),
    Variable(
        "publishable_as_the_record",
        None,
        "Store True if the desk can publish the contrast as a property of Sha "
        "Tin's PM2.5 record as a whole — the record's full span — else False.",
    ),
    Variable(
        "first_paired_date",
        None,
        "Store the calendar date of the earliest hour carrying both readings, "
        "as a string in YYYY-MM-DD form.",
    ),
]
validators = {
    "validate_ventilation_contrast": validate_ventilation_contrast,
    "validate_evidence_span": validate_evidence_span,
}
