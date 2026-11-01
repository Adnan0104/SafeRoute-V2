"""Unit tests for database session dependency, configuration, and health check."""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import (
    check_database_health,
    check_postgis_support,
    get_db,
)


class TestDatabaseConfig:
    """Tests for database settings and URL normalization."""

    def test_unconfigured_database_url(self) -> None:
        settings = Settings(database_url=None)
        assert settings.is_database_configured is False
        assert settings.async_database_url is None
        assert settings.sync_database_url is None

    def test_empty_database_url(self) -> None:
        settings = Settings(database_url="   ")
        assert settings.is_database_configured is False
        assert settings.async_database_url is None

    def test_postgres_url_converted_to_asyncpg(self) -> None:
        settings = Settings(
            database_url="postgresql://user:pass@localhost:5432/saferoute"
        )
        assert settings.is_database_configured is True
        assert (
            settings.async_database_url
            == "postgresql+asyncpg://user:pass@localhost:5432/saferoute"
        )
        assert (
            settings.sync_database_url
            == "postgresql://user:pass@localhost:5432/saferoute"
        )

    def test_postgres_legacy_scheme_converted(self) -> None:
        settings = Settings(database_url="postgres://user:pass@localhost:5432/saferoute")
        assert (
            settings.async_database_url
            == "postgresql+asyncpg://user:pass@localhost:5432/saferoute"
        )
        assert (
            settings.sync_database_url
            == "postgresql://user:pass@localhost:5432/saferoute"
        )

    def test_already_asyncpg_scheme_preserved(self) -> None:
        settings = Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/saferoute"
        )
        assert (
            settings.async_database_url
            == "postgresql+asyncpg://user:pass@localhost:5432/saferoute"
        )
        assert (
            settings.sync_database_url
            == "postgresql://user:pass@localhost:5432/saferoute"
        )


class TestDatabaseHealth:
    """Tests for honest health check reporting."""

    @pytest.mark.asyncio
    async def test_health_reports_not_configured_when_no_url(self) -> None:
        with patch("app.core.database.get_settings") as mock_settings:
            mock_settings.return_value = Settings(database_url=None)
            status = await check_database_health()
            assert status == "not_configured"

    @pytest.mark.asyncio
    async def test_health_reports_connected_when_ping_succeeds(self) -> None:
        with patch("app.core.database.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                database_url="postgresql+asyncpg://user:pass@localhost/db"
            )
            mock_engine = MagicMock()
            mock_conn = AsyncMock()
            mock_engine.connect.return_value.__aenter__.return_value = mock_conn

            with patch("app.core.database.get_engine", return_value=mock_engine):
                status = await check_database_health()
                assert status == "connected"

    @pytest.mark.asyncio
    async def test_health_reports_unhealthy_when_ping_fails(self) -> None:
        with patch("app.core.database.get_settings") as mock_settings:
            mock_settings.return_value = Settings(
                database_url="postgresql+asyncpg://user:pass@localhost/db"
            )
            mock_engine = MagicMock()
            mock_engine.connect.side_effect = ConnectionRefusedError(
                "Connection refused"
            )

            with patch("app.core.database.get_engine", return_value=mock_engine):
                status = await check_database_health()
                assert status == "unhealthy"


class TestDatabaseSessionDependency:
    """Tests for FastAPI get_db dependency injection."""

    @pytest.mark.asyncio
    async def test_get_db_raises_when_unconfigured(self) -> None:
        with patch("app.core.database.get_settings") as mock_settings:
            mock_settings.return_value = Settings(database_url=None)
            with pytest.raises(RuntimeError, match="Database is not configured"):
                async for _ in get_db():
                    pass

    def test_dependency_override_in_fastapi(self) -> None:
        """Verify that get_db can be cleanly overridden in FastAPI test client."""
        app = FastAPI()

        @app.get("/items")
        async def read_items(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
            return {"status": "ok"}

        mock_session = AsyncMock(spec=AsyncSession)

        async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
            yield mock_session

        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)
        response = client.get("/items")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestPostGISSupportCheck:
    """Tests for PostGIS extension detection."""

    @pytest.mark.asyncio
    async def test_postgis_installed(self) -> None:
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = "3.4.0"
        mock_conn.execute.return_value = mock_result

        result = await check_postgis_support(mock_conn)
        assert result["available"] is True
        assert result["installed"] is True
        assert result["version"] == "3.4.0"

    @pytest.mark.asyncio
    async def test_postgis_available_but_not_installed(self) -> None:
        mock_conn = AsyncMock()
        # First query for pg_extension returns None
        # Second query for pg_available_extensions returns version
        mock_result1 = MagicMock()
        mock_result1.scalar.return_value = None
        mock_result2 = MagicMock()
        mock_result2.scalar.return_value = "3.4.0"
        mock_conn.execute.side_effect = [mock_result1, mock_result2]

        result = await check_postgis_support(mock_conn)
        assert result["available"] is True
        assert result["installed"] is False
        assert result["version"] == "3.4.0"
