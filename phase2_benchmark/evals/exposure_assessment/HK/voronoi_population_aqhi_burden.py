
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
    pop = pd.read_csv(PROJECT_ROOT / "datasets" / "HK_population_1km.csv")
    stations = pd.read_sql(text("""
        SELECT name_en, ST_X(coordinate::geometry) AS lon, ST_Y(coordinate::geometry) AS lat
        FROM air_quality_station
    """), engine)

    all_dists = np.zeros((len(pop), len(stations)))
    for i, (_, s) in enumerate(stations.iterrows()):
        all_dists[:, i] = _haversine(s["lon"], s["lat"], pop["longitude"].values, pop["latitude"].values)

    nearest_idx = all_dists.argmin(axis=1)
    pop_copy = pop.copy()
    pop_copy["nearest"] = [stations.iloc[i]["name_en"] for i in nearest_idx]
    served = pop_copy.groupby("nearest")["population"].sum()

    aqhi = pd.read_sql(text("""
        SELECT s.name_en, ROUND(AVG(h.aqhi)::numeric, 1) AS avg_aqhi
        FROM hourly_station_air_quality h
        JOIN air_quality_station s ON h.station_id = s.id
        WHERE h.datetime >= '2025-07-01' AND h.datetime < '2025-08-01' AND h.aqhi IS NOT NULL
        GROUP BY s.name_en
    """), engine)
    aqhi_map = dict(zip(aqhi["name_en"], aqhi["avg_aqhi"]))

    return served, aqhi_map


def validate_t1(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    most_s = runtime.retrieve("most_served_station")
    most_p = runtime.retrieve("most_served_pop")
    least_s = runtime.retrieve("least_served_station")
    least_p = runtime.retrieve("least_served_pop")

    served, _ = _compute_ground_truth()
    exp_most = served.idxmax()
    exp_most_p = int(served.max())
    exp_least = served.idxmin()
    exp_least_p = int(served.min())

    errors = []
    if most_s is None:
        return ValidatorResult(False, "most_served_station not set", variables_not_set=True)
    if str(most_s).strip() != exp_most:
        errors.append(f"most_served_station='{most_s}', expected '{exp_most}'")

    if most_p is None:
        return ValidatorResult(False, "most_served_pop not set", variables_not_set=True)
    if not is_finite_number(most_p):
        errors.append("most_served_pop should be numeric")
    elif abs(int(most_p) - exp_most_p) / exp_most_p > 0.05:
        errors.append(f"most_served_pop={int(most_p)}, expected ~{exp_most_p}")

    if least_s is None:
        return ValidatorResult(False, "least_served_station not set", variables_not_set=True)
    if str(least_s).strip() != exp_least:
        errors.append(f"least_served_station='{least_s}', expected '{exp_least}'")

    if least_p is None:
        return ValidatorResult(False, "least_served_pop not set", variables_not_set=True)
    if not is_finite_number(least_p):
        errors.append("least_served_pop should be numeric")
    elif abs(int(least_p) - exp_least_p) / exp_least_p > 0.1:
        errors.append(f"least_served_pop={int(least_p)}, expected ~{exp_least_p}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: most={exp_most}({exp_most_p}), least={exp_least}({exp_least_p})")


def validate_t2(response: str, runtime: IPythonRuntime, turn: Turn) -> ValidatorResult:
    station = runtime.retrieve("highest_burden_station")
    burden = runtime.retrieve("highest_burden_value")
    pop_val = runtime.retrieve("highest_burden_pop")
    aqhi_val = runtime.retrieve("highest_burden_aqhi")

    served, aqhi_map = _compute_ground_truth()
    burdens = {s: int(served[s] * aqhi_map.get(s, 0)) for s in served.index}
    exp_station = max(burdens, key=burdens.get)
    exp_burden = burdens[exp_station]
    exp_pop = int(served[exp_station])
    exp_aqhi = float(aqhi_map[exp_station])

    errors = []
    if station is None:
        return ValidatorResult(False, "highest_burden_station not set", variables_not_set=True)
    if str(station).strip() != exp_station:
        errors.append(f"highest_burden_station='{station}', expected '{exp_station}'")

    if burden is None:
        return ValidatorResult(False, "highest_burden_value not set", variables_not_set=True)
    if not is_finite_number(burden):
        errors.append("highest_burden_value should be numeric")
    elif abs(int(burden) - exp_burden) / exp_burden > 0.05:
        errors.append(f"highest_burden_value={int(burden)}, expected ~{exp_burden}")

    if pop_val is None:
        return ValidatorResult(False, "highest_burden_pop not set", variables_not_set=True)
    if not is_finite_number(pop_val):
        errors.append("highest_burden_pop should be numeric")
    elif abs(int(pop_val) - exp_pop) / exp_pop > 0.05:
        errors.append(f"highest_burden_pop={int(pop_val)}, expected ~{exp_pop}")

    if aqhi_val is None:
        return ValidatorResult(False, "highest_burden_aqhi not set", variables_not_set=True)
    if not is_finite_number(aqhi_val):
        errors.append("highest_burden_aqhi should be numeric")
    elif abs(aqhi_val - exp_aqhi) > 0.2:
        errors.append(f"highest_burden_aqhi={aqhi_val}, expected ~{exp_aqhi}")

    if errors:
        return ValidatorResult(False, "; ".join(errors))
    return ValidatorResult(True, f"Correct: {exp_station} burden={exp_burden}")


tools = []
variables = [
    Variable("most_served_station", None, "Store the station serving the largest population (str)."),
    Variable("most_served_pop", None, "Store that station's served population (int)."),
    Variable("least_served_station", None, "Store the station serving the smallest population (str)."),
    Variable("least_served_pop", None, "Store that station's served population (int)."),
    Variable("highest_burden_station", None, "Store the station with highest AQHI burden (str)."),
    Variable("highest_burden_value", None, "Store the burden value (int)."),
    Variable("highest_burden_pop", None, "Store that station's served population (int)."),
    Variable("highest_burden_aqhi", None, "Store that station's average AQHI (float, 1dp)."),
]
validators = {"validate_t1": validate_t1, "validate_t2": validate_t2}
