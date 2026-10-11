# src/rhosocial/activerecord/backend/expression/datetime.py
"""Date/time expression structures."""

import math
from enum import Enum
from typing import Any, Dict, TYPE_CHECKING, Union

from .mixins import (
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
)

from .advanced_functions import DeclaredValueType
from .bases import BaseExpression, SQLQueryAndParams, SQLValueExpression
from .core import (
    IntegerValueExpression,
    IntervalValueExpression,
    NumericValueExpression,
    TimestampValueExpression,
)

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
    ComparisonMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Shared base for the temporal operation nodes.

    No ``StringPatternPredicateMixin``: a date, a time, a timestamp and a span
    are not text, so ``like`` is not an operation any of them offers. The same
    goes for arithmetic here — these nodes render, they do not compose — so the
    surface is what every value can do and nothing more.

    Each node below also names the value type it *produces*, by inheriting that
    type's class alongside this one. Two consequences, both wanted:

    * What the operation yields is readable off the object — ``EXTRACT`` is a
      :class:`~...expression.core.NumericValueExpression` because it derives
      from one, not because a tag said so and a tag could disagree with the
      class it sat on.
    * The operations follow from it. ``extract("year") + 1`` composes because a
      number composes, and ``date_trunc`` results can be truncated again because
      a timestamp is a timestamp.

    Being a value class is not the same as being a *wrapper* of one. The value
    classes hold a node and delegate rendering to it; these nodes are the nodes,
    with their own formatters and their own fields, so each carries
    :class:`~...expression.advanced_functions.DeclaredValueType` to keep the base
    rendering and each binds its dialect through
    :meth:`BaseExpression.__init__` rather than through ``super()``.
    """


class ExtractExpression(_TemporalValueExpression, DeclaredValueType, NumericValueExpression):
    """``EXTRACT(field FROM source)`` -- a number.

    Numeric rather than integral because ``EXTRACT(EPOCH FROM ts)`` is
    fractional. Widening here is deliberate: claiming a whole number would offer
    ``bit_length`` on a value that may be a million and a half.

    It is a :class:`~...expression.core.NumericValueExpression` because that is
    what it is, and that is why ``extract("year") + 1`` composes. The class
    declares the type rather than a tag recording it, so ``isinstance`` answers
    from the class alone.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        field: Union[str, DateTimeField],
        source: BaseExpression,
        alias: str = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.field = normalize_datetime_field(field)
        self.source = source
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_extract_expression"


class DatePartExpression(_TemporalValueExpression, DeclaredValueType, NumericValueExpression):
    """The SQL-standard spelling of :class:`ExtractExpression`, and a number too.

    Separate because a backend may render it differently, and because a caller
    writing standard SQL should say so. Same answer, same class family: some
    parts of a timestamp are whole numbers, but the unit decides, and a unit
    this cannot rule out being fractional exists.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        field: Union[str, DateTimeField],
        source: BaseExpression,
        alias: str = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.field = normalize_datetime_field(field)
        self.source = source
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_date_part_expression"


class DateTruncExpression(_TemporalValueExpression, DeclaredValueType, TimestampValueExpression):
    """Truncating a timestamp to a field gives a timestamp.

    Not an integer: the parts are dropped, not rounded away, so what comes back
    is still a point in time and can still be compared, truncated again, or
    added to.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        field: Union[str, DateTimeField],
        source: BaseExpression,
        alias: str = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.field = normalize_datetime_field(field)
        self.source = source
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_date_trunc_expression"


class IntervalExpression(_TemporalValueExpression, DeclaredValueType, IntervalValueExpression):
    """A structured interval value -- a span of time, its own type.

    Not a timestamp and not a number: `
ow() + INTERVAL '1 day'`` is a
    timestamp, and that is the operation the span exists to take part in. Its
    own class is what says so, which is why ``date_add`` takes one.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: Union[int, float],
        unit: Union[str, IntervalUnit],
        alias: str = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.value = validate_interval_value(value)
        self.unit = normalize_interval_unit(unit)
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_interval_expression"


class DateTimeAddExpression(_TemporalValueExpression, DeclaredValueType, TimestampValueExpression):
    """Adding an interval to a timestamp gives a timestamp.

    Shifting time keeps it time. The result is a point in time, not a count of
    anything, so it takes the same class the operand did -- which is what makes
    `
ow().date_add(1, "day").date_trunc("day")`` chain.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        source: BaseExpression,
        interval: IntervalExpression,
        alias: str = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.source = source
        self.interval = interval
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_datetime_add_expression"


class DateTimeSubtractExpression(_TemporalValueExpression, DeclaredValueType, TimestampValueExpression):
    """Subtracting an interval from a timestamp gives a timestamp.

    The mirror of :class:`DateTimeAddExpression`, and the same answer: going back
    in time leaves you at a point in time.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        source: BaseExpression,
        interval: IntervalExpression,
        alias: str = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.source = source
        self.interval = interval
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_datetime_subtract_expression"


class DateTimeDiffExpression(_TemporalValueExpression, DeclaredValueType, IntegerValueExpression):
    """The difference between two timestamps, counted in whole units.

    This is the one temporal operation that is not a temporal value: `
ow() -
    now()`` is a count, not a point in time. Whole rather than fractional
    because the unit is named -- ``DATEDIFF(day, a, b)`` counts days crossed, so
    there is nothing here to be half of. The class is what says so, rather than a
    tag distinguishing it from the operations that stay time.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        unit: Union[str, IntervalUnit],
        start: BaseExpression,
        end: BaseExpression,
        alias: str = None,
    ):
        BaseExpression.__init__(self, dialect)
        self.unit = normalize_interval_unit(unit)
        self.start = start
        self.end = end
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_datetime_diff_expression"


class TemporalOptionsExpression(BaseExpression):
    """FOR SYSTEM_TIME AS OF ... temporal table options."""

    def __init__(self, dialect, options: Dict[str, Any]):
        super().__init__(dialect)
        self.options = options

    @property
    def format_method(self) -> str:
        return "format_temporal_options"
