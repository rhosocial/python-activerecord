# src/rhosocial/activerecord/backend/expression/values.py
"""Typed value nodes (catalog §3.3) — one node per value type.

Each class is the expression for **one** value type and holds that type's
**host value**:

    IntegerValue(d, 18)                      holds ``int``
    DateValue(d, datetime.date(2026, 10, 17)) holds ``datetime.date``
    BinaryValue(d, b"\\x01\\x02")              holds ``bytes``

Why the host value and not the canonical spelling: the spelling is the
**artifact** form, and it is the codec's job (spec 4.8). A node that stored
``"2026-10-17"`` instead of a ``date`` would be storing the serialization, and
the value would have to be parsed back before the driver could bind it — work
the host language already did for free, undone on purpose. The three stages of
one value therefore stay separated (spec 2.1 / 4.4):

===========================  ============================  =======================
stage                       form                          who converts
===========================  ============================  =======================
the node's ``value`` param  host value                    the caller
the artifact                canonical spelling (wire 5)   the codec
the parameter sequence      host value                    nobody -- it is what
                                                         the driver binds
===========================  ============================  =======================

The spelling is not a free choice at the node: spec 4.8 requires the artifact
representation to be language-neutral, so a Python ``date`` and a Go
``time.Time`` must serialize identically. That constraint lands on the codec,
where it belongs.

Rendering splits on ``inline_params``, the class-level strategy: a data
position binds the host value behind a placeholder, a DDL syntax position
inlines a literal the dialect constructs. Which one happens is the **class's**
decision, never a per-instance flag (spec 4.4).
"""

import base64
import datetime
import re
import decimal
import uuid
from typing import TYPE_CHECKING, Any, Optional

from .bases import BaseExpression, SQLValue
from .mixins import IntervalMixin
from .surfaces import (
    BooleanSurface,
    NumericSurface,
    OpaqueSurface,
    TemporalSurface,
    TextSurface,
)

if TYPE_CHECKING:
    from ..dialect import SQLDialectBase


#: The two reserved wrapper keys (wire §5). A parameter named either would be
#: indistinguishable from the wrapper, so the serializer refuses them by name.
B64_KEY = "__b64__"
DUR_KEY = "__dur__"

#: ISO 8601 duration, reduced to what ``timedelta`` can hold: days, hours,
#: minutes, seconds and an optional fraction. Years and months are refused --
#: their length is not a constant, so a timedelta cannot carry them honestly.
_DURATION_RE = re.compile(
    r"^-?P"
    r"(?:(?P<days>\d+)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?"
    r")?$"
)


def _parse_duration(text: str) -> datetime.timedelta:
    """``"P1DT2H3M4.5S"`` -> timedelta, or a refusal naming what it cannot hold."""
    match = _DURATION_RE.match(text)
    if match is None:
        raise ValueError(
            f"{text!r} is not an ISO 8601 duration this implementation can "
            f"carry. Years and months have no fixed length, so they cannot "
            f"become a timedelta; use a day/hour/minute/second form."
        )
    parts = match.groupdict()
    delta = datetime.timedelta(
        days=int(parts["days"] or 0),
        hours=int(parts["hours"] or 0),
        minutes=int(parts["minutes"] or 0),
        seconds=float(parts["seconds"] or 0),
    )
    return -delta if text.startswith("-") else delta


