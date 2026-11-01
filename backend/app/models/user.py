"""SafeRoute V2 — User model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Index, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.safety_report import SafetyReport


class User(Base):
    """User account synced from Clerk authentication.

    Avoids storing sensitive personal information (no passwords, payment details,
    or phone numbers). Authentication is delegated to Clerk.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    clerk_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="External Clerk user identifier (e.g. user_2...)",
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=True,
        comment="User email address synced from Clerk",
    )

    display_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Public display name chosen by user",
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="user",
        server_default="user",
        comment="User role ('user' | 'admin')",
    )

    preferences: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
        comment="User application preferences (e.g. default travel mode, avoidance)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    safety_reports: Mapped[list["SafetyReport"]] = relationship(
        "SafetyReport",
        foreign_keys="SafetyReport.reporter_id",
        back_populates="reporter",
        cascade="all, delete-orphan",
    )

    moderated_reports: Mapped[list["SafetyReport"]] = relationship(
        "SafetyReport",
        foreign_keys="SafetyReport.moderated_by_id",
        back_populates="moderator",
    )

    __table_args__ = (
        Index("idx_users_role", "role"),
        Index("idx_users_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} clerk_id={self.clerk_id} role={self.role}>"
