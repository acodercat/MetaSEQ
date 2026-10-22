"""Reporting resolution and between-station SO2 spread, without scoring an unidentifiable true-concentration ranking.

Full review 2026-10-06: a single-observation reporting step is not the resolution of an average. Quantisation alone does not prove annual means indistinguishable. Interpret censoring and instrument uncertainty in the claims.
"""
import pandas as pd
from cave_agent import Variable
from domains.beijing.data import DATA_DIR
from validation import ValidatorResult, compare_numeric, reports_as
from tasks import Turn

def _floor_stats():
    aq = pd.read_csv(DATA_DIR / "air_quality.csv")
    stamp = pd.to_datetime(aq[["year", "month", "day", "hour"]])
    yr = aq[(stamp - pd.Timedelta(hours=1)).dt.year == 2023]
    means = yr.groupby("station")["SO2"].mean()
    return {"distinct": int(yr["SO2"].nunique()), "spread": float(means.max() - means.min())}

def validate_reporting_floor(response: str, runtime, turn: Turn) -> ValidatorResult:
    distinct = runtime.retrieve("so2_distinct_values")
    spread = runtime.retrieve("station_annual_so2_spread")
    missing = [n for n,v in [("so2_distinct_values",distinct),("station_annual_so2_spread",spread)] if v is None]
    if missing:
        return ValidatorResult(False, ", ".join(missing) + " not set", variables_not_set=True)
    gt = _floor_stats()
    if not compare_numeric(distinct, gt["distinct"], tolerance=0) or not reports_as(spread, gt["spread"], decimals=2):
        return ValidatorResult(False, "incorrect reporting resolution or station-mean spread")
    return ValidatorResult(True, "reporting resolution and annual-mean spread accepted")

tools = []
variables = [
    Variable("so2_distinct_values", None, "Store the number of distinct non-null station-hour SO2 values in the hour-ending year 2023, as an integer."),
    Variable("station_annual_so2_spread", None, "Store the highest minus lowest of the twelve stations' 2023 annual SO2 means, as a float in ug/m3, 2 decimal places. Each station mean pools its own reported hourly readings on the domain's hour-ending year convention."),
]
validators = {"validate_reporting_floor": validate_reporting_floor}
