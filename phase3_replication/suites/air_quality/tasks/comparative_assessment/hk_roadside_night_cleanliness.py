"""Is the roadside air cleaner at night? — low ozone is not cleanliness
(comparative_assessment).

BASELINE with an unnamed concept at its centre. Fresh NO from traffic
titrates ozone (NO + O3 -> NO2 + O2), so a kerbside site's ozone runs far
below a general site's while its NO2 runs far above, and the sum O3 + NO2
— the oxidant — barely moves. A comparison that reads the roadside's low
ozone as cleanliness has the sign of the answer wrong. Nothing in this case
names titration, oxidant, or Ox: the query asks the plain question a
resident would, and knowing what low kerbside ozone means IS the exam.

The three-layer probes (`docs/v2_measurements.md` §4) show both models hold
the concept in text — pro produces "compare Ox = O3 + NO2" unprompted, flash
gets the direction right without naming Ox — and the corpus's existing
carriers both point at the concept in the query
(`hk_roadside_oxidant_titration` says "oxidant"; `beijing_nocturnal_titration`
hands over the four means that form the pattern). This case removes the
pointer. Prediction, recorded before the first Gate C run: both models pass
the numbers; the claim is where flash is at risk, since its recognition-layer
answer never produced the oxidant frame.

**Gate C reversed that prediction.** Both models stored all four means
exactly. flash's answer names the mechanism unprompted ("ozone is rapidly
scavenged by the nitric oxide emitted in vehicle exhaust") and concludes the
roadside is "actually worse ... not genuinely cleaner" — claim covered, 1.00
from both judges. pro — the model that produces "compare Ox = O3 + NO2"
unprompted in the text probes — wrote "It is cleaner on ozone, but ... more
polluted on nitrogen dioxide": the two figures presented as independent
trade-offs, the shared cause never surfaced, the "cleaner on ozone" reading
left standing. Claim 0.00 from both judges. The layer-3 failure this case
exists for occurred on the model whose layers 1 and 2 are the stronger — a
knowing-doing gap, not a knowledge gap.

Night hours (22:00 through 05:00) of 2025, all stations of each register
class, in the record's ug/m3, measured:

                O3      NO2     O3+NO2
    general    55.0    26.5     81.5
    roadside   40.2    48.6     88.8

By ozone the roadside is "cleaner" by 15; by NO2 it is worse by 22; by the
sum it is worse by 7. The conclusion reverses on exactly the judgement the
concept supplies.

Pins, each measured.

- POOLED STATION-HOURS per class, stated on the variables. There are two
  alternatives, not one, and a verification pass on 2026-09-07 found this
  bullet and the tolerance table below using a single name for both. Forming
  hourly class means first over the station-hours reporting BOTH gases reads
  NO2 47.75/26.25 and Ox 88.75/81.51; doing it over each gas's own reporting
  hours reads NO2 47.73/26.34 and Ox 88.79/81.50. Against the pinned NO2
  48.58/26.54 and Ox 88.75/81.51 the contrast is robust to the choice — the
  roadside stays worse on NO2 and on the sum under both — but the scored means
  differ by up to 0.83, so one reading is named and the band excludes the
  others. The table below sweeps the both-gases variant; the unfiltered one is
  refused by general ozone alone, which reads 55.02 against the scored 54.97,
  1.09 bands out.
- NIGHT is EIGHT HOURS, 22:00 to 05:00 with the 05:00 hour INCLUDED, and the
  query now says so in those words. It first said only "22:00 through 05:00",
  with this line claiming that "half-open days [are] irrelevant since the
  window repeats daily". That was wrong, and it was wrong on a point the line
  shows was considered rather than overlooked: the domain prompt's TIME WINDOWS
  convention makes any named period half-open, not just a period of days, so
  "through 05:00" read against the convention EXCLUDES the 05:00 hour and gives
  seven hours, not eight.

  Measured, that is not a rounding difference. Excluding the hour reads
  39.19 / 55.03 / 50.60 / 27.60 against the pinned 40.17 / 54.97 / 48.58 /
  26.54 — the roadside NO2 figure moves 2.02, forty times the +/-0.05 band.

  It was found by running the case five times per model. Both models split
  between the two readings run to run: flash returned the seven-hour figures
  three times of five and pro twice of five, all ten runs internally
  consistent. A single Gate C run sees one side of that split and, if it lands
  on the pinned side, certifies a window that was never pinned. This case had
  passed Gate A, Gate B and a one-run Gate C in that state.

  The convention itself provides the repair — it applies "unless a question
  says otherwise" — so the query now says otherwise and the ground truth is
  unchanged.
- IN THE RECORD'S UNITS. The sibling oxidant case converts to ppb because
  it compares against banded thresholds; this one compares like with like
  and stays in ug/m3, which the variables state.
- 2025, per TIME WINDOWS.

Tolerance +/-0.05 ug/m3 on each mean: honest rounding at 2 decimals needs
0.005. The nearest foreclosed reading is the hourly-network-means-first one,
and it is worth stating per variable rather than as a single margin, because
the four differ by more than an order of magnitude:

    general O3     54.969 scored, 55.008 hourly-first    0.039  INSIDE the band
    roadside O3    40.169 scored, 40.213 hourly-first    0.044  INSIDE the band
    general NO2    26.536 scored, 26.252 hourly-first    0.284  5.7 bands out
    roadside NO2   48.584 scored, 47.752 hourly-first    0.832  16.6 bands out

All four are scored, so the reading is refused — but it is refused by the two
NO2 figures alone, and the ozone pair would accept it. (This paragraph claimed
the alternative sat "at least 3.8 bands out on the closest variable, general
O3" until a Gate A review on 2026-09-06 measured it; on that variable it is
inside.)

Adjacent cases, for Gate B to weigh: `hk_roadside_oxidant_titration` is the
same physics, named, paired stations, in ppb, scored on differences;
`hk_roadside_index_compression` turn 1 scores the roadside/general NO2 ratio
over six years. This case's distinct measurement is the unnamed application;
if Gate B judges the corpus needs only one roadside/general comparison, this
one's docstring records which question each answers.

All ground truths are recomputed here from the database.

**Split 2026-09-02 (query length):** the earlier single turn asked for the
figures and the judgement together; the judgement now has its own turn,
scored as a verdict, with the claims moved to it. The figures' turn keeps
only the deliverable.

**Gate B round 21 (2026-09-03):** `roadside_night_cleaner` had no stated
criterion, and with ozone lower and NO2 higher at the kerb no verdict follows
from the two figures without one. The variable now names it — lower in both
of the pollutants compared — which is a definition of the word, not a method.
The reviewer's alternative, keeping only `lower_ozone_means_cleaner`, was not
taken: the resident asked whether the air is cleaner, and a turn that scores
only the ozone judgement cannot tell a response that answers them from one
that talks past them.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable
from sqlalchemy import text

from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from domains.hk.db import read_frame

_SPAN = ("2025-01-01", "2026-01-01")
_NIGHT_START, _NIGHT_END = 22, 5   # 22:00 through 05:00, inclusive


def _class_means() -> Dict[str, float]:
    frame = read_frame(text("""
        select s.station_type, h.o3, h.no2
        from hourly_station_air_quality h
        join air_quality_station s on s.id = h.station_id
        where h.datetime > :lo and h.datetime <= :hi
          and (extract(hour from h.datetime) >= :ns
               or extract(hour from h.datetime) <= :ne)
    """), {"lo": _SPAN[0], "hi": _SPAN[1],
                          "ns": _NIGHT_START, "ne": _NIGHT_END})
    by = frame.groupby("station_type")[["o3", "no2"]].mean()
    return {
        "roadside_night_o3": float(by.loc["ROADSIDE", "o3"]),
        "general_night_o3": float(by.loc["GENERAL", "o3"]),
        "roadside_night_no2": float(by.loc["ROADSIDE", "no2"]),
        "general_night_no2": float(by.loc["GENERAL", "no2"]),
    }


_NAMES = ("roadside_night_o3", "general_night_o3",
          "roadside_night_no2", "general_night_no2")


def validate_night_means(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "roadside_night_o3": runtime.retrieve("roadside_night_o3"),
        "general_night_o3": runtime.retrieve("general_night_o3"),
        "roadside_night_no2": runtime.retrieve("roadside_night_no2"),
        "general_night_no2": runtime.retrieve("general_night_no2"),
    }
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set",
                               variables_not_set=True)
    for name, val in got.items():
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")

    gt = _class_means()
    wrong = [f"{name}={got[name]}, expected ~{gt[name]:.2f}"
             for name in _NAMES
             if not reports_as(got[name], gt[name], decimals=2)]
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, "correct: roadside O3 "
              f"{gt['roadside_night_o3']:.2f} vs general {gt['general_night_o3']:.2f}; "
              f"NO2 {gt['roadside_night_no2']:.2f} vs {gt['general_night_no2']:.2f}")




def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_night_verdict(response: str, runtime, turn: Turn) -> ValidatorResult:
    cleaner = runtime.retrieve("roadside_night_cleaner")
    lower_ozone = runtime.retrieve("lower_ozone_means_cleaner")
    missing = [n for n, v in (("roadside_night_cleaner", cleaner), ("lower_ozone_means_cleaner", lower_ozone)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _class_means()
    # Cleaner only if the roadside carries less of BOTH, which the variable
    # states, because the two pollutants move in opposite directions and no
    # unweighted verdict follows from that without a rule. Gate B round 21
    # raised the missing rule; the alternative it suggested — dropping the
    # bool and keeping only the ozone judgement — would have left the turn
    # unable to distinguish a response that answers the resident's actual
    # question from one that ducks it.
    expected_cleaner = bool(gt["roadside_night_no2"] < gt["general_night_no2"]
                            and gt["roadside_night_o3"] < gt["general_night_o3"])
    errors = []
    if not _bool_ok(cleaner, expected_cleaner):
        errors.append(f"roadside_night_cleaner={cleaner!r}, expected {expected_cleaner}")
    if not _bool_ok(lower_ozone, False):
        errors.append(f"lower_ozone_means_cleaner={lower_ozone!r}, expected False")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: not cleaner, and lower ozone is not cleanliness")


tools = []
variables = [
    Variable(
        "roadside_night_o3",
        None,
        "Store the mean night-time ozone across the roadside stations over "
        "2025 as a float in ug/m3, 2 decimal places — every qualifying "
        "station-hour of the class pooled with equal weight, not station or "
        "hourly means averaged afterwards. Night is the eight hours stamped "
        "22:00 to 05:00, the 05:00 hour included.",
    ),
    Variable(
        "general_night_o3",
        None,
        "Store the same for the general stations, on the same pooling, as a "
        "float in ug/m3, 2 decimal places.",
    ),
    Variable(
        "roadside_night_no2",
        None,
        "Store the mean night-time nitrogen dioxide across the roadside "
        "stations on the same pooling, as a float in ug/m3, 2 decimal places.",
    ),
    Variable(
        "general_night_no2",
        None,
        "Store the same for the general stations, as a float in ug/m3, "
        "2 decimal places.",
    ),
]
variables += [
    Variable("roadside_night_cleaner", None,
             "Store True if the roadside air at night is cleaner than the rest "
             "of the city's on the two pollutants you compared — lower in both "
             "— else False."),
    Variable("lower_ozone_means_cleaner", None,
             "Store True if the roadside's lower night-time ozone is evidence of "
             "cleaner air, else False."),
]


def validate_evidence_and_conclusion_full_review(response: str, runtime, turn: Turn) -> ValidatorResult:
    values = {
        'roadside_night_o3': runtime.retrieve("roadside_night_o3"),
        'general_night_o3': runtime.retrieve("general_night_o3"),
        'roadside_night_no2': runtime.retrieve("roadside_night_no2"),
        'general_night_no2': runtime.retrieve("general_night_no2"),
        'roadside_night_cleaner': runtime.retrieve("roadside_night_cleaner"),
        'lower_ozone_means_cleaner': runtime.retrieve("lower_ozone_means_cleaner"),
    }
    missing = [name for name, value in values.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    result = validate_night_means(response, runtime, turn)
    if not result.success:
        return result
    result = validate_night_verdict(response, runtime, turn)
    if not result.success:
        return result
    return ValidatorResult(True, "computed evidence and conclusion accepted")

validators = {
    "validate_night_means": validate_night_means,
    "validate_night_verdict": validate_night_verdict,
    'validate_evidence_and_conclusion_full_review': validate_evidence_and_conclusion_full_review,
}
