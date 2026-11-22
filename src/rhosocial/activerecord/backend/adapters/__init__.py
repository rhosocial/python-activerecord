# src/rhosocial/activerecord/backend/adapters/__init__.py
"""Neutral, driver-independent types and their adapter base classes."""

from .portable import PORTABLE_TYPE_MAPPINGS
from .bitstring import BitString, BitStringAdapterBase
from .geometry import (
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
from .json_codec import AdapterJSONCodec
from .network import MacAddress, MacAddressAdapterBase
from .range import Multirange, Range, RangeAdapterBase
from .vector import Vector, VectorAdapterBase

__all__ = [
    "AdapterJSONCodec",
    "BitString",
    "BitStringAdapterBase",
    "Geometry",
    "GeometryAdapterBase",
    "GeometryCollection",
    "LineString",
    "MacAddress",
    "MacAddressAdapterBase",
    "MultiLineString",
    "MultiPoint",
    "MultiPolygon",
    "Multirange",
    "Point",
    "Polygon",
    "Range",
    "RangeAdapterBase",
    "Vector",
    "VectorAdapterBase",
]
