"""Unit tests for Alembic migration configuration and offline SQL generation."""

from pathlib import Path

import pytest
from alembic.command import upgrade
from alembic.config import Config
from alembic.script import ScriptDirectory


@pytest.fixture
def alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parent.parent.parent
    ini_path = backend_dir / "alembic.ini"
    assert ini_path.exists(), f"alembic.ini not found at {ini_path}"
    config = Config(str(ini_path))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    return config


class TestAlembicMigrations:
    """Tests for database migration scripts and configuration."""

    def test_migration_scripts_exist_and_form_valid_dag(
        self, alembic_config: Config
    ) -> None:
        script = ScriptDirectory.from_config(alembic_config)
        heads = script.get_heads()
        assert len(heads) == 1
        assert heads[0] == "0001_initial_schema"

        rev = script.get_revision("0001_initial_schema")
        assert rev is not None
        assert rev.down_revision is None

    def test_offline_sql_generation_contains_all_models(
        self, alembic_config: Config, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Verify that offline SQL generation succeeds and emits expected DDL."""
        # Run offline upgrade to head
        upgrade(alembic_config, "head", sql=True)
        captured = capsys.readouterr()
        sql = captured.out

        # Verify PostGIS extension
        assert "CREATE EXTENSION IF NOT EXISTS postgis" in sql

        # Verify tables are created
        assert "CREATE TABLE users" in sql
        assert "CREATE TABLE safety_reports" in sql
        assert "CREATE TABLE routes_cache" in sql

        # Verify key columns and constraints
        assert "clerk_id" in sql
        assert "ck_safety_reports_latitude_range" in sql
        assert "ck_safety_reports_longitude_range" in sql
        assert "ck_safety_reports_severity" in sql
        assert "ck_safety_reports_status" in sql
        assert "ck_routes_cache_origin_lat" in sql
        assert "cache_key" in sql

        # Verify alembic version stamp
        assert "0001_initial_schema" in sql
