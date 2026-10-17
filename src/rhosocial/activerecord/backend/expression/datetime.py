# src/rhosocial/activerecord/backend/expression/datetime.py
"""Date/time expression structures."""

import math
from enum import Enum
from typing import Any, Dict, Optional, TYPE_CHECKING, Union

from .mixins import (
    IntervalMixin,
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
)

from .advanced_functions import DeclaredValueType
from .bases import BaseExpression, SQLValue

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


from .surfaces import (
    NumericSurface,
    TemporalSurface,
)

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



#: Accepted spellings for :class:`DateTimeField`, each mapped to the member it
#: names -- ``"yyyy"``, ``"yy"`` and ``"years"`` are three ways of writing YEAR.
#: It sits here, beside the enum that owns the domain, rather than as a private
#: table elsewhere. It cannot live in the enum body: every non-descriptor
#: assignment in an Enum body becomes a *member*, so a dict there would be an
#: enum member rather than a lookup table.
DATETIME_FIELD_ALIASES = {
    "years": DateTimeField.YEAR, "yyyy": DateTimeField.YEAR, "yy": DateTimeField.YEAR,
    "months": DateTimeField.MONTH, "mon": DateTimeField.MONTH, "mm": DateTimeField.MONTH,
    "weeks": DateTimeField.WEEK, "wk": DateTimeField.WEEK, "ww": DateTimeField.WEEK,
    "days": DateTimeField.DAY, "dd": DateTimeField.DAY,
    "hours": DateTimeField.HOUR, "hh": DateTimeField.HOUR,
    "minutes": DateTimeField.MINUTE, "mins": DateTimeField.MINUTE, "mi": DateTimeField.MINUTE,
    "seconds": DateTimeField.SECOND, "secs": DateTimeField.SECOND, "ss": DateTimeField.SECOND,
    "weekday": DateTimeField.DOW,
    "dayofyear": DateTimeField.DOY,
}


#: Accepted spellings for :class:`IntervalUnit`, same shape as
#: :data:`DATETIME_FIELD_ALIASES`.
INTERVAL_UNIT_ALIASES = {
    "years": IntervalUnit.YEAR, "yyyy": IntervalUnit.YEAR, "yy": IntervalUnit.YEAR,
    "months": IntervalUnit.MONTH, "mon": IntervalUnit.MONTH, "mm": IntervalUnit.MONTH,
    "weeks": IntervalUnit.WEEK, "wk": IntervalUnit.WEEK, "ww": IntervalUnit.WEEK,
    "days": IntervalUnit.DAY, "dd": IntervalUnit.DAY,
    "hours": IntervalUnit.HOUR, "hh": IntervalUnit.HOUR,
    "minutes": IntervalUnit.MINUTE, "mins": IntervalUnit.MINUTE, "mi": IntervalUnit.MINUTE,
    "seconds": IntervalUnit.SECOND, "secs": IntervalUnit.SECOND, "ss": IntervalUnit.SECOND,
}


def normalize_datetime_field(field: Union[str, DateTimeField]) -> DateTimeField:
    """Normalize and validate a datetime field token.

    A member passes through; a word that is a member's own value becomes that
    member; a word that is an alias of one becomes that member. Anything else is
    refused, so a typo cannot silently pick a neighbouring field.
    """
    if isinstance(field, DateTimeField):
        return field
    normalized = str(field).strip().lower()
    if not normalized:
        raise ValueError("datetime field cannot be empty")
    if normalized in DateTimeField._value2member_map_:
        return DateTimeField(normalized)
    aliased = DATETIME_FIELD_ALIASES.get(normalized)
    if aliased is not None:
        return DateTimeField(aliased)
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
    aliased = INTERVAL_UNIT_ALIASES.get(normalized)
    if aliased is not None:
        return IntervalUnit(aliased)
    raise ValueError(f"unsupported interval unit: {unit!r}")


def validate_interval_value(value: Union[int, float]) -> Union[int, float]:
    """Validate an interval numeric value."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("interval value must be a finite int or float")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("interval value must be finite")
    return value


class _TemporalValue(
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValue,
):
    """Shared base for the temporal operation nodes.

    No ``StringPatternPredicateMixin``: a date, a time, a timestamp and a span
    are not text, so ``like`` is not an operation any of them offers. The same
    goes for arithmetic here — these nodes render, they do not compose — so the
    surface is what every value can do and nothing more.

    Each node below also names the value type it *produces*, by inheriting that
    type's class alongside this one. Two consequences, both wanted:

    * What the operation yields is readable off the object — ``EXTRACT`` is a
      :class:`~...expression.surfaces.NumericSurface` because it derives
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

    @staticmethod
    def _precision(dialect: "SQLDialectBase", precision: Optional[int]):
        """The fractional-seconds scale as a node, or ``None`` when absent.

        A bare ``int`` is what a caller writes, and it is not what the formatter
        can render -- the precision is a parameter of the function, so it goes
        into the parameter sequence like any other. Normalising here rather than
        in each factory means constructing the node directly is safe too.
        """
        if precision is None:
            return None
        from . import values

        return values.IntegerValue.of(dialect, precision)


