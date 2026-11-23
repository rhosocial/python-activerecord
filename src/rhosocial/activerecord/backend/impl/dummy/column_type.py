# src/rhosocial/activerecord/backend/impl/dummy/column_type.py
"""The dummy dialect's column-type table: core's dialect-less baseline.

The dummy dialect renders the portable SQL surface and stands for no server,
so its table is the portable baseline -- deliberately **not** SQLite's table,
even though SQLite is the backend built into core and the two are easy to
conflate. It is the dialect-less default a unit test reads, not a copy of any
one backend: where a real backend has stated its own answer (sequences as
JSONColumn, for instance), the dummy keeps the standard-shaped one.
"""
from rhosocial.activerecord.backend.suggestion.definitions import ColumnTypeSuggestion, ExtraColumnTypeSuggestion


import datetime
import decimal
import enum
import uuid
from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.adapters import (
    AwareDatetime,
    BitString,
    Geometry,
    IPAddress,
    MacAddress,
    Multirange,
    Range,
    Vector,
)
from rhosocial.activerecord.backend.expression.column_types import (
    ArrayColumn,
    BinaryColumn,
    BitStringColumn,
    BooleanColumn,
    ColumnBase,
    GeometryColumn,
    IntegerColumn,
    IntervalColumn,
    IPAddressColumn,
    JSONColumn,
    MacAddressColumn,
    MultirangeColumn,
    NumericColumn,
    RangeColumn,
    StringColumn,
    TimestampColumn,
    UUIDColumn,
    VectorColumn,
)

#: The portable baseline: ``{framework-modelled Python type: ColumnBase subclass}``.
#:
#: The complex families name the core classes, because those classes carry only
#: the surface every column already has (alias, null tests, casting) and promise
#: no operation the dummy cannot answer. A backend that does have family
#: operations states its own class in its own table.
DUMMY_COLUMN_TYPES: Dict[Any, Optional[Type[ColumnBase]]] = {
    bool: BooleanColumn,
    int: IntegerColumn,
    float: NumericColumn,
    decimal.Decimal: NumericColumn,
    str: StringColumn,
    bytes: BinaryColumn,
    bytearray: BinaryColumn,
    datetime.date: TimestampColumn,
    datetime.time: TimestampColumn,
    AwareDatetime: TimestampColumn,
    datetime.datetime: TimestampColumn,
    datetime.timedelta: IntervalColumn,
    uuid.UUID: UUIDColumn,
    dict: JSONColumn,
    list: ArrayColumn,
    tuple: ArrayColumn,
    set: ArrayColumn,
    frozenset: ArrayColumn,
    enum.Enum: StringColumn,
    Geometry: GeometryColumn,
    Vector: VectorColumn,
    BitString: BitStringColumn,
    Range: RangeColumn,
    Multirange: MultirangeColumn,
    MacAddress: MacAddressColumn,
    IPAddress: IPAddressColumn,
}


class DummyColumnTypeMixin:
    """The dialect-less baseline table, for tests to read."""

    def suggest_column_types(self) -> Dict[Any, Optional[Type[ColumnBase]]]:
        return ColumnTypeSuggestion(table=dict(DUMMY_COLUMN_TYPES))


    def suggest_extra_column_types(self):
        """No backend-owned extra column types."""
        return ExtraColumnTypeSuggestion(table={})


__all__ = ["DUMMY_COLUMN_TYPES", "DummyColumnTypeMixin"]
