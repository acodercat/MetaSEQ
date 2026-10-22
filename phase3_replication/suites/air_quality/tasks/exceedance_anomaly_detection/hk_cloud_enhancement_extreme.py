"""More sunlight than the sun sends (exceedance_anomaly_detection).

TRAP since the 2026-09-02 split (baseline before it: the single turn scored
only the retrieval, and the "instrument error" reading lived in the claims).
The second turn now scores the judgement, and the naive path is real —
DeepSeek V4 Flash took it at Gate C the same day, storing True with the
reasoning "the surface can never receive more than arrives at the top of the
atmosphere", which is the textbook misconception the case exists for. Built
as an easy difficulty anchor and reclassified `medium` by Gate B round 7, which is the honest label: the retrieval is a maximum, its date and
a count over one file — one table, no join, no aggregation choice, and easy by
the guide's anchor — but the discriminating part is three CC judgements that
each need radiative interpretation, and the guide defines easy as requiring no
domain knowledge. Labelling it easy described the PV surface and misdescribed
the benchmark. HK's easy anchor is `hk_weather_variable_coverage` alone.

What makes the case worth asking is that the answer is physically startling and
the interpretation is where the work is.

**The finding.** Across 2025 the highest global solar irradiance sampled at
either of Hong Kong's two radiation sites is **1425.0 W/m2**, at King's Park at
13:00 on **2025-08-22**. Exactly **one** reading in the year exceeds the solar
constant of 1361 W/m2, and that is it. The next highest readings are 1334 and
1331, both at Kau Sai Chau.

A surface irradiance above the solar constant is not a measurement error and
not a violation of anything. The solar constant is the flux arriving at the top
of the atmosphere on a surface facing the sun; a ground sensor can briefly
exceed it when the direct beam is unobstructed AND bright cumulus near the sun
scatters additional light onto the same sensor. The effect is well documented
— overirradiance of 1.5 kW/m2 at 59 N (Yordanov et al. 2013, IEEE J.
Photovoltaics 3, 271, doi:10.1109/JPHOTOV.2012.2213581), 1832 W/m2 in the
Ecuadorian Andes (Emck and Richter 2008, J. Appl. Meteorol. Climatol. 47,
3007, doi:10.1175/2008JAMC1865.1), and enhancement ratios of 1.3-1.5 over
clear-sky in one-second radiometry (Gueymard 2017, Solar Energy 153, 755,
doi:10.1016/j.solener.2017.05.004) — and short-lived, which is why this
record catches it at all: these are
instantaneous one-minute samples taken once an hour, not hourly averages, and
an hourly mean would have smoothed a transient of this kind away.

**The file's own manifest forbids the closure check the reading invites.**
`datasets/HK/radiation_1min.sources.json` describes global, direct and diffuse
as three channels of a sampled feed, not as an additive decomposition to be
audited; at this reading direct 841 and diffuse 594 sum to 1435 against a
global of 1425, and the case neither scores nor mentions that sum. A reviewer
looking for a missed opportunity should read the manifest before treating it
as one.

**Convention sweep — three axes, eight combinations, all computed.**
Every one gives
1425.0, 2025-08-22 and 1: the window endpoint changes nothing because no
sampled hour falls at 2026-01-01 00:00, the threshold's open or closed edge
changes nothing because no reading equals 1361 exactly, and restricting to
King's Park changes nothing because the maximum is already there. The axes are
carried so the invariance is measured rather than asserted, which is what a
case with no live convention has to do instead of leaving the section empty.

**Tolerances.** `max_global_radiation_wm2` uses `decimals=1`, deriving
+/-0.06, the precision the source carries. The nearest other reading is 1334.0,
1517 bands out. The date is matched exactly as a string and its near miss is
five days off, 2025-05-24 at Kau Sai Chau. The count is an integer matched
exactly; the next reading down is 91 W/m2 below the threshold, so no
neighbouring value can move it.

Ground truth is recomputed from `datasets/HK/radiation_1min_hko.csv` at
validation time.

**Split 2026-09-02 (query length):** the earlier single turn asked for the
figures and the judgement together; the judgement now has its own turn,
scored as a verdict, with the claims moved to it. The figures' turn keeps
only the deliverable.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable

from domains.hk.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

_SPAN = ("2025-01-01", "2026-01-01")
_SOLAR_CONSTANT_WM2 = 1361.0


def _samples() -> pd.DataFrame:
    """The hourly radiation samples of 2025, both sites."""
    rows = pd.read_csv(
        DATA_DIR / "radiation_1min_hko.csv",
        usecols=["year", "month", "day", "hour", "station",
                 "global_radiation_wm2"],
    )
    rows["datetime"] = pd.to_datetime(rows[["year", "month", "day", "hour"]])
    return rows[(rows["datetime"] >= _SPAN[0]) & (rows["datetime"] < _SPAN[1])]


def _figures() -> Dict[str, object]:
    """The three scored quantities."""
    rows = _samples()
    peak = rows.loc[rows["global_radiation_wm2"].idxmax()]
    return {
        "max_global_radiation_wm2": float(peak["global_radiation_wm2"]),
        "max_global_radiation_date": str(peak["datetime"].date()),
        "hours_above_solar_constant":
            int((rows["global_radiation_wm2"] > _SOLAR_CONSTANT_WM2).sum()),
    }


def validate_peak_irradiance(response: str, runtime, turn: Turn) -> ValidatorResult:
    peak = runtime.retrieve("max_global_radiation_wm2")
    date = runtime.retrieve("max_global_radiation_date")
    if peak is None or date is None:
        missing = [n for n, v in (("max_global_radiation_wm2", peak),
                                  ("max_global_radiation_date", date)) if v is None]
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    if not is_finite_number(peak):
        return ValidatorResult(False, f"max_global_radiation_wm2={peak!r} is not a number")
    gt = _figures()
    wrong = []
    if not reports_as(peak, gt["max_global_radiation_wm2"], decimals=1):
        wrong.append(f"max_global_radiation_wm2={peak}, expected ~{gt['max_global_radiation_wm2']:.1f}")
    if str(date).strip() != gt["max_global_radiation_date"]:
        wrong.append(f"max_global_radiation_date={date!r}, expected {gt['max_global_radiation_date']!r}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(True, f"correct: {peak} W/m2 on {gt['max_global_radiation_date']}")


def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_above_constant(response: str, runtime, turn: Turn) -> ValidatorResult:
    count = runtime.retrieve("hours_above_solar_constant")
    error = runtime.retrieve("above_constant_is_error")
    missing = [n for n, v in (("hours_above_solar_constant", count), ("above_constant_is_error", error)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    if not isinstance(count, int) or isinstance(count, bool):
        return ValidatorResult(False, f"hours_above_solar_constant={count!r} is not an integer")
    gt = _figures()
    wrong = []
    if count != gt["hours_above_solar_constant"]:
        wrong.append(f"hours_above_solar_constant={count}, expected {gt['hours_above_solar_constant']}")
    # A judgement, not a computation: cloud-edge enhancement makes a ground
    # reading above the solar constant physically possible for a moment.
    if not _bool_ok(error, False):
        wrong.append(f"above_constant_is_error={error!r}, expected False")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(True, f"correct: {count} above the solar constant, and not an error")


tools = []
variables = [
    Variable(
        "max_global_radiation_wm2",
        None,
        "Store the highest global solar radiation sampled at either Hong Kong "
        "radiation site during 2025, as a float in W/m2 to 1 decimal place.",
    ),
    Variable(
        "max_global_radiation_date",
        None,
        "Store the calendar date of that sample, as a string 'YYYY-MM-DD' in "
        "Hong Kong local time.",
    ),
    Variable(
        "hours_above_solar_constant",
        None,
        "Store how many sampled readings of 2025 exceed 1361 W/m2, as an "
        "integer.",
    ),
]
variables += [
    Variable("above_constant_is_error", None,
             "Store True if a ground-level reading above the top-of-atmosphere "
             "flux must be an instrument error, else False."),
]


def validate_evidence_and_conclusion_full_review(response: str, runtime, turn: Turn) -> ValidatorResult:
    values = {
        'max_global_radiation_wm2': runtime.retrieve("max_global_radiation_wm2"),
        'max_global_radiation_date': runtime.retrieve("max_global_radiation_date"),
        'hours_above_solar_constant': runtime.retrieve("hours_above_solar_constant"),
        'above_constant_is_error': runtime.retrieve("above_constant_is_error"),
    }
    missing = [name for name, value in values.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    result = validate_peak_irradiance(response, runtime, turn)
    if not result.success:
        return result
    result = validate_above_constant(response, runtime, turn)
    if not result.success:
        return result
    return ValidatorResult(True, "computed evidence and conclusion accepted")

validators = {
    "validate_peak_irradiance": validate_peak_irradiance,
    "validate_above_constant": validate_above_constant,
    'validate_evidence_and_conclusion_full_review': validate_evidence_and_conclusion_full_review,
}
