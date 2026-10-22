
import numpy as np
import pandas as pd
from sqlalchemy import text

from cave_agent.runtime import IPythonRuntime, Variable
from domains.HK.db import engine
from core.types import Turn
from core.validation import ValidatorResult, is_finite_number
def validate_thiessen(
    response: str,
    runtime: IPythonRuntime,
    turn: Turn,
) -> ValidatorResult:
    largest_name = runtime.retrieve("largest_cell_station_name")
    largest_area = runtime.retrieve("largest_cell_area_km2")
    smallest_name = runtime.retrieve("smallest_cell_station_name")
    smallest_area = runtime.retrieve("smallest_cell_area_km2")

    # Compute Voronoi cell areas using PostGIS ST_VoronoiPolygons and clip to
    # the axis-aligned bounding box of all stations (the query's intent).
    # PostGIS's `extend_to` parameter on ST_VoronoiPolygons does not clip the
    # output cells — infinite outer cells still extend beyond the extent —
    # so an explicit ST_Intersection is required for accurate cell areas.
    stations = pd.read_sql(
        text("""
            WITH pts AS (
                SELECT id, name_en, coordinate::geometry AS geom
                FROM air_quality_station
            ),
            collected AS (
                SELECT ST_Collect(geom) AS geom, ST_Envelope(ST_Collect(geom)) AS bbox
                FROM pts
            ),
            voronoi AS (
                SELECT (ST_Dump(ST_VoronoiPolygons(collected.geom))).geom AS cell,
                       collected.bbox
                FROM collected
            ),
            clipped AS (
                SELECT ST_Intersection(cell, bbox) AS cell FROM voronoi
            ),
            matched AS (
                SELECT p.id, p.name_en,
                       ST_Area(c.cell::geography) / 1e6 AS cell_area_km2
                FROM clipped c
                JOIN pts p ON ST_Contains(c.cell, p.geom)
            )
            SELECT id, name_en, cell_area_km2 FROM matched ORDER BY id
        """),
        engine,
    )
    max_idx = stations["cell_area_km2"].idxmax()
    min_idx = stations["cell_area_km2"].idxmin()

    expected_largest_name = stations.loc[max_idx, "name_en"]
    expected_largest_area = round(stations.loc[max_idx, "cell_area_km2"], 1)
    expected_smallest_name = stations.loc[min_idx, "name_en"]
    expected_smallest_area = round(stations.loc[min_idx, "cell_area_km2"], 1)

    # Accept any station whose area is within 5% of the expected extreme
    largest_names = set(
        stations[abs(stations["cell_area_km2"] - stations["cell_area_km2"].max()) / max(stations["cell_area_km2"].max(), 0.01) <= 0.05]["name_en"]
        .str.strip().str.lower()
    )
    smallest_names = set(
        stations[abs(stations["cell_area_km2"] - stations["cell_area_km2"].min()) / max(stations["cell_area_km2"].min(), 0.01) <= 0.05]["name_en"]
        .str.strip().str.lower()
    )

    errors = []

    if largest_name is None:
        return ValidatorResult(False, "largest_cell_station_name not set", variables_not_set=True)
    if not isinstance(largest_name, str):
        errors.append(f"largest_cell_station_name should be str, got {type(largest_name).__name__}")
    elif largest_name.strip().lower() not in largest_names:
        errors.append(f"largest_cell_station_name='{largest_name}', expected '{expected_largest_name}'")

    if largest_area is None:
        return ValidatorResult(False, "largest_cell_area_km2 not set", variables_not_set=True)
    if not is_finite_number(largest_area):
        errors.append(f"largest_cell_area_km2 should be numeric, got {type(largest_area).__name__}")
    elif abs(largest_area - expected_largest_area) / max(expected_largest_area, 0.01) > 0.15:
        errors.append(f"largest_cell_area_km2={largest_area}, expected ≈ {expected_largest_area} (±15%)")

    if smallest_name is None:
        return ValidatorResult(False, "smallest_cell_station_name not set", variables_not_set=True)
    if not isinstance(smallest_name, str):
        errors.append(f"smallest_cell_station_name should be str, got {type(smallest_name).__name__}")
    elif smallest_name.strip().lower() not in smallest_names:
        errors.append(f"smallest_cell_station_name='{smallest_name}', expected '{expected_smallest_name}'")

    if smallest_area is None:
        return ValidatorResult(False, "smallest_cell_area_km2 not set", variables_not_set=True)
    if not is_finite_number(smallest_area):
        errors.append(f"smallest_cell_area_km2 should be numeric, got {type(smallest_area).__name__}")
    elif abs(smallest_area - expected_smallest_area) / max(expected_smallest_area, 0.01) > 0.15:
        errors.append(f"smallest_cell_area_km2={smallest_area}, expected ≈ {expected_smallest_area} (±15%)")

    if errors:
        return ValidatorResult(False, "; ".join(errors))

    return ValidatorResult(True, f"Correct: largest={largest_name}({largest_area}km²), smallest={smallest_name}({smallest_area}km²)")

tools = []
variables = [
    Variable("largest_cell_station_name", None, "Store the name of the station with the largest Voronoi cell (str)."),
    Variable("largest_cell_area_km2", None, "Store the area of the largest cell in km² rounded to 1 decimal place (float)."),
    Variable("smallest_cell_station_name", None, "Store the name of the station with the smallest Voronoi cell (str)."),
    Variable("smallest_cell_area_km2", None, "Store the area of the smallest cell in km² rounded to 1 decimal place (float)."),
]
validators = {
    "validate_thiessen": validate_thiessen,
}
