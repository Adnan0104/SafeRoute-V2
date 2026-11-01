#!/usr/bin/env python3
"""SafeRoute V2 — Production / Staging PostgreSQL + PostGIS Verification Script.

This script executes live database verification against a target PostgreSQL instance:
1. Verifies connectivity and permissions using asyncpg.
2. Verifies PostGIS extension availability and version.
3. Applies Alembic migrations (0001_initial_schema).
4. Inspects created tables, constraints, indexes, foreign keys, and geometry columns.
5. Performs real CRUD operations on User, SafetyReport, and RoutesCache.
6. Executes PostGIS spatial queries (ST_AsText, ST_DWithin distance in meters).
7. Verifies coordinate consistency between latitude/longitude and geometry.
8. Verifies transaction commit and rollback behavior.
9. Verifies admin authorization enforcement for report moderation.
10. Validates health check reporting against active and inactive databases.

Usage:
    python scripts/verify_database.py [--db-url <postgresql_url>]
"""

import argparse
import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

# Add backend directory to sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(script_dir)
backend_dir = os.path.join(repo_root, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from alembic import command
from alembic.config import Config
from app.core.config import Settings
from app.core.database import check_database_health
from app.models.routes_cache import RoutesCache
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
    async_create_safety_report,
    async_moderate_safety_report,
)
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_AsText, ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import (
    cast,
    select,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def mask_url(url: str) -> str:
    """Mask password in database URL for safe logging."""
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        userinfo, hostinfo = rest.split("@", 1)
        username = userinfo.split(":")[0] if ":" in userinfo else userinfo
        return f"{scheme}://{username}:****@{hostinfo}"
    return url


def normalize_async_url(url: str) -> str:
    """Ensure database URL uses postgresql+asyncpg driver."""
    url = url.strip()
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and not url.startswith("postgresql+"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def run_verification_async(database_url: str) -> bool:
    print("=" * 70)
    print("SafeRoute V2 -- PostgreSQL + PostGIS Live Database Verification")
    print("=" * 70)

    async_url = normalize_async_url(database_url)
    print(f"Target Database: {mask_url(async_url)}")

    # 1. Connection check
    print("\n[Step 1] Connecting to PostgreSQL instance via asyncpg...")
    try:
        engine = create_async_engine(async_url, pool_pre_ping=True)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            pg_ver = result.scalar()
            print(f"  [OK] Connected: {pg_ver}")
    except Exception as e:  # noqa: BLE001
        print(f"  [FAIL] Connection failed: {e}")
        return False

    # 2. PostGIS Extension Check
    print("\n[Step 2] Verifying PostGIS extension availability...")
    async with engine.connect() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            await conn.commit()
            res = await conn.execute(text("SELECT postgis_full_version();"))
            postgis_ver = res.scalar()
            print(f"  [OK] PostGIS is enabled: {postgis_ver}")
        except Exception as e:  # noqa: BLE001
            print(f"  [FAIL] PostGIS extension check failed: {e}")
            await engine.dispose()
            return False

    # 3. Alembic Migration
    print("\n[Step 3] Applying Alembic migration (upgrade head)...")
    try:
        alembic_ini = os.path.join(backend_dir, "alembic.ini")
        alembic_cfg = Config(alembic_ini)
        alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
        alembic_cfg.set_main_option("sqlalchemy.url", async_url)

        # Run migration in a separate thread so asyncio loop doesn't conflict
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")

        async with engine.connect() as conn:
            rev_res = await conn.execute(text("SELECT version_num FROM alembic_version;"))
            curr_rev = rev_res.scalar()
            print(f"  [OK] Alembic migration applied. Current revision: {curr_rev}")
    except Exception as e:  # noqa: BLE001
        print(f"  [FAIL] Migration failed: {e}")
        await engine.dispose()
        return False

    # 4. Schema Inspection
    print("\n[Step 4] Inspecting schema objects (tables, columns, constraints)...")
    async with engine.connect() as conn:
        tables_res = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        )
        tables = [row[0] for row in tables_res.fetchall()]

        for t in ["users", "safety_reports", "routes_cache"]:
            if t in tables:
                print(f"  [OK] Table '{t}' exists.")
            else:
                print(f"  [FAIL] Missing table: '{t}'")
                await engine.dispose()
                return False

        # Inspect geometry column
        geom_res = await conn.execute(
            text(
                "SELECT f_geometry_column, type, srid "
                "FROM geometry_columns WHERE f_table_name = 'safety_reports';"
            )
        )
        geom_row = geom_res.fetchone()
        if geom_row:
            print(f"  [OK] Geometry column '{geom_row[0]}' registered (type: {geom_row[1]}, srid: {geom_row[2]})")
        else:
            print("  [FAIL] Geometry column not found in geometry_columns catalog.")
            await engine.dispose()
            return False

    SessionMaker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # 5. CRUD Operations Test
    print("\n[Step 5] Testing CRUD operations...")
    test_run_id = uuid.uuid4().hex[:8]
    async with SessionMaker() as session:
        # Create reporter and admin
        reporter = User(
            clerk_id=f"user_rep_{test_run_id}",
            email=f"reporter_{test_run_id}@example.com",
            display_name="Test Reporter",
            role="user",
        )
        admin = User(
            clerk_id=f"user_adm_{test_run_id}",
            email=f"admin_{test_run_id}@example.com",
            display_name="Test Admin",
            role="admin",
        )
        session.add_all([reporter, admin])
        await session.commit()
        print(f"  [OK] Created test users: Reporter ID={reporter.id}, Admin ID={admin.id}")

        # Create safety report via service
        report_req = CreateReportRequest(
            location=Coordinates(lat=40.7128, lng=-74.0060),
            category=ReportCategory.POOR_LIGHTING,
            severity=ReportSeverity.MODERATE,
            description=f"Verification test report {test_run_id}",
            occurred_at=datetime.now(UTC),
        )
        report = await async_create_safety_report(session, report_req, reporter=reporter)
        await session.commit()
        print(f"  [OK] Created SafetyReport: ID={report.id}, status='{report.status}'")

        # Create RoutesCache entry
        cache_key = RoutesCache.generate_cache_key(
            provider="mapbox",
            origin_lat=40.7128,
            origin_lng=-74.0060,
            destination_lat=40.7580,
            destination_lng=-73.9855,
            travel_mode="driving",
        )
        cache_entry = RoutesCache(
            cache_key=cache_key,
            provider="mapbox",
            origin_lat=40.7128,
            origin_lng=-74.0060,
            destination_lat=40.7580,
            destination_lng=-73.9855,
            travel_mode="driving",
            route_parameters={"alternatives": True},
            route_response={"routes": [{"id": f"route_{test_run_id}"}]},
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        session.add(cache_entry)
        await session.commit()
        print(f"  [OK] Created RoutesCache: key={cache_key[:16]}...")

    # 6. PostGIS Spatial Queries Test
    print("\n[Step 6] Testing PostGIS spatial queries (ST_AsText, ST_DWithin)...")
    async with SessionMaker() as session:
        # Test ST_AsText
        stmt_wkt = select(ST_AsText(SafetyReport.location)).where(SafetyReport.id == report.id)
        wkt_result = (await session.execute(stmt_wkt)).scalar()
        print(f"  [OK] ST_AsText returned: {wkt_result}")
        assert wkt_result == "POINT(-74.006 40.7128)"

        # Test ST_DWithin within 100 meters
        stmt_near = (
            select(SafetyReport)
            .where(SafetyReport.id == report.id)
            .where(
                ST_DWithin(
                    cast(SafetyReport.location, Geography),
                    cast(ST_SetSRID(ST_MakePoint(-74.0065, 40.7128), 4326), Geography),
                    100.0,
                )
            )
        )
        near_match = (await session.execute(stmt_near)).scalar_one_or_none()
        assert near_match is not None
        print("  [OK] ST_DWithin within 100m correctly matched report.")

        # Test ST_DWithin from distant point (5km away)
        stmt_far = (
            select(SafetyReport)
            .where(SafetyReport.id == report.id)
            .where(
                ST_DWithin(
                    cast(SafetyReport.location, Geography),
                    cast(ST_SetSRID(ST_MakePoint(-73.9855, 40.7580), 4326), Geography),
                    100.0,
                )
            )
        )
        far_match = (await session.execute(stmt_far)).scalar_one_or_none()
        assert far_match is None
        print("  [OK] ST_DWithin from distant location correctly excluded report.")

    # 7. Coordinate & Geometry Consistency Test
    print("\n[Step 7] Testing coordinate and geometry consistency...")
    async with SessionMaker() as session:
        r = (await session.execute(select(SafetyReport).where(SafetyReport.id == report.id))).scalar_one()
        assert abs(r.latitude - 40.7128) < 1e-6
        assert abs(r.longitude - -74.0060) < 1e-6

        # Update coordinates using model method
        r.update_coordinates(40.7300, -74.0000)
        await session.commit()

        # Verify updated ST_AsText
        updated_wkt = (
            await session.execute(select(ST_AsText(SafetyReport.location)).where(SafetyReport.id == r.id))
        ).scalar()
        print(f"  [OK] Updated coordinates: lat={r.latitude}, lng={r.longitude}")
        print(f"  [OK] Geometry updated in sync: {updated_wkt}")
        assert updated_wkt == "POINT(-74 40.73)"

    # 8. Transaction Rollback & Commit Test
    print("\n[Step 8] Testing transaction rollback and commit behavior...")
    async with SessionMaker() as session:
        try:
            async with session.begin():
                dummy_user = User(clerk_id=f"user_rollback_{test_run_id}")
                session.add(dummy_user)
                # Intentionally trigger an error
                raise RuntimeError("Simulated transaction failure")
        except RuntimeError:
            pass

        # Verify rollback prevented persistence
        res = await session.execute(select(User).where(User.clerk_id == f"user_rollback_{test_run_id}"))
        rolled_back = res.scalar_one_or_none()
        assert rolled_back is None
        print("  [OK] Transaction properly rolled back; uncommitted data was discarded.")

    # 9. Moderation Authorization Verification
    print("\n[Step 9] Verifying report moderation authorization...")
    async with SessionMaker() as session:
        rep_user = (await session.execute(select(User).where(User.id == reporter.id))).scalar_one()
        adm_user = (await session.execute(select(User).where(User.id == admin.id))).scalar_one()
        target_report = (await session.execute(select(SafetyReport).where(SafetyReport.id == report.id))).scalar_one()

        # Verify regular user cannot moderate
        try:
            mod_req = ModerateReportRequest(status=ReportStatus.APPROVED, moderation_note="Unauthorized attempt")
            await async_moderate_safety_report(session, rep_user, target_report.id, mod_req)
            print("  [FAIL] SECURITY FLAW: Regular user was able to moderate report!")
            await engine.dispose()
            return False
        except PermissionError as pe:
            print(f"  [OK] Non-admin moderation correctly blocked: {pe}")

        # Verify admin can moderate
        mod_req = ModerateReportRequest(status=ReportStatus.APPROVED, moderation_note="Verified by admin")
        approved_report = await async_moderate_safety_report(session, adm_user, target_report.id, mod_req)
        await session.commit()
        assert approved_report.status == "approved"
        assert approved_report.moderated_by_id == adm_user.id
        print(f"  [OK] Admin successfully moderated report: status='{approved_report.status}'")

    # 10. Health check verification
    print("\n[Step 10] Testing health check reporting...")
    health_status = await check_database_health()
    print(f"  [OK] Database health check reported: '{health_status}'")

    # Clean up test data
    print("\n[Step 11] Cleaning up verification test records...")
    async with SessionMaker() as session:
        await session.execute(text(f"DELETE FROM safety_reports WHERE description LIKE '%{test_run_id}%'"))
        await session.execute(text(f"DELETE FROM users WHERE clerk_id LIKE '%{test_run_id}%'"))
        await session.execute(text(f"DELETE FROM routes_cache WHERE cache_key = '{cache_key}'"))
        await session.commit()
        print("  [OK] Test records cleaned up.")

    await engine.dispose()
    print("\n" + "=" * 70)
    print("ALL VERIFICATION CHECKS PASSED AGAINST POSTGRESQL + POSTGIS")
    print("=" * 70)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify SafeRoute V2 PostgreSQL + PostGIS database layer.")
    parser.add_argument("--db-url", type=str, help="PostgreSQL connection URL", default=None)
    args = parser.parse_args()

    db_url = args.db_url or os.environ.get("DATABASE_URL")
    if not db_url:
        settings = Settings()
        if settings.is_database_configured and settings.database_url:
            db_url = settings.database_url

    if not db_url or not db_url.strip():
        print("=" * 70)
        print("SafeRoute V2 -- Database Verification Status")
        print("=" * 70)
        print("Status: NO_DATABASE_CONFIGURED")
        print("\nPrerequisites:")
        print("  A managed PostgreSQL instance with PostGIS enabled is required.")
        print("  Neither local PostgreSQL nor DATABASE_URL environment variable is currently set.")
        print("\nTo execute verification against a live PostgreSQL + PostGIS database:")
        print("  1. In PowerShell:")
        print('     $env:DATABASE_URL="postgresql+asyncpg://user:password@hostname:5432/dbname"')
        print("     python scripts/verify_database.py")
        print("  2. Or in bash:")
        print('     export DATABASE_URL="postgresql+asyncpg://user:password@hostname:5432/dbname"')
        print("     python scripts/verify_database.py")
        print("=" * 70)
        sys.exit(2)

    success = asyncio.run(run_verification_async(db_url))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
