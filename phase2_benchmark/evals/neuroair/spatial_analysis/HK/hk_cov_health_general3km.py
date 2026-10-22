import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_cov_health_general3km(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    gt={'v':float(pd.read_sql(text("SELECT count(DISTINCT s.id) v FROM sensitive_area s, air_quality_station a WHERE s.category='HEALTH_CARE_INSTITUTION' AND a.station_type='GENERAL' AND ST_DWithin(ST_Centroid(s.geometry)::geography,a.coordinate::geography,3000)"),engine).iloc[0]['v'])}
    errs=[]
    v=runtime.retrieve("health_general_3km")
    if v is None: return ValidatorResult(False,"health_general_3km not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"health_general_3km not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["v"]),tolerance=25.0): errs.append(f"health_general_3km={round(float(v),1)}, expected ~{round(float(gt['v']),1)} (tol 25.0)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("health_general_3km", None, "distinct healthcare institutions whose centroid is within 3000 m of at least one general station"),
]
validators = {"validate_hk_cov_health_general3km": validate_hk_cov_health_general3km}
