import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_x_monument_mongkok(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    d=pd.read_sql(text("SELECT s.name, ST_Distance(ST_Centroid(s.geometry)::geography, a.coordinate::geography) dist FROM sensitive_area s, air_quality_station a WHERE a.id=14 AND s.category='DECLARED_MONUMENT' ORDER BY dist LIMIT 2"),engine)
    gt={'name':str(d.iloc[0]['name']),'v':float(d.iloc[0]['dist']),'_diag':('margin',round(float(d.iloc[1]['dist']-d.iloc[0]['dist'])))}
    errs=[]
    v=runtime.retrieve("nearest_monument")
    if v is None: return ValidatorResult(False,"nearest_monument not set",variables_not_set=True)
    if str(v).strip()!=str(gt["name"]).strip(): errs.append(f"nearest_monument={v!r}, expected {gt['name']!r}")
    v=runtime.retrieve("monument_dist_m")
    if v is None: return ValidatorResult(False,"monument_dist_m not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"monument_dist_m not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["v"]),tolerance=60.0): errs.append(f"monument_dist_m={round(float(v),3)}, expected ~{round(float(gt['v']),3)} (tol 60.0)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("nearest_monument", None, "exact stored name of the DECLARED_MONUMENT nearest (by centroid) to station 14"),
    Variable("monument_dist_m", None, "that centroid-to-station distance in metres"),
]
validators = {"validate_hk_x_monument_mongkok": validate_hk_x_monument_mongkok}
