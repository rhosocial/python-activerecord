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
    BooleanLogicMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TemporalArithmeticMixin,
    ArrayMixin,
    ComparisonMixin,
    DateTimeMixin,
    JSONAccessorMixin,
    NotANumberMixin,
    NotComparableMixin,
    NullTestMixin,
    StringPatternPredicateMixin,
    StringToIntegerMixin,
    StringValueMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class ColumnBase(
    AliasableMixin,
    NullTestMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """Common base for every column expression.

    Carries only the operations that make sense for *any* value — aliasing,
    null tests, casting and collation — plus the eight attributes
    :meth:`SQLDialectBase.format_column` reads (``name`` / ``table`` /
    ``schema_name`` / ``alias`` and their four ``*_need_quote`` flags).

    Comparison is deliberately **not** here. It used to be, which made
    ``xml_col = xml_col`` an identity comparison in Python and a refused
    predicate at the database. Every family that can be compared names
    :class:`ComparisonMixin` for itself, and the XML family names
    :class:`NotComparableMixin` instead.

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

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_column"

    def __repr__(self) -> str:
        parts = [repr(self.name)]
        if self.table:
            parts.insert(0, f"{self.table}.")
        return f"<{type(self).__name__} {''.join(parts)}>"


class StringColumn(ComparisonMixin, StringValueMixin, StringPatternPredicateMixin, StringToIntegerMixin, ColumnBase):
    """A column holding text: comparison, ``LIKE`` / ``ILIKE``, casting.

    Not available: arithmetic. ``LIKE`` against a numeric column is a
    database-side type error, so the framework no longer offers it.
    """



class NumericColumn(ComparisonMixin, ArithmeticMixin, NumericValueMixin, TranscendentalMixin, ColumnBase):
    """A column holding a number: comparison and arithmetic.

    One class for every numeric width and precision: the operations are the
    same whatever the value was declared as, and the difference between a
    ``NUMERIC(18,4)`` and a ``DOUBLE PRECISION`` belongs to the DDL layer's
    ``DataType``, which is a separate concern and never read from here. A
    backend that models a numeric type of its own — a monetary amount, an
    unsigned width — derives from this and inherits what it agrees with.

    Not available: ``LIKE`` / ``ILIKE``.
    """



class IntegerColumn(NumericColumn):
    """A column holding a whole number.

    A subclass rather than a sibling of :class:`NumericColumn`: arithmetic on a
    whole number is arithmetic, so there is nothing to redeclare. What differs
    is the *result* — SQL keeps ``CEIL`` of a whole number a whole number, while
    ``SQRT`` of one generally is not — and the result type is settled by the
    operation's own declaration at run time (the math factories tag their
    results through ``value_class_of``), not by a mixin arranged in the MRO.

    ``TranscendentalMixin`` is inherited and not withheld: ``log(2)`` is a legal
    query the database will answer, and an integer behaving differently from the
    float it widens to would be a difference the caller cannot see or explain.
    A monetary column is different in kind rather than in width, and is the case
    that leaves this mixin out.
    """


class DateTimeColumn(ComparisonMixin, TemporalArithmeticMixin, DateTimeMixin, ColumnBase):

    """A column holding a date/time.

    Adds the temporal surface — :meth:`~...mixins.DateTimeMixin.date_trunc`,
    :meth:`~...mixins.DateTimeMixin.extract`, :meth:`~...mixins.DateTimeMixin.date_add`
    and friends — so ``User.c.created_at.date_trunc("month")`` no longer
    requires threading the dialect into a free function by hand.

    Arithmetic is interval-based: ``created_at + one_day`` is allowed, while
    ``created_at + created_at`` is refused at construction (see
    :class:`~...mixins.TemporalArithmeticMixin`).

    Not available: ``LIKE`` / ``ILIKE``.
    """


class BooleanColumn(BooleanLogicMixin, ComparisonMixin, ColumnBase):

    """A column holding a truth value: boolean algebra, comparison, casting.

    The boolean-domain surface a ``bool`` field is guaranteed: ``is_true()`` /
    ``is_false()`` (three-valued-logic-correct, and spelled ``IS TRUE`` /
    ``IS FALSE`` rather than ``= 1`` / ``= 0`` -- PostgreSQL rejects
    ``boolean = integer`` outright), plus ``&`` / ``|`` / ``~`` for combining
    and negating them.

    :class:`BooleanLogicMixin` is the reason the class is not just
    ``ComparisonMixin``: those three operators are the same connectives
    :class:`~...mixins.LogicalMixin` gives a *predicate*, applied here to a
    value that is itself a truth value. The mixin is composed rather than
    inherited for the reason every family here is -- a string column has no
    ``AND``, and giving it one would be the guess the narrow classes exist to
    avoid.

    Aggregates (``SUM`` / ``BOOL_AND``) are deliberately **not** here. Four
    backends split on them -- PostgreSQL has no ``sum(boolean)`` while SQLite
    has no ``BOOL_AND`` -- so there is no single expression that means "any" or
    "all" everywhere; a caller that needs one states the backend-specific
    spelling explicitly.
    """


class BinaryColumn(ComparisonMixin, ColumnBase):

    """A column holding raw bytes: comparison, casting, collation."""


class UUIDColumn(ComparisonMixin, ColumnBase):

    """A column holding a UUID.

    Carries no UUID-specific operator, because portable SQL has none — a UUID
    column supports exactly what any other value column does. The class
    exists so the value family is visible (in reprs, in tests) and so a
    backend that *does* have an operation for it has an
    unambiguous home. Storage is the DDL layer's concern.
    """


class JSONColumn(ComparisonMixin, JSONAccessorMixin, ColumnBase):

    """A column holding JSON: comparison, casting, and path access.

    Adds :meth:`~...mixins.JSONAccessorMixin.json_path` (scalar, terminal)
    and :meth:`~...mixins.JSONAccessorMixin.json_value` (JSON, chainable).

    Not available: ``LIKE`` / ``ILIKE`` and arithmetic — those apply to the
    text a path access *returns*, not to the document.
    """


class ArrayColumn(ComparisonMixin, ArrayMixin, ColumnBase):

    """A column holding an array: :meth:`~...mixins.ArrayMixin.array_length`
    and :meth:`~...mixins.ArrayMixin.unnest`."""


class XMLColumn(NotComparableMixin, NotANumberMixin, ColumnBase):
    """A column holding an XML document: alias, null tests, casting — no comparison.

    The XML value surface is *not* the general value surface with a few
    operations missing; it is a different shape. Every backend that has an XML
    type refuses comparison on it:

    * PostgreSQL: ``SELECT '<a/>'::xml = '<a/>'::xml`` is
      ``ERROR: operator does not exist: xml = xml``. Ordering and ``IN`` are
      refused the same way; ``IS NULL`` / ``IS NOT NULL`` are accepted.
    * SQL Server: "the xml data type cannot be compared or sorted" — its
      documented limitation, and the reason ``xml`` columns reject ``=``,
      ``<``, ``ORDER BY`` and ``GROUP BY``.
    * Oracle: ``XMLType`` has no comparison operators either; equality is
      expressed by SQL/XML functions (``XMLExists``, ``existsNode``), not by
      ``=``.

    So this class carries what remains: aliasing, the null tests (the one test
    those backends all accept), casting, and an explicit refusal of arithmetic
    and comparison — the latter via :class:`NotComparableMixin`, because
    Python resolves ``==`` / ``<`` on the type and a class that merely omitted
    them would silently fall back to identity equality.

    **No Python annotation maps to this class yet.** A field annotated ``str``
    is a :class:`StringColumn`, even when its DDL type is ``XML``: the model
    layer classifies by the Python value and this package deliberately models
    no Python XML document type. The class exists
    for the lattice — an operation that hands back an XML value from a column
    has something to be typed as, casts to :class:`~...types.XmlType` land
    here, and a backend that models its own XML column has a correct parent
    to derive from. A future annotation is possible but is not this change:
    the options are a third-party document class, bytes-as-document, or a
    dedicated wrapper type, and choosing one is a modelling decision rather
    than a mapping entry.
    """



def value_class_of(expr: object):
    """The value class an operation handing *expr* back should be typed as.

    ``MIN`` of an integer column is an integer; ``MIN`` of a string column is a
    string, and can still be compared and matched. ``LAG`` over a name is a
    name. So when an operation answers with the thing it was given, this is
    what it asks. It is read off the column *class* because that is where the
    type already lives -- there is no tag to read and no attribute that
    duplicates the class.

    Resolution walks the MRO, so a column class that narrows an existing one
    (``IntegerColumn`` under ``NumericColumn``) is found under its own name and
    a backend's own column class resolves through whichever core class it
    derives from.

    ``None`` is a real answer rather than a failure. A ``Literal`` and an
    untyped ``Column`` say nothing about what a database would hand back, so an
    operation over them stays untyped instead of guessing: the caller who needs
    a specific type says so with ``cast()``.

    The table is built on first use and kept. This module is imported by
    :mod:`..core`, so building it at import time would need the value classes
    from the module that imports this one.
    """
    global _COLUMN_VALUE_CLASSES
    if _COLUMN_VALUE_CLASSES is None:
        _COLUMN_VALUE_CLASSES = _value_classes()

    for klass in type(expr).__mro__:
        value_class = _COLUMN_VALUE_CLASSES.get(klass)
        if value_class is not None:
            return value_class
    return None


#: Column class -> the value class an operation handing that column back is
#: typed as. Resolution walks the MRO, so a column class that narrows an
#: existing one is found under its own name: an ``IntegerColumn`` is a whole
#: number even though it is also a ``NumericColumn``.
#:
#: Every concrete column class this module declares is in here. The test that
#: says so lives beside the map and is why a class added without an entry is a
#: test failure rather than a silently untyped operation.
#:
#: ``DateTimeColumn`` is the one judgement call: a column declared ``DATETIME``
#: holds a date and a time together, which is what ``TimestampValueExpression``
#: is. A ``DATE`` or ``TIME`` column is a different storage type in DDL and this
#: module has no column class for either -- the distinction between the four
#: temporal types is made where the value is known (see
#: :class:`~...expression.datetime.ExtractExpression`), not by guessing here.
def _value_classes():
    from . import core

    return {
        IntegerColumn: core.IntegerValueExpression,
        NumericColumn: core.NumericValueExpression,
        StringColumn: core.StringValueExpression,
        JSONColumn: core.JSONValueExpression,
        ArrayColumn: core.ArrayValueExpression,
        BooleanColumn: core.BooleanValueExpression,
        BinaryColumn: core.BinaryValueExpression,
        UUIDColumn: core.UUIDValueExpression,
        DateTimeColumn: core.TimestampValueExpression,
        # XML is a value like the rest: the operations that hand one back (a
        # column, xmlagg, a cast to XmlType) are typed, they just offer the
        # surface an XML value has -- see XMLColumn.
        XMLColumn: core.XMLValueExpression,
    }


_COLUMN_VALUE_CLASSES = None


__all__ = [
    "ColumnBase",
    "StringColumn",
    "NumericColumn",
    "IntegerColumn",
    "DateTimeColumn",
    "BooleanColumn",
    "BinaryColumn",
    "UUIDColumn",
    "JSONColumn",
    "ArrayColumn",
    "XMLColumn",
    "value_class_of",
]
