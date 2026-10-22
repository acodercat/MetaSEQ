import pandas as pd
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_1_12(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    def mv(a,b):
        return float(pd.read_sql(text(f"SELECT AVG(aqhi) v FROM hourly_station_air_quality WHERE station_id=15 AND datetime>='{a}' AND datetime<'{b}' AND aqhi IS NOT NULL"), engine).iloc[0]['v'])
    checks = [("weekday_mean_aqhi", mv('2025-01-20','2025-01-25'), 0.4), ("weekend_mean_aqhi", mv('2025-01-25','2025-01-27'), 0.6)]
    for var, exp, tol in checks:
        val = runtime.retrieve(var)
        if val is None: return ValidatorResult(False, f"{var} not set", variables_not_set=True)
        if not is_finite_number(val) or not compare_numeric(float(val), float(exp), tolerance=tol):
            return ValidatorResult(False, f"{var}={val!r}, expected ~{round(float(exp),2)} (tol {tol})")
    return ValidatorResult(True, "all variables within tolerance")


tools = []
variables = [
    Variable("weekday_mean_aqhi", None, "mean hourly AQHI at station 15, 2025-01-20..24 (float)."),
    Variable("weekend_mean_aqhi", None, "mean hourly AQHI at station 15, 2025-01-25..26 (float)."),
]
validators = {"validate_hk_1_12": validate_hk_1_12}
