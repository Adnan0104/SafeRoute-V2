"""SafeRoute V2 — SafetyReport model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base
from app.models.types import PointGeometry

if TYPE_CHECKING:
    from app.models.user import User


class SafetyReport(Base):
    """Community-submitted and open-data incident safety report.

    Supports spatial indexing via PostGIS Point geometry and latitude/longitude
    coordinates for corridor queries and verification workflows.
    """

    __tablename__ = "safety_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Incident category (e.g. poor_lighting, traffic_hazard)",
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="moderate",
        server_default="moderate",
        comment="Incident severity: 'low' | 'moderate' | 'high'",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Detailed description of the safety concern",
    )

    # Geospatial location
    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="WGS84 latitude coordinate (-90 to 90)",
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="WGS84 longitude coordinate (-180 to 180)",
    )

    location: Mapped[Any | None] = mapped_column(
        PointGeometry(srid=4326),
        nullable=True,
        comment="PostGIS geometry point (SRID 4326: WGS84)",
    )

    # Timestamps
    occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the incident occurred, if known",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        index=True,
        comment="When this report was submitted",
    )

    # Verification / Moderation
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending_review",
        server_default="pending_review",
        index=True,
        comment="Moderation status: 'pending_review' | 'approved' | 'rejected'",
    )

    moderated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when moderation decision was recorded",
    )

    moderated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="ID of the admin user who reviewed this report",
    )

    moderation_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal review or justification note",
    )

    # Provenance metadata
    reporter_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who submitted this report (null if anonymous/external)",
    )

    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="community",
        server_default="community",
        comment="Data origin ('community' | 'open_data' | 'partner')",
    )

    provenance_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Origin metadata (e.g. data source license, client app version)",
    )

    # Relationships
    reporter: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[reporter_id],
        back_populates="safety_reports",
    )

    moderator: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[moderated_by_id],
        back_populates="moderated_reports",
    )

    __table_args__ = (
        CheckConstraint(
            "latitude >= -90.0 AND latitude <= 90.0",
            name="ck_safety_reports_latitude_range",
        ),
        CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0",
            name="ck_safety_reports_longitude_range",
        ),
        CheckConstraint(
            "severity IN ('low', 'moderate', 'high')",
            name="ck_safety_reports_severity",
        ),
        CheckConstraint(
            "status IN ('pending_review', 'approved', 'rejected')",
            name="ck_safety_reports_status",
        ),
        Index("idx_safety_reports_status_created", "status", "created_at"),
        Index("idx_safety_reports_category_status", "category", "status"),
        Index("idx_safety_reports_lat_lng", "latitude", "longitude"),
    )

    def __repr__(self) -> str:
        return (
            f"<SafetyReport id={self.id} category={self.category} status={self.status}>"
        )
