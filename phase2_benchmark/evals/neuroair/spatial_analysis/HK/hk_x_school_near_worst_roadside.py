import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_x_school_near_worst_roadside(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    no2=pd.read_sql(text("SELECT station_id, avg(no2) v FROM hourly_station_air_quality WHERE station_id IN (14,16,17) AND datetime>='2025-06-01' AND datetime<'2025-07-01' AND no2 IS NOT NULL GROUP BY 1 ORDER BY v DESC"),engine)
    top=int(no2.iloc[0]['station_id'])
    c=pd.read_sql(text(f"SELECT count(*) c FROM sensitive_area s, air_quality_station a WHERE a.id={top} AND s.category='EDUCATIONAL_INSTITUTION' AND ST_DWithin(ST_Centroid(s.geometry)::geography, a.coordinate::geography, 1000)"),engine).iloc[0]['c']
    gt={'sid':top,'n':float(c),'_diag':('no2margin',round(float(no2.iloc[0]['v']-no2.iloc[1]['v']),1))}
    errs=[]
    v=runtime.retrieve("worst_road_station_id")
    if v is None: return ValidatorResult(False,"worst_road_station_id not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"worst_road_station_id not numeric: {v!r}")
    if int(round(float(v)))!=int(round(float(gt["sid"]))): errs.append(f"worst_road_station_id={int(round(float(v)))}, expected {int(round(float(gt['sid'])))}")
    v=runtime.retrieve("school_count_1km")
    if v is None: return ValidatorResult(False,"school_count_1km not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"school_count_1km not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["n"]),tolerance=5.0): errs.append(f"school_count_1km={round(float(v),3)}, expected ~{round(float(gt['n']),3)} (tol 5.0)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("worst_road_station_id", None, "roadside station_id with highest June 2025 mean NO2"),
    Variable("school_count_1km", None, "number of EDUCATIONAL_INSTITUTION sensitive areas whose centroid is within 1000 m of that station"),
]
validators = {"validate_hk_x_school_near_worst_roadside": validate_hk_x_school_near_worst_roadside}
