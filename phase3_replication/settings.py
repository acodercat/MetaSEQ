"""Project paths and `METASEQ_*` environment settings.

Secrets have no defaults. Nothing here connects to anything: a missing
database URL is reported when something actually needs the database
(`require`), so listing suites and running unit tests work offline.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from errors import ConfigurationError

PROJECT_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="METASEQ_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    hk_database_url: str | None = None
    google_places_api_key: str | None = None

    models_toml: Path = PROJECT_ROOT / "models.toml"
    results_dir: Path = PROJECT_ROOT / "results"
    suites_dir: Path = PROJECT_ROOT / "suites"
    configs_dir: Path = PROJECT_ROOT / "configs"
    data_dir: Path = PROJECT_ROOT / "data"

    def require(self, field: str) -> str:
        """The value of a secret-bearing field, or a clear error naming its variable."""
        value = getattr(self, field)
        if not value:
            raise ConfigurationError(
                f"METASEQ_{field.upper()} is not set (see .env.example)"
            )
        return value


settings = Settings()
