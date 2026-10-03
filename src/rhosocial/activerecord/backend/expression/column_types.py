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
from .value_types import (
    ARRAY,
    INTEGER,
    BINARY,
    BOOLEAN,
    DATETIME,
    JSON,
    NUMERIC,
    STRING,
    UUID,
)
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    NumericValueMixin,
    WholeNumberResultMixin,
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

    ``value_family`` narrows the declared family per instance, which is what
    lets an ``int`` field be INTEGER while a ``float`` field on the same class
    is NUMERIC.
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
        value_family: Optional[str] = None,
    ):
        super().__init__(dialect)
        # get_params() resolves a constructor parameter to `_name` or `name`,
        # so the value has to live under the private spelling. Storing it
        # unconditionally keeps the round trip working for the default case
        # too; the parameter is part of the signature either way.
        self._value_family = value_family
        if value_family is not None:
            # Instance attribute shadows the class default, which is how one
            # class can serve two families: NumericColumn is INTEGER for an
            # `int` annotation and NUMERIC for `float`, because SQL really does
            # round a whole number to a whole number. Without this the family
            # would be whatever the class declares, and "integer in, integer
            # out" could not be expressed.
            self.VALUE_FAMILY = value_family
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

    VALUE_FAMILY = STRING
    """A column holding text: comparison, ``LIKE`` / ``ILIKE``, casting.

    Not available: arithmetic. ``LIKE`` against a numeric column is a
    database-side type error, so the framework no longer offers it.
    """


class NumericColumn(ArithmeticMixin, NumericValueMixin, ColumnBase):

    VALUE_FAMILY = NUMERIC
    """A column holding a number: comparison and arithmetic.

    Not available: ``LIKE`` / ``ILIKE``.
    """


class IntegerColumn(ArithmeticMixin, WholeNumberResultMixin,
                  NumericValueMixin, ColumnBase):
    """A column holding a whole number.

    Separate from :class:`NumericColumn` because SQL keeps the two apart in the
    result, not only in the input: ``CEIL`` of a whole number is a whole number,
    while ``SQRT`` of one is generally not. One column class for both meant the
    distinction lived in an instance attribute, which a checker cannot see, so
    ``ceil(int_column)`` and ``ceil(float_column)`` had to be told apart at run
    time by reading it back.

    As two classes the answer is in the type. ``IntegerColumn`` says what it
    holds before anything is called, and a factory that has to choose between an
    integer result and a fractional one can choose with ``isinstance`` and stay
    readable.
    """

    VALUE_FAMILY = INTEGER
    """A whole number, which SQL preserves through CEIL, FLOOR and ABS."""


class DateTimeColumn(ArithmeticMixin, DateTimeMixin, ColumnBase):

    VALUE_FAMILY = DATETIME
    """A column holding a date/time.

    Adds the temporal surface — :meth:`~...mixins.DateTimeMixin.date_trunc`,
    :meth:`~...mixins.DateTimeMixin.extract`, :meth:`~...mixins.DateTimeMixin.date_add`
    and friends — so ``User.c.created_at.date_trunc("month")`` no longer
    requires threading the dialect into a free function by hand.

    Not available: ``LIKE`` / ``ILIKE``.
    """


class BooleanColumn(ColumnBase):

    VALUE_FAMILY = BOOLEAN
    """A column holding a truth value: comparison, casting, collation."""


class BinaryColumn(ColumnBase):

    VALUE_FAMILY = BINARY
    """A column holding raw bytes: comparison, casting, collation."""


class UUIDColumn(ColumnBase):

    VALUE_FAMILY = UUID
    """A column holding a UUID.

    Carries no UUID-specific operator, because portable SQL has none — a UUID
    column supports exactly what any other value column does. The class
    exists so the value family is visible (in reprs, in ``value_type``, in
    tests) and so a backend that *does* have an operation for it has an
    unambiguous home. Storage is the DDL layer's concern.
    """


class JSONColumn(JSONAccessorMixin, ColumnBase):

    VALUE_FAMILY = JSON
    """A column holding JSON: comparison, casting, and path access.

    Adds :meth:`~...mixins.JSONAccessorMixin.json_path` (scalar, terminal)
    and :meth:`~...mixins.JSONAccessorMixin.json_value` (JSON, chainable).

    Not available: ``LIKE`` / ``ILIKE`` and arithmetic — those apply to the
    text a path access *returns*, not to the document.
    """


class ArrayColumn(ArrayMixin, ColumnBase):

    VALUE_FAMILY = ARRAY
    """A column holding an array: :meth:`~...mixins.ArrayMixin.array_length`
    and :meth:`~...mixins.ArrayMixin.unnest`."""


__all__ = [
    "ColumnBase",
    "StringColumn",
    "NumericColumn",
    "DateTimeColumn",
    "BooleanColumn",
    "BinaryColumn",
    "UUIDColumn",
    "JSONColumn",
    "ArrayColumn",
]
