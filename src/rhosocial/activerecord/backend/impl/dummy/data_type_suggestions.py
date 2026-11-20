# src/rhosocial/activerecord/backend/impl/dummy/data_type_suggestions.py
"""The dummy dialect's **suggested data types**: core's portable baseline.

The dummy dialect renders the portable SQL surface and stands for no server,
so its suggestion is the standard-shaped declaration -- deliberately **not**
SQLite's answer, for the same reason its column-class table is not SQLite's:
the dummy is the dialect-less default a unit test reads, not a copy of a
backend.

Every framework-modelled type is answered, including the six complex
families: the portable carriers are text (the geometry the adapters render
as WKT, bit strings as their digits), JSON documents (a vector, a range and
a multirange), and a fixed-width text column for a MAC address. A suggestion
is what a bare field gets, so an answer of ``None`` would take the table
away from the caller; a backend that wants a precise spelling overrides the
entry or the field declares ``UseSqlType``.

Each call returns a fresh dict whose values are this module's read-only
templates; a caller binds a dialect on a copy of the entry it uses.
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
    UUIDType,
    VarCharType,
)

#: The portable baseline suggestion per framework-modelled Python type.
DUMMY_DATA_TYPE_SUGGESTIONS: Dict[Any, Optional[Any]] = {
    bool: BooleanType(),
    int: IntegerType(),
    float: DoubleType(),
    decimal.Decimal: DecimalType(),
    str: TextType(),
    bytes: BlobType(),
    bytearray: BlobType(),
    datetime.date: DateType(),
    datetime.time: TimeType(),
    datetime.datetime: TimestampType(precision=3),
    datetime.timedelta: IntervalType(),
    uuid.UUID: UUIDType(),
    dict: JsonType(),
    list: JsonType(),
    tuple: JsonType(),
    set: JsonType(),
    frozenset: JsonType(),
    enum.Enum: VarCharType(length=255),
    # Complex families: the portable surface carries them as text or a JSON
    # document. ``Geometry`` is text because that is what the adapters render
    # as WKT; a vector and a range are structured JSON; a bit string is its
    # digits; a MAC address is its canonical 17-character text.
    Geometry: TextType(),
    Vector: JsonType(),
    BitString: TextType(),
    Range: JsonType(),
    Multirange: JsonType(),
    MacAddress: VarCharType(length=17),
}


class DummyDataTypeSuggestionsMixin:
    """The dialect-less baseline data-type suggestion, for tests to read."""

    def suggested_data_types(self) -> Dict[Any, Optional[Any]]:
        return dict(DUMMY_DATA_TYPE_SUGGESTIONS)


__all__ = ["DUMMY_DATA_TYPE_SUGGESTIONS", "DummyDataTypeSuggestionsMixin"]
