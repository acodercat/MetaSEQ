import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_cov_schools_roadside5km(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    gt={'v':float(pd.read_sql(text("SELECT count(DISTINCT s.id) v FROM sensitive_area s, air_quality_station a WHERE s.category='EDUCATIONAL_INSTITUTION' AND a.id IN (14,16,17) AND ST_DWithin(ST_Centroid(s.geometry)::geography,a.coordinate::geography,5000)"),engine).iloc[0]['v'])}
    errs=[]
    v=runtime.retrieve("schools_roadside_5km")
    if v is None: return ValidatorResult(False,"schools_roadside_5km not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"schools_roadside_5km not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["v"]),tolerance=80.0): errs.append(f"schools_roadside_5km={round(float(v),1)}, expected ~{round(float(gt['v']),1)} (tol 80.0)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("schools_roadside_5km", None, "distinct schools whose centroid is within 5000 m of at least one roadside station"),
]
validators = {"validate_hk_cov_schools_roadside5km": validate_hk_cov_schools_roadside5km}
