"""Tests for Pydantic schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas import (
    Coordinates,
    CreateReportRequest,
    RouteSearchRequest,
    TravelMode,
)


class TestCoordinates:
    """Tests for the Coordinates schema."""

    def test_valid_coordinates(self) -> None:
        coords = Coordinates(lat=40.7128, lng=-74.0060)
        assert coords.lat == 40.7128
        assert coords.lng == -74.0060

    def test_rejects_invalid_latitude(self) -> None:
        with pytest.raises(ValidationError):
            Coordinates(lat=91.0, lng=0.0)

    def test_rejects_invalid_longitude(self) -> None:
        with pytest.raises(ValidationError):
            Coordinates(lat=0.0, lng=181.0)

    def test_boundary_values(self) -> None:
        coords = Coordinates(lat=90.0, lng=180.0)
        assert coords.lat == 90.0
        assert coords.lng == 180.0

        coords = Coordinates(lat=-90.0, lng=-180.0)
        assert coords.lat == -90.0
        assert coords.lng == -180.0


class TestRouteSearchRequest:
    """Tests for the RouteSearchRequest schema."""

    def test_valid_request(self) -> None:
        req = RouteSearchRequest(
            origin=Coordinates(lat=40.7128, lng=-74.0060),
            destination=Coordinates(lat=40.7580, lng=-73.9855),
        )
        assert req.mode == TravelMode.DRIVING
        assert req.alternatives is True
        assert req.safety_corridor_m == 200

    def test_custom_corridor_width(self) -> None:
        req = RouteSearchRequest(
            origin=Coordinates(lat=0.0, lng=0.0),
            destination=Coordinates(lat=1.0, lng=1.0),
            safety_corridor_m=500,
        )
        assert req.safety_corridor_m == 500

    def test_rejects_too_small_corridor(self) -> None:
        with pytest.raises(ValidationError):
            RouteSearchRequest(
                origin=Coordinates(lat=0.0, lng=0.0),
                destination=Coordinates(lat=1.0, lng=1.0),
                safety_corridor_m=10,
            )

    def test_rejects_too_large_corridor(self) -> None:
        with pytest.raises(ValidationError):
            RouteSearchRequest(
                origin=Coordinates(lat=0.0, lng=0.0),
                destination=Coordinates(lat=1.0, lng=1.0),
                safety_corridor_m=2000,
            )


class TestCreateReportRequest:
    """Tests for the CreateReportRequest schema."""

    def test_valid_report(self) -> None:
        report = CreateReportRequest(
            location=Coordinates(lat=40.73, lng=-74.00),
            category="poor_lighting",
            severity="moderate",
            description="Unlit alley between Main St and 2nd Ave",
        )
        assert report.category == "poor_lighting"

    def test_rejects_short_description(self) -> None:
        with pytest.raises(ValidationError):
            CreateReportRequest(
                location=Coordinates(lat=40.73, lng=-74.00),
                category="poor_lighting",
                severity="moderate",
                description="Short",  # < 10 chars
            )

    def test_rejects_invalid_category(self) -> None:
        with pytest.raises(ValidationError):
            CreateReportRequest(
                location=Coordinates(lat=40.73, lng=-74.00),
                category="invalid_category",
                severity="moderate",
                description="A sufficiently long description for testing",
            )
