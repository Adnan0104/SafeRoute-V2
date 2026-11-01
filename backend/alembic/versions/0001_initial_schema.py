"""Initial database schema with PostGIS support.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-01 19:30:00.000000
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enable PostGIS extension if available on PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "clerk_id",
            sa.String(length=255),
            nullable=False,
            comment="External Clerk user identifier (e.g. user_2...)",
        ),
        sa.Column(
            "email",
            sa.String(length=255),
            nullable=True,
            comment="User email address synced from Clerk",
        ),
        sa.Column(
            "display_name",
            sa.String(length=100),
            nullable=True,
            comment="Public display name chosen by user",
        ),
        sa.Column(
            "role",
            sa.String(length=50),
            server_default="user",
            nullable=False,
            comment="User role ('user' | 'admin')",
        ),
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="User application preferences",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clerk_id", name="uq_users_clerk_id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("idx_users_clerk_id", "users", ["clerk_id"], unique=True)
    op.create_index("idx_users_email", "users", ["email"], unique=True)
    op.create_index("idx_users_role", "users", ["role"])
    op.create_index("idx_users_created_at", "users", ["created_at"])

    # 3. Safety reports table
    op.create_table(
        "safety_reports",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "category",
            sa.String(length=50),
            nullable=False,
            comment="Incident category (e.g. poor_lighting, traffic_hazard)",
        ),
        sa.Column(
            "severity",
            sa.String(length=20),
            server_default="moderate",
            nullable=False,
            comment="Incident severity: 'low' | 'moderate' | 'high'",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=False,
            comment="Detailed description of the safety concern",
        ),
        sa.Column(
            "latitude",
            sa.Float(),
            nullable=False,
            comment="WGS84 latitude coordinate (-90 to 90)",
        ),
        sa.Column(
            "longitude",
            sa.Float(),
            nullable=False,
            comment="WGS84 longitude coordinate (-180 to 180)",
        ),
        sa.Column(
            "location",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=True,
            ),
            nullable=True,
            comment="PostGIS geometry point (SRID 4326: WGS84)",
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the incident occurred, if known",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="When this report was submitted",
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="pending_review",
            nullable=False,
            comment="Moderation status: 'pending_review' | 'approved' | 'rejected'",
        ),
        sa.Column(
            "moderated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when moderation decision was recorded",
        ),
        sa.Column(
            "moderated_by_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="ID of the admin user who reviewed this report",
        ),
        sa.Column(
            "moderation_note",
            sa.Text(),
            nullable=True,
            comment="Internal review or justification note",
        ),
        sa.Column(
            "reporter_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="User who submitted this report (null if anonymous/external)",
        ),
        sa.Column(
            "source",
            sa.String(length=50),
            server_default="community",
            nullable=False,
            comment="Data origin ('community' | 'open_data' | 'partner')",
        ),
        sa.Column(
            "provenance_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="Origin metadata",
        ),
        sa.CheckConstraint(
            "latitude >= -90.0 AND latitude <= 90.0",
            name="ck_safety_reports_latitude_range",
        ),
        sa.CheckConstraint(
            "longitude >= -180.0 AND longitude <= 180.0",
            name="ck_safety_reports_longitude_range",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'moderate', 'high')",
            name="ck_safety_reports_severity",
        ),
        sa.CheckConstraint(
            "status IN ('pending_review', 'approved', 'rejected')",
            name="ck_safety_reports_status",
        ),
        sa.ForeignKeyConstraint(
            ["moderated_by_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_safety_reports_category", "safety_reports", ["category"]
    )
    op.create_index("idx_safety_reports_status", "safety_reports", ["status"])
    op.create_index(
        "idx_safety_reports_created_at", "safety_reports", ["created_at"]
    )
    op.create_index(
        "idx_safety_reports_status_created",
        "safety_reports",
        ["status", "created_at"],
    )
    op.create_index(
        "idx_safety_reports_category_status",
        "safety_reports",
        ["category", "status"],
    )
    op.create_index(
        "idx_safety_reports_lat_lng", "safety_reports", ["latitude", "longitude"]
    )
    op.create_index(
        "idx_safety_reports_reporter_id", "safety_reports", ["reporter_id"]
    )

    # 4. Routes cache table
    op.create_table(
        "routes_cache",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "cache_key",
            sa.String(length=64),
            nullable=False,
            comment="SHA-256 hash of normalized provider and route parameters",
        ),
        sa.Column(
            "provider",
            sa.String(length=50),
            server_default="mapbox",
            nullable=False,
            comment="Routing data provider",
        ),
        sa.Column(
            "origin_lat",
            sa.Float(),
            nullable=False,
            comment="Origin latitude coordinate",
        ),
        sa.Column(
            "origin_lng",
            sa.Float(),
            nullable=False,
            comment="Origin longitude coordinate",
        ),
        sa.Column(
            "destination_lat",
            sa.Float(),
            nullable=False,
            comment="Destination latitude coordinate",
        ),
        sa.Column(
            "destination_lng",
            sa.Float(),
            nullable=False,
            comment="Destination longitude coordinate",
        ),
        sa.Column(
            "travel_mode",
            sa.String(length=30),
            server_default="driving",
            nullable=False,
            comment="Travel mode ('driving' | 'walking' | 'cycling')",
        ),
        sa.Column(
            "route_parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
            comment="Input parameters passed to routing provider",
        ),
        sa.Column(
            "route_response",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            comment="Cached provider response payload",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Expiration timestamp based on TTL policy",
        ),
        sa.Column(
            "is_valid",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="Whether this cached entry is valid",
        ),
        sa.Column(
            "invalidated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when invalidated",
        ),
        sa.Column(
            "invalidation_reason",
            sa.String(length=255),
            nullable=True,
            comment="Reason for invalidation",
        ),
        sa.CheckConstraint(
            "origin_lat >= -90.0 AND origin_lat <= 90.0",
            name="ck_routes_cache_origin_lat",
        ),
        sa.CheckConstraint(
            "origin_lng >= -180.0 AND origin_lng <= 180.0",
            name="ck_routes_cache_origin_lng",
        ),
        sa.CheckConstraint(
            "destination_lat >= -90.0 AND destination_lat <= 90.0",
            name="ck_routes_cache_dest_lat",
        ),
        sa.CheckConstraint(
            "destination_lng >= -180.0 AND destination_lng <= 180.0",
            name="ck_routes_cache_dest_lng",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cache_key", name="uq_routes_cache_key"),
    )
    op.create_index(
        "idx_routes_cache_cache_key", "routes_cache", ["cache_key"], unique=True
    )
    op.create_index("idx_routes_cache_provider", "routes_cache", ["provider"])
    op.create_index(
        "idx_routes_cache_expires_at", "routes_cache", ["expires_at"]
    )
    op.create_index("idx_routes_cache_is_valid", "routes_cache", ["is_valid"])
    op.create_index(
        "idx_routes_cache_provider_expires",
        "routes_cache",
        ["provider", "expires_at"],
    )
    op.create_index(
        "idx_routes_cache_lookup", "routes_cache", ["cache_key", "is_valid"]
    )


def downgrade() -> None:
    op.drop_table("routes_cache")
    op.drop_table("safety_reports")
    op.drop_table("users")
