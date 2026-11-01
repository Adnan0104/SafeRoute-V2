"""SafeRoute V2 — Core configuration."""

from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # General
    app_name: str = "SafeRoute V2"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str | None = None
    database_url_sync: str | None = None
    database_url_test: str | None = None

    # Mapbox
    mapbox_access_token: str = ""
    mapbox_secret_token: str = ""

    # Clerk Auth
    clerk_secret_key: str = ""
    clerk_webhook_secret: str = ""

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Security
    secret_key: str = "change-me-to-a-random-secret-string"

    # Rate limiting
    rate_limit_per_minute: int = 60

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_database_configured(self) -> bool:
        """Check whether a database URL has been explicitly configured."""
        return bool(self.database_url and self.database_url.strip())

    @computed_field  # type: ignore[prop-decorator]
    @property
    def async_database_url(self) -> str | None:
        """Return database URL normalized for asyncpg driver."""
        if not self.database_url or not self.database_url.strip():
            return None
        url = self.database_url.strip()
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        if url.startswith("postgresql://") and not url.startswith("postgresql+"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str | None:
        """Return database URL normalized for sync drivers (e.g., Alembic / psycopg)."""
        if self.database_url_sync and self.database_url_sync.strip():
            return self.database_url_sync.strip()
        if not self.database_url or not self.database_url.strip():
            return None
        url = self.database_url.strip()
        if "+asyncpg" in url:
            return url.replace("+asyncpg", "")
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql://", 1)
        return url


def get_settings() -> Settings:
    """Return settings instance."""
    return Settings()
