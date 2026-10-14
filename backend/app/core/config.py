"""Application settings, loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration.

    Values are read from the environment or from a local `.env` file. Every
    setting that changes behaviour between environments belongs here.
    """

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "ERP-Lite API"
    app_version: str = "0.2.0"
    environment: str = "development"
    debug: bool = True
    # Separate from `debug`: logging every statement drowns CLI tools like the
    # seeder, which do not need it.
    sql_echo: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Database ---
    # SQLite by default so the project runs with zero external services.
    # Switch to PostgreSQL by setting DATABASE_URL, for example:
    #   postgresql+psycopg://erp:erp@localhost:5432/erp_lite
    database_url: str = Field(
        default=f"sqlite:///{BACKEND_ROOT / 'erp_lite.db'}",
    )

    # --- Security ---
    # Override this in every non-local environment. HS256 requires at least
    # 32 bytes; the placeholder is long enough to avoid a runtime warning.
    secret_key: str = "dev-only-insecure-key-change-me-0123456789abcdef"
    access_token_expire_minutes: int = 60 * 12
    algorithm: str = "HS256"

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:3000"]

    # --- Multi-tenancy ---
    default_company: str = "DEMO_SL"

    @field_validator("database_url")
    @classmethod
    def _normalise_sqlite_url(cls, value: str) -> str:
        """Allow a bare path to be used as DATABASE_URL for convenience."""
        if value.endswith(".db") or value.endswith(".sqlite"):
            return value
        if "://" not in value:
            return f"sqlite:///{value}"
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_in_memory(self) -> bool:
        """Whether the database lives in memory rather than on disk."""
        return self.database_url in ("sqlite://", "sqlite:///:memory:")


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance.

    Cached so that dependencies resolving settings during a request all share
    the same object and connection configuration.
    """
    return Settings()


settings = get_settings()