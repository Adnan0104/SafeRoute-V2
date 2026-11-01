"""Unit tests for SQLAlchemy models: User, SafetyReport, RoutesCache."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.models.routes_cache import RoutesCache
from app.models.safety_report import SafetyReport
from app.models.user import User


@pytest.fixture
def sync_db_session() -> Generator[Session, None, None]:
    """Create an isolated in-memory SQLite database session for model tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class TestUserModel:
    """Tests for the User model."""

    def test_user_creation_defaults(self, sync_db_session: Session) -> None:
        user = User(
            clerk_id="user_clerk_12345",
            email="test@example.com",
            display_name="Test User",
        )
        sync_db_session.add(user)
        sync_db_session.commit()

        assert user.id is not None
        assert isinstance(user.id, uuid.UUID)
        assert user.role == "user"
        assert user.is_active is True
        assert user.preferences == {}
        assert "<User id=" in repr(user)

    def test_user_avoids_sensitive_information(self) -> None:
        """Verify the User model contains no password or sensitive authentication fields."""
        column_names = {col.name for col in User.__table__.columns}
        forbidden_fields = {"password", "hashed_password", "salt", "secret", "token"}
        assert forbidden_fields.isdisjoint(column_names)

    def test_user_role_admin(self, sync_db_session: Session) -> None:
        admin = User(
            clerk_id="user_admin_999",
            email="admin@example.com",
            role="admin",
        )
        sync_db_session.add(admin)
        sync_db_session.commit()

        queried = sync_db_session.scalar(
            select(User).where(User.clerk_id == "user_admin_999")
        )
        assert queried is not None
        assert queried.role == "admin"


class TestSafetyReportModel:
    """Tests for the SafetyReport model."""

    def test_safety_report_creation(self, sync_db_session: Session) -> None:
        report = SafetyReport(
            category="poor_lighting",
            severity="moderate",
            description="Dark stretch of sidewalk with broken streetlights.",
            latitude=40.7128,
            longitude=-74.0060,
            location="POINT(-74.0060 40.7128)",
            source="community",
            provenance_metadata={"client": "web_v2", "version": "0.1.0"},
        )
        sync_db_session.add(report)
        sync_db_session.commit()

        assert report.id is not None
        assert isinstance(report.id, uuid.UUID)
        assert report.status == "pending_review"
        assert report.created_at is not None
        assert report.moderated_at is None
        assert report.moderated_by_id is None
        assert "<SafetyReport id=" in repr(report)

    def test_safety_report_moderation_relationship(
        self, sync_db_session: Session
    ) -> None:
        reporter = User(clerk_id="user_rep_1", email="rep@example.com")
        moderator = User(clerk_id="user_mod_1", email="mod@example.com", role="admin")
        sync_db_session.add_all([reporter, moderator])
        sync_db_session.commit()

        report = SafetyReport(
            category="traffic_hazard",
            severity="high",
            description="Fallen tree branch blocking bicycle lane.",
            latitude=37.7749,
            longitude=-122.4194,
            reporter_id=reporter.id,
            status="approved",
            moderated_by_id=moderator.id,
            moderated_at=datetime.now(UTC),
            moderation_note="Verified by city maintenance feed.",
        )
        sync_db_session.add(report)
        sync_db_session.commit()

        queried = sync_db_session.scalar(
            select(SafetyReport).where(SafetyReport.id == report.id)
        )
        assert queried is not None
        assert queried.reporter is not None
        assert queried.reporter.clerk_id == "user_rep_1"
        assert queried.moderator is not None
        assert queried.moderator.clerk_id == "user_mod_1"
        assert queried.moderation_note == "Verified by city maintenance feed."


class TestRoutesCacheModel:
    """Tests for the RoutesCache model."""

    def test_generate_cache_key_deterministic(self) -> None:
        key1 = RoutesCache.generate_cache_key(
            provider="mapbox",
            origin_lat=40.712800,
            origin_lng=-74.006000,
            destination_lat=40.758000,
            destination_lng=-73.985500,
            travel_mode="driving",
            parameters={"alternatives": True, "safety_corridor_m": 200},
        )
        key2 = RoutesCache.generate_cache_key(
            provider="MAPBOX",
            origin_lat=40.7128001,  # rounds to 6 decimals
            origin_lng=-74.0060001,
            destination_lat=40.7580001,
            destination_lng=-73.9855001,
            travel_mode="DRIVING",
            parameters={"safety_corridor_m": 200, "alternatives": True},
        )
        assert len(key1) == 64
        assert key1 == key2

    def test_cache_expiration(self) -> None:
        now = datetime.now(UTC)
        past_expires = now - timedelta(minutes=5)
        future_expires = now + timedelta(minutes=30)

        expired_entry = RoutesCache(
            cache_key="key_expired",
            origin_lat=40.0,
            origin_lng=-74.0,
            destination_lat=40.1,
            destination_lng=-73.9,
            expires_at=past_expires,
            route_response={"routes": []},
        )
        active_entry = RoutesCache(
            cache_key="key_active",
            origin_lat=40.0,
            origin_lng=-74.0,
            destination_lat=40.1,
            destination_lng=-73.9,
            expires_at=future_expires,
            route_response={"routes": []},
        )

        assert expired_entry.is_expired(now=now) is True
        assert active_entry.is_expired(now=now) is False

    def test_cache_invalidation(self, sync_db_session: Session) -> None:
        entry = RoutesCache(
            cache_key="key_to_invalidate",
            provider="mapbox",
            origin_lat=40.7128,
            origin_lng=-74.0060,
            destination_lat=40.7580,
            destination_lng=-73.9855,
            travel_mode="driving",
            route_parameters={"alternatives": True},
            route_response={"routes": [{"id": "route_1"}]},
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )
        sync_db_session.add(entry)
        sync_db_session.commit()

        assert entry.is_valid is True
        assert entry.invalidated_at is None

        entry.invalidate(reason="critical_incident_reported_on_corridor")
        sync_db_session.commit()

        assert entry.is_valid is False
        assert entry.invalidated_at is not None
        assert entry.invalidation_reason == "critical_incident_reported_on_corridor"
        assert "<RoutesCache" in repr(entry)
