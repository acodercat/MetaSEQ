import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_deep_pm_ratio_max(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    m=pd.read_sql(text("SELECT station_id, avg(pm2_5)/NULLIF(avg(pm10),0) v FROM hourly_station_air_quality WHERE datetime>='2025-06-01' AND datetime<'2025-07-01' AND pm2_5 IS NOT NULL AND pm10 IS NOT NULL GROUP BY station_id ORDER BY v DESC"),engine)
    gt={'sid':int(m.iloc[0]['station_id']),'v':float(m.iloc[0]['v']),'_diag':('margin',round(float(m.iloc[0]['v']-m.iloc[1]['v']),4))}
    errs=[]
    v=runtime.retrieve("pmr_station_id")
    if v is None: return ValidatorResult(False,"pmr_station_id not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"pmr_station_id not numeric: {v!r}")
    if int(round(float(v)))!=int(gt["sid"]): errs.append(f"pmr_station_id={int(round(float(v)))}, expected {int(gt['sid'])}")
    v=runtime.retrieve("pmr_ratio")
    if v is None: return ValidatorResult(False,"pmr_ratio not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"pmr_ratio not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["v"]),tolerance=0.02): errs.append(f"pmr_ratio={round(float(v),3)}, expected ~{round(float(gt['v']),3)} (tol 0.02)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK "+str({k:v for k,v in gt.items() if k!='_diag'}))


tools = []
variables = [
    Variable("pmr_station_id", None, "station_id with highest mean(PM2.5)/mean(PM10), June 2025"),
    Variable("pmr_ratio", None, "that ratio, 3dp"),
]
validators = {"validate_hk_deep_pm_ratio_max": validate_hk_deep_pm_ratio_max}
