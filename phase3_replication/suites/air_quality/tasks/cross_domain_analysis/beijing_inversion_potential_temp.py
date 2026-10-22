"""Difficulty upgrade — beijing_inversion_potential_temp (2026-10-06).

Dry static stability and shallow inversion structure, rather than two endpoint subtractions.
Professional consequence: Diagnose resistance to vertical dilution without attributing the pollution episode to mixing alone.
Plausible wrong reading: Using the ordinary-temperature gradient in place of the potential-temperature gradient omits the dry-adiabatic reference. An inversion top is not a diagnosed mixing height.

Source concept: https://acp.copernicus.org/articles/20/15585/2020/
The paper supports the concept, not these dataset-specific answers. This case
uses its stated data, time conventions and statistical target; no causal or
surface-emission claim is inferred from a column or conditional association.

Independent raw-data results frozen before authoring the advanced helper:
{
  "inversion_top_hpa": 950,
  "inversion_depth_m": 421.4,
  "strongest_layer_n2_scaled": 7.205008843942812
}

Numerical answers use the decimal places declared on their variables and
reports_as; counts use tolerance zero and finite-number guards. This excludes
adjacent reported answers, not just gross errors. All sample definitions and
units are visible. Author-selected analysis recipes are marked execution in
the scenario, and are not counted as autonomous method discovery.

The earlier module/validator remains for its original outputs; the current
scenario calls the extended validator requiring those and the added evidence.
The pre-upgrade content is archived in .codex-review/difficulty_20261006/before.
"""

from typing import Dict

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

_STATION, _LOWER_HPA, _UPPER_HPA = "Dongsi", 1000.0, 850.0
_WHEN = dict(year=2021, month=2, day=12, hour=8)


def _levels() -> pd.DataFrame:
    prof = pd.read_csv(DATA_DIR / "profile_era5.csv")
    sel = prof[(prof["station"] == _STATION)
               & (prof["year"] == _WHEN["year"])
               & (prof["month"] == _WHEN["month"])
               & (prof["day"] == _WHEN["day"])
               & (prof["hour"] == _WHEN["hour"])]
    return sel


def _diffs() -> Dict[str, float]:
    """Both differences across the layer.

    Raises rather than returning NaN if a level is absent: `profile_df` covers
    selected months only, and a silent NaN would score a correct answer wrong.
    """
    sel = _levels()
    rows = {}
    for level in (_LOWER_HPA, _UPPER_HPA):
        at = sel[sel["pressure_hpa"] == level]
        if at.empty:
            raise LookupError(
                f"profile_era5 has no {level:.0f} hPa row for {_STATION} at "
                f"{_WHEN}; the case's layer cannot be formed")
        rows[level] = at.iloc[0]
    lo, hi = rows[_LOWER_HPA], rows[_UPPER_HPA]
    return {
        "stability_diff_k": float(
            hi["potential_temperature_k"] - lo["potential_temperature_k"]),
        "temperature_diff_c": float(hi["temperature_c"] - lo["temperature_c"]),
    }


def validate_stability_diff_k(response: str, runtime, turn: Turn) -> ValidatorResult:
    theta = runtime.retrieve("stability_diff_k")
    temp = runtime.retrieve("temperature_diff_c")
    for name, val in (("stability_diff_k", theta), ("temperature_diff_c", temp)):
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(val):
            return ValidatorResult(False, f"{name}={val!r} is not a number")

    gt = _diffs()
    wrong = []
    if not reports_as(theta, gt["stability_diff_k"], decimals=1):
        wrong.append(f"stability_diff_k={theta}, "
                     f"expected ~{gt['stability_diff_k']:.1f}")
    if not reports_as(temp, gt["temperature_diff_c"], decimals=1):
        wrong.append(f"temperature_diff_c={temp}, "
                     f"expected ~{gt['temperature_diff_c']:.1f}")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(
        True, f"correct: {theta} K stable, {temp} C over the layer")


