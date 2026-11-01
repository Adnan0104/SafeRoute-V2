"""SafeRoute V2 — Health check endpoint."""

from typing import Any

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.database import check_database_health

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Return application health status.

    Provides honest reporting of database and routing provider configuration/connectivity.
    """
    settings = get_settings()
    db_status = await check_database_health()
    return {
        "status": "ok",
        "data": {
            "version": settings.app_version,
            "database": db_status,
            "routing_provider": "not_configured",  # Will connect in milestone M3
        },
    }
