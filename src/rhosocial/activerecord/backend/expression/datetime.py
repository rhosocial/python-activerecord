# src/rhosocial/activerecord/backend/expression/datetime.py
"""Date/time expression structures."""

import math
from enum import Enum
from typing import TYPE_CHECKING, Union

from .bases import BaseExpression, SQLQueryAndParams, SQLValueExpression
from .mixins import AliasableMixin, ArithmeticMixin, ComparisonMixin, StringMixin, TypeCastingMixin

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class DateTimeField(str, Enum):
    """Supported datetime fields."""

    YEAR = "year"
    MONTH = "month"
    WEEK = "week"
    DAY = "day"
    HOUR = "hour"
    MINUTE = "minute"
    SECOND = "second"
    DOW = "dow"
    DOY = "doy"


class IntervalUnit(str, Enum):
    """Supported interval units."""

    YEAR = "year"
    MONTH = "month"
    WEEK = "week"
    DAY = "day"
    HOUR = "hour"
    MINUTE = "minute"
    SECOND = "second"


_FIELD_ALIASES = {
    "years": DateTimeField.YEAR,
    "yyyy": DateTimeField.YEAR,
    "yy": DateTimeField.YEAR,
    "months": DateTimeField.MONTH,
    "mon": DateTimeField.MONTH,
    "mm": DateTimeField.MONTH,
    "weeks": DateTimeField.WEEK,
    "wk": DateTimeField.WEEK,
    "ww": DateTimeField.WEEK,
    "days": DateTimeField.DAY,
    "dd": DateTimeField.DAY,
    "hours": DateTimeField.HOUR,
    "hh": DateTimeField.HOUR,
    "minutes": DateTimeField.MINUTE,
    "mins": DateTimeField.MINUTE,
    "mi": DateTimeField.MINUTE,
    "seconds": DateTimeField.SECOND,
    "secs": DateTimeField.SECOND,
    "ss": DateTimeField.SECOND,
    "dow": DateTimeField.DOW,
    "weekday": DateTimeField.DOW,
    "doy": DateTimeField.DOY,
    "dayofyear": DateTimeField.DOY,
}

_UNIT_ALIASES = {
    "years": IntervalUnit.YEAR,
    "yyyy": IntervalUnit.YEAR,
    "yy": IntervalUnit.YEAR,
    "months": IntervalUnit.MONTH,
    "mon": IntervalUnit.MONTH,
    "mm": IntervalUnit.MONTH,
    "weeks": IntervalUnit.WEEK,
    "wk": IntervalUnit.WEEK,
    "ww": IntervalUnit.WEEK,
    "days": IntervalUnit.DAY,
    "dd": IntervalUnit.DAY,
    "hours": IntervalUnit.HOUR,
    "hh": IntervalUnit.HOUR,
    "minutes": IntervalUnit.MINUTE,
    "mins": IntervalUnit.MINUTE,
    "mi": IntervalUnit.MINUTE,
    "seconds": IntervalUnit.SECOND,
    "secs": IntervalUnit.SECOND,
    "ss": IntervalUnit.SECOND,
}


def normalize_datetime_field(field: Union[str, DateTimeField]) -> DateTimeField:
    """Normalize and validate a datetime field token."""
    if isinstance(field, DateTimeField):
        return field
    normalized = str(field).strip().lower()
    if not normalized:
        raise ValueError("datetime field cannot be empty")
    if normalized in DateTimeField._value2member_map_:
        return DateTimeField(normalized)
    if normalized in _FIELD_ALIASES:
        return _FIELD_ALIASES[normalized]
    raise ValueError(f"unsupported datetime field: {field!r}")


def normalize_interval_unit(unit: Union[str, IntervalUnit]) -> IntervalUnit:
    """Normalize and validate an interval unit token."""
    if isinstance(unit, IntervalUnit):
        return unit
    normalized = str(unit).strip().lower()
    if not normalized:
        raise ValueError("interval unit cannot be empty")
    if normalized in IntervalUnit._value2member_map_:
        return IntervalUnit(normalized)
    if normalized in _UNIT_ALIASES:
        return _UNIT_ALIASES[normalized]
    raise ValueError(f"unsupported interval unit: {unit!r}")


def validate_interval_value(value: Union[int, float]) -> Union[int, float]:
    """Validate an interval numeric value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("interval value must be a finite int or float")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("interval value must be finite")
    return value


class _TemporalValueExpression(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    StringMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    pass


class ExtractExpression(_TemporalValueExpression):
    """Represents extraction of a datetime field from an expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        field: Union[str, DateTimeField],
        source: BaseExpression,
        alias: str = None,
    ):
        super().__init__(dialect)
        self.field = normalize_datetime_field(field)
        self.source = source
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_extract_expression(self)


class DatePartExpression(_TemporalValueExpression):
    """Represents backend-specific date part extraction."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        field: Union[str, DateTimeField],
        source: BaseExpression,
        alias: str = None,
    ):
        super().__init__(dialect)
        self.field = normalize_datetime_field(field)
        self.source = source
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_date_part_expression(self)


class DateTruncExpression(_TemporalValueExpression):
    """Represents truncating a datetime expression to a field."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        field: Union[str, DateTimeField],
        source: BaseExpression,
        alias: str = None,
    ):
        super().__init__(dialect)
        self.field = normalize_datetime_field(field)
        self.source = source
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_date_trunc_expression(self)


class IntervalExpression(_TemporalValueExpression):
    """Represents a structured interval value."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: Union[int, float],
        unit: Union[str, IntervalUnit],
        alias: str = None,
    ):
        super().__init__(dialect)
        self.value = validate_interval_value(value)
        self.unit = normalize_interval_unit(unit)
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_interval_expression(self)


class DateTimeAddExpression(_TemporalValueExpression):
    """Represents adding an interval to a datetime expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        source: BaseExpression,
        interval: IntervalExpression,
        alias: str = None,
    ):
        super().__init__(dialect)
        self.source = source
        self.interval = interval
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_datetime_add_expression(self)


class DateTimeSubtractExpression(_TemporalValueExpression):
    """Represents subtracting an interval from a datetime expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        source: BaseExpression,
        interval: IntervalExpression,
        alias: str = None,
    ):
        super().__init__(dialect)
        self.source = source
        self.interval = interval
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_datetime_subtract_expression(self)


class DateTimeDiffExpression(_TemporalValueExpression):
    """Represents the difference between two datetime expressions."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        unit: Union[str, IntervalUnit],
        start: BaseExpression,
        end: BaseExpression,
        alias: str = None,
    ):
        super().__init__(dialect)
        self.unit = normalize_interval_unit(unit)
        self.start = start
        self.end = end
        self.alias = alias

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_datetime_diff_expression(self)
