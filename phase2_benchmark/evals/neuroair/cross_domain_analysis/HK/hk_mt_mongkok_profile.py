import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_mt_mongkok_profile(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    no2=float(pd.read_sql(text("SELECT avg(no2) v FROM hourly_station_air_quality WHERE station_id=14 AND datetime>='2025-06-01' AND datetime<'2025-07-01' AND no2 IS NOT NULL"),engine).iloc[0]['v'])
    ci=float(pd.read_sql(text("SELECT avg(tr.congestion_index) v FROM road_segment rs JOIN hourly_road_segment_traffic tr ON tr.road_segment_id=rs.id, air_quality_station a WHERE a.id=14 AND ST_DWithin(rs.geometry::geography,a.coordinate::geography,500) AND EXTRACT(hour FROM tr.datetime) IN (8,9) AND tr.congestion_index IS NOT NULL"),engine).iloc[0]['v'])
    sch=float(pd.read_sql(text("SELECT count(*) v FROM sensitive_area s, air_quality_station a WHERE a.id=14 AND s.category='EDUCATIONAL_INSTITUTION' AND ST_DWithin(ST_Centroid(s.geometry)::geography,a.coordinate::geography,500)"),engine).iloc[0]['v'])
    lu=pd.read_sql(text("SELECT z.land_category, sum(ST_Area(ST_Intersection(z.geometry, ST_Buffer(a.coordinate::geography,500)::geometry)::geography)) ar FROM land_use_zone z, air_quality_station a WHERE a.id=14 AND ST_DWithin(z.geometry::geography,a.coordinate::geography,500) GROUP BY 1 ORDER BY ar DESC"),engine)
    gt={'no2':no2,'ci':ci,'sch':sch,'lu':str(lu.iloc[0]['land_category'])}
    errs=[]
    v=runtime.retrieve("mk_no2")
    if v is None: return ValidatorResult(False,"mk_no2 not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"mk_no2 not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["no2"]),tolerance=1.0): errs.append(f"mk_no2={round(float(v),3)}, expected ~{round(float(gt['no2']),3)} (tol 1.0)")
    v=runtime.retrieve("mk_rush_ci")
    if v is None: return ValidatorResult(False,"mk_rush_ci not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"mk_rush_ci not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["ci"]),tolerance=0.2): errs.append(f"mk_rush_ci={round(float(v),3)}, expected ~{round(float(gt['ci']),3)} (tol 0.2)")
    v=runtime.retrieve("mk_schools")
    if v is None: return ValidatorResult(False,"mk_schools not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"mk_schools not numeric: {v!r}")
    if int(round(float(v)))!=int(round(float(gt["sch"]))): errs.append(f"mk_schools={int(round(float(v)))}, expected {int(round(float(gt['sch'])))}")
    v=runtime.retrieve("mk_dom_landuse")
    if v is None: return ValidatorResult(False,"mk_dom_landuse not set",variables_not_set=True)
    if str(v).strip().lower()!=str(gt["lu"]).strip().lower(): errs.append(f"mk_dom_landuse={v!r}, expected {gt['lu']!r}")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("mk_no2", None, "June mean NO2 at station 14, 1dp"),
    Variable("mk_rush_ci", None, "mean congestion_index (hours 8,9) of road segments <=500m of station 14, 2dp"),
    Variable("mk_schools", None, "# EDUCATIONAL_INSTITUTION centroids <=500m of station 14"),
    Variable("mk_dom_landuse", None, "land_category with largest intersection area with the 500m buffer around station 14"),
]
validators = {"validate_hk_mt_mongkok_profile": validate_hk_mt_mongkok_profile}
