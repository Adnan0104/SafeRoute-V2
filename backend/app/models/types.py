"""SafeRoute V2 — Custom SQLAlchemy types for geospatial support."""

from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import String, TypeDecorator
from sqlalchemy.engine import Dialect


class PointGeometry(TypeDecorator[Any]):
    """PostGIS Point geometry type that falls back safely on non-PostGIS dialects.

    On PostgreSQL, this maps directly to GeoAlchemy2's Geometry('POINT', srid=srid).
    On SQLite and other dialects, this maps to String for offline and lightweight
    unit-testing without requiring SpatiaLite C binaries.
    """

    impl = Geometry
    cache_ok = True

    def __init__(self, srid: int = 4326, **kwargs: Any) -> None:
        self.srid = srid
        self.kwargs = kwargs
        super().__init__(**kwargs)

    def load_dialect_impl(self, dialect: Dialect | None) -> Any:
        if dialect is not None and dialect.name == "postgresql":
            return dialect.type_descriptor(
                Geometry(geometry_type="POINT", srid=self.srid, **self.kwargs)
            )
        elif dialect is None:
            return String(255)
        return dialect.type_descriptor(String(255))
