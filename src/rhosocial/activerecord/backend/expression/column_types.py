# src/rhosocial/activerecord/backend/expression/column_types.py
"""Type-narrowed column expressions.

A column reference is a value, and the operations a value supports depend on
what it holds. A numeric column can be added to; a text column can be
``LIKE``-matched; a JSON column can be navigated by path. Before this module
every :class:`~...expression.core.Column` carried every one of those
operations, so ``User.c.age.like('%x%')`` rendered happily against an integer
column and only failed at the database.

The narrowing
-------------
Python cannot *remove* a mixin from a base class, so the families here are
**siblings** of each other under :class:`ColumnBase`, not subclasses of one
another. ``StringColumn(ColumnBase)`` and ``NumericColumn(ColumnBase)`` each
compose only the mixins their value type supports; there is no permissive
parent in between that they would inherit from. :class:`~...expression.core.Column`
is a sibling too — it keeps the full mixin set as the escape hatch for
columns whose type is not known (see its docstring).

Nothing about the *storage* type appears here. A ``UUIDColumn`` is a
``UUIDColumn`` on every backend; how the value is stored is the DDL layer's
business (``DataType`` / ``format_data_type_*``), and the two never read each
other. See ``expression/types/__init__.py`` for the DDL-side boundary.
"""

from typing import Optional, TYPE_CHECKING

