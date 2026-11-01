"""Tests for moderation authorization, transaction behavior, and coordinate consistency."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db_context
from app.models.safety_report import SafetyReport
from app.models.user import User
from app.schemas.schemas import (
    Coordinates,
    CreateReportRequest,
    ModerateReportRequest,
    ReportCategory,
    ReportSeverity,
    ReportStatus,
)
from app.services.reports import (
    async_moderate_safety_report,
    create_safety_report,
    moderate_safety_report,
)


@pytest.fixture
def sync_db_session() -> Generator[Session, None, None]:
    """Provide an isolated SQLite database session for authorization tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


class TestModerationAuthorization:
    """Tests ensuring moderation and admin privileges cannot be bypassed."""

    def test_report_creation_always_defaults_to_pending_review(
        self, sync_db_session: Session
    ) -> None:
        user = User(clerk_id="user_normal_1", role="user")
        sync_db_session.add(user)
        sync_db_session.commit()

        req = CreateReportRequest(
            location=Coordinates(lat=40.7128, lng=-74.0060),
            category=ReportCategory.POOR_LIGHTING,
            severity=ReportSeverity.LOW,
            description="Dim streetlight in residential alley.",
        )

        report = create_safety_report(sync_db_session, req, reporter=user)
        sync_db_session.commit()

        assert report.status == "pending_review"
        assert report.moderated_at is None
        assert report.moderated_by_id is None
        assert report.moderation_note is None

    def test_non_admin_cannot_moderate_report(
        self, sync_db_session: Session
    ) -> None:
        normal_user = User(clerk_id="user_regular", role="user")
        report = SafetyReport(
            category="poor_lighting",
            severity="moderate",
            description="Test report description",
            latitude=40.7128,
            longitude=-74.0060,
        )
        sync_db_session.add_all([normal_user, report])
        sync_db_session.commit()

        mod_req = ModerateReportRequest(
            status=ReportStatus.APPROVED,
            moderation_note="Self-approval attempt",
        )

        with pytest.raises(PermissionError, match="Only users with role 'admin'"):
            moderate_safety_report(
                sync_db_session, normal_user, report.id, mod_req
            )

        # Verify status remained unchanged
        sync_db_session.refresh(report)
        assert report.status == "pending_review"

    def test_admin_can_moderate_report(
        self, sync_db_session: Session
    ) -> None:
        admin_user = User(clerk_id="admin_123", role="admin")
        report = SafetyReport(
            category="traffic_hazard",
            severity="high",
            description="Pothole near crosswalk",
            latitude=40.7128,
            longitude=-74.0060,
        )
        sync_db_session.add_all([admin_user, report])
        sync_db_session.commit()

        mod_req = ModerateReportRequest(
            status=ReportStatus.APPROVED,
            moderation_note="Verified with transportation logs",
        )

        moderated = moderate_safety_report(
            sync_db_session, admin_user, report.id, mod_req
        )
        sync_db_session.commit()

        assert moderated.status == "approved"
        assert moderated.moderated_by_id == admin_user.id
        assert moderated.moderated_at is not None
        assert moderated.moderation_note == "Verified with transportation logs"

    def test_moderation_rejects_invalid_target_status(
        self, sync_db_session: Session
    ) -> None:
        admin_user = User(clerk_id="admin_456", role="admin")
        report = SafetyReport(
            category="road_condition",
            severity="low",
            description="Debris on shoulder",
            latitude=40.7128,
            longitude=-74.0060,
        )
        sync_db_session.add_all([admin_user, report])
        sync_db_session.commit()

        mod_req = ModerateReportRequest(
            status=ReportStatus.PENDING_REVIEW,
        )

        with pytest.raises(
            ValueError, match="Reports can only be moderated to 'approved' or 'rejected'"
        ):
            moderate_safety_report(
                sync_db_session, admin_user, report.id, mod_req
            )

    @pytest.mark.asyncio
    async def test_async_moderation_authorization(self) -> None:
        mock_session = AsyncMock()
        admin_user = User(clerk_id="admin_async", role="admin")
        normal_user = User(clerk_id="user_async", role="user")
        report = SafetyReport(
            category="crime_incident",
            severity="high",
            description="Incident description",
            latitude=40.7128,
            longitude=-74.0060,
        )

        # Mock query return
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = report
        mock_session.execute.return_value = mock_result

        # Non-admin fails
        mod_req = ModerateReportRequest(status=ReportStatus.APPROVED)
        with pytest.raises(PermissionError):
            await async_moderate_safety_report(
                mock_session, normal_user, report.id, mod_req
            )

        # Admin succeeds
        approved = await async_moderate_safety_report(
            mock_session, admin_user, report.id, mod_req
        )
        assert approved.status == "approved"
        assert approved.moderated_by_id == admin_user.id


class TestCoordinateConsistency:
    """Tests verifying latitude, longitude and geometry remain consistent."""

    def test_sync_location_format(self) -> None:
        report = SafetyReport(
            category="poor_lighting",
            severity="low",
            description="Dark sidewalk",
            latitude=40.7128,
            longitude=-74.0060,
        )
        # Verify automatic geometry synchronization in __init__
        assert report.location == "SRID=4326;POINT(-74.006 40.7128)"

    def test_update_coordinates_validates_and_syncs(self) -> None:
        report = SafetyReport(
            category="poor_lighting",
            severity="low",
            description="Dark sidewalk",
            latitude=40.7128,
            longitude=-74.0060,
        )

        report.update_coordinates(latitude=37.7749, longitude=-122.4194)
        assert report.latitude == 37.7749
        assert report.longitude == -122.4194
        assert report.location == "SRID=4326;POINT(-122.4194 37.7749)"

    def test_update_coordinates_rejects_out_of_bounds(self) -> None:
        report = SafetyReport(
            category="poor_lighting",
            severity="low",
            description="Dark sidewalk",
            latitude=40.7128,
            longitude=-74.0060,
        )

        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            report.update_coordinates(latitude=95.0, longitude=-74.0)

        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            report.update_coordinates(latitude=40.0, longitude=190.0)


class TestTransactionBehavior:
    """Tests verifying transaction commit and rollback behavior."""

    @pytest.mark.asyncio
    async def test_get_db_context_commit_on_success(self) -> None:
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__.return_value = mock_session

        with pytest.MonkeyPatch.context() as m:
            m.setattr("app.core.database.get_session_factory", lambda: mock_factory)
            async with get_db_context() as session:
                assert session is mock_session

        mock_session.commit.assert_awaited_once()
        mock_session.rollback.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_db_context_rollback_on_exception(self) -> None:
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=mock_session)
        mock_session.__aenter__.return_value = mock_session

        with pytest.MonkeyPatch.context() as m:
            m.setattr("app.core.database.get_session_factory", lambda: mock_factory)
            with pytest.raises(RuntimeError, match="Simulated error"):
                async with get_db_context():
                    raise RuntimeError("Simulated error")

        mock_session.rollback.assert_awaited_once()
        mock_session.commit.assert_not_awaited()
