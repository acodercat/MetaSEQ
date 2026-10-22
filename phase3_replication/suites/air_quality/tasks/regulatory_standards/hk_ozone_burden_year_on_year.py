"""Ozone rose; the ozone health-risk column fell (regulatory_standards).

BASELINE, with the diagnostic weight in CC. Nothing here says coefficient,
revision, method change or seam: turn 1 asks for a year-on-year comparison a
desk would ask for, turn 2 asks for a specific check, and reading the figures that
check returns — the same ozone level carrying a different added risk at the
two ends of 2025, and not of 2024 — IS the exam.

**The condition in the record.** `hourly_station_air_quality.o3_ar` is the
ozone term of the AQHI, an added health risk computed from the concentration.
On 22 March 2025 EPD revised the AQHI's ozone risk factor and only that one
(https://www.aqhi.gov.hk/en/what-is-aqhi/faqs.html); the repository applied
the revision to the stored column from that date, so the record carries the old
mapping before it and the new one after (`scripts/ingest/fix_hk_o3_coefficient
.py`, `datasets/EXTERNAL_DATA_SOURCES.md`). Nothing on the agent's surface says
so. The prompt describes `o3_ar` as an added-risk value and no more.

Over every station-hour of 2024 and 2025 carrying both an ozone concentration
and an ozone added-risk value, pooled:

                       2024      2025     change
    ozone, ug/m3     54.3337   55.0473    +1.31 %
    ozone added risk  2.8399    2.7794    -2.13 %

Concentration rose; the risk column fell. An added-risk index is an increasing
function of concentration, so those two lines cannot both be about one mapping.
Converting the post-revision rows back onto the earlier basis gives 2.8756 for
2025 — +1.26 %, in step with concentration. **The fall is the revision, not the
air.** A desk that publishes "ozone health risk fell 2 % in 2025" has reported
a change in the index's arithmetic as an improvement in public health, with the
sign reversed.

**Why the check in turn 2 is the one asked for, and why the seam date is
not scored.** The first draft of this docstring said the seam could not be
located at daily resolution. That was false, and Gate B round 12 showed how:
`o3_ar` is built on a THREE-HOUR ROLLING concentration, and reverse-solving the
risk factor against that input rather than the instantaneous value puts the
daily median at 0.0005116312 on 21 March and 0.0004888025 on 22 March — the
two published factors to seven digits, and a step on exactly the revision day.
A search against the instantaneous concentration is noisy and returns dates
before 22 March as readily as after; that was the author's search, not a
property of the record. The date is still not scored, for a different reason:
neither the formula nor the rolling construction is on the agent's surface, so
requiring that reconstruction would set a hidden premise. What the record
shows WITHOUT the formula is whether the same concentration band carries the
same added risk at the two ends of a year — an inconsistency check, not an
identification (see the limit stated below) — and turn 2 asks for that, with
the level and the months stated:

    hours with ozone in [80, 100) ug/m3      Jan-Feb    Oct-Dec    ratio
    2024                                     4.5856     4.6035     1.004
    2025                                     4.6078     4.3577     0.946

At a fixed ozone level the column reads 5.4 % lower at the end of 2025 than at
the start, and reads the same at both ends of 2024. Two daily means could not
separate a method change from a change in the air; four figures at a held
concentration can, and the control year is what makes the separation clean. The
query directs the check but does not say what it will find — in 2024 it finds
nothing.

**Why [80, 100) and not a lower band.** Because of that three-hour window, the
risk at an instantaneous level drifts slightly with season even under one
mapping: at [40, 50) the 2024 control moves 3.5 % between the two ends of the
year, at [60, 70) 1.7 %, at [80, 100) 0.4 %. The high band is the one where the
control is flat enough that a 5.4 % change reads as a change.

**The composition reading, and the pin Gate C added to close it.** The first
live runs — five real responses across two models, all eight figures exact —
each observed that only late 2025 departs from 4.6 and each then offered a
reason the surface left open: a shift in the mix of exact concentrations within
the band, a different set of stations or hours, the three-hour rolling mean
behind the column, or season. Season and the rolling mean are answered by the
2024 control, which sits under both and does not move. Composition was NOT
answered by anything scored, so it was a defensible reading, and under §6 a
defensible wrong reading is a missing pin. Measured, it cannot carry the change:

    cell          hours   mean ozone in band   stations reporting
    2024 Jan-Feb  2,880       89.46                 18
    2024 Oct-Dec  6,630       89.28                 18
    2025 Jan-Feb  4,769       89.54                 18
    2025 Oct-Dec  5,627       89.19                 18

The within-band mean moves 0.35 ug/m3 across the four cells, and every station
is present in every cell. Under a fixed mapping 0.35 ug/m3 near 90 ug/m3 is
worth about 0.019 added-risk points, 0.4 % of 4.6; the observed change is
5.4 %. A revision after round 12 scored the four within-band concentration means
beside the four risk means, so that a shift in WHICH concentrations the band
held could be checked from scored figures; the 2026-09-02 surface rebuild
replaced that turn and the eight band figures are now computed in `_figures()`
and read by nothing. What checks the shift today is the claim, which requires
the response to establish the inconsistency itself. That is as far as it goes, and round 12 was right to
insist on the limit: four equal means do not hold fixed the distribution inside
the band, the three-hour history behind each row, or the station weights — the
per-station counts run from 71 to 557 across the cells — so the check narrows
the reading, it does not close it.

**What the record supports, and what the claims may therefore ask for.** The
twelve figures establish an internal inconsistency: an increasing index that
fell while its input rose, and the same concentration carrying 5 % less risk
in one cell of four. They do not establish that the column's DEFINITION changed
— Jensen's inequality alone allows a mean of a convex transform to move against
the mean of its input, and the lag history is not held fixed. Round 12 ruled
the first version of the claims unreachable for demanding that identification,
and eight of eight live responses stopping short of it is consistent with the
ruling. The claims now ask for what a careful analyst does with an
inconsistency: hold the annual added-risk comparison until the series' basis is
verified, and do not publish the fall as a health trend. A response may
hypothesise a method or factor change; it is not required to, and it is not
failed for declining to name a cause it cannot see.

**Pins, and where each one goes** (`case_design_standard.md` §3.1). The row
population — station-hours carrying BOTH values — is pinned on the turn-1
variables because it moves the 2024 concentration mean by 0.036: the
ozone-only population reads 54.3691. POOLED station-hours are pinned there too,
and — a correction round 12 forced — that pin is NOT measured-equivalent to the
domain's TERRITORY reading at the requested precision: hour-first reads 54.35 /
55.04 and station-first 54.34 / 55.04 against the pooled 54.33 / 55.05, and
under the +/-0.02 band this case first carried both complete assignments
passed. The scored figures then used the repository's two-decimal contract,
+/-0.006, which refused both. After the reliability_tool study (2026-10-12) the
band is +/-0.01: at +/-0.006 the 2025 concentration turned on whether the year
is the rows stamped after 1 January up to and including the next 1 January
(55.0447) or the rows stamped within the calendar year (55.0473) — one row's
difference, a convention the variables do not test, on which 17 otherwise
correct turns across two models failed. +/-0.01 still refuses the ozone-only
row population (54.3691) and hour-first (54.3473); it admits station-first
(54.3346, 55.0418), which no run took. The level band and the two sets of
months are stated in the query
because they are the framing of the check, not the exam; the four edge
conventions differ by up to 0.007 and are separated on at least one figure.
The years are stated because the comparison is the question.

**Readings measured and excluded.**

    ozone-only row population, 2024 concentration     54.3691   (pinned 54.3337)
    the 2025 added-risk change reported as a trend     -2.13 %   (the claim, not PV)

Every scored figure uses the +/-0.01 band. The case does not rest on
an arithmetic trap, and says so — its weight is in what the twelve figures are
read to mean.

**What is NOT claimed, and what the claims may not demand.** That the agent
know the revision, its date, or either coefficient — none is on its surface. A
response that reports the fixed-level result and reads it as an inconsistency
in the added-risk series that the annual comparison cannot be published across
has done what the record supports; one that goes on to say a method or
coefficient change is a possible cause has drawn a reasonable inference and is
not penalised for it, nor for its absence; one that asserts the date or the
factor as fact has claimed something it cannot have seen, but the claims do not
fail it for that alone. What they do fail is the draft: reporting the annual
added-risk fall as ozone becoming less of a health burden, when the
concentration rose and the fixed-level check leaves the series' basis
unverified.

**Overlap, stated.** `hk_roadside_index_compression` scores added-risk ratios
pooled over 2020-2025 and names the revision in its docstring as the known
reason its ozone term recomputes on 99.54 % of rows rather than 100; it does
not split the years. `hk_aqhi_not_reproducible` is about the published index
against the stored components. Neither compares the column across the seam.

All ground truths are recomputed from the database at validation time.

**Turn 2 rebuilt 2026-09-01 on the surface rule.** The query no longer names
the fixed-ozone-band check; it asks whether the two years' added-risk figures
can be compared. PV scores the verdict (the draft cannot go out) and whether
the stored added risk for a given ozone level reads differently at the end of
2025 from the start (it does — the coefficient changed on 2025-03-22).
`_mapping_verdicts()` checks three concentration bands (60-80, 80-100,
100-120 ug/m3) and refuses to score unless all three agree; the 80-100 band
figures remain above as the reference route.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number
from domains.hk.db import read_frame

_YEARS = (2024, 2025)
_BAND_LO, _BAND_HI = 80.0, 100.0        # ozone, ug/m3: at or above, below
_EARLY, _LATE = (1, 2), (10, 11, 12)    # calendar months


def _frame() -> pd.DataFrame:
    """Every 2024-2025 station-hour carrying both an ozone concentration and an
    ozone added-risk value, pooled across stations."""
    frame = read_frame(text("""
        select datetime, o3, o3_ar
        from hourly_station_air_quality
        where datetime > '2024-01-01' and datetime <= '2026-01-01'
          and o3 is not null and o3_ar is not null
    """))
    hour_start = frame["datetime"] - pd.Timedelta(hours=1)  # stamps are hour-ending
    frame["year"] = hour_start.dt.year
    frame["month"] = hour_start.dt.month
    return frame


def _figures() -> Dict[str, float]:
    frame = _frame()
    out = {}
    for year in _YEARS:
        sub = frame[frame["year"] == year]
        out[f"o3_mean_{year}"] = float(sub["o3"].mean())
        out[f"o3_added_risk_mean_{year}"] = float(sub["o3_ar"].mean())
        band = sub[(sub["o3"] >= _BAND_LO) & (sub["o3"] < _BAND_HI)]
        early = band[band["month"].isin(_EARLY)]
        late = band[band["month"].isin(_LATE)]
        out[f"band_added_risk_{year}_early"] = float(early["o3_ar"].mean())
        out[f"band_added_risk_{year}_late"] = float(late["o3_ar"].mean())
        # The mean concentration WITHIN the band, per cell: the pin that closes
        # the composition reading (see docstring). Same rows as the risk means.
        out[f"band_o3_mean_{year}_early"] = float(early["o3"].mean())
        out[f"band_o3_mean_{year}_late"] = float(late["o3"].mean())
    return out


def _check(runtime, names) -> ValidatorResult:
    got = {name: runtime.retrieve(name) for name in names}
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)
    for name, val in got.items():
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")
    gt = _figures()
    # +/-0.01 (docstring, "Pins"): wider than the two-decimal report, which made
    # the year's boundary row decisive; narrower than the +/-0.02 that admitted
    # the hour-first aggregation (54.3473 against the pooled 54.3328).
    wrong = [f"{name}={got[name]}, expected ~{gt[name]:.2f}"
             for name in names
             if not compare_numeric(got[name], gt[name], tolerance=0.01)]
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, "correct: " + ", ".join(f"{n} {gt[n]:.2f}" for n in names))


def validate_annual_means(response: str, runtime, turn: Turn) -> ValidatorResult:
    names = ("o3_mean_2024", "o3_mean_2025",
             "o3_added_risk_mean_2024", "o3_added_risk_mean_2025")
    return _check(runtime, names)




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


def _mapping_verdicts() -> Dict[str, object]:
    """Whether the stored added risk reads the same for a given ozone level
    across 2025, checked in three concentration bands so the answer does not
    depend on which band an analyst picks."""
    frame = read_frame(text("""
        select datetime, o3, o3_ar from hourly_station_air_quality
        where o3 is not null and o3_ar is not null
          and datetime > '2025-01-01' and datetime <= '2026-01-01'
    """))
    month = (frame["datetime"] - pd.Timedelta(hours=1)).dt.month
    changed = set()
    for lo, hi in ((60, 80), (80, 100), (100, 120)):
        band = frame[(frame["o3"] >= lo) & (frame["o3"] < hi)]
        early = band[month[band.index] <= 2]["o3_ar"].mean()
        late = band[month[band.index] >= 10]["o3_ar"].mean()
        changed.add(bool(abs(early - late) / early > 0.02))
    if len(changed) != 1:
        raise RuntimeError("the mapping-change verdict is not invariant across bands")
    return {"draft_can_go_out": False, "added_risk_mapping_changed_within_2025": changed.pop()}


def validate_draft(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "draft_can_go_out": runtime.retrieve("draft_can_go_out"),
        "added_risk_mapping_changed_within_2025": runtime.retrieve("added_risk_mapping_changed_within_2025"),
    }
    return _verdict_check(got, _mapping_verdicts())

tools = []
variables = [
    Variable(
        "o3_mean_2024",
        None,
        "Store the mean ozone concentration over 2024 as a float in ug/m3, "
        "2 decimal places: every station-hour of the year that carries both an "
        "ozone concentration and an ozone added-risk value, pooled across all "
        "stations with equal weight.",
    ),
    Variable(
        "o3_mean_2025",
        None,
        "Store the same for 2025, as a float in ug/m3, 2 decimal places.",
    ),
    Variable(
        "o3_added_risk_mean_2024",
        None,
        "Store the mean ozone added-risk value over those same 2024 "
        "station-hours, as a float in the units the column stores, 2 decimal "
        "places.",
    ),
    Variable(
        "o3_added_risk_mean_2025",
        None,
        "Store the same for 2025, as a float, 2 decimal places.",
    ),
    Variable("draft_can_go_out", None,
             "Store True if the desk's line that the ozone health risk fell in "
             "2025 can go out as it stands, else False."),
    Variable("added_risk_mapping_changed_within_2025", None,
             "Store True if the stored ozone added-risk value for a given ozone "
             "concentration reads differently at the end of 2025 from the start, "
             "else False."),
]


def validate_evidence_and_conclusion_full_review(response: str, runtime, turn: Turn) -> ValidatorResult:
    values = {
        'o3_mean_2024': runtime.retrieve("o3_mean_2024"),
        'o3_mean_2025': runtime.retrieve("o3_mean_2025"),
        'o3_added_risk_mean_2024': runtime.retrieve("o3_added_risk_mean_2024"),
        'o3_added_risk_mean_2025': runtime.retrieve("o3_added_risk_mean_2025"),
        'draft_can_go_out': runtime.retrieve("draft_can_go_out"),
        'added_risk_mapping_changed_within_2025': runtime.retrieve("added_risk_mapping_changed_within_2025"),
    }
    missing = [name for name, value in values.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    result = validate_annual_means(response, runtime, turn)
    if not result.success:
        return result
    result = validate_draft(response, runtime, turn)
    if not result.success:
        return result
    return ValidatorResult(True, "computed evidence and conclusion accepted")

validators = {
    "validate_annual_means": validate_annual_means,
    "validate_draft": validate_draft,
    'validate_evidence_and_conclusion_full_review': validate_evidence_and_conclusion_full_review,
}
