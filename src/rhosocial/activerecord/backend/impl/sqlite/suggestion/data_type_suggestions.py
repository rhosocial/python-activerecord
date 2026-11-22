# src/rhosocial/activerecord/backend/impl/sqlite/suggestion/data_type_suggestions.py
"""SQLite's **suggested data types**: the declaration a bare field gets here.

This is the DDL half of SQLite's type answer, and it is deliberately separate
from :mod:`.column_type`: that table says which *operations* a value has here,
this one says what a column's declaration is when a field writes only a Python
type.

SQLite has no ``VARCHAR(n)`` that behaves differently from ``TEXT``, no
``DECIMAL`` of fixed precision, and no spatial or vector type at all. So the
suggestions are the affinities SQLite really stores, not a pretence of the
SQL-standard family:

* text and everything the adapters render as text (``UUID``, geometry,
  bit strings, ranges, MAC addresses) -> ``TEXT``;
* documents and containers (``dict``/``list``/``tuple``/``set``/``frozenset``,
  and ``Vector``, whose adapter writes JSON) -> ``JSON``, which SQLite stores
  as ``TEXT`` with JSON1 operations;
* binary -> ``BLOB``;
* numbers, booleans, temporal values -> ``INTEGER``/``REAL``/``NUMERIC``, as
  the formatters render them.

Every call returns a **fresh dict** whose values are this module's read-only
templates. A ``DataType``'s dialect is a mutable rendering attribute, so a
caller binds the dialect on a **copy of the one entry it uses** -- the table
itself is never rebound. Copying the whole table per call was measured at
~100 us (``copy.copy`` costs more than constructing a fresh instance), and the
derivation path copies the single entry anyway.
"""
import datetime
import decimal
import enum
import uuid
from typing import Any, Dict, Optional

from rhosocial.activerecord.backend.adapters import (
    BitString,
    Geometry,
    MacAddress,
    Multirange,
    Range,
    Vector,
)
from rhosocial.activerecord.backend.expression.types import (
    BlobType,
    BooleanType,
    DateType,
    DecimalType,
    DoubleType,
    IntegerType,
    IntervalType,
    JsonType,
    TextType,
    TimeType,
    TimestampType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.types import SQLiteTextType

#: SQLite's suggested storage declaration per framework-modelled Python type.
SQLITE_DATA_TYPE_SUGGESTIONS: Dict[Any, Optional[Any]] = {
    bool: BooleanType(),
    int: IntegerType(),
    float: DoubleType(),
    decimal.Decimal: DecimalType(),
    str: TextType(),
    bytes: BlobType(),
    bytearray: BlobType(),
    datetime.date: DateType(),
    datetime.time: TimeType(),
    # Milliseconds, the framework's timestamp default: SQLite stores the value
    # as NUMERIC either way, so declaring precision costs nothing here and
    # keeps the declaration identical across backends.
    datetime.datetime: TimestampType(precision=3),
    datetime.timedelta: IntervalType(),
    # The generic UUIDType has no formatter on SQLite; the dialect's own text
    # type is the declaration it actually stores.
    uuid.UUID: SQLiteTextType(),
    dict: JsonType(),
    list: JsonType(),
    tuple: JsonType(),
    set: JsonType(),
    frozenset: JsonType(),
    enum.Enum: VarCharType(length=255),
    # Complex families: no native type, carried as text/JSON.
    Geometry: TextType(),
    Vector: JsonType(),
    BitString: TextType(),
    Range: TextType(),
    Multirange: TextType(),
    MacAddress: TextType(),
}


class SQLiteDataTypeSuggestionsMixin:
    """SQLite's answer to "what declaration does a bare field get here"."""

    def suggest_data_types(self) -> Dict[Any, Optional[Any]]:
        return dict(SQLITE_DATA_TYPE_SUGGESTIONS)



    def suggest_substitute_types(self) -> Dict[str, type]:
        return {}

    def suggest_substitute_advice(self, name: str) -> str:
        return ""

    def suggest_extra_data_types(self) -> Dict[type, "DataType"]:
        return {}


__all__ = ["SQLITE_DATA_TYPE_SUGGESTIONS", "SQLiteDataTypeSuggestionsMixin"]
