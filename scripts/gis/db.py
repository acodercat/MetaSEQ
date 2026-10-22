"""Shared database engine and paths for the GIS map scripts (supp_maps.py, layer_maps.py).

The database URL is not stored here: it is read through phase2_benchmark/config.py from
phase2_benchmark/.env, which is gitignored. Run from this directory:

    cd scripts/gis
    uv run --with geopandas --with contextily --with osmnx \
           --with "psycopg[binary]" --with sqlalchemy --with pydantic-settings \
           python supp_maps.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # the MetaSEQ repo root
BENCHMARK = ROOT / "phase2_benchmark"

sys.path.insert(0, str(BENCHMARK))
from config import settings  # noqa: E402  (phase2_benchmark/config.py; URL from .env)

engine = create_engine(settings.hk_database_url)

# Large query caches live under phase2_benchmark/ (gitignored, multi-GB tolerated).
TRAFFIC_CACHE = BENCHMARK / "gis_cache" / "traffic_cache"
TRAFFIC_CACHE.mkdir(parents=True, exist_ok=True)

