"""Hong Kong's weekend ozone rise is the weekday NO2 fall wearing a different
name: odd oxygen barely moves, and the background station shows no effect
(temporal_pattern_analysis).

BASELINE, hard, and the science is the exam. On 2025 afternoons (hours
starting 12 to 17) ozone is higher at weekends than on weekdays at
seventeen of the eighteen stations. Pooled over the general stations the
rise is 5.96 ug/m3; over the three roadside stations 3.72. A desk that
reads this as "less traffic, more ozone" and goes on to "cutting NOx will
make ozone worse" has made the inference the case is built to catch.

**The mechanism.** Ozone at a site with fresh NO is set by titration:
NO + O3 -> NO2 consumes ozone MOLECULE FOR MOLECULE and stores it as NO2,
so the conserved quantity is odd oxygen, Ox = O3 + NO2 counted in moles.
Weekend traffic emits less NO, less ozone is titrated, and the ozone gained
matches the NO2 lost mole for mole — while Ox does not move. Gate B round 19
required the arithmetic to follow the chemistry: adding ug/m3 of two gases
with different molar masses (48 against 46) is not a conservation test, so
the scored Ox is the molar sum expressed as NO2-equivalent mass,
(O3/48 + NO2/46) x 46. The record, station by station:

    2025 afternoons, weekend minus weekday
                                 O3       NO2       Ox (molar, as NO2)
    general stations pooled    +5.96    -5.91    -0.20
    roadside stations pooled   +3.72    -4.92    -1.36
    Tap Mun                    -0.18    -0.73    -0.90
                                            (mass sums: +0.05 / -1.21 / -0.91)

Two features carry the judgement. Ox barely moves in the urban groups
against ozone changes of 4-6 ug/m3: the ozone "rise" is redistribution
between O3 and NO2, not additional production. And Tap Mun — the rural
background, NO2 7.7 ug/m3 on weekday afternoons, with no local NO source
that stops for the weekend — shows NO WEEKEND EFFECT THAT THIS YEAR CAN
RESOLVE, which is weaker than saying regional production is equal: the
day-level 95 % interval there is -0.24 +/- 9.33 on ozone. "NOx cuts raise
ozone" is true of the NO-saturated urban core in the narrow sense that less
titration leaves more of the same ozone as O3; this contrast does not
identify what NOx controls would do to regional production, and saying so
is the point.

A third feature is worth a sentence: the largest rises are at new-town
general stations (Tuen Mun +9.3, Yuen Long +8.6), not at the roadside;
Causeway Bay rises 0.6. Its NO is so high that weekend ozone is still fully
titrated — the weekend effect is largest where weekday NO is enough to
titrate and weekend NO is not.

**Turn 1** asks how big the weekend effect on afternoon ozone is and scores
the three O3 differences. **Turn 2** relays the desk's proposed line —
"cutting NOx will make ozone worse" — and scores the NO2 and Ox
differences for the same three groups; the claims carry the reasoning: the
near-constancy of odd oxygen against a 4-6 ug/m3 ozone change identifies
titration; Tap Mun shows no weekend effect this year can resolve, which is
not the same as equal regional production; the line cannot be written, and
what can.

**What is claimed and what is not.** On a naive day-level contrast (each
day's group mean, weekend days against weekday days, 95 % half-widths):

    general    O3 +6.09 +/- 7.78     Ox -0.05 +/- 9.24
    roadside   O3 +3.70 +/- 4.06     Ox -1.37 +/- 8.88
    Tap Mun    O3 -0.24 +/- 9.33     Ox -0.93 +/- 9.44

Only the ROADSIDE ozone difference clears zero on that test; the general
group's day-to-day spread is wider than its own mean effect, and Tap Mun's
figure is a non-result rather than an equality. The case's evidence is
therefore the pooled station-hour contrast together with the internal
consistency of the O3 rise against the NO2 fall — not a significance claim,
and the claims must not be read as one.

**Pins, and where each one goes** (`case_design_standard.md` §3.1).
Afternoon is the hours starting 12:00 to 17:00 (stamps 13:00 to 18:00
under the domain's hour-ending convention); weekend is Saturday and Sunday
by the day the hour starts in; each group's figure pools its station-hours
(mean over station-hours, not mean of station means); Ox is the molar sum
of O3 and NO2 on the same station-hour, both present, reported as
NO2-equivalent mass. All on the variables.

**Readings measured and excluded** (general / roadside / Tap Mun):

    stamps 12-17 read as the hour           O3 +6.02 / +3.72 / +0.50
                                            NO2 -5.43 / -4.45 / -0.85
                                            Ox +0.34 / -0.89 / -0.37
    Ox as the mass sum O3 + NO2             +0.05 / -1.21 / -0.91
    all hours of the day                    O3 +2.44 / +1.39 / +0.28
    mean of station means (general)         O3 +5.95 — 0.01 from pooled;
                                            not separable at two decimals,
                                            which is why pooling is pinned
                                            rather than scored

Every figure uses `reports_as` at two decimals.

**Tap Mun is in the general group, and the query says so.** Asking for "the
general stations together ... and for Tap Mun on its own" reads naturally as
three disjoint groups, and Gate C runs converged on that reading: fourteen
general stations without Tap Mun give O3 +6.34, NO2 -6.23, Ox -0.15. Tap Mun is
a general station in the record, and the group is EPD's general network, so
the background station's own figure is reported beside the group it belongs
to, not carved out of it. Only the ozone variable said "all fifteen, Tap Mun
included"; the query and both turn-2 general variables now say it too, since a
pin that reaches one variable of three binds only that one.

**Overlap, stated.** `hk_roadside_oxidant_titration` scores the Ox
difference between roadside and general stations on one basis; this case
scores the Ox difference between weekend and weekday within each group.
`beijing_weekend_ozone_regime_reversal` is the regime question on the
season axis in a different city; neither has the background-station null
that carries this case's second claim.

All ground truths are recomputed from the database at validation time.

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
from validation import ValidatorResult, is_finite_number, reports_as
from domains.hk.db import read_frame

_AFTERNOON = (12, 17)   # hours the window STARTS in, inclusive
_BACKGROUND = "Tap Mun"


def _hours() -> pd.DataFrame:
    frame = read_frame(text("""
        select h.datetime, s.name_en as station, s.station_type as station_type,
               h.o3, h.no2
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where h.o3 is not null and h.no2 is not null
          and h.datetime > '2025-01-01' and h.datetime <= '2026-01-01'
    """))
    start = frame["datetime"] - pd.Timedelta(hours=1)   # stamps are hour-ending
    frame = frame[(start.dt.hour >= _AFTERNOON[0]) & (start.dt.hour <= _AFTERNOON[1])].copy()
    frame["weekend"] = (start.loc[frame.index].dt.dayofweek >= 5)
    # Odd oxygen is conserved mole for mole, so the sum is molar; it is
    # reported as NO2-equivalent mass. Molar masses in g/mol.
    frame["ox"] = (frame["o3"] / 48.0 + frame["no2"] / 46.0) * 46.0
    return frame


def _figures() -> Dict[str, float]:
    frame = _hours()
    groups = {
        "general": frame[frame["station_type"] == "GENERAL"],
        "roadside": frame[frame["station_type"] == "ROADSIDE"],
        "tap_mun": frame[frame["station"] == _BACKGROUND],
    }
    out = {}
    for name, sub in groups.items():
        for col, key in (("o3", "o3"), ("no2", "no2"), ("ox", "ox")):
            out[f"weekend_{key}_diff_{name}"] = float(
                sub.loc[sub["weekend"], col].mean() - sub.loc[~sub["weekend"], col].mean())
    return out


def _check(got: Dict[str, object]) -> ValidatorResult:
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    for name, val in got.items():
        if not is_finite_number(val):
            errors.append(f"{name}={val!r} is not a number")
        elif not reports_as(val, gt[name], decimals=2):
            errors.append(f"{name}={val}, expected ~{gt[name]:+.2f}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[n]:+.2f}" for n in got))


def validate_weekend_ozone(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "weekend_o3_diff_general": runtime.retrieve("weekend_o3_diff_general"),
        "weekend_o3_diff_roadside": runtime.retrieve("weekend_o3_diff_roadside"),
        "weekend_o3_diff_tap_mun": runtime.retrieve("weekend_o3_diff_tap_mun"),
    })


def validate_no2_and_ox(response: str, runtime, turn: Turn) -> ValidatorResult:
    return _check({
        "weekend_no2_diff_general": runtime.retrieve("weekend_no2_diff_general"),
        "weekend_no2_diff_roadside": runtime.retrieve("weekend_no2_diff_roadside"),
        "weekend_no2_diff_tap_mun": runtime.retrieve("weekend_no2_diff_tap_mun"),
        "weekend_ox_diff_general": runtime.retrieve("weekend_ox_diff_general"),
        "weekend_ox_diff_roadside": runtime.retrieve("weekend_ox_diff_roadside"),
        "weekend_ox_diff_tap_mun": runtime.retrieve("weekend_ox_diff_tap_mun"),
    })




def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_desk_line(response: str, runtime, turn: Turn) -> ValidatorResult:
    val = runtime.retrieve("line_can_be_written")
    if val is None:
        return ValidatorResult(False, "line_can_be_written not set", variables_not_set=True)
    # A judgement, not a computation: the weekend ozone rise is titration
    # released (odd oxygen barely moves, and the background station shows no
    # effect), which says nothing about what an emission cut would do to
    # ozone production.
    if not _bool_ok(val, False):
        return ValidatorResult(False, f"line_can_be_written={val!r}, expected False")
    return ValidatorResult(True, "correct: the line cannot be written")


_COMMON = (
    "Afternoon hours are the hours STARTING at 12:00 through 17:00 — under "
    "the domain's hour-ending stamps, the rows stamped 13:00 through 18:00. "
    "Weekend is Saturday and Sunday by the day the hour starts in. Pool the "
    "group's station-hours (one mean over all of them, not a mean of station "
    "means), and use only hours with both ozone and NO2 present. "
)
tools = []
variables = [
    Variable("weekend_o3_diff_general", None,
             "Store the weekend-minus-weekday mean afternoon ozone across the "
             "general (non-roadside) stations — all fifteen, Tap Mun included — in "
             "2025, as a "
             "float in ug/m3, 2 decimal places. " + _COMMON),
    Variable("weekend_o3_diff_roadside", None,
             "Store the same for the roadside stations, as a float in ug/m3, 2 decimal places."),
    Variable("weekend_o3_diff_tap_mun", None,
             "Store the same for the Tap Mun station alone, as a float in ug/m3, 2 decimal places."),
    Variable("weekend_no2_diff_general", None,
             "Store the weekend-minus-weekday mean afternoon NO2 across the general "
             "(non-roadside) stations — all fifteen, Tap Mun included — in 2025, "
             "built exactly as the ozone figure was, as a float in "
             "ug/m3, 2 decimal places."),
    Variable("weekend_no2_diff_roadside", None,
             "Store the same for the roadside stations, as a float, 2 decimal places."),
    Variable("weekend_no2_diff_tap_mun", None,
             "Store the same for Tap Mun alone, as a float, 2 decimal places."),
    Variable("weekend_ox_diff_general", None,
             "Store the weekend-minus-weekday mean afternoon odd oxygen across the "
             "general (non-roadside) stations — all fifteen, Tap Mun included — in "
             "2025, built the same way, as a "
             "float, 2 decimal places. Odd oxygen is the MOLAR sum of ozone and "
             "NO2 on the same station-hour, reported as NO2-equivalent mass: "
             "(ozone/48 + NO2/46) x 46, with both present."),
    Variable("weekend_ox_diff_roadside", None,
             "Store the same for the roadside stations, as a float, 2 decimal places."),
    Variable("weekend_ox_diff_tap_mun", None,
             "Store the same for Tap Mun alone, as a float, 2 decimal places."),
]
variables += [
    Variable("line_can_be_written", None,
             "Store True if the desk's line — that the weekend ozone rise shows "
             "cutting nitrogen oxide emissions will make Hong Kong's ozone "
             "worse — can be written on this evidence, else False."),
]


def validate_evidence_and_conclusion(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "weekend_no2_diff_general": runtime.retrieve("weekend_no2_diff_general"),
        "weekend_no2_diff_roadside": runtime.retrieve("weekend_no2_diff_roadside"),
        "weekend_no2_diff_tap_mun": runtime.retrieve("weekend_no2_diff_tap_mun"),
        "weekend_ox_diff_general": runtime.retrieve("weekend_ox_diff_general"),
        "weekend_ox_diff_roadside": runtime.retrieve("weekend_ox_diff_roadside"),
        "weekend_ox_diff_tap_mun": runtime.retrieve("weekend_ox_diff_tap_mun"),
        "line_can_be_written": runtime.retrieve("line_can_be_written"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, f"{missing} not set", variables_not_set=True)
    result_0 = validate_no2_and_ox(response, runtime, turn)
    if not result_0.success:
        return result_0
    result_1 = validate_desk_line(response, runtime, turn)
    if not result_1.success:
        return result_1
    return ValidatorResult(True, result_0.message + "; " + result_1.message)

validators = {
    "validate_weekend_ozone": validate_weekend_ozone,
    "validate_no2_and_ox": validate_no2_and_ox,
    "validate_desk_line": validate_desk_line,
    "validate_evidence_and_conclusion": validate_evidence_and_conclusion,
}
