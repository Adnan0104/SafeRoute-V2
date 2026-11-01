"""SafeRoute V2 — Report service with strict moderation authorization."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.safety_report import SafetyReport
from app.models.user import User
from app.schemas.schemas import (
    CreateReportRequest,
    ModerateReportRequest,
    ReportStatus,
)


def create_safety_report(
    session: Session,
    request: CreateReportRequest,
    reporter: User | None = None,
    source: str = "community",
    provenance_metadata: dict[str, Any] | None = None,
) -> SafetyReport:
    """Create a new safety report.

    Guarantees that new community submissions enter the 'pending_review' state
    and cannot bypass moderation or self-approve during submission.
    """
    report = SafetyReport(
        category=request.category.value,
        severity=request.severity.value,
        description=request.description,
        latitude=request.location.lat,
        longitude=request.location.lng,
        occurred_at=request.occurred_at,
        reporter_id=reporter.id if reporter else None,
        source=source,
        provenance_metadata=provenance_metadata or {},
        # Moderation fields are strictly initialized
        status=ReportStatus.PENDING_REVIEW.value,
        moderated_at=None,
        moderated_by_id=None,
        moderation_note=None,
    )
    report.sync_location()
    session.add(report)
    return report


def moderate_safety_report(
    session: Session,
    moderator: User,
    report_id: uuid.UUID,
    request: ModerateReportRequest,
) -> SafetyReport:
    """Moderate a safety report.

    Strictly enforces admin authorization. Non-admin users cannot approve,
    reject, or alter moderation fields.
    """
    if moderator.role != "admin":
        raise PermissionError(
            f"User {moderator.id} has role '{moderator.role}'. "
            "Only users with role 'admin' are authorized to moderate reports."
        )

    if request.status not in (ReportStatus.APPROVED, ReportStatus.REJECTED):
        raise ValueError(
            f"Invalid moderation target status '{request.status}'. "
            "Reports can only be moderated to 'approved' or 'rejected'."
        )

    report = session.scalar(
        select(SafetyReport).where(SafetyReport.id == report_id)
    )
    if not report:
        raise ValueError(f"SafetyReport with id {report_id} not found.")

    report.status = request.status.value
    report.moderated_at = datetime.now(UTC)
    report.moderated_by_id = moderator.id
    report.moderation_note = request.moderation_note

    return report


async def async_create_safety_report(
    session: AsyncSession,
    request: CreateReportRequest,
    reporter: User | None = None,
    source: str = "community",
    provenance_metadata: dict[str, Any] | None = None,
) -> SafetyReport:
    """Async variant: Create a new safety report in pending_review state."""
    report = SafetyReport(
        category=request.category.value,
        severity=request.severity.value,
        description=request.description,
        latitude=request.location.lat,
        longitude=request.location.lng,
        occurred_at=request.occurred_at,
        reporter_id=reporter.id if reporter else None,
        source=source,
        provenance_metadata=provenance_metadata or {},
        status=ReportStatus.PENDING_REVIEW.value,
        moderated_at=None,
        moderated_by_id=None,
        moderation_note=None,
    )
    report.sync_location()
    session.add(report)
    return report


async def async_moderate_safety_report(
    session: AsyncSession,
    moderator: User,
    report_id: uuid.UUID,
    request: ModerateReportRequest,
) -> SafetyReport:
    """Async variant: Moderate a safety report with admin authorization check."""
    if moderator.role != "admin":
        raise PermissionError(
            f"User {moderator.id} has role '{moderator.role}'. "
            "Only users with role 'admin' are authorized to moderate reports."
        )

    if request.status not in (ReportStatus.APPROVED, ReportStatus.REJECTED):
        raise ValueError(
            f"Invalid moderation target status '{request.status}'. "
            "Reports can only be moderated to 'approved' or 'rejected'."
        )

    result = await session.execute(
        select(SafetyReport).where(SafetyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise ValueError(f"SafetyReport with id {report_id} not found.")

    report.status = request.status.value
    report.moderated_at = datetime.now(UTC)
    report.moderated_by_id = moderator.id
    report.moderation_note = request.moderation_note

    return report
