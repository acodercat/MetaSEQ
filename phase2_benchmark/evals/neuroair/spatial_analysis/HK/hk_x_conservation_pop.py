import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_x_conservation_pop(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    pop=pd.read_csv(PROJECT_ROOT/"datasets"/"HK_population_1km.csv")
    vals=",".join(f"({r.longitude},{r.latitude},{r.population})" for r in pop.itertuples())
    q=f"""WITH cells(lon,lat,p) AS (VALUES {vals})
    SELECT COALESCE(sum(p),0) s FROM cells WHERE EXISTS (SELECT 1 FROM land_use_zone z WHERE z.land_category='Conservation' AND ST_Contains(z.geometry, ST_SetSRID(ST_Point(lon,lat),4326)))"""
    gt={'v':float(pd.read_sql(text(q),engine).iloc[0]['s'])}
    errs=[]
    v=runtime.retrieve("conservation_pop")
    if v is None: return ValidatorResult(False,"conservation_pop not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"conservation_pop not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["v"]),tolerance=3000.0): errs.append(f"conservation_pop={round(float(v),3)}, expected ~{round(float(gt['v']),3)} (tol 3000.0)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("conservation_pop", None, "total population of grid cells whose lon/lat point falls inside a Conservation land-use polygon"),
]
validators = {"validate_hk_x_conservation_pop": validate_hk_x_conservation_pop}
