import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_x_who_station_days(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    d=pd.read_sql(text("SELECT station_id, datetime::date dt, avg(pm2_5) v FROM hourly_station_air_quality WHERE datetime>='2025-06-01' AND datetime<'2025-07-01' AND pm2_5 IS NOT NULL GROUP BY 1,2"),engine)
    gt={'n':float((d['v']>15.0).sum()),'_diag':('total_station_days',len(d))}
    errs=[]
    v=runtime.retrieve("who_exceed_station_days")
    if v is None: return ValidatorResult(False,"who_exceed_station_days not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"who_exceed_station_days not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["n"]),tolerance=1.0): errs.append(f"who_exceed_station_days={round(float(v),3)}, expected ~{round(float(gt['n']),3)} (tol 1.0)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("who_exceed_station_days", None, "number of June station-days with daily-mean PM2.5 strictly above the WHO 2021 24-hour guideline"),
]
validators = {"validate_hk_x_who_station_days": validate_hk_x_who_station_days}
