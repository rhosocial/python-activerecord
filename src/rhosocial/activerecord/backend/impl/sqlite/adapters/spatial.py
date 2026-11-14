# src/rhosocial/activerecord/backend/impl/sqlite/adapters/spatial.py
"""Geometry adapter for SQLite (TEXT WKT, optional EWKT SRID prefix).

SQLite has no native geometry type outside R*Tree virtual tables, so a geometry
column is ordinary TEXT. This adapter stores neutral geometry values as WKT and
presents an SRID as the widely used ``SRID=...;`` prefix. Reading accepts both
plain WKT and prefixed EWKT, and returns a concrete neutral geometry.
"""

from typing import Any, Dict, Type

from rhosocial.activerecord.backend.adapters.geometry import (
    Geometry,
    GeometryAdapterBase,
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)

_GEOMETRY_TYPES = (
    Geometry,
    Point,
    LineString,
    Polygon,
    MultiPoint,
    MultiLineString,
    MultiPolygon,
    GeometryCollection,
)


class SQLiteGeometryAdapter(GeometryAdapterBase):
    """Store neutral geometries as ``TEXT`` WKT.

    The adapter accepts a :class:`Geometry`, WKT text, or a GeoJSON mapping on
    write (the base class normalizes them first) and always binds a string.
    When the geometry carries an SRID, the output is ``SRID=<n>;<wkt>``; the
    optional ``srid`` entry in ``options`` is used only when the value itself
    has none.
    """

    def __init__(self):
        super().__init__()
        for geometry_type in _GEOMETRY_TYPES:
            self.register_type(geometry_type, str)

    def _encode(self, geometry: Geometry, target_type: Type, options: Dict[str, Any]) -> str:
        wkt = geometry.to_wkt()
        srid = geometry.srid
        if srid is None:
            srid = options.get("srid")
        if srid is not None:
            if isinstance(srid, bool) or not isinstance(srid, int):
                raise TypeError(f"srid must be int or None, got {type(srid).__name__}")
            if srid < 0:
                raise ValueError(f"srid must be non-negative, got {srid}")
            wkt = f"SRID={srid};{wkt}"
        return wkt

    def _decode(self, value: Any, options: Dict[str, Any]) -> Geometry:
        text = self._require_text(value)
        srid = options.get("srid")
        return Geometry.from_wkt(text, srid=srid)
