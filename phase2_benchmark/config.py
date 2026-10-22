import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent
MODELS_TOML = PROJECT_ROOT / "models.toml"
# The 50 tasks of experiment 1; overridable with the BENCHMARKS_JSON env var.
BENCHMARKS_JSON = Path(os.environ.get("BENCHMARKS_JSON", PROJECT_ROOT / "benchmarks_metaseq.json"))


class Settings(BaseSettings):
    """Application settings, read from environment variables or a local .env
    file (see .env.example). No credentials are stored in code."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Hong Kong database configuration, e.g. postgresql+psycopg://user:pass@host:port/db
    hk_database_url: str = ""

    # Hebei province database configuration
    hb_database_url: str = ""

    google_places_api_key: str = Field(
        default="",
        description="Google Places API key for location search",
    )


settings = Settings()
