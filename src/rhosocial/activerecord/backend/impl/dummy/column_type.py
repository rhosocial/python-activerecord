# src/rhosocial/activerecord/backend/impl/dummy/column_type.py
"""The dummy dialect's column-type table: core's dialect-less baseline.

The dummy dialect renders the portable SQL surface and stands for no server,
so its table is the portable baseline -- deliberately **not** SQLite's table,
even though SQLite is the backend built into core and the two are easy to
conflate. It is the dialect-less default a unit test reads, not a copy of any
one backend: where a real backend has stated its own answer (sequences as
JSONColumn, for instance), the dummy keeps the standard-shaped one.
"""

import datetime
import decimal
import enum
import uuid
from typing import Any, Dict, Type

from rhosocial.activerecord.backend.dialect.mixins.column_type import ColumnTypeMixin
from rhosocial.activerecord.backend.expression.column_types import (
    ArrayColumn,
    BinaryColumn,
    BooleanColumn,
    ColumnBase,
    TimestampColumn,
    IntegerColumn,
    JSONColumn,
    NumericColumn,
    StringColumn,
    UUIDColumn,
)

#: The portable baseline: ``{common Python type: ColumnBase subclass}``.
DUMMY_COLUMN_TYPES: Dict[Any, Type[ColumnBase]] = {
    bool: BooleanColumn,
    int: IntegerColumn,
    float: NumericColumn,
    decimal.Decimal: NumericColumn,
    str: StringColumn,
    bytes: BinaryColumn,
    bytearray: BinaryColumn,
    datetime.date: TimestampColumn,
    datetime.time: TimestampColumn,
    datetime.datetime: TimestampColumn,
    datetime.timedelta: NumericColumn,
    uuid.UUID: UUIDColumn,
    dict: JSONColumn,
    list: ArrayColumn,
    tuple: ArrayColumn,
    set: ArrayColumn,
    frozenset: ArrayColumn,
    enum.Enum: StringColumn,
}


class DummyColumnTypeMixin(ColumnTypeMixin):
    """The dialect-less baseline table, for tests to read."""

    def suggested_column_types(self) -> Dict[Any, Type[ColumnBase]]:
        return dict(DUMMY_COLUMN_TYPES)


__all__ = ["DUMMY_COLUMN_TYPES", "DummyColumnTypeMixin"]
