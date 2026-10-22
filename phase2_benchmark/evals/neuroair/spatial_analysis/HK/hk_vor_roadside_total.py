import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_vor_roadside_total(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    _vor="""WITH pts AS (SELECT id,name_en,coordinate::geometry g FROM air_quality_station),
    bbox AS (SELECT ST_Envelope(ST_Collect(g)) b FROM pts),
    vor AS (SELECT (ST_Dump(ST_VoronoiPolygons(ST_Collect(g)))).geom cell FROM pts),
    cells AS (SELECT p.id,p.name_en, ST_Intersection(v.cell,(SELECT b FROM bbox)) cg FROM pts p JOIN vor v ON ST_Contains(v.cell,p.g))"""
    gt={'v':float(pd.read_sql(text(_vor+" SELECT sum(ST_Area(cg::geography))/1e6 v FROM cells WHERE id IN (14,16,17)"),engine).iloc[0]['v'])}
    errs=[]
    v=runtime.retrieve("roadside_cells_km2")
    if v is None: return ValidatorResult(False,"roadside_cells_km2 not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"roadside_cells_km2 not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["v"]),tolerance=4.0): errs.append(f"roadside_cells_km2={round(float(v),3)}, expected ~{round(float(gt['v']),3)} (tol 4.0)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("roadside_cells_km2", None, "total bbox-clipped Voronoi cell area of stations 14,16,17 in km²"),
]
validators = {"validate_hk_vor_roadside_total": validate_hk_vor_roadside_total}
