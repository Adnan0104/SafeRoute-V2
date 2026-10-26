"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient


def test_health_check_returns_ok(client: TestClient) -> None:
    """Health endpoint should return status ok with version info."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data["data"]


def test_health_check_reports_unconfigured_services(client: TestClient) -> None:
    """Health endpoint should honestly report unconfigured services."""
    response = client.get("/api/v1/health")
    data = response.json()
    # At this stage, DB and routing are not yet connected
    assert data["data"]["database"] == "not_configured"
    assert data["data"]["routing_provider"] == "not_configured"
