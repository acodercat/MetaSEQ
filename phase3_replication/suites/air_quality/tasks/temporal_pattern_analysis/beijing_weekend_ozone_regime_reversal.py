"""Difficulty upgrade — beijing_weekend_ozone_regime_reversal (2026-10-06).

Quantified weekend reversal plus a molar oxidant-budget diagnostic.
Professional consequence: Assess whether a weekend contrast supports claims about precursor interventions.
Plausible wrong reading: Adding mass concentrations without molecular-weight conversion is not a molar Ox budget. A change in Ox does not isolate ozone production or NOx sensitivity.

Source concept: https://www.londonair.org.uk/london/reports/clapp_and%20_jenkin_O3_NOX.pdf
The paper supports the concept, not these dataset-specific answers. This case
uses its stated data, time conventions and statistical target; no causal or
surface-emission claim is inferred from a column or conditional association.

Independent raw-data results frozen before authoring the advanced helper:
{
  "weekend_o3_early_difference": 6.6272306094044025,
  "weekend_o3_late_difference": -10.661425009933913,
  "weekend_ox_late_difference": -12.214263353413289,
  "weekend_ox_late_hours": 40565
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

import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as
from tasks import Turn

_MONTHS = (5, 9)
_HOURS = (10, 17)
_EARLY = (2020, 2021, 2022)
_LATE = (2023, 2024, 2025)
_CELL = ["year", "month", "station", "hour"]
POSITIVE = "positive"
NEGATIVE = "negative"


def _window() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "air_quality.csv")
    df = df[
        df["month"].between(*_MONTHS)
        & df["hour"].between(*_HOURS)
        & df["year"].isin(_EARLY + _LATE)
    ].copy()
    # Labels 10-17 close hours that lie wholly inside their own date, so the
    # label date is the day the hour belongs to and needs no shift.
    weekday = pd.to_datetime(df[["year", "month", "day"]]).dt.dayofweek
    df["weekend"] = weekday >= 5
    return df


def _effect(df: pd.DataFrame, pollutant: str) -> float:
    """Weekend minus weekday inside each cell, then the unweighted mean."""
    cells = (
        df.dropna(subset=[pollutant])
        .groupby(_CELL + ["weekend"])[pollutant]
        .mean()
        .unstack("weekend")
    )
    return float((cells[True] - cells[False]).dropna().mean())


def _raw_effect(df: pd.DataFrame, pollutant: str) -> float:
    """Weekend minus weekday over pooled station-hours — the other weighting."""
    rows = df.dropna(subset=[pollutant])
    return float(rows[rows["weekend"]][pollutant].mean() - rows[~rows["weekend"]][pollutant].mean())


def _effects() -> dict:
    """Signs asserted invariant across the cell weighting the earlier version
    pinned and pooled station-hours (+6.6/+6.1 early, -10.7/-10.7 late,
    -1.8/-2.0 pooled, -2.0/-2.0 NO2)."""
    df = _window()
    early, late = df[df["year"].isin(_EARLY)], df[df["year"].isin(_LATE)]
    quantities = {"o3_early": (early, "O3"), "o3_late": (late, "O3"),
                  "o3_pooled": (df, "O3"), "no2_late": (late, "NO2")}
    out = {}
    for key, (frame, pollutant) in quantities.items():
        signs = {POSITIVE if v > 0 else NEGATIVE for v in (_effect(frame, pollutant), _raw_effect(frame, pollutant))}
        if len(signs) != 1:
            raise RuntimeError(f"the sign of {key} is not invariant across weightings")
        out[key] = signs.pop()
    # The pooled figure (-1.8 cell-weighted, -2.0 pooled station-hours) is
    # smaller in size than every individual year's effect (the smallest is
    # 3.6 / 3.4 in 2021) under both weightings; asserted, not assumed.
    smaller = set()
    for f, pooled in ((_effect, _effect(df, "O3")), (_raw_effect, _raw_effect(df, "O3"))):
        yearly = [f(df[df["year"] == y], "O3") for y in _EARLY + _LATE]
        smaller.add(bool(abs(pooled) < min(abs(v) for v in yearly)))
    if len(smaller) != 1:
        raise RuntimeError("whether the pooled effect is smaller than every year's is not invariant")
    out["pooled_smaller_than_every_year"] = smaller.pop()
    return out


def _check_signs(got: dict, names: dict) -> ValidatorResult:
    missing = [n for n, v in got.items() if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _effects()
    errors = []
    for name, key in names.items():
        expected = gt[key]
        if isinstance(expected, bool):
            ok = (isinstance(got[name], bool) and got[name] == expected) or (
                isinstance(got[name], str) and got[name].strip().lower() in
                {str(expected).lower(), "yes" if expected else "no"})
        else:
            ok = str(got[name]).strip().lower() == expected
        if not ok:
            errors.append(f"{name}={got[name]!r}, expected {expected!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: " + ", ".join(f"{n}={gt[k]!r}" for n, k in names.items()))


def validate_era_effects(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "weekend_o3_sign_2020_2022": runtime.retrieve("weekend_o3_sign_2020_2022"),
        "weekend_o3_sign_2023_2025": runtime.retrieve("weekend_o3_sign_2023_2025"),
    }
    return _check_signs(got, {"weekend_o3_sign_2020_2022": "o3_early",
                              "weekend_o3_sign_2023_2025": "o3_late"})


def validate_pooled_and_no2(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "weekend_o3_sign_pooled": runtime.retrieve("weekend_o3_sign_pooled"),
        "pooled_smaller_than_every_year": runtime.retrieve("pooled_smaller_than_every_year"),
        "weekend_no2_sign_2023_2025": runtime.retrieve("weekend_no2_sign_2023_2025"),
    }
    return _check_signs(got, {"weekend_o3_sign_pooled": "o3_pooled",
                              "pooled_smaller_than_every_year": "pooled_smaller_than_every_year",
                              "weekend_no2_sign_2023_2025": "no2_late"})


tools = []
_DEFINITION = (
    "The summer afternoon weekend ozone effect is the weekend-minus-weekday "
    "contrast in ozone over May to September, for the eight hours stamped "
    "10:00 to 17:00, both included, Saturday and Sunday counting as the "
    "weekend. "
)
variables = [
    Variable("weekend_o3_sign_2020_2022", None,
             "Store the sign of the 2020-2022 summer afternoon weekend ozone "
             "effect, as one of exactly these strings: 'positive', 'negative'. "
             + _DEFINITION),
    Variable("weekend_o3_sign_2023_2025", None,
             "Store the sign of the 2023-2025 effect, as 'positive' or 'negative'."),
    Variable("weekend_o3_sign_pooled", None,
             "Store the sign of the effect over 2020 to 2025 together, as "
             "'positive' or 'negative'."),
    Variable("pooled_smaller_than_every_year", None,
             "Store True if the all-years figure is smaller in size than the "
             "weekend ozone effect of every individual year in the record, else "
             "False."),
    Variable("weekend_no2_sign_2023_2025", None,
             "Store the sign of the same contrast for nitrogen dioxide over "
             "2023-2025, as 'positive' or 'negative'."),
    Variable('weekend_o3_early_difference', None, 'Store the 2020-2022 weekend-minus-weekday O3 difference in µg/m³ to 2 decimal places. Use May-September and the eight timestamps with hour labels 10,11,12,13,14,15,16,17; first contrast weekends and weekdays within each year-month-station-hour cell, then weight eligible cells equally.'),
    Variable('weekend_o3_late_difference', None, 'Store the corresponding 2023-2025 O3 contrast under the same cell weighting, in µg/m³ to 2 decimal places.'),
    Variable('weekend_ox_late_difference', None, 'Store the 2023-2025 weekend-minus-weekday molar odd-oxygen contrast under that same cell weighting, expressed as NO2-equivalent µg/m³ to 2 decimal places. Use contemporaneous O3/NO2 pairs and molar masses 48 and 46 g/mol; compute from unrounded concentrations.'),
    Variable('weekend_ox_late_hours', None, 'Store the exact integer number of 2023-2025 station-hours in the stated summer-afternoon cohort reporting both O3 and NO2 before calculating eligible cell contrasts.'),
]

# Difficulty upgrade 2026-10-06: older docstring magnitudes describe the
# earlier scoring surface. Added metrics below are recomputed from source data.
# Their single declared decimal report is checked by reports_as; counts are
# exact. The independent raw-data maps were frozen before these helpers.

def _advanced_metrics():
    frame = _window()
    paired = frame.dropna(subset=["O3", "NO2"]).copy()
    paired["ox"] = paired["O3"]*46.0/48.0+paired["NO2"]
    late = paired[paired["year"].isin(_LATE)]
    return {"weekend_o3_early_difference": _effect(frame[frame["year"].isin(_EARLY)], "O3"),
            "weekend_o3_late_difference": _effect(frame[frame["year"].isin(_LATE)], "O3"),
            "weekend_ox_late_difference": _effect(late, "ox"),
            "weekend_ox_late_hours": len(late)}






def validate_harder_turn_1(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "weekend_o3_sign_2020_2022": runtime.retrieve("weekend_o3_sign_2020_2022"),
        "weekend_o3_sign_2023_2025": runtime.retrieve("weekend_o3_sign_2023_2025"),
        "weekend_o3_early_difference": runtime.retrieve("weekend_o3_early_difference"),
        "weekend_o3_late_difference": runtime.retrieve("weekend_o3_late_difference"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_era_effects(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["weekend_o3_early_difference"]) or not reports_as(got["weekend_o3_early_difference"], gt["weekend_o3_early_difference"], decimals=2):
        errors.append(f"weekend_o3_early_difference={got["weekend_o3_early_difference"]!r}, expected {gt["weekend_o3_early_difference"]!r}")
    if not is_finite_number(got["weekend_o3_late_difference"]) or not reports_as(got["weekend_o3_late_difference"], gt["weekend_o3_late_difference"], decimals=2):
        errors.append(f"weekend_o3_late_difference={got["weekend_o3_late_difference"]!r}, expected {gt["weekend_o3_late_difference"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


def validate_harder_turn_2(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "weekend_o3_sign_pooled": runtime.retrieve("weekend_o3_sign_pooled"),
        "pooled_smaller_than_every_year": runtime.retrieve("pooled_smaller_than_every_year"),
        "weekend_no2_sign_2023_2025": runtime.retrieve("weekend_no2_sign_2023_2025"),
        "weekend_ox_late_difference": runtime.retrieve("weekend_ox_late_difference"),
        "weekend_ox_late_hours": runtime.retrieve("weekend_ox_late_hours"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_pooled_and_no2(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["weekend_ox_late_difference"]) or not reports_as(got["weekend_ox_late_difference"], gt["weekend_ox_late_difference"], decimals=2):
        errors.append(f"weekend_ox_late_difference={got["weekend_ox_late_difference"]!r}, expected {gt["weekend_ox_late_difference"]!r}")
    if not is_finite_number(got["weekend_ox_late_hours"]) or not compare_numeric(got["weekend_ox_late_hours"], gt["weekend_ox_late_hours"], tolerance=0):
        errors.append(f"weekend_ox_late_hours={got["weekend_ox_late_hours"]!r}, expected {gt["weekend_ox_late_hours"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


validators = {
    "validate_era_effects": validate_era_effects,
    "validate_pooled_and_no2": validate_pooled_and_no2,
    "validate_harder_turn_2": validate_harder_turn_2,
    "validate_harder_turn_1": validate_harder_turn_1,
}