class _ExtractBase(_TemporalValue):
    """The field-and-source shape both extract spellings share.

    ``EXTRACT(YEAR FROM ts)`` and ``YEAR(ts)`` ask the same question of the same
    operands, so the fields, the validation and :attr:`spelling` live here once.
    What is *not* shared is the type they answer with, which is the reason there
    are two classes below rather than one -- see each one's own docstring.
    """

    #: The spellings this node can be asked for. ``EXTRACT`` is the standard's
    #: form; the rest name the field after the function that takes it.
    SPELLINGS = ("EXTRACT", "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND")

    def __init__(
        self,
        dialect: "SQLDialectBase",
        field: Union[str, DateTimeField],
        source: BaseExpression,
        alias: str = None,
        spelling: str = "EXTRACT",
    ):
        spelling = spelling.upper()
        if spelling not in self.SPELLINGS:
            raise ValueError(
                f"unknown extract spelling {spelling!r}: the spellings are {list(self.SPELLINGS)}"
            )
        normalized_field = normalize_datetime_field(field)
        if spelling != "EXTRACT" and normalized_field.value.upper() != spelling:
            # The field-named form writes ``YEAR(ts)`` and nothing else, so a
            # mismatched field would be silently dropped from the SQL and the
            # node would answer a different question than it was asked. Caught
            # here, where the caller can still see which of the two was meant.
            raise ValueError(
                f"spelling {spelling!r} extracts {spelling.lower()}, not "
                f"{normalized_field.value!r}"
            )
        BaseExpression.__init__(self, dialect)
        self.field = normalized_field
        self.source = source
        self.alias = alias
        self.spelling = spelling

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_extract_expression"


class ExtractExpression(
    _ExtractBase,
    DeclaredValueType,
    NumericSurface,
):
    """``EXTRACT(field FROM source)`` -- a number.

    Numeric rather than integral because ``EXTRACT(EPOCH FROM ts)`` is
    fractional. Widening here is deliberate: claiming a whole number would offer
    ``bit_length`` on a value that may be a million and a half.

    It is a :class:`~...expression.surfaces.NumericSurface` because that is
    what it is, and that is why ``extract("year") + 1`` composes. The class
    declares the type rather than a tag recording it, so ``isinstance`` answers
    from the class alone.

    :attr:`spelling` is the same answer asked the way a backend spells it. The
    default is the standard's own, so ``extract()`` and a deserialized artifact
    that names no spelling both mean ``EXTRACT``. The field-named form is
    :class:`ExtractFieldExpression` rather than this class with a spelling,
    because it answers with a whole number and this one may not.
    """


class ExtractFieldExpression(
    _ExtractBase,
    DeclaredValueType,
    NumericSurface,
):
    """``YEAR(source)`` / ``MONTH(source)`` / ... -- a whole number.

    One class for all six field-named extractions rather than six, which is what
    catalog 3.4 asks for: they differ only in the field, and a backend's
    differences in spelling are the formatter's business.

    Integral, unlike :class:`ExtractExpression`: a calendar component is a whole
    number on every backend, so claiming a fractional one would offer
    ``bit_length`` on a year. The two are separate classes precisely because
    ``EXTRACT(EPOCH FROM ts)`` is *not* a whole number -- one field splits the
    question, so the type cannot.
    """


