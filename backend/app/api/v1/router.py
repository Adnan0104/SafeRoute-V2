"""SafeRoute V2 — API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()

# Health check — always available first
api_router.include_router(health.router, tags=["health"])
