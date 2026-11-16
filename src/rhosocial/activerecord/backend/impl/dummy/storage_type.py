# src/rhosocial/activerecord/backend/impl/dummy/storage_type.py
"""The dummy dialect's **suggested storage types**: core's portable baseline.

The dummy dialect renders the portable SQL surface and stands for no server,
so its suggestion is the standard-shaped declaration -- deliberately **not**
SQLite's answer, for the same reason its column-class table is not SQLite's:
the dummy is the dialect-less default a unit test reads, not a copy of a
backend.

The complex families fall back to text for the geometry-shaped values (the
adapters render WKT) and to ``None`` where nothing portable describes them.
Values are copies: see ``StorageTypeMixin.storage_type_copies``.
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
from rhosocial.activerecord.backend.dialect.mixins.storage_type import StorageTypeMixin
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
DUMMY_STORAGE_TYPES: Dict[Any, Optional[Any]] = {
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
    # Complex families: the portable surface has no type of its own for them.
    # ``Geometry`` is text (WKT) because that is what the adapters render; the
    # rest answer ``None`` rather than invent a portable spelling.
    Geometry: TextType(),
    Vector: None,
    BitString: None,
    Range: None,
    Multirange: None,
    MacAddress: None,
}


class DummyStorageTypeMixin(StorageTypeMixin):
    """The dialect-less baseline storage suggestion, for tests to read."""

    def suggested_storage_types(self) -> Dict[Any, Optional[Any]]:
        return self.storage_type_copies(DUMMY_STORAGE_TYPES)


__all__ = ["DUMMY_STORAGE_TYPES", "DummyStorageTypeMixin"]