class TypedValue(SQLValue):
    """Base for the typed value nodes.

    A subclass declares three things and nothing else: the wire ``kind``, the
    host type it holds (:attr:`value_type`), and the dialect method that renders
    it (:attr:`format_method`).

    :attr:`value_type` does two jobs, and they are the same job seen from two
    sides. It says what the node holds, and -- through :meth:`normalise` -- what
    a serialized form is turned into. An artifact cannot carry a ``date``, only
    the string that stands for one, so a constructor that accepted only
    ``date`` would make every ``date_value`` unreadable. It accepts the string
    and converts it, which is the rule for every argument in this package: the
    expression declares what it takes and is the one place that says so.

    The class is public because other nodes need to *ask* whether something is
    a typed value -- to read the number behind an integer position, say. That is
    a question with a declared answer, asked with ``isinstance`` against this
    base; it is not a reason to reach for :func:`getattr` and find out.
    """

    #: The wire kind. Spec 4.11.1 derives it mechanically from the class name;
    #: it is declared rather than inferred so the contract is readable here.
    kind_name: str = ""

    #: The host type this value holds, and the target of :meth:`normalise`.
    value_type: type = object

    @classmethod
    def normalise(cls, value: Any) -> Any:
        """*value* as this class holds it, converting its serialized form.

        The default does nothing, because a class whose host type is a JSON
        scalar -- ``int``, ``bool``, ``str``, ``None`` -- arrives already in the
        form it is stored in. A class holding something JSON cannot carry
        overrides this to parse: a ``date_value`` receives ``"2026-10-17"`` and
        returns a ``date``.

        This is not a second declaration of the type. It is the conversion that
        :attr:`value_type` implies, and it lives here because here is the only
        place that knows both the type and how to produce it.
        """
        return value

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: Any,
        *,
        alias: Optional[str] = None,
    ):
        value = self.normalise(value)
        if not isinstance(value, self.value_type):
            raise TypeError(
                f"{type(self).__name__} takes a {self.value_type.__name__}, "
                f"not a {type(value).__name__}"
            )
        super().__init__(dialect)
        self.value = value
        self.alias = alias

    @classmethod
    def of(cls, dialect: "SQLDialectBase", value: Any) -> "TypedValue":
        """*value* as a node of this class, if it is not one already.

        The one place a bare host value becomes a node, and it is a classmethod
        on the class that knows the value's own type -- so the choice of node is
        written at the call site as ``StringValue.of(dialect, x)`` rather than
        decided by a lookup table that has to be kept in step with the classes.
        An expression is returned untouched: a caller who wrote a node said what
        they meant.
        """
        if isinstance(value, BaseExpression):
            return value
        return cls(dialect, value)

    @property
    def format_method(self) -> str:
        """The dialect method that renders this value.

        One method per value type, named for the type, so a backend overrides
        exactly the kinds whose grammar it spells differently and leaves the
        rest to the base (spec 4.4: who defines a value type constructs its
        literal).
        """
        return f"format_{self.kind_name}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.value!r})"


class NullValue(TypedValue):
    """The NULL literal.

    The one value type carrying nothing: ``null_value`` takes no ``value``
    param, so the artifact is ``{"kind": "null"}``.
    """

    kind_name = "null_value"
    value_type = type(None)

    def __init__(self, dialect: "SQLDialectBase", *, alias: Optional[str] = None):
        super().__init__(dialect, None, alias=alias)


class BooleanValue(
    TypedValue,
    BooleanSurface,
):
    """A boolean literal."""

    kind_name = "boolean_value"
    value_type = bool


class IntegerValue(
    TypedValue,
    NumericSurface,
):
    """An integer literal.

    ``int`` is arbitrary precision in Python, which spec 4.8 explicitly allows:
    a value another language's reader cannot hold must fail **there**, not be
    narrowed on the way out.
    """

    kind_name = "integer_value"
    value_type = int

    def __init__(self, dialect, value, *, alias=None):
        # bool is an int subclass, so True would slip through as 1. The wire
        # declares this param boolean-or-integer; a bool belongs to
        # boolean_value, and conflating them changes the rendered type.
        if isinstance(value, bool):
            raise TypeError(
                f"IntegerValue takes an int, not a bool -- use BooleanValue for {value!r}"
            )
        super().__init__(dialect, value, alias=alias)


class FloatValue(
    TypedValue,
    NumericSurface,
):
    """A floating-point literal (IEEE 754 double)."""

    kind_name = "float_value"
    value_type = float

    def __init__(self, dialect, value, *, alias=None):
        # int is acceptable and exact; float() widens it. NaN and Inf are
        # refused: spec 4.8 rejects them outright rather than trusting the host
        # encoder, because every language spells them differently (and
        # ``str(float('inf'))`` is ``'inf'``, which would read as an identifier).
        if isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
        super().__init__(dialect, value, alias=alias)
        if self.value != self.value or self.value in (float("inf"), float("-inf")):
            raise ValueError("FloatValue rejects NaN and Inf (spec 4.8)")


