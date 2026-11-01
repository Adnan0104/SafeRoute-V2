"""SafeRoute V2 — RoutesCache model."""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


class RoutesCache(Base):
    """Cached route geometries and directions API responses.

    Supports provider tracking, route parameters hashing, TTL expiry,
    and granular invalidation (e.g. when new severe incidents are reported).
    """

    __tablename__ = "routes_cache"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    cache_key: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="SHA-256 hash of normalized provider and route parameters",
    )

    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="mapbox",
        server_default="mapbox",
        index=True,
        comment="Routing data provider (e.g. 'mapbox')",
    )

    origin_lat: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Origin latitude coordinate",
    )

    origin_lng: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Origin longitude coordinate",
    )

    destination_lat: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Destination latitude coordinate",
    )

    destination_lng: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Destination longitude coordinate",
    )

    travel_mode: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="driving",
        server_default="driving",
        comment="Travel mode ('driving' | 'walking' | 'cycling')",
    )

    route_parameters: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Input parameters passed to routing provider (alternatives, corridor, etc.)",
    )

    route_response: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        comment="Cached provider response payload including geometries and steps",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Expiration timestamp based on TTL policy",
    )

    is_valid: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
        comment="Whether this cached entry is valid or has been invalidated",
    )

    invalidated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when this cache entry was invalidated",
    )

    invalidation_reason: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Reason for invalidation (e.g. 'hazard_reported', 'manual_refresh')",
    )

    __table_args__ = (
        CheckConstraint(
            "origin_lat >= -90.0 AND origin_lat <= 90.0",
            name="ck_routes_cache_origin_lat",
        ),
        CheckConstraint(
            "origin_lng >= -180.0 AND origin_lng <= 180.0",
            name="ck_routes_cache_origin_lng",
        ),
        CheckConstraint(
            "destination_lat >= -90.0 AND destination_lat <= 90.0",
            name="ck_routes_cache_dest_lat",
        ),
        CheckConstraint(
            "destination_lng >= -180.0 AND destination_lng <= 180.0",
            name="ck_routes_cache_dest_lng",
        ),
        Index("idx_routes_cache_provider_expires", "provider", "expires_at"),
        Index("idx_routes_cache_lookup", "cache_key", "is_valid"),
    )

    @classmethod
    def generate_cache_key(
        cls,
        provider: str,
        origin_lat: float,
        origin_lng: float,
        destination_lat: float,
        destination_lng: float,
        travel_mode: str,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        """Generate a deterministic 64-character SHA-256 cache key."""
        payload = {
            "provider": provider.lower().strip(),
            "origin": [round(origin_lat, 6), round(origin_lng, 6)],
            "destination": [round(destination_lat, 6), round(destination_lng, 6)],
            "mode": travel_mode.lower().strip(),
            "params": parameters or {},
        }
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def is_expired(self, now: datetime | None = None) -> bool:
        """Check whether this cache entry has expired."""
        current_time = now or datetime.now(UTC)
        if self.expires_at.tzinfo is None:
            # Assume UTC if naive
            return current_time.replace(tzinfo=None) >= self.expires_at
        return current_time >= self.expires_at

    def invalidate(self, reason: str = "manual_invalidation") -> None:
        """Mark this cache entry as invalidated."""
        self.is_valid = False
        self.invalidated_at = datetime.now(UTC)
        self.invalidation_reason = reason

    def __repr__(self) -> str:
        key_preview = self.cache_key[:12]
        return f"<RoutesCache key={key_preview}... provider={self.provider} valid={self.is_valid}>"
