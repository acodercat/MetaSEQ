"""File-backed Hong Kong datasets, and the named handles a suite can expose.

A suite's environment lists runtime variables by name; `HANDLES` maps
each name to the loader that produces its value. Loaders are cached, so an
agent's `pop_df` and a validator's `load_population()` are the same frame.
Provenance for every file is in `data/hk/*.sources.json`.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import cache
from typing import Any

import pandas as pd

from settings import settings

DATA_DIR = settings.data_dir / "hk"


@cache
def load_population() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "population_1km.csv")


@cache
def _csv(name: str, date_column: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, parse_dates=[date_column])


def _engine() -> Any:
    from domains.hk.db import engine

    return engine


HANDLES: dict[str, Callable[[], Any]] = {
    "engine": _engine,
    "pop_df": load_population,
    "sounding_df": lambda: _csv("profile_sounding.csv", "datetime"),
    "sounding_index_df": lambda: _csv("sounding_indices.csv", "datetime"),
    "radiation_df": lambda: _csv("radiation_hko.csv", "date"),
    "radiation_hourly_df": lambda: _csv("radiation_1min_hko.csv", "observed"),
    "met_df": lambda: _csv("met_era5.csv", "datetime"),
}
