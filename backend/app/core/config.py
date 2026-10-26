"""SafeRoute V2 — Core configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # General
    app_name: str = "SafeRoute V2"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://saferoute:password@localhost:5432/saferoute_dev"
    database_url_sync: str = "postgresql://saferoute:password@localhost:5432/saferoute_dev"

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
    }


def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
