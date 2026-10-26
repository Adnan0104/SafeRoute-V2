"""SafeRoute V2 — Pydantic schemas for API requests and responses.

These schemas define the API contract and are used for both
request validation and response serialization.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ── Common ────────────────────────────────────────────────────


class Coordinates(BaseModel):
    """Geographic coordinates."""

    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")


class ApiResponse(BaseModel):
    """Standard API response envelope."""

    status: str = "ok"
    data: dict | list | None = None
    error: dict | None = None


# ── Route Search ──────────────────────────────────────────────


class TravelMode(str, Enum):
    """Supported travel modes."""

    DRIVING = "driving"
    WALKING = "walking"
    CYCLING = "cycling"


class RouteSearchRequest(BaseModel):
    """Request body for route search."""

    origin: Coordinates
    destination: Coordinates
    mode: TravelMode = TravelMode.DRIVING
    alternatives: bool = True
    safety_corridor_m: int = Field(
        default=200,
        ge=50,
        le=1000,
        description="Corridor width in meters for safety data lookup",
    )


class SafetyFactor(BaseModel):
    """Individual factor contributing to safety score."""

    name: str
    label: str
    value: float
    unit: str
    impact: str  # "positive" | "negative" | "neutral"
    description: str


class DataCoverage(BaseModel):
    """Information about safety data coverage for a route."""

    reports_in_corridor: int
    corridor_width_m: int
    most_recent_report: datetime | None = None
    oldest_report: datetime | None = None


class SafetyInfo(BaseModel):
    """Safety assessment for a single route."""

    score: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Safety score 0-100, or null if insufficient data",
    )
    confidence: str = "none"  # "none" | "low" | "medium" | "high"
    data_coverage: DataCoverage
    factors: list[SafetyFactor] = []
    disclaimer: str = (
        "Safety information is based on community reports "
        "and may not reflect current conditions."
    )


class RouteTreatment(BaseModel):
    """Trade-off comparison against reference routes."""

    extra_duration_seconds: int = 0
    extra_distance_meters: int = 0


class TradeOffs(BaseModel):
    """Trade-offs comparing this route to alternatives."""

    vs_fastest: RouteTreatment = RouteTreatment()
    vs_safest: RouteTreatment = RouteTreatment()


class GeoJsonLineString(BaseModel):
    """GeoJSON LineString geometry."""

    type: str = "LineString"
    coordinates: list[list[float]]


class RouteResult(BaseModel):
    """A single route with safety information."""

    id: str
    geometry: GeoJsonLineString
    duration_seconds: int
    distance_meters: int
    summary: str
    safety: SafetyInfo
    trade_offs: TradeOffs = TradeOffs()


class RouteSearchMetadata(BaseModel):
    """Metadata about the route search."""

    origin_address: str | None = None
    destination_address: str | None = None
    routing_provider: str = "mapbox"
    computed_at: datetime


class RouteSearchResponse(BaseModel):
    """Response body for route search."""

    routes: list[RouteResult]
    metadata: RouteSearchMetadata


# ── Safety Reports ────────────────────────────────────────────


class ReportCategory(str, Enum):
    """Categories for community safety reports."""

    POOR_LIGHTING = "poor_lighting"
    TRAFFIC_HAZARD = "traffic_hazard"
    PEDESTRIAN_SAFETY = "pedestrian_safety"
    CRIME_INCIDENT = "crime_incident"
    ROAD_CONDITION = "road_condition"
    CONSTRUCTION = "construction"
    FLOODING = "flooding"
    OTHER = "other"


class ReportSeverity(str, Enum):
    """Severity levels for safety reports."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ReportStatus(str, Enum):
    """Moderation status for safety reports."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class CreateReportRequest(BaseModel):
    """Request body to create a safety report."""

    location: Coordinates
    category: ReportCategory
    severity: ReportSeverity
    description: str = Field(..., min_length=10, max_length=1000)
    occurred_at: datetime | None = None


class ModerateReportRequest(BaseModel):
    """Request body to moderate a safety report."""

    status: ReportStatus
    moderation_note: str | None = None
