import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_vor_smallest(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    _vor="""WITH pts AS (SELECT id,name_en,coordinate::geometry g FROM air_quality_station),
    bbox AS (SELECT ST_Envelope(ST_Collect(g)) b FROM pts),
    vor AS (SELECT (ST_Dump(ST_VoronoiPolygons(ST_Collect(g)))).geom cell FROM pts),
    cells AS (SELECT p.id,p.name_en, ST_Intersection(v.cell,(SELECT b FROM bbox)) cg FROM pts p JOIN vor v ON ST_Contains(v.cell,p.g))"""
    d=pd.read_sql(text(_vor+" SELECT name_en, ST_Area(cg::geography)/1e6 v FROM cells ORDER BY v ASC"),engine)
    gt={'name':str(d.iloc[0]['name_en']),'v':float(d.iloc[0]['v']),'_diag':('margin',round(float(d.iloc[1]['v']-d.iloc[0]['v']),1))}
    errs=[]
    v=runtime.retrieve("smallest_cell_station")
    if v is None: return ValidatorResult(False,"smallest_cell_station not set",variables_not_set=True)
    if str(v).strip()!=str(gt["name"]).strip(): errs.append(f"smallest_cell_station={v!r}, expected {gt['name']!r}")
    v=runtime.retrieve("smallest_cell_km2")
    if v is None: return ValidatorResult(False,"smallest_cell_km2 not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"smallest_cell_km2 not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["v"]),tolerance=2.0): errs.append(f"smallest_cell_km2={round(float(v),3)}, expected ~{round(float(gt['v']),3)} (tol 2.0)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("smallest_cell_station", None, "name of the station with the smallest bbox-clipped Voronoi cell"),
    Variable("smallest_cell_km2", None, "that cell's area in km²"),
]
validators = {"validate_hk_vor_smallest": validate_hk_vor_smallest}