from .bases import SQLValueExpression
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    NumericValueMixin,
    TranscendentalMixin,
    ArrayMixin,
    ComparisonMixin,
    DateTimeMixin,
    JSONAccessorMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class ColumnBase(
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Common base for every column expression.

    Carries only the operations that make sense for *any* value —
    aliasing, comparison, casting and collation — plus the eight attributes
    :meth:`SQLDialectBase.format_column` reads (``name`` / ``table`` /
    ``schema_name`` / ``alias`` and their four ``*_need_quote`` flags).

    Because it renders through the same ``format_column`` as before, adding
    this layer required no dialect change and no change to the SQL produced
    for a plain column reference.

    A column's value type is the class itself. There is no tag, no label and
    no per-instance override: ``StringColumn`` holds text, ``IntegerColumn``
    holds a whole number, and an operation is offered because the class mixes
    in the mixin that provides it. Two classes that offer the same operations
    are still two classes when they hold different things, and one class that
    held two different things would be the bug.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        name: str,
        table: Optional[str] = None,
        alias: Optional[str] = None,
        schema_name: Optional[str] = None,
        name_need_quote: bool = True,
        alias_need_quote: bool = True,
        schema_need_quote: bool = True,
        table_need_quote: bool = True,
        value_type: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.name_need_quote = name_need_quote
        self.alias_need_quote = alias_need_quote
        self.schema_need_quote = schema_need_quote
        self.table_need_quote = table_need_quote
        self.name = name
        self.table = table
        self.alias = alias
        self.schema_name = schema_name
        #: Logical value family (``"integer"``, ``"varchar"``, ``"json"``, …)
        #: or ``None`` when unknown. Recorded so serialization round-trips
        #: and diagnostics can see it; it never changes rendering.
        self.value_type = value_type

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column"

    def __repr__(self) -> str:
        parts = [repr(self.name)]
        if self.table:
            parts.insert(0, f"{self.table}.")
        return f"<{type(self).__name__} {''.join(parts)}>"


class StringColumn(StringValueMixin, StringPatternPredicateMixin, ColumnBase):
    """A column holding text: comparison, ``LIKE`` / ``ILIKE``, casting.

    Not available: arithmetic. ``LIKE`` against a numeric column is a
    database-side type error, so the framework no longer offers it.
    """



class NumericColumn(ArithmeticMixin, NumericValueMixin, TranscendentalMixin, ColumnBase):
    """A column holding a number: comparison and arithmetic.

    The base of every numeric family. ``DecimalColumn`` and ``FloatColumn``
    derive from it rather than repeating the mixins, so a backend that models a
    numeric type of its own — a monetary amount, an unsigned width — derives
    from this and inherits what it agrees with.

    Not available: ``LIKE`` / ``ILIKE``.

    Precision is deliberately absent. SQL's arithmetic syntax has nowhere to
    state it — ``a + b`` is the same statement whatever ``a`` was declared as —
    so a ``NUMERIC(18,4)`` column and a ``NUMERIC(4,1)`` column offer exactly the
    same operations. Width and scale belong to the DDL layer's ``DataType``,
    which is a separate concern and never read from here.
    """



class IntegerColumn(NumericColumn):
    """A column holding a whole number.

    A subclass rather than a sibling of :class:`NumericColumn`: arithmetic on a
    whole number is arithmetic, so there is nothing to redeclare. What differs
    is the *result* — SQL keeps ``CEIL`` of a whole number a whole number, while
    ``SQRT`` of one generally is not — and :class:`WholeNumberResultMixin`
    supplies that by overriding the five operations whose result follows the
    operand.

    It has to be listed ahead of :class:`NumericValueMixin` for those overrides
    to win, which is what the MRO below arranges.

    ``TranscendentalMixin`` is inherited and not withheld: ``log(2)`` is a legal
    query the database will answer, and an integer behaving differently from the
    float it widens to would be a difference the caller cannot see or explain.
    A monetary column is different in kind rather than in width, and is the case
    that leaves this mixin out.
    """

    """A whole number, which SQL preserves through CEIL, FLOOR and ABS."""


class DecimalColumn(NumericColumn):
    """A column holding an exact fixed-point number.

    Separate from :class:`FloatColumn` because the two answer different
    questions — an amount that must add up exactly is not one that must stay
    within a rounding error — but they offer the same operations, so the
    difference is in the name a caller reads rather than in the method set.

    Scale is not a parameter here. See :class:`NumericColumn` on why.
    """



class FloatColumn(NumericColumn):
    """A column holding an approximate number.

    The parent of :class:`RealColumn` and :class:`DoubleColumn`. Those three
    offer **the same operations** — an approximate value is an approximate value
    whichever width it is stored at, and ``sqrt`` of one is as approximate as
    ``sqrt`` of the other. The split exists for two narrower reasons: SQL
    standard and every backend distinguish single from double precision, and a
    backend needs a class to derive from when it models its own widths (PostgreSQL
    has ``float4`` and ``float8``). Nothing about the operation set depends on
    which of the three a column is.
    """



class RealColumn(FloatColumn):
    """A single-precision approximate number (``REAL``).

    Operationally identical to :class:`FloatColumn`; see its docstring for why
    the class exists anyway.
    """



class DoubleColumn(FloatColumn):
    """A double-precision approximate number (``DOUBLE PRECISION``).

    Operationally identical to :class:`FloatColumn`; see its docstring for why
    the class exists anyway.
    """



class DateTimeColumn(ArithmeticMixin, DateTimeMixin, ColumnBase):

    """A column holding a date/time.

    Adds the temporal surface — :meth:`~...mixins.DateTimeMixin.date_trunc`,
    :meth:`~...mixins.DateTimeMixin.extract`, :meth:`~...mixins.DateTimeMixin.date_add`
    and friends — so ``User.c.created_at.date_trunc("month")`` no longer
    requires threading the dialect into a free function by hand.

    Not available: ``LIKE`` / ``ILIKE``.
    """


class BooleanColumn(ColumnBase):

    """A column holding a truth value: comparison, casting, collation."""


class BinaryColumn(ColumnBase):

    """A column holding raw bytes: comparison, casting, collation."""


class UUIDColumn(ColumnBase):

    """A column holding a UUID.

    Carries no UUID-specific operator, because portable SQL has none — a UUID
    column supports exactly what any other value column does. The class
    exists so the value family is visible (in reprs, in ``value_type``, in
    tests) and so a backend that *does* have an operation for it has an
    unambiguous home. Storage is the DDL layer's concern.
    """


class JSONColumn(JSONAccessorMixin, ColumnBase):

    """A column holding JSON: comparison, casting, and path access.

    Adds :meth:`~...mixins.JSONAccessorMixin.json_path` (scalar, terminal)
    and :meth:`~...mixins.JSONAccessorMixin.json_value` (JSON, chainable).

    Not available: ``LIKE`` / ``ILIKE`` and arithmetic — those apply to the
    text a path access *returns*, not to the document.
    """


class ArrayColumn(ArrayMixin, ColumnBase):

    """A column holding an array: :meth:`~...mixins.ArrayMixin.array_length`
    and :meth:`~...mixins.ArrayMixin.unnest`."""



__all__ = [
    "ColumnBase",
    "StringColumn",
    "NumericColumn",
    "IntegerColumn",
    "DecimalColumn",
    "FloatColumn",
    "RealColumn",
    "DoubleColumn",
    "DateTimeColumn",
    "BooleanColumn",
    "BinaryColumn",
    "UUIDColumn",
    "JSONColumn",
    "ArrayColumn",
]
