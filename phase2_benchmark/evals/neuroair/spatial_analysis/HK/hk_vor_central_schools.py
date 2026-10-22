import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_vor_central_schools(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    _vor="""WITH pts AS (SELECT id,name_en,coordinate::geometry g FROM air_quality_station),
    bbox AS (SELECT ST_Envelope(ST_Collect(g)) b FROM pts),
    vor AS (SELECT (ST_Dump(ST_VoronoiPolygons(ST_Collect(g)))).geom cell FROM pts),
    cells AS (SELECT p.id,p.name_en, ST_Intersection(v.cell,(SELECT b FROM bbox)) cg FROM pts p JOIN vor v ON ST_Contains(v.cell,p.g))"""
    q=_vor+""" SELECT count(*) n FROM sensitive_area s, cells c WHERE c.id=16 AND s.category='EDUCATIONAL_INSTITUTION' AND ST_Contains(c.cg, ST_Centroid(s.geometry))"""
    gt={'n':float(pd.read_sql(text(q),engine).iloc[0]['n'])}
    errs=[]
    v=runtime.retrieve("central_cell_schools")
    if v is None: return ValidatorResult(False,"central_cell_schools not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"central_cell_schools not numeric: {v!r}")
    if int(round(float(v)))!=int(round(float(gt["n"]))): errs.append(f"central_cell_schools={int(round(float(v)))}, expected {int(round(float(gt['n'])))}")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("central_cell_schools", None, "number of school sensitive-areas whose centroid lies in Central's bbox-clipped Voronoi cell"),
]
validators = {"validate_hk_vor_central_schools": validate_hk_vor_central_schools}
