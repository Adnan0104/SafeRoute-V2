"""SafeRoute V2 — Health check endpoint."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Return application health status.

    This is the first endpoint to verify the backend is running.
    Database and routing provider checks will be added in milestone M2.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "data": {
            "version": settings.app_version,
            "database": "not_configured",  # Will connect in M2
            "routing_provider": "not_configured",  # Will connect in M3
        },
    }
