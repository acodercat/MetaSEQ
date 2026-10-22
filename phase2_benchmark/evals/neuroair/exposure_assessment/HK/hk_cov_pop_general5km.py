import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_cov_pop_general5km(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    pop=pd.read_csv(PROJECT_ROOT/"datasets"/"HK_population_1km.csv")
    _v=",".join(f"({r.longitude},{r.latitude},{r.population})" for r in pop.itertuples())
    gt={'v':float(pd.read_sql(text(f"""WITH cells(lon,lat,p) AS (VALUES {_v}) SELECT sum(p) v FROM cells c WHERE EXISTS(SELECT 1 FROM air_quality_station a WHERE a.station_type='GENERAL' AND ST_DWithin(ST_SetSRID(ST_Point(c.lon,c.lat),4326)::geography,a.coordinate::geography,5000))"""),engine).iloc[0]['v'])}
    errs=[]
    v=runtime.retrieve("pop_near_general")
    if v is None: return ValidatorResult(False,"pop_near_general not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"pop_near_general not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["v"]),tolerance=200000.0): errs.append(f"pop_near_general={round(float(v),1)}, expected ~{round(float(gt['v']),1)} (tol 200000.0)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("pop_near_general", None, "total grid population within 5000 m of at least one general station, each cell once"),
]
validators = {"validate_hk_cov_pop_general5km": validate_hk_cov_pop_general5km}