class DecimalValue(
    TypedValue,
    NumericSurface,
):
    """An exact decimal literal -- money.

    ``Decimal``, never ``float``: the point of this type is that no precision
    is lost before the value reaches the artifact, where it becomes a string
    (wire §5).
    """

    @classmethod
    def normalise(cls, value: Any) -> Any:
        # A Decimal travels as a string: binary floating point cannot carry its
        # precision, and an artifact must not round a money value.
        return value if isinstance(value, decimal.Decimal) else decimal.Decimal(value)
    kind_name = "decimal_value"
    value_type = decimal.Decimal


class StringValue(
    TypedValue,
    TextSurface,
):
    """A string literal."""

    kind_name = "string_value"
    value_type = str


class BinaryValue(
    TypedValue,
    OpaqueSurface,
):
    """A binary literal.

    Holds ``bytes`` and binds them as bytes -- which is why the artifact's
    base64 (wire §5 ``__b64__``) stays in the codec. SQLite cannot decode
    base64 in SQL, so a spelling in the payload would have had nowhere to go;
    the host value needs no conversion at all on the bind path, and only the
    inline path cares, where the dialect builds ``X'...'`` (SQLite) or
    ``'\\x...'::bytea`` (PostgreSQL) from the bytes.
    """

    @classmethod
    def normalise(cls, value: Any) -> Any:
        # ``{"__b64__": "..."}`` is the wire form (wire §5); this class is the one
        # that knows its own payload is base64, and no other class's is.
        if isinstance(value, dict) and "__b64__" in value:
            return base64.b64decode(value["__b64__"])
        return value
    kind_name = "binary_value"
    value_type = (bytes, bytearray)


class DateValue(
    TypedValue,
    TemporalSurface,
):
    """A date literal. The host value carries its own awareness."""

    @classmethod
    def normalise(cls, value: Any) -> Any:
        return value if isinstance(value, datetime.date) else datetime.date.fromisoformat(value)
    kind_name = "date_value"
    value_type = datetime.date


class TimeValue(
    TypedValue,
    TemporalSurface,
):
    """A time-of-day literal."""

    @classmethod
    def normalise(cls, value: Any) -> Any:
        return value if isinstance(value, datetime.time) else datetime.time.fromisoformat(value)
    kind_name = "time_value"
    value_type = datetime.time


class TimestampValue(
    TypedValue,
    TemporalSurface,
):
    """A date-time literal.

    Naive and aware are both ``datetime``; the distinction lives in
    ``tzinfo`` and the spelling keeps the offset. This layer never adds ``Z``
    and never reinterprets a naive value in some other zone.
    """

    @classmethod
    def normalise(cls, value: Any) -> Any:
        return (
            value
            if isinstance(value, datetime.datetime)
            else datetime.datetime.fromisoformat(value)
        )
    kind_name = "timestamp_value"
    value_type = datetime.datetime


class IntervalValue(IntervalMixin, TypedValue):
    """A time-interval literal.

    ``datetime.timedelta``, kept because a year and a month have no fixed
    length: ``P1Y2M`` cannot be a number of seconds without changing what it
    means. The artifact carries an ISO 8601 duration (``__dur__``, wire §5).
    """

    @classmethod
    def normalise(cls, value: Any) -> Any:
        # ``{"__dur__": "P1DT2H"}`` is the wire form (wire §5). A bare number is
        # read as seconds -- the only unit a plain scalar can name.
        if isinstance(value, dict) and "__dur__" in value:
            return _parse_duration(value["__dur__"])
        if isinstance(value, str) and value.startswith(("-P", "P")):
            return _parse_duration(value)
        return (
            value
            if isinstance(value, datetime.timedelta)
            else datetime.timedelta(seconds=float(value))
        )

    kind_name = "interval_value"
    value_type = datetime.timedelta


class UUIDValue(
    TypedValue,
    OpaqueSurface,
):
    """A UUID literal."""

    @classmethod
    def normalise(cls, value: Any) -> Any:
        # Every spelling names one value: hyphenated, plain hex, any case, the
        # ``0x`` form. Widening here is a compatibility question -- external
        # sources write all four -- not a semantic one.
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))

    kind_name = "uuid_value"
    value_type = uuid.UUID


__all__ = [
    "B64_KEY",
    "DUR_KEY",
    "TypedValue",
    "NullValue",
    "BooleanValue",
    "IntegerValue",
    "FloatValue",
    "DecimalValue",
    "StringValue",
    "BinaryValue",
    "DateValue",
    "TimeValue",
    "TimestampValue",
    "IntervalValue",
    "UUIDValue",
]
