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

import datetime
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


class TypedValue(SQLValue):
    """Base for the typed value nodes.

    A subclass declares three things and nothing else: the wire ``kind``, the
    host type it accepts (:attr:`value_type`), and the dialect method that
    renders it (:attr:`format_method`). The host type is enforced at
    construction because spec 4.8 makes the kind the declaration of the
    parameter's type -- a reader that hands a ``date`` to ``date_value`` must
    fail here rather than at the driver.

    The class is public because other nodes need to *ask* whether something is
    a typed value -- to read the number behind an integer position, say. That is
    a question with a declared answer, asked with ``isinstance`` against this
    base; it is not a reason to reach for :func:`getattr` and find out.
    """

    #: The wire kind. Spec 4.11.1 derives it mechanically from the class name;
    #: it is declared rather than inferred so the contract is readable here.
    kind_name: str = ""

    #: The host type this value accepts. Checked on construction.
    value_type: type = object

    def __init__(
        self,
        dialect: "SQLDialectBase",
        value: Any,
        *,
        alias: Optional[str] = None,
    ):
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

    kind_name = "binary_value"
    value_type = (bytes, bytearray)


class DateValue(
    TypedValue,
    TemporalSurface,
):
    """A date literal. The host value carries its own awareness."""

    kind_name = "date_value"
    value_type = datetime.date


class TimeValue(
    TypedValue,
    TemporalSurface,
):
    """A time-of-day literal."""

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

    kind_name = "timestamp_value"
    value_type = datetime.datetime


class IntervalValue(IntervalMixin, TypedValue):
    """A time-interval literal.

    ``datetime.timedelta``, kept because a year and a month have no fixed
    length: ``P1Y2M`` cannot be a number of seconds without changing what it
    means. The artifact carries an ISO 8601 duration (``__dur__``, wire §5).
    """

    kind_name = "interval_value"
    value_type = datetime.timedelta


class UUIDValue(
    TypedValue,
    OpaqueSurface,
):
    """A UUID literal."""

    kind_name = "uuid_value"
    value_type = uuid.UUID


__all__ = [
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
