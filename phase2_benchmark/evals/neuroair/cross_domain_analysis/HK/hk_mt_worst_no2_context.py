import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_mt_worst_no2_context(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    d=pd.read_sql(text("SELECT station_id FROM hourly_station_air_quality WHERE datetime>='2025-06-01' AND datetime<'2025-07-01' AND no2 IS NOT NULL GROUP BY 1 ORDER BY avg(no2) DESC LIMIT 1"),engine)
    sid=int(d.iloc[0]['station_id']); nm=str(pd.read_sql(text(f"SELECT name_en FROM air_quality_station WHERE id={sid}"),engine).iloc[0]['name_en'])
    lu=pd.read_sql(text(f"SELECT z.land_category, sum(ST_Area(ST_Intersection(z.geometry, ST_Buffer(a.coordinate::geography,500)::geometry)::geography)) ar FROM land_use_zone z, air_quality_station a WHERE a.id={sid} AND ST_DWithin(z.geometry::geography,a.coordinate::geography,500) GROUP BY 1 ORDER BY ar DESC"),engine).iloc[0]['land_category']
    h=float(pd.read_sql(text(f"SELECT count(*) v FROM sensitive_area s, air_quality_station a WHERE a.id={sid} AND s.category='HEALTH_CARE_INSTITUTION' AND ST_DWithin(ST_Centroid(s.geometry)::geography,a.coordinate::geography,1000)"),engine).iloc[0]['v'])
    gt={'name':nm,'lu':str(lu),'h':h}
    errs=[]
    v=runtime.retrieve("worst_no2_station")
    if v is None: return ValidatorResult(False,"worst_no2_station not set",variables_not_set=True)
    if str(v).strip().lower()!=str(gt["name"]).strip().lower(): errs.append(f"worst_no2_station={v!r}, expected {gt['name']!r}")
    v=runtime.retrieve("worst_no2_landuse")
    if v is None: return ValidatorResult(False,"worst_no2_landuse not set",variables_not_set=True)
    if str(v).strip().lower()!=str(gt["lu"]).strip().lower(): errs.append(f"worst_no2_landuse={v!r}, expected {gt['lu']!r}")
    v=runtime.retrieve("worst_no2_health")
    if v is None: return ValidatorResult(False,"worst_no2_health not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"worst_no2_health not numeric: {v!r}")
    if int(round(float(v)))!=int(round(float(gt["h"]))): errs.append(f"worst_no2_health={int(round(float(v)))}, expected {int(round(float(gt['h'])))}")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("worst_no2_station", None, "station with highest June mean NO2"),
    Variable("worst_no2_landuse", None, "dominant land_category within its 500m buffer"),
    Variable("worst_no2_health", None, "# HEALTH_CARE_INSTITUTION centroids within 1000m of it"),
]
validators = {"validate_hk_mt_worst_no2_context": validate_hk_mt_worst_no2_context}