tools = []
variables = [
    Variable(
        "stability_diff_k",
        None,
        "Store the POTENTIAL TEMPERATURE at 850 hPa minus that at 1000 hPa, "
        "over Dongsi at 08:00 on 2021-02-12, in kelvin (float, 1 decimal "
        "place).",
    ),
    Variable(
        "temperature_diff_c",
        None,
        "Store the ordinary temperature at 850 hPa minus that at 1000 hPa, at "
        "the same place and hour, in degrees Celsius (float, 1 decimal place).",
    ),
    Variable('inversion_top_hpa', None, 'Store the pressure level at the top of the contiguous temperature inversion beginning at the lowest available pressure-profile height, as an integer in hPa. Use the seven reported levels over Dongsi at 08:00 on 2021-02-12; a connected inversion ends at the first non-increasing temperature step.'),
    Variable('inversion_depth_m', None, 'Store the geopotential-height difference between that inversion top and its lowest available level, in metres to 1 decimal place; use the unrounded profile heights.'),
    Variable('strongest_layer_n2_scaled', None, 'Store the largest adjacent-level dry Brunt-Vaisala frequency squared in that seven-level profile, expressed in units of 10^-4 s^-2 to 2 decimal places. Use geopotential height, midpoint potential temperature for each layer, and standard gravity 9.80665 m/s²; this is a dry diagnostic, not a moist stability calculation.'),
]

# Difficulty upgrade 2026-10-06: older docstring magnitudes describe the
# earlier scoring surface. Added metrics below are recomputed from source data.
# Their single declared decimal report is checked by reports_as; counts are
# exact. The independent raw-data maps were frozen before these helpers.

def _advanced_metrics():
    p = _levels().sort_values("geopotential_height_m")
    if len(p) != 7:
        raise LookupError("The complete seven-level profile is required")
    z = p["geopotential_height_m"].to_numpy()
    temp = p["temperature_c"].to_numpy()
    theta = p["potential_temperature_k"].to_numpy()
    top = 0
    while top < len(p)-1 and temp[top+1] > temp[top]:
        top += 1
    n2 = 9.80665 * (theta[1:]-theta[:-1]) / ((theta[1:]+theta[:-1])/2) / (z[1:]-z[:-1])
    return {"inversion_top_hpa": int(p["pressure_hpa"].iloc[top]),
            "inversion_depth_m": float(z[top]-z[0]),
            "strongest_layer_n2_scaled": float(n2.max()*1e4)}





def validate_harder_turn_1(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "stability_diff_k": runtime.retrieve("stability_diff_k"),
        "temperature_diff_c": runtime.retrieve("temperature_diff_c"),
        "inversion_top_hpa": runtime.retrieve("inversion_top_hpa"),
        "inversion_depth_m": runtime.retrieve("inversion_depth_m"),
        "strongest_layer_n2_scaled": runtime.retrieve("strongest_layer_n2_scaled"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_stability_diff_k(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["inversion_top_hpa"]) or not compare_numeric(got["inversion_top_hpa"], gt["inversion_top_hpa"], tolerance=0):
        errors.append(f"inversion_top_hpa={got["inversion_top_hpa"]!r}, expected {gt["inversion_top_hpa"]!r}")
    if not is_finite_number(got["inversion_depth_m"]) or not reports_as(got["inversion_depth_m"], gt["inversion_depth_m"], decimals=1):
        errors.append(f"inversion_depth_m={got["inversion_depth_m"]!r}, expected {gt["inversion_depth_m"]!r}")
    if not is_finite_number(got["strongest_layer_n2_scaled"]) or not reports_as(got["strongest_layer_n2_scaled"], gt["strongest_layer_n2_scaled"], decimals=2):
        errors.append(f"strongest_layer_n2_scaled={got["strongest_layer_n2_scaled"]!r}, expected {gt["strongest_layer_n2_scaled"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


validators = {
    "validate_stability_diff_k": validate_stability_diff_k,
    "validate_harder_turn_1": validate_harder_turn_1,
}