class DatePartExpression(
    _ExtractBase,
    DeclaredValueType,
    NumericSurface,
):
    """``DATE_PART('field', source)`` -- the standard's spelling, and a number.

    Separate from :class:`ExtractExpression` because a caller writing standard
    SQL should say so, and a backend may render it differently.

    Its :attr:`spelling` is ``EXTRACT``, because that is how it renders: the
    base dialect formats ``DATE_PART`` as ``EXTRACT`` (they are the same answer),
    and a backend that has a native ``DATE_PART`` overrides the formatter. The
    field and the spelling are therefore both present, and agreeing -- the same
    invariant the field-named form holds.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        field: Union[str, DateTimeField],
        source: BaseExpression,
        alias: str = None,
    ):
        super().__init__(dialect, field, source, alias=alias, spelling="EXTRACT")

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_date_part_expression"


class DateTruncExpression(
    _TemporalValue,
    DeclaredValueType,
    TemporalSurface,
):
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


class IntervalExpression(
    _TemporalValue,
    DeclaredValueType,
    TemporalSurface,
    IntervalMixin,
):
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


class DateTimeAddExpression(
    _TemporalValue,
    DeclaredValueType,
    TemporalSurface,
):
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


class DateTimeSubtractExpression(
    _TemporalValue,
    DeclaredValueType,
    TemporalSurface,
):
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


class DateTimeDiffExpression(
    _TemporalValue,
    DeclaredValueType,
    NumericSurface,
):
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


class NowFunction(
    _TemporalValue,
    DeclaredValueType,
    TemporalSurface,
):
    """``NOW()`` -- the instant the statement began.

    A timestamp, so the temporal operations are on it: ``now().date_add(...)``
    and ``now() - some_interval`` compose. The parentheses are a spelling the
    backend decides (MySQL's ``NOW`` requires them, and its
    ``CURRENT_TIMESTAMP`` may omit them), which is why the node is not named after
    the text it writes.
    """

    #: The standard writes this with parentheses; ``NOW`` without them is
    #: a syntax error on MySQL, which is why it is declared rather than
    #: assumed.
    niladic = False

    def __init__(self, dialect: "SQLDialectBase", precision: Optional[int] = None, alias: str = None):
        BaseExpression.__init__(self, dialect)
        self.precision = self._precision(dialect, precision)
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_now_function"


class CurrentDateFunction(
    _TemporalValue,
    DeclaredValueType,
    TemporalSurface,
):
    """``CURRENT_DATE`` -- today's date, with no time and no zone.

    A date rather than a timestamp, so ``CURRENT_TIMESTAMP()::date`` and
    ``CURRENT_DATE`` are distinguishable at the type level even where a backend
    would render them alike.

    The standard writes this with no arguments, so :attr:`precision` is
    normally ``None``; it is carried because a backend that spells the scale
    (``CURRENT_DATE(6)``) needs somewhere to read it from.
    """

    #: The standard writes this without parentheses, and the backend may
    #: keep that spelling or add them.
    niladic = True

    def __init__(
        self, dialect: "SQLDialectBase", precision: Optional[int] = None, alias: str = None
    ):
        BaseExpression.__init__(self, dialect)
        self.precision = self._precision(dialect, precision)
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_current_date_function"


class CurrentTimeFunction(
    _TemporalValue,
    DeclaredValueType,
    TemporalSurface,
):
    """``CURRENT_TIME`` -- the time of day, with no date and no zone."""

    #: The standard writes this without parentheses, and the backend may
    #: keep that spelling or add them.
    niladic = True

    def __init__(self, dialect: "SQLDialectBase", precision: Optional[int] = None, alias: str = None):
        BaseExpression.__init__(self, dialect)
        self.precision = self._precision(dialect, precision)
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_current_time_function"


class CurrentTimestampFunction(
    _TemporalValue,
    DeclaredValueType,
    TemporalSurface,
):
    """``CURRENT_TIMESTAMP`` -- the instant the statement began, as a timestamp.

    :attr:`precision` is the fractional-seconds scale, and it is also a
    **spelling** question rather than only a value one: the standard writes this
    without parentheses when there is no precision and with them when there is
    one, and not every backend agrees either way. Both cases are this node, so
    the parentheses are the formatter's decision.
    """

    #: The standard writes this without parentheses, and the backend may
    #: keep that spelling or add them.
    niladic = True

    def __init__(self, dialect: "SQLDialectBase", precision: Optional[int] = None, alias: str = None):
        BaseExpression.__init__(self, dialect)
        self.precision = self._precision(dialect, precision)
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_current_timestamp_function"


class LocalTimestampFunction(
    _TemporalValue,
    DeclaredValueType,
    TemporalSurface,
):
    """``LOCALTIMESTAMP`` -- the instant as the session's time zone reads it.

    Distinct from :class:`CurrentTimestampFunction` because the two disagree
    wherever the session zone is not UTC, and on PostgreSQL only the latter is
    stored as an instant while this one is a wall-clock reading.
    """

    #: The standard writes this without parentheses, and the backend may
    #: keep that spelling or add them.
    niladic = True

    def __init__(self, dialect: "SQLDialectBase", precision: Optional[int] = None, alias: str = None):
        BaseExpression.__init__(self, dialect)
        self.precision = self._precision(dialect, precision)
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_localtimestamp_function"


class TemporalOptionsExpression(BaseExpression):
    """FOR SYSTEM_TIME AS OF ... temporal table options."""

    def __init__(self, dialect, options: Dict[str, Any]):
        super().__init__(dialect)
        self.options = options

    @property
    def format_method(self) -> str:
        return "format_temporal_options"
