import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_deep_ratio_rank(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    rows=pd.read_sql(text("SELECT station_id, CASE WHEN EXTRACT(hour FROM datetime) IN (7,8,9) THEN 'r' WHEN EXTRACT(hour FROM datetime) IN (0,1,2,3,4) THEN 'o' END g, no2 FROM hourly_station_air_quality WHERE station_id IN (14,16,17) AND datetime>='2025-06-01' AND datetime<'2025-07-01' AND no2 IS NOT NULL"),engine)
    rows=rows.dropna(subset=['g'])
    m=rows.groupby(['station_id','g'])['no2'].mean().unstack()
    ratios={int(s): float(m.loc[s,'r']/m.loc[s,'o']) for s in m.index}
    best=max(ratios,key=ratios.get)
    gt={'sid':best,'ratio':ratios[best]}
    errs=[]
    v=runtime.retrieve("top_ratio_station_id")
    if v is None: return ValidatorResult(False,"top_ratio_station_id not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"top_ratio_station_id not numeric: {v!r}")
    if int(round(float(v)))!=int(gt["sid"]): errs.append(f"top_ratio_station_id={int(round(float(v)))}, expected {int(gt['sid'])}")
    v=runtime.retrieve("top_ratio")
    if v is None: return ValidatorResult(False,"top_ratio not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"top_ratio not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["ratio"]),tolerance=0.02): errs.append(f"top_ratio={round(float(v),3)}, expected ~{round(float(gt['ratio']),3)} (tol 0.02)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK "+str(gt))


tools = []
variables = [
    Variable("top_ratio_station_id", None, "station_id (14/16/17) with the largest rush(07,08,09)/overnight(00-04) NO2 ratio, June 2025"),
    Variable("top_ratio", None, "that largest ratio, 3 decimals"),
]
validators = {"validate_hk_deep_ratio_rank": validate_hk_deep_ratio_rank}
