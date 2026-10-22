"""File-backed Beijing datasets, and the named handles a suite can expose.

Every value an agent sees is a pandas frame read from `data/beijing/`, copied
from AirBench's `datasets/Beijing/` (provenance in `*.sources.json`). There is
no database, so ground truth cannot drift between runs. Loaders are cached, so
an agent's frame and a validator's read of the same file are one object, and
they read each file exactly as AirBench's domain module does.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import cache
from typing import Any

import pandas as pd

from settings import settings

DATA_DIR = settings.data_dir / "beijing"

_STATION_DTYPES = {
    "station_code": "string",
    "site_district_code": "string",
    "coordinate_district_code": "string",
}


@cache
def _csv(name: str) -> pd.DataFrame:
    dtype = _STATION_DTYPES if name == "station_metadata.csv" else None
    return pd.read_csv(DATA_DIR / name, dtype=dtype)


HANDLES: dict[str, Callable[[], Any]] = {
    "df": lambda: _csv("air_quality.csv"),
    "poi_df": lambda: _csv("poi.csv"),
    "pop_df": lambda: _csv("population_100m.csv"),
    "station_df": lambda: _csv("station_metadata.csv"),
    "met_df": lambda: _csv("met_era5.csv"),
    "profile_df": lambda: _csv("profile_era5.csv"),
    "cities_df": lambda: _csv("region_cities.csv"),
    "aerosol_df": lambda: _csv("aerosol_cams.csv"),
    "fire_df": lambda: _csv("fire_firms.csv"),
}
