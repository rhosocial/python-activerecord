# src/rhosocial/activerecord/base/framework_types.py
"""The Python types the framework models, in lookup order.

Two dialect tables are keyed by these -- the column-class table
(``suggested_column_types``) and the suggested storage-type table
(``suggested_storage_types``) -- and the DDL derivation falls back to them
when a field declares no SQL type. Keeping the list in one place is what
makes "every key must be answered" checkable in both layers without a test
having to restate the population.

Order matters. ``bool`` precedes ``int`` because a bool is an int subclass,
and a table lookup walks subclasses in key order (``User.c.flag`` must not
land on the integer column). ``enum.Enum`` is checked before the walk by the
lookup itself, so a ``(int, Enum)`` class still counts as an enum.

The complex families are the framework's own value classes, each with an
adapter base in :mod:`...backend.adapters`. They are framework-modelled
types, so they belong in the main tables; a backend's *own* types belong in
the extras tables and are not listed here.
"""
from __future__ import annotations

import datetime
import decimal
import enum
import uuid
from typing import Any, Tuple

from ..backend.adapters import (
    BitString,
    Geometry,
    MacAddress,
    Multirange,
    Range,
    Vector,
)

#: The twenty-four Python types the framework models.
FRAMEWORK_PYTHON_TYPES: Tuple[Any, ...] = (
    # -- common scalars, in the reading order the lookup walk depends on ---
    bool,
    int,
    float,
    decimal.Decimal,
    str,
    bytes,
    bytearray,
    datetime.date,
    datetime.time,
    datetime.datetime,
    datetime.timedelta,
    uuid.UUID,
    dict,
    list,
    tuple,
    set,
    frozenset,
    enum.Enum,
    # -- complex families: framework-modelled value classes ----------------
    # ``Geometry`` is a key for the whole family: the lookup's subclass walk
    # resolves Point, LineString, Polygon, MultiPoint, MultiLineString,
    # MultiPolygon and GeometryCollection to it in one entry.
    Geometry,
    Vector,
    BitString,
    Range,
    Multirange,
    MacAddress,
)

__all__ = ["FRAMEWORK_PYTHON_TYPES"]
