import pandas as pd
import numpy as np
from sqlalchemy import text
from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number, compare_numeric


def validate_hk_pop_roadside_share(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    pop=pd.read_csv(PROJECT_ROOT/"datasets"/"HK_population_1km.csv")
    st=pd.read_sql(text("SELECT id,name_en,station_type,area_type,ST_X(coordinate::geometry) lon,ST_Y(coordinate::geometry) lat FROM air_quality_station"),engine)
    R=6371.0
    def hav(lo1,la1,lo2,la2):
        dlat=np.radians(la2-la1); dlon=np.radians(lo2-lo1)
        a=np.sin(dlat/2)**2+np.cos(np.radians(la1))*np.cos(np.radians(la2))*np.sin(dlon/2)**2
        return R*2*np.arcsin(np.sqrt(a))
    D=np.zeros((len(pop),len(st)))
    for i,(_,s) in enumerate(st.iterrows()):
        D[:,i]=hav(s["lon"],s["lat"],pop["longitude"].values,pop["latitude"].values)
    ni=D.argmin(axis=1)
    pop=pop.copy(); pop["sid"]=st["id"].values[ni]; pop["sname"]=st["name_en"].values[ni]
    pop["area"]=st["area_type"].values[ni]; pop["stype"]=st["station_type"].values[ni]
    tot=pop["population"].sum(); road=pop[pop["stype"]=="ROADSIDE"]["population"].sum()
    gt={'v':float(road/tot)}
    errs=[]
    v=runtime.retrieve("roadside_pop_share")
    if v is None: return ValidatorResult(False,"roadside_pop_share not set",variables_not_set=True)
    if not is_finite_number(v): return ValidatorResult(False,f"roadside_pop_share not numeric: {v!r}")
    if not compare_numeric(float(v),float(gt["v"]),tolerance=0.002): errs.append(f"roadside_pop_share={round(float(v),3)}, expected ~{round(float(gt['v']),3)} (tol 0.002)")
    if errs: return ValidatorResult(False,"Custom validator failed: "+"; ".join(errs))
    return ValidatorResult(True,"OK")


tools = []
variables = [
    Variable("roadside_pop_share", None, "fraction of total grid population nearest to a roadside station, 4dp"),
]
validators = {"validate_hk_pop_roadside_share": validate_hk_pop_roadside_share}
