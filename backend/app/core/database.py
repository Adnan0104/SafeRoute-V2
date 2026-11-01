"""SafeRoute V2 — Database configuration and session management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""

    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Get or create the global async SQLAlchemy engine."""
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        if not settings.is_database_configured or not settings.async_database_url:
            raise RuntimeError(
                "Database is not configured. Set DATABASE_URL in the environment."
            )
        _engine = create_async_engine(
            settings.async_database_url,
            echo=settings.debug,
            future=True,
            pool_pre_ping=True,
        )
        _session_factory = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory."""
    global _session_factory
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for obtaining an async database session.

    Yields an active database session that automatically commits on success
    or rolls back on unhandled exceptions.
    """
    settings = get_settings()
    if not settings.is_database_configured:
        raise RuntimeError("Database is not configured.")

    session_maker = get_session_factory()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for obtaining an async database session outside of FastAPI DI."""
    session_maker = get_session_factory()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_health() -> str:
    """Check database connection health honestly.

    Returns:
        "connected" if the database responds to a ping.
        "not_configured" if DATABASE_URL is not set.
        "unhealthy" if configured but connection fails.
    """
    settings = get_settings()
    if not settings.is_database_configured:
        return "not_configured"

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "connected"
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return "unhealthy"


async def check_postgis_support(connection: AsyncConnection) -> dict[str, Any]:
    """Verify whether PostGIS extension is available or installed on PostgreSQL.

    Returns a dict with 'available', 'installed', and 'version' info.
    """
    try:
        # Check if already installed
        result = await connection.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
        )
        installed_version = result.scalar()
        if installed_version:
            return {"available": True, "installed": True, "version": installed_version}

        # Check if available in pg_available_extensions
        avail_result = await connection.execute(
            text(
                "SELECT default_version FROM pg_available_extensions WHERE name = 'postgis'"
            )
        )
        avail_version = avail_result.scalar()
        if avail_version:
            return {"available": True, "installed": False, "version": avail_version}

        return {"available": False, "installed": False, "version": None}
    except Exception as exc:
        logger.warning("PostGIS check query failed: %s", exc)
        return {"available": False, "installed": False, "error": str(exc)}
