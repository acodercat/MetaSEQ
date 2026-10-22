"""Difficulty upgrade — beijing_olympics_meteorological_adjustment (2026-10-06).

Quantitative raw and log-ventilation-adjusted intervention-window contrasts.
Professional consequence: Bound what an adjusted before/after contrast can say about the Olympics controls.
Plausible wrong reading: Calling the adjusted year/window coefficient a causal control effect ignores omitted weather, transport and other between-year changes.

Source concept: https://acp.copernicus.org/articles/18/6223/2018/
The paper supports the concept, not these dataset-specific answers. This case
uses its stated data, time conventions and statistical target; no causal or
surface-emission claim is inferred from a column or conditional association.

Independent raw-data results frozen before authoring the advanced helper:
{
  "raw_window_difference": -43.95293732831294,
  "log_ventilation_adjusted_difference": -27.95251202119301,
  "adjustment_days": 34
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

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from cave_agent import Variable

from domains.beijing.data import DATA_DIR
from tasks import Turn
from validation import ValidatorResult, compare_numeric, is_finite_number, reports_as

_OLYMPIC = ("2022-02-04", "2022-02-20")
_BASELINE = ("2021-02-04", "2021-02-20")


def _window(df: pd.DataFrame, span: tuple) -> pd.DataFrame:
    return df[(df["date"] >= span[0]) & (df["date"] <= span[1])]


def _daily_table(recipe: str = "pooled") -> pd.DataFrame:
    """Daily PM2.5 and ventilation over the two windows under three recipes:
    each day's station-hours pooled, the domain's two-step daily figure, or
    the two series joined on (station, hour) before averaging."""
    bj = DATA_DIR
    df = pd.read_csv(bj / "air_quality.csv")
    # Air-quality label h is the hour ending at h:00, so its day is the label
    # shifted back one hour; ERA5 values are instants and keep their own date.
    df["ts"] = pd.to_datetime(df[["year", "month", "day", "hour"]])
    df["date"] = (df["ts"] - pd.Timedelta(hours=1)).dt.normalize()
    met = pd.read_csv(bj / "met_era5.csv")
    met["ts"] = pd.to_datetime(met[["year", "month", "day", "hour"]])
    met["date"] = met["ts"].dt.normalize()
    pm = pd.concat([_window(df, _OLYMPIC), _window(df, _BASELINE)])
    vent = pd.concat([_window(met, _OLYMPIC), _window(met, _BASELINE)])
    if recipe == "joined":
        # Joined on the stamp, as the schema says to join, and grouped by the
        # air-quality day the row's PM2.5 belongs to.
        joined = pm.merge(met[["ts", "station", "ventilation_m2s"]], on=["ts", "station"])
        table = joined.groupby("date")[["PM2.5", "ventilation_m2s"]].mean()
        table.columns = ["pm25", "ventilation"]
    elif recipe == "two-step":
        table = pd.concat([pm.groupby(["date", "hour"])["PM2.5"].mean().groupby(level=0).mean().rename("pm25"),
                           vent.groupby(["date", "hour"])["ventilation_m2s"].mean().groupby(level=0).mean().rename("ventilation")],
                          axis=1).dropna()
    else:
        table = pd.concat([pm.groupby("date")["PM2.5"].mean().rename("pm25"),
                           vent.groupby("date")["ventilation_m2s"].mean().rename("ventilation")],
                          axis=1).dropna()
    table["olympic"] = table.index >= pd.Timestamp(_OLYMPIC[0])
    return table


def _stratified(t: pd.DataFrame, groups: int, allocation=None) -> float:
    ordered = t.sort_values("ventilation")
    label = (pd.qcut(ordered["ventilation"], groups, labels=False) if allocation is None
             else np.repeat(range(groups), allocation))
    diffs = []
    for _, g in ordered.assign(group=label).groupby("group"):
        olympic, baseline = g[g["olympic"]]["pm25"], g[~g["olympic"]]["pm25"]
        if len(olympic) and len(baseline):
            diffs.append(olympic.mean() - baseline.mean())
    return float(np.mean(diffs))


def _regression(t: pd.DataFrame, log: bool) -> float:
    vent = np.log(t["ventilation"]) if log else t["ventilation"]
    design = np.column_stack([np.ones(len(t)), vent, t["olympic"].astype(float)])
    return float(np.linalg.lstsq(design, t["pm25"].to_numpy(), rcond=None)[0][2])


def _matched(t: pd.DataFrame) -> float:
    olympic, baseline = t[t["olympic"]], t[~t["olympic"]]
    return float(np.mean([row["pm25"] - baseline.loc[(baseline["ventilation"] - row["ventilation"]).abs().idxmin(), "pm25"]
                          for _, row in olympic.iterrows()]))


def _routes() -> List[Tuple[str, float]]:
    routes = []
    for recipe in ("pooled", "two-step", "joined"):
        t = _daily_table(recipe)
        routes += [(f"{recipe}: stratified, {n} groups", _stratified(t, n)) for n in (2, 3, 4, 5)]
        routes += [(f"{recipe}: stratified, 3 groups of {a}", _stratified(t, 3, a))
                   for a in ([11, 12, 11], [11, 11, 12])]
        routes += [(f"{recipe}: regression, linear", _regression(t, False)),
                   (f"{recipe}: regression, log ventilation", _regression(t, True)),
                   (f"{recipe}: nearest-neighbour matching", _matched(t))]
    return routes


def _figures() -> Dict[str, object]:
    t = _daily_table()
    raw = float(t[t["olympic"]]["pm25"].mean() - t[~t["olympic"]]["pm25"].mean())
    table = [(name, {"still_lower_after_the_weather_adjustment": bool(adjusted < 0),
                     "adjusted_cut_smaller_than_raw": bool(abs(adjusted) < abs(raw))})
             for name, adjusted in _routes()]
    out: Dict[str, object] = {}
    for key in table[0][1]:
        values = {row[key] for _, row in table}
        if len(values) != 1:
            raise RuntimeError(f"{key} is not invariant across adjustments: "
                               + "; ".join(f"{n}={row[key]}" for n, row in table))
        out[key] = values.pop()
    return out


def validate_adjusted_difference(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "still_lower_after_the_weather_adjustment":
            runtime.retrieve("still_lower_after_the_weather_adjustment"),
        "adjusted_cut_smaller_than_raw": runtime.retrieve("adjusted_cut_smaller_than_raw"),
    }
    missing = [name for name, val in got.items() if val is None]
    if missing:
        return ValidatorResult(False, f"{', '.join(missing)} not set", variables_not_set=True)
    gt = _figures()
    errors = []
    for name, val in got.items():
        expected = gt[name]
        ok = (isinstance(val, bool) and val == expected) or (
            isinstance(val, str) and val.strip().lower() in
            {str(expected).lower(), "yes" if expected else "no"})
        if not ok:
            errors.append(f"{name}={val!r}, expected {expected}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: the Olympic window is still lower after the weather "
                                 "adjustment, by less than the raw contrast")


tools = []
variables = [
    Variable("still_lower_after_the_weather_adjustment", None,
             "Store True if, once the difference in ventilation between the "
             "two windows is allowed for, PM2.5 over 4 to 20 February 2022 was "
             "still lower than over the same dates in 2021, else False."),
    Variable("adjusted_cut_smaller_than_raw", None,
             "Store True if the ventilation-adjusted reduction is smaller in size "
             "than the plain difference between the two windows' means, else "
             "False."),
    Variable('raw_window_difference', None, "Store later-window minus earlier-window mean daily network PM2.5 on the adjustment's complete positive daily PM2.5/ventilation cohort, in µg/m³ to 2 decimal places; include both 4 February and 20 February in each year."),
    Variable('log_ventilation_adjusted_difference', None, 'Store the 2022-window indicator coefficient from OLS of daily PM2.5 on an intercept, that indicator and natural-log daily ventilation, in µg/m³ to 2 decimal places. Fit the same complete positive daily cohort from the two stated windows; daily PM2.5 and meteorology use their domain time conventions.'),
    Variable('adjustment_days', None, 'Store the exact integer number of daily observations entering that adjustment across both windows.'),
]

# Difficulty upgrade 2026-10-06: older docstring magnitudes describe the
# earlier scoring surface. Added metrics below are recomputed from source data.
# Their single declared decimal report is checked by reports_as; counts are
# exact. The independent raw-data maps were frozen before these helpers.

def _advanced_metrics():
    frame = _daily_table(recipe="two-step")
    frame = frame[(frame["pm25"] > 0) & (frame["ventilation"] > 0)]
    x = np.column_stack([np.ones(len(frame)), frame["olympic"].astype(float), np.log(frame["ventilation"])])
    coef = np.linalg.lstsq(x, frame["pm25"].to_numpy(), rcond=None)[0]
    means = frame.groupby("olympic")["pm25"].mean()
    return {"raw_window_difference": float(means[True]-means[False]),
            "log_ventilation_adjusted_difference": float(coef[1]),
            "adjustment_days": len(frame)}





def validate_harder_turn_1(response: str, runtime, turn: Turn) -> ValidatorResult:
    got = {
        "still_lower_after_the_weather_adjustment": runtime.retrieve("still_lower_after_the_weather_adjustment"),
        "adjusted_cut_smaller_than_raw": runtime.retrieve("adjusted_cut_smaller_than_raw"),
        "raw_window_difference": runtime.retrieve("raw_window_difference"),
        "log_ventilation_adjusted_difference": runtime.retrieve("log_ventilation_adjusted_difference"),
        "adjustment_days": runtime.retrieve("adjustment_days"),
    }
    missing = [name for name, value in got.items() if value is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing)+" not set", variables_not_set=True)
    original = validate_adjusted_difference(response, runtime, turn)
    if not original.success:
        return original
    gt = _advanced_metrics()
    errors = []
    if not is_finite_number(got["raw_window_difference"]) or not reports_as(got["raw_window_difference"], gt["raw_window_difference"], decimals=2):
        errors.append(f"raw_window_difference={got["raw_window_difference"]!r}, expected {gt["raw_window_difference"]!r}")
    if not is_finite_number(got["log_ventilation_adjusted_difference"]) or not reports_as(got["log_ventilation_adjusted_difference"], gt["log_ventilation_adjusted_difference"], decimals=2):
        errors.append(f"log_ventilation_adjusted_difference={got["log_ventilation_adjusted_difference"]!r}, expected {gt["log_ventilation_adjusted_difference"]!r}")
    if not is_finite_number(got["adjustment_days"]) or not compare_numeric(got["adjustment_days"], gt["adjustment_days"], tolerance=0):
        errors.append(f"adjustment_days={got["adjustment_days"]!r}, expected {gt["adjustment_days"]!r}")
    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, "correct: numerical evidence and original conclusion")


validators = {
    "validate_adjusted_difference": validate_adjusted_difference,
    "validate_harder_turn_1": validate_harder_turn_1,
}
