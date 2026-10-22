
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from config import PROJECT_ROOT
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
from domains.HK.db import engine


def _haversine(lon1, lat1, lon2, lat2):
    R = 6371
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def _compute_ground_truth():
    pop_df = pd.read_csv(PROJECT_ROOT / "datasets" / "HK_population_1km.csv")
    stations = pd.read_sql(text("""
        SELECT name_en, area_type, ST_X(coordinate::geometry) AS lon, ST_Y(coordinate::geometry) AS lat
        FROM air_quality_station
    """), engine)
    pm25 = pd.read_sql(text("""
        SELECT s.name_en, s.area_type, ROUND(AVG(h.pm2_5)::numeric, 1) AS avg_pm25
        FROM hourly_station_air_quality h
        JOIN air_quality_station s ON h.station_id = s.id
        WHERE h.datetime >= '2025-10-01' AND h.datetime < '2025-11-01' AND h.pm2_5 IS NOT NULL
        GROUP BY s.name_en, s.area_type
    """), engine)

    pops_3km = {}
    for _, s in stations.iterrows():
        d = _haversine(s["lon"], s["lat"], pop_df["longitude"].values, pop_df["latitude"].values)
        pops_3km[s["name_en"]] = int(pop_df[d <= 3]["population"].sum())

    type_pm25 = {}
    type_pop = {}
    for atype in ["URBAN", "NEW_TOWN", "RURAL"]:
        subset = pm25[pm25["area_type"] == atype]
        type_pm25[atype] = round(float(subset["avg_pm25"].mean()), 1)
        # Unique population: cells within 3km of ANY station of this type
        type_stations = stations[stations["area_type"] == atype]
        within = np.zeros(len(pop_df), dtype=bool)
        for _, s in type_stations.iterrows():
            d = _haversine(s["lon"], s["lat"], pop_df["longitude"].values, pop_df["latitude"].values)
            within |= (d <= 3)
        type_pop[atype] = int(pop_df[within]["population"].sum())

    return type_pm25, type_pop


def validate_t1(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    urban = runtime.retrieve("urban_pm25")
    new_town = runtime.retrieve("new_town_pm25")
    rural = runtime.retrieve("rural_pm25")

    type_pm25, _ = _compute_ground_truth()

    errors = []
    for name, val, atype in [
        ("urban_pm25", urban, "URBAN"),
        ("new_town_pm25", new_town, "NEW_TOWN"),
        ("rural_pm25", rural, "RURAL"),
    ]:
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(val):
            errors.append(f"{name} should be numeric")
        elif abs(val - type_pm25[atype]) > 1.0:
            errors.append(f"{name}={val}, expected ~{type_pm25[atype]}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: URBAN={type_pm25['URBAN']}, NEW_TOWN={type_pm25['NEW_TOWN']}, RURAL={type_pm25['RURAL']}")


def validate_t2(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    u_pop = runtime.retrieve("urban_pop")
    nt_pop = runtime.retrieve("new_town_pop")
    r_pop = runtime.retrieve("rural_pop")
    highest = runtime.retrieve("highest_exposure_type")

    type_pm25, type_pop = _compute_ground_truth()
    exp_highest = max(type_pm25, key=type_pm25.get)

    errors = []
    for name, val, atype in [
        ("urban_pop", u_pop, "URBAN"),
        ("new_town_pop", nt_pop, "NEW_TOWN"),
        ("rural_pop", r_pop, "RURAL"),
    ]:
        if val is None:
            return ValidatorResult(False, f"{name} not set", variables_not_set=True)
        if not is_finite_number(val):
            errors.append(f"{name} should be numeric")
        elif abs(int(val) - type_pop[atype]) / max(type_pop[atype], 1) > 0.1:
            errors.append(f"{name}={int(val)}, expected ~{type_pop[atype]}")

    if highest is None:
        return ValidatorResult(False, "highest_exposure_type not set", variables_not_set=True)
    if str(highest).strip().upper().replace(" ", "_") != exp_highest:
        errors.append(f"highest_exposure_type='{highest}', expected '{exp_highest}'")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: highest={exp_highest}")


tools = []
variables = [
    Variable("urban_pm25", None, "Store the average PM2.5 for urban stations (float, 1dp)."),
    Variable("new_town_pm25", None, "Store the average PM2.5 for new town stations (float, 1dp)."),
    Variable("rural_pm25", None, "Store the average PM2.5 for rural stations (float, 1dp)."),
    Variable("urban_pop", None, "Store the total population within 3km of all urban stations (int)."),
    Variable("new_town_pop", None, "Store the total population within 3km of all new town stations (int)."),
    Variable("rural_pop", None, "Store the total population within 3km of the rural station (int)."),
    Variable("highest_exposure_type", None, "Store the area type with highest average PM2.5 (str)."),
]
validators = {"validate_t1": validate_t1, "validate_t2": validate_t2}
