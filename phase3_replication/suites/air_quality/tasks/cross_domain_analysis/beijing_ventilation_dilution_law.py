"""Difficulty upgrade — beijing_ventilation_dilution_law (2026-10-06).

Held-out log-model retransformation and forecast losses.
Professional consequence: Assess a ventilation-only forecasting product before using it operationally.
Plausible wrong reading: A training smearing correction does not guarantee improved held-out MAE or RMSE; actual future meteorology is an oracle-input scenario.

Source concept: https://www.tandfonline.com/doi/abs/10.1080/01621459.1983.10478017
The paper supports the concept, not these dataset-specific answers. This case
uses its stated data, time conventions and statistical target; no causal or
surface-emission claim is inferred from a column or conditional association.

Independent raw-data results frozen before authoring the advanced helper:
{
  "naive_retransform_mae": 15.584985957152169,
  "smearing_retransform_mae": 18.518168451763646,
  "naive_retransform_rmse": 24.04956329572462,     NOT SCORED since 2026-10-07
  "smearing_retransform_rmse": 24.93374275532328,  NOT SCORED since 2026-10-07
  "ventilation_test_days": 365
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

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

_DAY = ["year", "month", "day"]
_HOUR = _DAY + ["hour"]
_YEARS = (2020, 2025)


def _daily(pooled: bool = False) -> pd.DataFrame:
    """Daily PM2.5 and ventilation over 2020-2025: the domain's two-step daily
    figure, or every station-hour pooled into the day."""
    bj = DATA_DIR
    aq = pd.read_csv(bj / "air_quality.csv")
    met = pd.read_csv(bj / "met_era5.csv")
    # An air-quality hour h is the hour ENDING at h:00, so its day is that of
    # h minus one hour (hours 1-23 and the next date's hour 0); the ERA5 rows
    # are instants and keep their own date (hours 0-23).
    stamp = pd.to_datetime(aq[_HOUR])
    owner = stamp - pd.Timedelta(hours=1)
    aq = aq.assign(year=owner.dt.year, month=owner.dt.month, day=owner.dt.day, _ts=stamp)
    aq = aq[aq["year"].between(*_YEARS)]
    met = met[met["year"].between(*_YEARS)]
    if pooled:
        pm = aq.groupby(_DAY)["PM2.5"].mean().rename("pm")
    else:
        pm = aq.groupby(_DAY + ["_ts"])["PM2.5"].mean().groupby(level=[0, 1, 2]).mean().rename("pm")
    vent = met.groupby(_HOUR)["ventilation_m2s"].mean().groupby(level=[0, 1, 2]).mean().rename("vent")
    daily = pd.concat([pm, vent], axis=1).dropna().reset_index()
    return daily[(daily["pm"] > 0) & (daily["vent"] > 0)]


def _figures() -> Dict[str, object]:
    # Both daily recipes are asserted to agree within 0.01 (-0.351 two-step,
    # -0.350 pooled) and on the verdict. "Holds" means the slope is within
    # 0.5 of the -1 the box relation predicts — nearer to -1 than to 0.
    slopes, shares = {}, {}
    for label, d in (("two-step", _daily()), ("pooled", _daily(pooled=True))):
        x, y = np.log(d["vent"]), np.log(d["pm"])
        slopes[label] = float(np.polyfit(x, y, 1)[0])
        shares[label] = float(np.corrcoef(x, y)[0, 1] ** 2)
    if max(slopes.values()) - min(slopes.values()) > 0.01 or len({abs(s + 1.0) < 0.5 for s in slopes.values()}) != 1:
        raise RuntimeError(f"the slope is not invariant across daily recipes: {slopes}")
    rounded = {round(v * 20) * 5 for v in shares.values()}
    if len(rounded) != 1:
        raise RuntimeError(f"the explained share is not invariant to the nearest 5 %: {shares}")
    slope = slopes["two-step"]
    return {
        "dilution_log_slope": slope,
        "inverse_law_holds": bool(abs(slope + 1.0) < 0.5),
        "variance_explained_pct": rounded.pop(),
        "shares": shares,
    }


def _bool_ok(val, expected: bool) -> bool:
    return (isinstance(val, bool) and val == expected) or (
        isinstance(val, str) and val.strip().lower() in {str(expected).lower(), "yes" if expected else "no"})


def validate_dilution_law(response: str, runtime, turn: Turn) -> ValidatorResult:
    slope = runtime.retrieve("dilution_log_slope")
    holds = runtime.retrieve("inverse_law_holds")
    explained = runtime.retrieve("variance_explained_pct")
    missing = [n for n, v in (("dilution_log_slope", slope), ("inverse_law_holds", holds),
                              ("variance_explained_pct", explained)) if v is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    if not is_finite_number(slope):
        return ValidatorResult(False, f"dilution_log_slope={slope!r} is not a number")
    gt = _figures()
    wrong = []
    # Score the one-decimal report of the domain-defined daily construction.
    # Other weighting recipes do not justify a second rounded answer.
    if not reports_as(slope, gt["dilution_log_slope"], decimals=1):
        wrong.append(f"dilution_log_slope={slope}, expected ~{gt['dilution_log_slope']:.1f}")
    if not _bool_ok(holds, gt["inverse_law_holds"]):
        wrong.append(f"inverse_law_holds={holds!r}, expected {gt['inverse_law_holds']}")
    if not is_finite_number(explained):
        wrong.append(f"variance_explained_pct={explained!r} is not a number")
    elif not reports_as(explained / 5, gt["variance_explained_pct"] / 5, decimals=0):
        wrong.append(f"variance_explained_pct={explained}, expected ~{gt['variance_explained_pct']} "
                     f"(exact: {gt['shares']})")
    if wrong:
        return ValidatorResult(False, "; ".join(wrong))
    return ValidatorResult(True, f"correct: slope {gt['dilution_log_slope']:.1f} against the predicted -1, "
                                 f"and {gt['variance_explained_pct']} % of the day-to-day variance explained")


tools = []
variables = [
    Variable("dilution_log_slope", None,
             "Store the slope of log daily PM2.5 on log daily ventilation "
             "coefficient over 2020 through 2025, as a float to 1 decimal place "
             "— natural logs of both, ordinary least squares, one point per day."),
    Variable("inverse_law_holds", None,
             "Store True if the record bears out the desk's reasoning that "
             "concentration scales as the INVERSE of the ventilation "
             "coefficient — that halving the ventilation roughly doubles the "
             "concentration — else False. Moving in the opposite direction is "
             "not enough on its own."),
    Variable("variance_explained_pct", None,
             "Store how much of the day-to-day variation in the logarithm of "
             "daily PM2.5 the ventilation coefficient accounts for, as a "
             "percentage to the nearest 5."),
    Variable('naive_retransform_mae', None, 'Store 2025 daily PM2.5 MAE for naive exponentiation of a log-OLS forecast, in µg/m³ to 2 decimal places. Fit an intercept and log daily ventilation to log daily PM2.5 on complete positive daily pairs from 2020-2024; use observed 2025 ventilation as a perfect-input forecast scenario.'),
    Variable('smearing_retransform_mae', None, "Store 2025 MAE for the same forecast with Duan's single empirical smearing factor estimated only from the 2020-2024 training residuals, in µg/m³ to 2 decimal places; retain the same test days."),
    Variable('ventilation_test_days', None, 'Store the exact integer number of complete positive PM2.5/ventilation days scored in 2025.'),
]

# Difficulty upgrade 2026-10-06: older docstring magnitudes describe the
# earlier scoring surface. Added metrics below are recomputed from source data.
# Their single declared decimal report is checked by reports_as; counts are
# exact. The independent raw-data maps were frozen before these helpers.

def _advanced_metrics():
    frame = _daily()
    train = frame[frame["year"].between(2020, 2024)]
    test = frame[frame["year"] == 2025]
    x, y = np.log(train["vent"].to_numpy()), np.log(train["pm"].to_numpy())
    beta = np.polyfit(x, y, 1)
    residual = y-np.polyval(beta, x)
    naive = np.exp(np.polyval(beta, np.log(test["vent"].to_numpy())))
    smeared = naive*np.exp(residual).mean()
    truth = test["pm"].to_numpy()
    return {"naive_retransform_mae": float(np.mean(np.abs(truth-naive))),
            "smearing_retransform_mae": float(np.mean(np.abs(truth-smeared))),
            "ventilation_test_days": len(test)}







def validate_harder_turn_1(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "dilution_log_slope": runtime.retrieve("dilution_log_slope"),
        "inverse_law_holds": runtime.retrieve("inverse_law_holds"),
        "variance_explained_pct": runtime.retrieve("variance_explained_pct"),
        "naive_retransform_mae": runtime.retrieve("naive_retransform_mae"),
        "smearing_retransform_mae": runtime.retrieve("smearing_retransform_mae"),
        "ventilation_test_days": runtime.retrieve("ventilation_test_days"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_dilution_law(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["naive_retransform_mae"]) or not reports_as(got["naive_retransform_mae"], gt["naive_retransform_mae"], decimals=2):
        errors.append(f"naive_retransform_mae={got["naive_retransform_mae"]!r}, expected {gt["naive_retransform_mae"]!r}")
    if not is_finite_number(got["smearing_retransform_mae"]) or not reports_as(got["smearing_retransform_mae"], gt["smearing_retransform_mae"], decimals=2):
        errors.append(f"smearing_retransform_mae={got["smearing_retransform_mae"]!r}, expected {gt["smearing_retransform_mae"]!r}")
    if not is_finite_number(got["ventilation_test_days"]) or not compare_numeric(got["ventilation_test_days"], gt["ventilation_test_days"], tolerance=0):
        errors.append(f"ventilation_test_days={got["ventilation_test_days"]!r}, expected {gt["ventilation_test_days"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


validators = {
    "validate_dilution_law": validate_dilution_law,
    "validate_harder_turn_1": validate_harder_turn_1,
}
