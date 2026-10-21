# src/rhosocial/activerecord/backend/expression/mixins.py
"""
Mixin classes that provide operator-overloading capabilities to expression classes.

This module implements Python's magic methods (dunder methods) to allow intuitive
SQL expression building using familiar operators like ==, !=, +, -, &, |, etc.

Key Architecture Concepts:
- Each mixin provides specific types of operations (comparisons, arithmetic, logical)
- When operators are used (e.g., col1 == col2), the left operand's dialect is used
- This ensures that the resulting expression uses the correct dialect for SQL generation
- Deferred local imports prevent circular dependency issues

Example Usage:
    # Comparison operations
    col1 == col2  # Creates ComparisonPredicate with col1's dialect
    col1 > 5      # Creates ComparisonPredicate with col1's dialect

    # Arithmetic operations
    col1 + col2   # Creates ArithmeticOperation with col1's dialect

    # Logical operations
    (col1 == 1) & (col2 == 2)  # Creates LogicalPredicate with left predicate's dialect

The dialect parameter is always inherited from the left-hand side operand,
ensuring consistent SQL generation across the expression tree.
"""

import copy
import datetime
import decimal
from typing import (
    Any,
    List,
    Optional,
    TYPE_CHECKING,
    TypeVar,
    Union,
)
if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .bases import BaseExpression, SQLValue, SQLPredicate
    # Annotations only. The classes themselves are imported inside the methods
    # that need them, because core imports this module.
    from .core import CastExpression, FunctionCall, Literal
    from .datetime import (
        DatePartExpression,
        DateTimeAddExpression,
        DateTimeDiffExpression,
        DateTimeSubtractExpression,
        DateTruncExpression,
        ExtractExpression,
    )
    from .advanced_functions import JSONDocumentValue, JSONTextValue
    from .declared import (
        ArrayAnnotation,
        BinaryAnnotation,
        BooleanAnnotation,
        IntegerAnnotation,
        JSONAnnotation,
        NumberAnnotation,
        TemporalAnnotation,
        TextAnnotation,
        UUIDAnnotation,
        XMLAnnotation,
    )

T = TypeVar("T")
_ResultT = TypeVar("_ResultT")


class AliasableMixin:
    """Mixin class that provides aliasing capability to expressions.

    This mixin allows expressions to be given aliases for use in SQL queries,
    particularly useful in SELECT clauses and subqueries.

    ``alias`` is declared here rather than created by :meth:`as_`: the field
    is part of the contract of every aliased expression, so formatters read it
    directly instead of probing for an attribute that only exists on the
    aliased copies.

    Example:
        >>> Column(dialect, "name").as_("user_name")
        >>> # Results in: "name AS user_name" in SQL
    """

    #: The alias this expression renders as, or ``None`` when unaliased.
    alias: Optional[str] = None

    def as_(self: T, alias: str) -> T:
        """
        Set an alias for this expression.

        This method enables the AS clause in SQL generation, allowing expressions
        to be referenced by a different name in the query context.

        Args:
            alias: The alias name to assign to this expression

        Returns:
            A copy of this expression with the alias applied

        Example:
            >>> col = Column(dialect, "first_name").as_("fname")
            >>> # When used in a query, this will generate: "first_name" AS "fname"
        """
        new = copy.copy(self)
        new.alias = alias
        return new


class NullTestMixin:
    """``IS NULL`` / ``IS NOT NULL``: the test that works when comparison does not.

    A null test asks whether a value is present, not what it equals, so it is
    available wherever a value is — including where comparison is refused.
    PostgreSQL refuses ``xml = xml`` outright ("operator does not exist: xml =
    xml"), SQL Server documents that "the xml data type cannot be compared or
    sorted", and Oracle's ``XMLType`` has no comparison operators either; every
    one of the three accepts ``IS NULL``. Splitting this out of
    :class:`ComparisonMixin` is what lets an XML value keep the test while
    refusing the comparisons.

    This is the part of the comparison surface that every value type shares, so
    :class:`~...expression.column_types.ColumnBase` carries it directly and the
    comparable families take :class:`ComparisonMixin` (which inherits it) as
    well.

    Example:
        >>> col = Column(dialect, "email")
        >>> predicate = col.is_null()  # Generates: "email IS NULL"
    """

    def is_null(self: "SQLValue") -> "SQLPredicate":
        """
        Generate an IS NULL predicate for this expression.

        Returns:
            SQLPredicate representing the IS NULL check

        Example:
            >>> col = Column(dialect, "email")
            >>> predicate = col.is_null()  # Generates: "email IS NULL"
        """
        from .predicates import IsNullPredicate

        return IsNullPredicate(self._dialect, self)

    def is_not_null(self: "SQLValue") -> "SQLPredicate":
        """
        Generate an IS NOT NULL predicate for this expression.

        Returns:
            SQLPredicate representing the IS NOT NULL check

        Example:
            >>> col = Column(dialect, "email")
            >>> predicate = col.is_not_null()  # Generates: "email IS NOT NULL"
        """
        from .predicates import IsNullPredicate

        return IsNullPredicate(self._dialect, self, is_not=True)


class ComparisonMixin(NullTestMixin):
    """
    Provides comparison operators (==, !=, >, <, etc.) and other boolean-producing methods.

    This mixin enables Python's comparison operators to generate SQL comparison predicates.
    When using these operators, the left operand's dialect is used for the resulting
    expression, ensuring consistent SQL generation across the expression tree.

    The mixin handles both expression-to-expression comparisons and expression-to-value
    comparisons by automatically wrapping non-expression values in Literal objects.

    The null tests (``is_null`` / ``is_not_null``) come from
    :class:`NullTestMixin`, which every value class carries. This mixin adds the
    ordering and equality comparisons on top; a value that cannot be compared —
    an XML document — keeps :class:`NullTestMixin` without this one.

    Example:
        >>> # Expression-to-expression comparison
        >>> col1 = Column(dialect, "age")
        >>> col2 = Column(dialect, "min_age")
        >>> predicate = col1 >= col2  # Uses col1's dialect
        >>>
        >>> # Expression-to-value comparison
        >>> predicate = col1 >= 18  # Automatically wraps 18 in Literal
        >>>
        >>> # Method-based comparisons
        >>> col1.is_null()  # Generates "age IS NULL"
        >>> col1.in_([1, 2, 3])  # Generates "age IN (?, ?, ?)"
        >>> col1.is_distinct_from(0)  # NULL-safe: "age IS DISTINCT FROM ?"
    """

    def is_distinct_from(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLPredicate":
        """NULL-safe inequality: true when the two differ, NULL included.

        ``a != b`` answers NULL when either side is NULL, so a query filtering
        for "not equal" silently drops every NULL row -- the row the caller was
        most likely looking for. ``IS DISTINCT FROM`` is the NULL-safe spelling
        and is what :meth:`is_not_distinct_from` negates.

        The renderer is a dialect hook, because the spelling is not universal:
        PostgreSQL, Firebird, Snowflake, BigQuery, SQL Server (2022+) and
        SQLite (3.39+) have it, while Oracle answers ``NOT LNNVL(a = b)``,
        ``IS NOT DISTINCT FROM`` is ``ORA-00908`` there, and an older SQL Server
        or SQLite has neither. The gate lives with the dialect that has the
        limit and **refuses** rather than substituting a different question.

        Args:
            other: Right operand, wrapped as a literal when not an expression.

        Returns:
            A predicate rendering ``<left> IS DISTINCT FROM <right>``.

        Example:
            >>> Column(dialect, "name").is_distinct_from("root").to_sql()
            ('"name" IS DISTINCT FROM ?', ('root',))
        """
        from .core import Literal
        from .predicates import DistinctFromPredicate
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return DistinctFromPredicate(self._dialect, self, other_expr, is_not=False)

    def is_not_distinct_from(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLPredicate":
        """NULL-safe equality: true when the two match, two NULLs included.

        The counterpart of :meth:`is_distinct_from` -- ``IS NOT DISTINCT FROM``
        is true for two NULLs, where ``=`` is not.

        Args:
            other: Right operand, wrapped as a literal when not an expression.

        Returns:
            A predicate rendering ``<left> IS NOT DISTINCT FROM <right>``.

        Example:
            >>> Column(dialect, "name").is_not_distinct_from("root").to_sql()
            ('"name" IS NOT DISTINCT FROM ?', ('root',))
        """
        from .core import Literal
        from .predicates import DistinctFromPredicate
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return DistinctFromPredicate(self._dialect, self, other_expr, is_not=True)

    def __eq__(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLPredicate":
        """
        Implement the equality operator (==) to generate SQL equality predicate.

        This method enables expressions like: `Column(...) == value` or `Column(...) == Column(...)`
        The resulting ComparisonPredicate uses the left operand's dialect for SQL generation.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLPredicate representing the equality comparison

        Example:
            >>> col = Column(dialect, "status")
            >>> predicate = col == "active"  # Generates: "status = ?" with params ("active",)
        """
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, "=", self, other_expr)

    def __ne__(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLPredicate":
        """
        Implement the inequality operator (!=) to generate SQL inequality predicate.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLPredicate representing the inequality comparison
        """
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, "!=", self, other_expr)

    def __gt__(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLPredicate":
        """
        Implement the greater-than operator (>) to generate SQL comparison predicate.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLPredicate representing the greater-than comparison
        """
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, ">", self, other_expr)

    def __ge__(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLPredicate":
        """
        Implement the greater-or-equal operator (>=) to generate SQL comparison predicate.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLPredicate representing the greater-or-equal comparison
        """
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, ">=", self, other_expr)

    def __lt__(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLPredicate":
        """
        Implement the less-than operator (<) to generate SQL comparison predicate.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLPredicate representing the less-than comparison
        """
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, "<", self, other_expr)

    def __le__(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLPredicate":
        """
        Implement the less-or-equal operator (<=) to generate SQL comparison predicate.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLPredicate representing the less-or-equal comparison
        """
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, "<=", self, other_expr)

    def is_true(self: "SQLValue") -> "SQLPredicate":
        """
        Generate an IS TRUE predicate for this expression.

        IS TRUE matches only TRUE values, not FALSE or NULL.
        This is different from = TRUE which would not match NULL values
        but also wouldn't correctly handle three-valued logic.

        Returns:
            SQLPredicate representing the IS TRUE check

        Example:
            >>> col = Column(dialect, "is_active")
            >>> predicate = col.is_true()  # Generates: "is_active IS TRUE"
        """
        from .predicates import IsBooleanPredicate

        return IsBooleanPredicate(self._dialect, self, value=True, is_not=False)

    def is_not_true(self: "SQLValue") -> "SQLPredicate":
        """
        Generate an IS NOT TRUE predicate for this expression.

        IS NOT TRUE matches FALSE values and NULL values.
        This is useful for finding records where a boolean field is
        either explicitly false or unset (NULL).

        Returns:
            SQLPredicate representing the IS NOT TRUE check

        Example:
            >>> col = Column(dialect, "is_active")
            >>> predicate = col.is_not_true()  # Generates: "is_active IS NOT TRUE"
        """
        from .predicates import IsBooleanPredicate

        return IsBooleanPredicate(self._dialect, self, value=True, is_not=True)

    def is_false(self: "SQLValue") -> "SQLPredicate":
        """
        Generate an IS FALSE predicate for this expression.

        IS FALSE matches only FALSE values, not TRUE or NULL.
        This is different from = FALSE which would not match NULL values
        but also wouldn't correctly handle three-valued logic.

        Returns:
            SQLPredicate representing the IS FALSE check

        Example:
            >>> col = Column(dialect, "is_deleted")
            >>> predicate = col.is_false()  # Generates: "is_deleted IS FALSE"
        """
        from .predicates import IsBooleanPredicate

        return IsBooleanPredicate(self._dialect, self, value=False, is_not=False)

    def is_not_false(self: "SQLValue") -> "SQLPredicate":
        """
        Generate an IS NOT FALSE predicate for this expression.

        IS NOT FALSE matches TRUE values and NULL values.
        This is useful for finding records where a boolean field is
        either explicitly true or unset (NULL).

        Returns:
            SQLPredicate representing the IS NOT FALSE check

        Example:
            >>> col = Column(dialect, "is_deleted")
            >>> predicate = col.is_not_false()  # Generates: "is_deleted IS NOT FALSE"
        """
        from .predicates import IsBooleanPredicate

        return IsBooleanPredicate(self._dialect, self, value=False, is_not=True)

    def in_(self: "SQLValue", values: List[Any]) -> "SQLPredicate":
        """
        Generate an IN predicate for this expression with a list of values.

        Args:
            values: List of values to check for inclusion

        Returns:
            SQLPredicate representing the IN check

        Example:
            >>> col = Column(dialect, "status")
            >>> predicate = col.in_(["active", "pending"])  # Generates: "status IN (?, ?)"
        """
        from .bases import BaseExpression
        from .core import Literal
        from .predicates import InPredicate

        # An ActiveQuery renders as an IN subquery. The capability is asked of
        # the declared protocol rather than looked for by name: `values` is
        # either an ActiveQuery, which has the method, or a plain sequence of
        # values, which cannot have it.
        to_query_expression = getattr(values, "to_query_expression", None)
        if callable(to_query_expression):
            # An ActiveQuery-like object: render as an IN subquery. The
            # Subquery is bound to the same dialect as the two branches below
            # it: rendering reaches it through format_in_predicate, which calls
            # to_sql() on anything that is not a Literal, and to_sql() resolves
            # the formatter on the node's own dialect.
            from .core import Subquery

            return InPredicate(
                self._dialect, self, Subquery(self._dialect, to_query_expression())
            )
        if isinstance(values, BaseExpression):
            # Already an expression (e.g. Subquery): pass through.
            return InPredicate(self._dialect, self, values)

        return InPredicate(self._dialect, self, Literal(self._dialect, tuple(values)))

    def not_in(self: "SQLValue", values: List[Any]) -> "SQLPredicate":
        """
        Generate a NOT IN predicate for this expression with a list of values.

        Args:
            values: List of values to check for exclusion

        Returns:
            SQLPredicate representing the NOT IN check
        """
        from .core import Literal
        from .predicates import InPredicate, LogicalPredicate

        return LogicalPredicate(
            self._dialect, "NOT", InPredicate(self._dialect, self, Literal(self._dialect, tuple(values)))
        )

    def between(self: "SQLValue", low: Any, high: Any) -> "SQLPredicate":
        """
        Generate a BETWEEN predicate for this expression with low and high bounds.

        Args:
            low: Lower bound of the range (inclusive)
            high: Upper bound of the range (inclusive)

        Returns:
            SQLPredicate representing the BETWEEN check

        Example:
            >>> col = Column(dialect, "age")
            >>> predicate = col.between(18, 65)  # Generates: "age BETWEEN ? AND ?"
        """
        from .core import Literal
        from .predicates import BetweenPredicate

        return BetweenPredicate(self._dialect, self, Literal(self._dialect, low), Literal(self._dialect, high))


class ArithmeticMixin:
    """
    Provides arithmetic operators (+, -, *, /, %) for SQL value expressions.

    This mixin enables Python's arithmetic operators to generate SQL arithmetic expressions.
    When using these operators, the left operand's dialect is used for the resulting
    expression, ensuring consistent SQL generation across the expression tree.

    The mixin handles both expression-to-expression operations and expression-to-value
    operations by automatically wrapping non-expression values in Literal objects.

    Example:
        >>> # Expression-to-expression arithmetic
        >>> col1 = Column(dialect, "price")
        >>> col2 = Column(dialect, "discount")
        >>> arithmetic_expr = col1 + col2  # Uses col1's dialect
        >>>
        >>> # Expression-to-value arithmetic
        >>> arithmetic_expr = col1 * 0.9  # Automatically wraps 0.9 in Literal
        >>>
        >>> # Chained operations
        >>> complex_expr = (col1 + col2) * 1.1  # Generates: "(price + discount) * ?"
    """

    def __add__(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLValue":
        """
        Implement the addition operator (+) to generate SQL arithmetic expression.

        This method enables expressions like: `Column(...) + value` or `Column(...) + Column(...)`
        The resulting ArithmeticOperation uses the left operand's dialect for SQL generation.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLValue representing the addition operation

        Example:
            >>> col = Column(dialect, "price")
            >>> expr = col + 10  # Generates: "price + ?" with params (10,)
        """
        from .core import Literal
        from .operators import ArithmeticOperation
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ArithmeticOperation(self._dialect, "add", self, other_expr)

    def __sub__(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLValue":
        """
        Implement the subtraction operator (-) to generate SQL arithmetic expression.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLValue representing the subtraction operation
        """
        from .core import Literal
        from .operators import ArithmeticOperation
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ArithmeticOperation(self._dialect, "sub", self, other_expr)

    def __mul__(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLValue":
        """
        Implement the multiplication operator (*) to generate SQL arithmetic expression.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLValue representing the multiplication operation
        """
        from .core import Literal
        from .operators import ArithmeticOperation
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ArithmeticOperation(self._dialect, "mul", self, other_expr)

    def __truediv__(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLValue":
        """Division, rendered as the portable ``/`` — and what ``/`` means is
        **the backend's**, not this operator's.

        Measured on four backends, ``SELECT 7 / 2``:

        * MySQL, MariaDB — ``Decimal('3.5000')``. True division, with scale 4,
          on *integer* operands: ``7 / 2`` is not an integer expression at all;
        * PostgreSQL, Firebird — ``3``. Integer division, truncating toward
          zero, because both operands are integers and that is what ``/`` means
          for them;
        * SQLite — ``3`` for the same reason (``suggested-mappings.md`` §8.3
          records it as one of the silent-wrong entries: the *literal* ``3``
          and the truncating ``7 / 2`` are indistinguishable in the result).

        So the same model code, unchanged, yields ``3.5`` on MySQL and ``3`` on
        PostgreSQL. Nothing here detects that, and that is deliberate: the
        alternative — a framework that rewrites ``/`` per dialect — would be
        choosing a semantics, and which semantics is the caller's question. A
        caller who wants one can make it one by making an operand a decimal
        (``7.0 / 2`` is true division on every backend measured, PostgreSQL
        included) or by casting explicitly.

        What is *not* deliberate is a caller discovering this from a wrong
        number. The plan's open question (``suggested-mappings.md`` §8.6 item 1)
        is whether ``/`` on a numeric column should stay portable or move behind
        a capability gate; until that is decided, this operator renders the
        portable spelling and the difference stays a documented property of the
        backends rather than a silent property of the model.
        """
        from .core import Literal
        from .operators import ArithmeticOperation
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ArithmeticOperation(self._dialect, "div", self, other_expr)

    def __mod__(self: "SQLValue", other: Union["SQLValue", Any]) -> "SQLValue":
        """
        Implement the modulo operator (%) to generate SQL arithmetic expression.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLValue representing the modulo operation
        """
        from .core import Literal
        from .operators import ArithmeticOperation
        from .bases import BaseExpression

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ArithmeticOperation(self._dialect, "mod", self, other_expr)


class NotANumberMixin:
    """The statement that a value is not a number, in the only form Python allows.

    Every refusal about a *missing operation* elsewhere in this package is an
    :class:`AttributeError`, because that is what a missing attribute raises and
    therefore what a caller already knows how to catch. Arithmetic is the one
    operation Python looks up on the *type* for the interpreter, never through
    the instance, so a class without ``__add__`` does not reach ``__getattr__``
    and does not get to speak: CPython raises
    ``TypeError: unsupported operand type(s) for +`` itself.

    That message names neither the operation nor the reason, and it arrives from
    machinery the caller cannot inspect -- which is the wrong failure for a
    branch whose whole claim is that a mistake is caught *at the call*, by the
    type, saying what is missing. ``min(str_col) + 1`` is not SQL; it is a
    mistake about what a string is, and the answer should say so the same way
    ``min(str_col).like("a%")`` does.

    So the refusal is declared rather than left to happen. These methods exist
    only to raise, and that is the point: mixing this in says "this value is not
    a number", and the arithmetic operators are where that claim has to be
    checkable. The alternative -- inheriting nothing and accepting the
    interpreter's ``TypeError`` -- is the same decision with the message thrown
    away.

    Why ``AttributeError`` and not ``TypeError``: the object genuinely has no
    such operation, which is exactly what ``AttributeError`` means, and a caller
    handling "this value does not offer that" handles one exception type
    everywhere in the package rather than learning a second vocabulary for the
    operator forms alone.

    Example:
        >>> min_(dialect, name) + 1        # AttributeError, naming '+'
        >>> min_(dialect, name).like("a%") # works: it is a string
    """

    def _not_a_number(self, symbol: str, dunder: str) -> "AttributeError":
        """Build the refusal for *symbol*, to be raised by the operator named."""
        return AttributeError(
            f"{type(self).__name__} has no attribute {dunder!r}: it does not "
            f"support {symbol!r}. It is a {type(self).__name__}, not a number, "
            f"and a typed value offers the operations its type supports."
        )

    def __add__(self, other):
        raise self._not_a_number("+", "__add__")

    def __radd__(self, other):
        raise self._not_a_number("+", "__radd__")

    def __sub__(self, other):
        raise self._not_a_number("-", "__sub__")

    def __rsub__(self, other):
        raise self._not_a_number("-", "__rsub__")

    def __mul__(self, other):
        raise self._not_a_number("*", "__mul__")

    def __rmul__(self, other):
        raise self._not_a_number("*", "__rmul__")

    def __truediv__(self, other):
        raise self._not_a_number("/", "__truediv__")

    def __rtruediv__(self, other):
        raise self._not_a_number("/", "__rtruediv__")

    def __mod__(self, other):
        raise self._not_a_number("%", "__mod__")

    def __rmod__(self, other):
        raise self._not_a_number("%", "__rmod__")


class TemporalArithmeticMixin(NotANumberMixin):
    """Arithmetic for date, time, timestamp and interval values, gated by operand.

    What temporal arithmetic defines, and the only things this mixin performs:

    * a temporal value ± an interval is that kind of temporal value
      (``created_at + one_day``, ``now() - one_hour``);
    * a temporal value − a temporal value is a **duration**, and the framework
      does not pretend its type is one thing: measured 2026-10-09, PostgreSQL
      answers a whole number of days, Firebird a decimal number of days,
      ClickHouse a number of seconds, Snowflake and BigQuery an interval,
      Oracle a ``timedelta``-shaped value and MySQL/MariaDB a silent numeric
      difference. The node keeps the temporal family here and lets each
      dialect declare what its subtraction yields; only ``timestamp −
      timestamp`` is an interval nearly everywhere (``finished - started``);
    * an interval ± an interval is an interval;
    * an interval × a number is an interval.

    Everything else is refused at construction, in the package's refusal
    vocabulary (``AttributeError``; see :class:`NotANumberMixin`). The
    combination this class exists for is ``created_at + created_at``: two
    points in time have no sum, and without the gate it rendered
    ``"created_at" + "created_at"`` -- SQL only the database rejected. The
    failure belongs at the call, where the mistake was made.

    :class:`NotANumberMixin` is inherited for the refusals Python cannot
    express by omission -- the reflected operators, ``/`` and ``%`` -- so the
    vocabulary stays one exception type; this class adds the operations that
    do exist, each checking its operands first.
    """

    def __add__(self, other):
        return self._temporal_binary("+", other, subtracting=False)

    def __sub__(self, other):
        return self._temporal_binary("-", other, subtracting=True)

    def __mul__(self, other):
        if not self._is_interval_value() or not self._is_number_operand(other):
            raise self._temporal_refusal(
                "*", other, "only an interval scales, and only by a number"
            )
        return self._build("*", other)

    # -- classification ------------------------------------------------------

    def _is_interval_value(self) -> bool:
        return isinstance(self, IntervalMixin)

    def _is_interval_operand(self, other) -> bool:
        from .bases import BaseExpression

        if isinstance(other, IntervalMixin):
            return True
        if isinstance(other, BaseExpression):
            return False
        return isinstance(other, datetime.timedelta)

    def _is_temporal_operand(self, other) -> bool:
        from .bases import BaseExpression

        if isinstance(other, BaseExpression):
            # Both a temporal *column* and a temporal *node* carry
            # DateTimeMixin; an interval does too, and is excluded first.
            return isinstance(other, DateTimeMixin) and not isinstance(
                other, IntervalMixin
            )
        return isinstance(other, (datetime.date, datetime.time, datetime.datetime))

    def _is_number_operand(self, other) -> bool:
        from .bases import BaseExpression

        if isinstance(other, bool):
            return False
        if isinstance(other, (int, float, decimal.Decimal)):
            return True
        if isinstance(other, BaseExpression):
            return not self._is_temporal_operand(other) and not self._is_interval_operand(other)
        return False

    # -- building and refusing -----------------------------------------------

    def _temporal_binary(self, symbol: str, other, subtracting: bool):
        if self._is_interval_value():
            if self._is_interval_operand(other):
                return self._build(symbol, other)
            if subtracting and self._is_temporal_operand(other):
                reason = (
                    "an interval cannot have a point in time subtracted from "
                    "it; subtract the interval from the temporal value instead"
                )
            else:
                reason = "an interval combines with another interval, or scales by a number"
            raise self._temporal_refusal(symbol, other, reason)

        if self._is_interval_operand(other):
            return self._build(symbol, other)

        if self._is_temporal_operand(other):
            if subtracting:
                return self._build(symbol, other)
            raise self._temporal_refusal(
                symbol,
                other,
                "two points in time have no sum; subtract one from the other "
                "for an interval, or move it with an interval",
            )

        raise self._temporal_refusal(
            symbol, other, "a temporal value combines with an interval, not with a number"
        )

    #: The Python operator symbols the temporal dunders hand down, mapped to
    #: the operation words the node's contract uses. The symbols stay in the
    #: refusal messages (they name the Python operator the caller wrote); the
    #: node gets the word.
    #:
    #: The words are :class:`~...expression.operators.ArithmeticOperator`
    #: values, written as strings because this table is a class attribute and
    #: ``operators`` imports the mixins this one is mixed into -- importing the
    #: enum back at module level would be circular. :class:`ArithmeticOperation`
    #: normalises the string to the member at construction, so the wire value is
    #: unchanged.
    _OPERATOR_WORDS = {"+": "add", "-": "sub", "*": "mul"}

    def _build(self, symbol: str, other):
        from .bases import BaseExpression
        from .core import Literal
        from .operators import ArithmeticOperation

        other_expr = other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
        return ArithmeticOperation(self._dialect, self._OPERATOR_WORDS[symbol], self, other_expr)

    def _temporal_refusal(self, symbol: str, other, reason: str) -> AttributeError:
        return AttributeError(
            f"{type(self).__name__} has no attribute {symbol!r} for "
            f"{type(other).__name__}: {reason}. Temporal arithmetic is "
            f"interval-based, so the combination is not declared."
        )


class NotComparableMixin:
    """The statement that a value cannot be compared, in the only form Python allows.

    The same problem :class:`NotANumberMixin` solves, for the comparison
    operators. Python looks ``__eq__``, ``__lt__`` and the rest up on the
    *type*, never through ``__getattr__``, so a class that simply does not
    declare them is not silent — it silently gets ``object``'s identity
    semantics, and ``xml_col == other`` answers ``False`` instead of refusing.
    A call that should have been caught at the call site would instead travel
    as an always-false predicate (or, for ``<``, raise the interpreter's bare
    ``TypeError`` whose message names neither the operation nor the reason).

    So the refusal is declared. These methods exist only to raise, and that is
    the point: mixing this in says "this value cannot be compared", which is
    true of every backend that has an XML type. PostgreSQL refuses ``xml =
    xml`` with "operator does not exist", SQL Server documents that "the xml
    data type cannot be compared or sorted", and Oracle's ``XMLType`` has no
    comparison operators. What those backends *do* accept — ``IS NULL`` — comes
    from :class:`NullTestMixin` and is kept separately.

    Why ``AttributeError``: the object genuinely has no such operation, which
    is exactly what ``AttributeError`` means, and a caller handling "this value
    does not offer that" handles one exception type everywhere in the package
    rather than learning a second vocabulary for the operator forms alone.

    ``__hash__`` is re-stated because defining ``__eq__`` sets it to ``None``
    in Python; an XML expression still goes in sets and dictionaries (it is a
    value object like any other), it just cannot be ordered or compared.

    Example:
        >>> xml_col == other          # AttributeError, naming '__eq__'
        >>> xml_col.is_null()         # works: a null test is not a comparison
    """

    def _not_comparable(self, symbol: str, dunder: str) -> "AttributeError":
        """Build the refusal for *symbol*, to be raised by the operator named."""
        return AttributeError(
            f"{type(self).__name__} has no attribute {dunder!r}: it does not "
            f"support {symbol!r}. An XML value cannot be compared on any "
            f"backend that has an XML type, and a typed value offers the "
            f"operations its type supports."
        )

    def __eq__(self, other):
        raise self._not_comparable("==", "__eq__")

    def __ne__(self, other):
        raise self._not_comparable("!=", "__ne__")

    def __lt__(self, other):
        raise self._not_comparable("<", "__lt__")

    def __le__(self, other):
        raise self._not_comparable("<=", "__le__")

    def __gt__(self, other):
        raise self._not_comparable(">", "__gt__")

    def __ge__(self, other):
        raise self._not_comparable(">=", "__ge__")

    __hash__ = object.__hash__


class _LogicalOperators:
    """The three connectives (``&``, ``|``, ``~``), shared by both receivers.

    The receiver decides the result class, and that is the whole difference: a
    predicate stays a predicate -- combining predicates is how ``WHERE``
    clauses are built -- while a truth *value* keeps its value type
    (:class:`~...core.LogicalValue`), so the result can be aliased
    into a ``SELECT`` list, compared, cast, and combined further. Both render
    through the same dialect entry point (``format_logical_predicate``).

    Deliberately private: the two public mixins below are the vocabulary
    (predicate receivers / value receivers), and neither is a kind of the
    other -- a truth value is not a predicate.
    """

    def __and__(self, other):
        return self._logical_operation("AND", other)

    def __or__(self, other):
        return self._logical_operation("OR", other)

    def __invert__(self):
        return self._logical_operation("NOT")

    def _logical_operation(self, op: str, *others):
        from .bases import BaseExpression, SQLPredicate
        from .core import Literal
        from .predicates import LogicalPredicate

        operands = [
            other
            if isinstance(other, BaseExpression)
            else Literal(self._dialect, other)
            for other in others
        ]
        if isinstance(self, SQLPredicate):
            return LogicalPredicate(self._dialect, op, self, *operands)

        from .core import LogicalValue

        return LogicalValue(self._dialect, op, self, *operands)


class LogicalMixin(_LogicalOperators):
    """
    Provides logical operators (&, |, ~) for SQL predicates.

    The result stays a predicate: this is the receiver for ``WHERE``-building
    combinations. A truth *value* carries :class:`BooleanLogicMixin` instead,
    and the two share one implementation (:class:`_LogicalOperators`).

    This mixin enables Python's logical operators to generate SQL logical expressions.
    When using these operators, the left operand's dialect is used for the resulting
    expression, ensuring consistent SQL generation across the expression tree.

    The mixin handles combinations of predicates using AND, OR, and NOT operations.

    Example:
        >>> # Predicate combination using AND
        >>> p1 = Column(dialect, "status") == "active"
        >>> p2 = Column(dialect, "age") >= 18
        >>> combined = p1 & p2  # Uses p1's dialect, generates: "(status = ?) AND (age >= ?)"
        >>>
        >>> # Predicate combination using OR
        >>> combined = p1 | p2  # Uses p1's dialect, generates: "(status = ?) OR (age >= ?)"
        >>>
        >>> # Predicate negation using NOT
        >>> negated = ~p1  # Uses p1's dialect, generates: "NOT (status = ?)"
    """

class BooleanLogicMixin(_LogicalOperators):
    """Boolean algebra over a value that is itself a truth value: ``&``/``|``/``~``.

    :class:`LogicalMixin` gives the same three operators to a **predicate**,
    because ``p1 & p2`` is how two predicates are combined. A boolean column
    needs the same three because ``IS TRUE`` / ``IS FALSE`` is a predicate in
    SQL but the column is what the caller has in hand::

        Model.c.flag.is_true() & Model.c.other.is_true()   # renders AND
        ~Model.c.flag.is_true()                            # renders NOT

    Neither mixin extends the other: a value expression is not a predicate,
    and giving every value expression boolean operators would hand ``str`` an
    ``AND`` it has no meaning for. Both share the private
    :class:`_LogicalOperators` implementation and differ only in the result
    class -- this one keeps the value type
    (:class:`~...core.LogicalValue`), so ``(a & b)`` can be aliased
    into a ``SELECT`` list, while :class:`LogicalMixin` keeps the predicate.

    ``is_true`` / ``is_false`` are **not** redeclared here. They already come
    from :class:`ComparisonMixin`, which every comparable family carries, and
    they render through the same ``IsBooleanPredicate`` a comparison uses --
    ``IS TRUE`` / ``IS FALSE``, three-valued-logic-correct, and with the boolean
    literal spelled as the keyword rather than ``1``/``0``. Declaring them again
    would be a second source of truth for a rendering that already exists, and
    the keyword discipline that keeps ``flag = 1`` from exploding on PostgreSQL
    would then be maintained in two places.

    Example:
        >>> # AND / OR / NOT over boolean columns
        >>> (col.is_true() & other.is_true()).to_sql()   # '"flag" IS TRUE AND ...'
    """

class ResultTypeMixin:
    """Stating a result type that the source cannot settle.

    Most operations know what they yield and say so by returning the matching
    expression class: ``sqrt`` of a numeric is a numeric, and it returns one.
    A few cannot, and the standard gives the example itself -- ``NULLIF(x, y)``
    yields ``x`` when the two differ and NULL when they do not, so whether the
    result is a string or an integer depends on the data.

    For those, the caller states it. Each method here is one statement, and
    each has a return type a checker can read, so the next call in the chain is
    checked too::

        NULLIF(name, blank).as_text().upper()   # fine
        NULLIF(name, blank).as_text().sqrt()    # error: text has no sqrt

    The alternative -- a ``result_type=`` keyword -- reads as if it did the same
    thing and does not. It is a claim rather than a type: the declared return
    stays ``FunctionCall``, the checker learns nothing, and the wrong
    continuation is still unchecked when the server rejects it minutes later.

    A method rather than a free function for three reasons. The dialect is
    already on the node, so there is nothing to pass. Chaining reads as one
    expression instead of an argument in the middle of one. And ``dir()`` finds
    it, so the way to say it is discoverable rather than something to be told.

    This is mixed into the nodes whose result type genuinely is not in the
    source. Anything that knows its own result type returns the class for it and
    never reaches this mixin.
    """

    if TYPE_CHECKING:
        from ..dialect import SQLDialectBase
        from .core import FunctionCall

        #: Declared here because a mixin is not a BaseExpression, so the
        #: attribute arrives with the class it is mixed into. ``dialect``
        #: rather than ``_dialect``: reading it validates that one is bound.
        dialect: "SQLDialectBase"

    def _annotate(self, cls) -> _ResultT:
        """This expression, declared to yield *cls*.

        Only the declared type changes. The node underneath -- and therefore the
        SQL -- is left exactly as it was, because the statement was already
        correct and what was missing was the knowledge of what it yields.

        Generic in the class so the declared return type of each ``as_*`` method
        is the class it names: returning a base type would leave a checker
        unable to tell that ``as_text()`` is text, which is the whole point of
        the method.

        Args:
            cls: One of the annotation classes in
                :mod:`~...expression.declared`, each of which carries exactly one
                surface.

        Returns:
            An expression of *cls*.
        """
        return cls(self.dialect, self)

    def as_text(self) -> "TextAnnotation":
        """This yields text, whatever the data turns out to be."""
        from .declared import TextAnnotation

        return self._annotate(TextAnnotation)

    def as_number(self) -> "NumberAnnotation":
        """This yields a fractional number."""
        from .declared import NumberAnnotation

        return self._annotate(NumberAnnotation)

    def as_integer(self) -> "IntegerAnnotation":
        """This yields a whole number."""
        from .declared import IntegerAnnotation

        return self._annotate(IntegerAnnotation)

    def as_datetime(self) -> "TemporalAnnotation":
        """This yields a date, a time or a date-time."""
        from .declared import TemporalAnnotation

        return self._annotate(TemporalAnnotation)

    def as_boolean(self) -> "BooleanAnnotation":
        """This yields a truth value."""
        from .declared import BooleanAnnotation

        return self._annotate(BooleanAnnotation)

    def as_array(self) -> "ArrayAnnotation":
        """This yields a sequence."""
        from .declared import ArrayAnnotation

        return self._annotate(ArrayAnnotation)

    def as_json(self) -> "JSONAnnotation":
        """This yields a JSON document."""
        from .declared import JSONAnnotation

        return self._annotate(JSONAnnotation)

    def as_uuid(self) -> "UUIDAnnotation":
        """This yields a UUID."""
        from .declared import UUIDAnnotation

        return self._annotate(UUIDAnnotation)

    def as_binary(self) -> "BinaryAnnotation":
        """This yields bytes."""
        from .declared import BinaryAnnotation

        return self._annotate(BinaryAnnotation)

    def as_xml(self) -> "XMLAnnotation":
        """This yields an XML document."""
        from .declared import XMLAnnotation

        return self._annotate(XMLAnnotation)


class NumericValueMixin:
    """Operations on a **fractional**-valued expression.
    Distinct from the integer value family (:class:`IntegerValue`)
    because ``ceil``/``floor``/``truncate`` of a whole number is a whole
    number, while ``sqrt``/``log``/``abs`` of one may not be. SQL makes the
    same distinction: a backend
    returns ``numeric`` for ``ABS(numeric)`` and ``double precision`` for
    ``ABS(double precision)``, so the family depends on the operand.

    Which one applies is decided per factory, not here — see
    :func:`...functions.math.abs_`, which preserves the operand's family. This
    mixin holds the operations whose result is fractional regardless.

    The SQL already existed as free functions in
    :mod:`...expression.functions.math`; this mixin makes them reachable from
    a numeric column. Each factory already tags its result with the right
    family, so ``col.sqrt()`` is a number and ``col.sign()`` is an integer
    without this mixin having to restate either.

    Example:
        >>> col.abs()                  # ABS("price")
        >>> col.round(2)               # ROUND("price", 2)
        >>> col.power(2)               # POWER("price", 2)
        >>> col.mod(3)                 # MOD("price", 3)
    """

    @staticmethod
    def _number_operand(dialect, value):
        """A numeric operand as the value node its host type declares.

        An ``int`` is an integer and a ``Decimal`` is exact, and the two are not
        interchangeable: ``MOD(x, 3)`` with a floating-point divisor stops being
        an integer modulus. So the host type picks the node rather than one type
        standing in for both. An expression is returned untouched.

        One ``Literal`` carries every value, so the host type no longer picks
        the node -- it picks the *kind*, which is what serialization writes and
        what the dialect's literal construction dispatches on. An expression is
        returned untouched: the caller said what it meant.
        """
        from .bases import BaseExpression
        from .core import Literal

        if isinstance(value, BaseExpression):
            return value
        if isinstance(value, int):
            return Literal(dialect, value)
        return Literal(dialect, decimal.Decimal(str(value)))

    @staticmethod
    def _math_functions():
        """The math factory module, imported on first use.

        Local because ``functions.math`` imports the mixins this one is mixed
        into. Handed back as a module so there is one import site per class
        rather than one per method.
        """
        from .functions import math as _module

        return _module

    # --- sign-preserving ---

    def abs(self) -> "NumericValueMixin":
        """Absolute value. ``ABS(col)``

        Keeps the operand's family: absolute value of an integer is an
        integer, and of a double is a double.
        """
        return self._math_functions().abs_(self._dialect, self)

    def sign(self) -> "NumericValueMixin":
        """Sign of the value: -1, 0 or 1. ``SIGN(col)``

        The three answers are whole numbers, but the **result is not declared
        an integer**, because the backends do not return integers: measured
        2026-10-09 on PostgreSQL, an integer argument comes back
        ``double precision`` and a numeric one comes back ``numeric``. A value
        that carries the numeric surface stays usable for the arithmetic that
        follows it, which an integer-tagged result would forbid.
        """
        return self._math_functions().sign(self._dialect, self)

    # --- rounding ---

    def round(self, decimals: Optional[int] = None) -> "NumericValueMixin":
        """Round to *decimals* places, or to a whole number. ``ROUND(col[, n])``

        Whether a **half** rounds up or to even is the backend's, and no two of
        the answers line up on both axes — measured across MySQL 8.0/5.7/5.6,
        MariaDB 11.7, PostgreSQL 18.6, Firebird 5.0.4, Oracle 23c, ClickHouse
        26.7 and SQL Server 2025:

        * on a **decimal/numeric**, half is **away from zero** on MySQL (all
          three versions), MariaDB, PostgreSQL, Firebird, Oracle and SQL Server
          (``ROUND(2.5)`` is 3, ``ROUND(3.5)`` is 4, ``ROUND(-2.5)`` is -3), and
          half to **even** on **ClickHouse** (2.5 is 2.0, 0.5 is 0.0). One
          server disagrees on this axis;
        * on a **double/float**, half to **even** on MySQL 8.0, MariaDB,
          PostgreSQL and ClickHouse, and half **away from zero** on Oracle,
          Firebird and SQL Server. Four against three, and *not the same split*
          as the decimal one — Oracle rounds a decimal away from zero and a
          float away from zero while ClickHouse rounds its decimal to even and
          its float to even, so the two axes realign there, while MySQL rounds
          its decimal away and its float to even.

        Two further facts that are not about halves and matter more:

        * SQL Server **raises** on some halves: ``ROUND(0.5, 0)`` and
          ``ROUND(-0.5, 0)`` are ``22003: arithmetic overflow``, where 2.5, 3.5
          and -2.5 round normally. So a half is not merely rounded differently
          here, it can fail;
        * MySQL 5.6 and 5.7 do not accept ``CAST(x AS DOUBLE)`` at all (a syntax
          error), where 8.0 does — the same model, different answer by *server
          version*, on top of the type.

        So "rounding" is a function of *(backend, backend version, column type)*,
        and a caller comparing a rounded value against an unrounded one — or the
        same expression on another backend — is relying on something no SQL here
        promises. The portable way to state a rule is to not be at a half:
        rounding is well-defined for every value that is not exactly ``.5``, and
        a caller who cares should decide the tie-break in the model rather than
        inherit whichever one the server, its version and the column type happen
        to give.
        """
        return self._math_functions().round_(self._dialect, self, decimals)

    def ceil(self) -> "NumericValueMixin":
        """Smallest integer not below the value. ``CEIL(col)``"""
        return self._math_functions().ceil(self._dialect, self)

    def floor(self) -> "NumericValueMixin":
        """Largest integer not above the value. ``FLOOR(col)``"""
        return self._math_functions().floor(self._dialect, self)

    def truncate(self, precision: Optional[int] = None) -> "NumericValueMixin":
        """Truncate toward zero. ``TRUNCATE(col[, n])``

        Not the same as ``round`` for a negative value: truncation drops the
        digits, rounding moves them.

        The core name is ``TRUNCATE``; the rendered one is the backend's, and
        the backends are not even spelling-compatible among themselves --
        measured 2026-10-09: ``TRUNC`` on PostgreSQL, Oracle, Firebird,
        BigQuery, SQLite and ClickHouse, ``TRUNCATE`` on MySQL, MariaDB and
        Snowflake, and SQL Server has no scalar truncate at all, spelling it
        ``ROUND(x, n, 1)``. A dialect override therefore renames rather than
        re-implements.
        """
        return self._math_functions().truncate(self._dialect, self, precision)

    # --- roots, powers, logarithms ---

    def mod(self, divisor: Union[int, float, "BaseExpression"]) -> "NumericValueMixin":
        """Remainder of division by *divisor*. ``MOD(col, n)``"""
        return self._math_functions().mod(self._dialect, self, self._number_operand(self._dialect, divisor))

    def sqrt(self) -> "NumericValueMixin":
        """Square root. ``SQRT(col)``

        Kept here rather than in :class:`TranscendentalMixin`: a square root is
        an algebraic operation, and a monetary amount has a meaningful one
        (an interest factor), which is why this mixin is the part a money
        column can reuse.
        """
        return self._math_functions().sqrt(self._dialect, self)

    def power(self, exponent: Union[int, float, "BaseExpression"]) -> "NumericValueMixin":
        """Raise to *exponent*. ``POWER(col, n)``

        Compound interest makes this meaningful for a monetary amount, so it
        belongs with the algebraic operations rather than the transcendental
        ones.
        """
        return self._math_functions().power(self._dialect, self, self._number_operand(self._dialect, exponent))


class TranscendentalMixin:
    """Operations whose result falls outside the numeric domain.

    Split from :class:`NumericValueMixin` by *what the result is*, not by which
    family the operand belongs to. ``exp``, ``log``, ``sin``, ``cos`` and
    ``tan`` answer with a real number whatever they are handed: ``log(2)`` is
    not a whole number even though 2 is, and ``sin(0)`` happens to be0 for a
    reason that has nothing to do with the operand being whole. A caller that
    wants a whole number back asks an operation that returns one — the
    rounding rungs keep the operand's family, and these five are not among
    them — rather than one that happens to land on an integer.

    ``sqrt`` and ``power`` are *not* here. They are algebraic, and a monetary
    amount has a meaningful square root and a meaningful power — compound
    interest is the obvious one — so a money column reuses those. What it does
    not have is a logarithm, which is why this is the mixin it leaves out.

    A whole-number column still mixes this in. ``log(2)`` is a legal query that
    the database will answer, and refusing to offer it would make an integer
    behave differently from the float it widens to for no reason the caller can
    see. A money column is different in kind, not in width: an interest rate is
    a logarithm taken somewhere else, and none of these belong to the amount.

    Example:
        >>> col.exp()                # EXP("x")
        >>> col.log()                # LOG("x")
        >>> col.sin()                # SIN("x")
    """

    @staticmethod
    def _math_functions():
        """The math factory module, imported on first use.

        Local because ``functions.math`` imports the mixins this one is mixed
        into. Handed back as a module so there is one import site per class
        rather than one per method.
        """
        from .functions import math as _module

        return _module

    @staticmethod
    def _number_operand(dialect, value):
        """A numeric operand as the value node its host type declares.

        An ``int`` is an integer and a ``Decimal`` is exact, and the two are not
        interchangeable: ``MOD(x, 3)`` with a floating-point divisor stops being
        an integer modulus. So the host type picks the node rather than one type
        standing in for both. An expression is returned untouched.

        One ``Literal`` carries every value, so the host type no longer picks
        the node -- it picks the *kind*, which is what serialization writes and
        what the dialect's literal construction dispatches on. An expression is
        returned untouched: the caller said what it meant.
        """
        from .bases import BaseExpression
        from .core import Literal

        if isinstance(value, BaseExpression):
            return value
        if isinstance(value, int):
            return Literal(dialect, value)
        return Literal(dialect, decimal.Decimal(str(value)))

    # --- roots, powers, logarithms ---
    #
    # sqrt and power live in NumericValueMixin; only the logarithm is here.

    def exp(self) -> "NumericValueMixin":
        """e raised to the power of the value. ``EXP(col)``"""
        return self._math_functions().exp(self._dialect, self)

    def log(self, base: Optional[Union[int, float, "BaseExpression"]] = None) -> "NumericValueMixin":
        """Natural logarithm, or logarithm to *base*. ``LOG(col[, base])``

        Two spellings, two settled meanings (measured 2026-10-09 across the ten
        backends): the one-argument form is the **natural** logarithm -- the one
        exception is PostgreSQL, where ``log(x)`` is base 10 and ``ln(x)`` is
        the natural one -- and the two-argument form takes the **base second**,
        which is the order SQL Server, ClickHouse and BigQuery use natively and
        the reverse of PostgreSQL's, MySQL's, MariaDB's, Oracle's, Firebird's
        and Snowflake's. The meaning is fixed here; a dialect override swaps the
        spelling or the argument order, never the semantics.
        """
        base_expr = None if base is None else self._number_operand(self._dialect, base)
        return self._math_functions().log(self._dialect, self, base_expr)

    # --- trigonometry ---

    def sin(self) -> "NumericValueMixin":
        """Sine. ``SIN(col)``"""
        return self._math_functions().sin(self._dialect, self)

    def cos(self) -> "NumericValueMixin":
        """Cosine. ``COS(col)``"""
        return self._math_functions().cos(self._dialect, self)

    def tan(self) -> "NumericValueMixin":
        """Tangent. ``TAN(col)``"""
        return self._math_functions().tan(self._dialect, self)


class StringToIntegerMixin:
    """Operations that read a **string** and produce an integer.
    Named for both ends of the direction: these accept a string and *return* a
    number. ``"name".length()`` is a legal string operation whose result is a
    number, and that number must not carry string operations —
    ``LENGTH(name).upper()`` is a type error in every backend; putting the
    result in its own family (:class:`IntegerValue`) is what makes
    the rule checkable instead of a convention. Because the receiver is a
    string, the mixin is attached to the string classes only: an integer never
    grows these methods, so ``LENGTH(name).length()`` cannot be constructed.

    Members are the SQL integer functions that read a string and produce a
    count or a code. Arithmetic on the result comes from
    :class:`ArithmeticMixin`, which the integer value expression also carries.
    """

    if TYPE_CHECKING:  # pragma: no cover
        from .core import IntegerValue

    @staticmethod
    def _string_functions():
        """The string factory module, imported on first use.

        Local because ``functions.string`` imports the mixins this one is mixed
        into.
        """
        from .functions import string as _module

        return _module

    def position(self, substring: str) -> "BaseExpression":
        """1-based position of *substring*. ``POSITION(substring IN expr)``

        The needle comes first here, matching the standard spelling, while
        :meth:`strpos` takes the haystack first like its native function. Both
        are one operation with two spellings, and each backend renders whichever
        of them it has: PostgreSQL takes only ``POSITION(sub IN s)`` -- its
        comma form is a syntax error -- SQL Server spells it ``CHARINDEX``,
        ClickHouse and BigQuery put the haystack first, MySQL and MariaDB
        ``LOCATE``, Oracle and Firebird ``INSTR``.
        """
        return self._string_functions().position(self._dialect, substring, self)

    # --- operations that read a string and produce a number ---

    def length(self) -> "BaseExpression":
        """Length of the string, in **whatever unit the backend's ``LENGTH`` uses**.

        ``LENGTH(expr)`` — and that unit is not characters everywhere, which is
        the discipline this docstring exists to state rather than leave to be
        discovered from a wrong answer.

        Measured per backend (``suggested-pairing-string-enum.md``, the S-length
        row):

        * PostgreSQL, Oracle, Firebird — **characters**, so a 5-character string
          reports 5 whatever its encoding;
        * MySQL, MariaDB, ClickHouse — **bytes**, so the same string reports its
          encoded length and a multi-byte character counts for more than one;
        * SQL Server — **UTF-16 code units**, so a 5-character string holding
          astral characters reports 10. There is no portable fix here: this
          backend maps both ``LENGTH`` and ``CHAR_LENGTH`` to ``LEN``, and
          ``LEN`` is what counts code units.

        Only the first group agrees with what this method's old one-line
        docstring promised. A caller who needs a *character* count on every
        backend therefore cannot use ``length`` alone; :meth:`octet_length` is
        the honest byte count where the backend distinguishes them, and a
        character count on MySQL-family backends needs the backend's own
        ``CHAR_LENGTH`` spelled out through the function layer rather than
        assumed here.

        What this method does **not** do is pick a unit and pretend it is
        portable. The word ``LENGTH`` is the one every backend here has, so it
        is the one written, and the difference is a property of the backends
        rather than of the operation — the same shape as the ``= 1`` boolean
        literal, where the framework refuses the non-portable spelling instead
        of rendering it and hoping.
        """
        return self._string_functions().length(self._dialect, self)

    def ascii(self) -> "BaseExpression":
        """Code of the first character. ``ASCII(expr)``"""
        return self._string_functions().ascii(self._dialect, self)

    def octet_length(self) -> "BaseExpression":
        """Length in bytes. ``OCTET_LENGTH(expr)``"""
        return self._string_functions().octet_length(self._dialect, self)

    def bit_length(self) -> "BaseExpression":
        """Length in bits. ``BIT_LENGTH(expr)``"""
        return self._string_functions().bit_length(self._dialect, self)

    def strpos(self, substring: str) -> "BaseExpression":
        """1-based position of *substring*, or 0. ``STRPOS(expr, substring)``

        The mirror spelling of :meth:`position`: haystack first, as every
        native ``STRPOS``/``LOCATE``/``INSTR``/``CHARINDEX`` takes it. On
        backends with no such function a dialect renders the other spelling.
        """
        return self._string_functions().strpos(self._dialect, self, substring)


class StringValueMixin:
    """String **value** operations: each returns a new string-valued expression.

    Distinct from :class:`StringPatternPredicateMixin`, which answers questions
    about a string instead of deriving one. These operations derive, so they
    chain: ``col.upper().substr(0, 3).length()`` stays a string until the last
    step, which is numeric.

    The SQL itself comes from :mod:`...expression.functions.string`, where all
    of these already existed as free functions; this mixin only makes them
    reachable from a column and gives the result a string type so the next call
    in the chain is available. Result types are honest about SQL semantics:
    ``length``, ``ascii``, ``strpos``, ``octet_length`` and ``bit_length``
    return numbers, and they are not on this mixin.

    Example:
        >>> col.upper().substr(1, 3)      # SUBSTRING(UPPER("name"), 1, 3)
        >>> col.length() > 5              # LENGTH("name") > ?
    """


    # --- case ---

    @staticmethod
    def _string_functions():
        """The string factory module, imported on first use.

        A local import because ``functions.string`` imports the mixins this one
        is mixed into. Handing back the module (rather than each factory) keeps
        one import site instead of twelve.
        """
        from .functions import string as _module

        return _module

    def upper(self) -> "StringValueMixin":
        """Upper-case the string. ``UPPER(col)``"""
        return self._string_functions().upper(self._dialect, self)

    def lower(self) -> "StringValueMixin":
        """Lower-case the string. ``LOWER(col)``"""
        return self._string_functions().lower(self._dialect, self)

    def initcap(self) -> "StringValueMixin":
        """Capitalise the first letter of each word. ``INITCAP(col)``"""
        return self._string_functions().initcap(self._dialect, self)

    def reverse(self) -> "StringValueMixin":
        """Reverse the string. ``REVERSE(col)``"""
        return self._string_functions().reverse(self._dialect, self)

    def translate(self, from_chars: str, to_chars: str) -> "StringValueMixin":
        """Replace characters pairwise. ``TRANSLATE(col, from, to)``"""
        return self._string_functions().translate(self._dialect, self, from_chars, to_chars)

    # --- slicing and padding ---

    def substr(self, start: int, length: Optional[int] = None) -> "StringValueMixin":
        """Substring, 1-based. ``SUBSTRING(col, start[, length])``

        ``start >= 1`` and ``length >= 0``; both are refused otherwise, because
        an out-of-range position is consumed by the length on some backends,
        yields an empty string on others and is read as 1 on Oracle (see
        :func:`~...functions.string.substring`).
        """
        return self._string_functions().substring(self._dialect, self, start, length)

    def left(self, n: int) -> "StringValueMixin":
        """First *n* characters. ``LEFT(col, n)``

        ``n >= 0``: 0 is the empty string and more than the length is the whole
        string on every backend. A negative count is refused at construction --
        the backends answer four different ways to it (see
        :func:`~...functions.string.left`).
        """
        return self._string_functions().left(self._dialect, self, n)

    def right(self, n: int) -> "StringValueMixin":
        """Last *n* characters. ``RIGHT(col, n)``

        ``n >= 0``, with 0 and over-length agreeing everywhere; a negative
        count is refused, same as :meth:`left`.
        """
        return self._string_functions().right(self._dialect, self, n)

    def lpad(self, length: int, pad: Optional[str] = None) -> "StringValueMixin":
        """Left-pad to *length*. ``LPAD(col, length, pad)``

        ``length >= 0`` and a non-empty *pad*; an omitted pad means one space
        and is always spelled out, because MySQL raises 1582 without it while
        MariaDB fills with spaces. An empty pad is refused -- the backends
        answer it as untouched string, empty string or NULL.
        """
        return self._string_functions().lpad(self._dialect, self, length, pad)

    def rpad(self, length: int, pad: Optional[str] = None) -> "StringValueMixin":
        """Right-pad to *length*. ``RPAD(col, length, pad)``

        The mirror of :meth:`lpad`: ``length >= 0``, a non-empty *pad*, an
        omitted pad spelled as one space, an empty pad refused.
        """
        return self._string_functions().rpad(self._dialect, self, length, pad)

    def repeat(self, count: int) -> "StringValueMixin":
        """Repeat the string *count* times. ``REPEAT(col, count)``

        A negative *count* is the empty string rather than a refusal -- the
        native answer on PostgreSQL, MySQL, MariaDB and ClickHouse alike.
        """
        return self._string_functions().repeat(self._dialect, self, count)

    def overlay(self, replacement: str, start: int, length: Optional[int] = None) -> "StringValueMixin":
        """Overwrite a span. ``OVERLAY(col PLACING replacement FROM start [FOR length])``"""
        return self._string_functions().overlay(self._dialect, self, replacement, start, length)

    # --- search and replace ---

    def replace(self, pattern: str, replacement: str) -> "StringValueMixin":
        """Replace every occurrence. ``REPLACE(col, pattern, replacement)``"""
        return self._string_functions().replace(self._dialect, self, pattern, replacement)

    # --- whitespace ---

    def trim(self, chars: Optional[str] = None, direction: str = "BOTH") -> "StringValueMixin":
        """Trim whitespace or *chars*. ``TRIM([direction] [chars] FROM col)``

        Args:
            chars: One character to trim, or ``None`` for spaces. A
                multi-character set is refused: SQL:2016 feature E021-09
                defines a single trim character, and in the field a longer set
                is a character set on PostgreSQL/SQL Server/ClickHouse/
                Snowflake, a whole string repeated on MySQL/MariaDB/Firebird
                and ``ORA-30001`` on Oracle.
            direction: One of ``BOTH`` (default), ``LEADING``, ``TRAILING``.
        """
        return self._string_functions().trim(self._dialect, self, chars=chars, direction=direction)

    # --- combination ---

    def concat(self, *others) -> "StringValueMixin":
        """Concatenate with other values. ``CONCAT(col, ...)``

        Note: SQL ``||`` is not used. Its meaning is dialect-dependent — it is
        logical OR by default in MySQL — so the portable function is the only
        spelling offered here.
        """
        from .functions import string as _string
        from .bases import BaseExpression
        from .core import Literal

        operands = [self]
        for other in others:
            operands.append(
                other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
            )
        return _string.concat(self._dialect, *operands)

    def concat_using_operator(self, *others) -> "StringValueMixin":
        """Concatenate using whatever spelling this dialect uses for ``||``.

        The operator is resolved by the dialect, not baked in: MySQL, MariaDB
        and SQL Server read a literal ``||`` as logical OR, and BigQuery does
        not accept it as concatenation, so those render ``CONCAT(a, b)`` while
        the rest emit ``a || b``. Either way the *intent* is concatenation.

        Prefer :meth:`concat` unless the operator form is specifically wanted;
        it renders the same thing but reads more clearly at the call site.
        """
        from .functions import string as _string
        from .bases import BaseExpression
        from .core import Literal

        operands = [self]
        for other in others:
            operands.append(
                other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
            )
        return _string.concat_op(self._dialect, *operands)

    def coalesce(self, *others) -> "StringValueMixin":
        """First non-null value. ``COALESCE(col, ...)``"""
        from .functions import string as _string
        from .bases import BaseExpression
        from .core import Literal

        operands = [self]
        for other in others:
            operands.append(
                other if isinstance(other, BaseExpression) else Literal(self._dialect, other)
            )
        return _string.coalesce(self._dialect, *operands)


class StringPatternPredicateMixin:
    """Pattern-matching **predicates** on a string-valued expression.

    This is a predicate surface, not a set of value operations: ``like`` and
    ``ilike`` produce no new value, they answer a yes/no question about the
    operand. In SQL they are not functions either — ``LIKE`` sits in the
    predicate grammar beside ``=`` and ``<``, and appears wherever a boolean is
    legal: a SELECT list, ``CASE WHEN``, ``JOIN ... ON``, a ``CHECK``
    constraint, a partial-index predicate. It is therefore not something a
    *column* owns.

    The previous class was named ``StringMixin`` and held only these two
    methods, so a class called ``StringColumn`` offered no string operations at
    all — it offered the ability to be LIKE-matched. String *value* operations
    live in :class:`StringValueMixin`.

    Crossing into a predicate ends the value chain: the result is a boolean and
    can be combined with ``&`` / ``|`` / ``~``, but it never becomes a string
    again.

    Example:
        >>> col = Column(dialect, "name")
        >>> starts_with_a = col.like("A%")   # "name LIKE ?"   params ("A%",)
        >>> both = col.like("A%") & (col.ilike("%x%") | col.like("B%"))
    """

    def like(self: "SQLValue", pattern: str) -> "SQLPredicate":
        """
        Generate a LIKE predicate for pattern matching.

        - % matches zero or more characters
        - _ matches a single character

        **Case sensitivity is the backend's, not this method's.** Measured
        2026-10-09: SQLite, MySQL, MariaDB and SQL Server match
        ``'abc' LIKE 'A%'`` case-insensitively (following their collation),
        while PostgreSQL, ClickHouse, Oracle and BigQuery are case-sensitive
        and Firebird follows its collation. Nothing here changes that, and no
        ``COLLATE`` clause bolted onto the predicate rescues it on SQLite.
        A predicate that must mean the same thing everywhere is
        :meth:`ilike`.

        Args:
            pattern: Pattern string with SQL LIKE wildcards

        Returns:
            SQLPredicate representing the LIKE operation

        Example:
            >>> col = Column(dialect, "name")
            >>> predicate = col.like("John%")  # Matches names starting with "John"
            >>> # Generates: "name LIKE ?" with params ("John%",)
        """
        from .core import Literal
        from .predicates import LikeOperator, LikePredicate

        return LikePredicate(
            self._dialect, LikeOperator.LIKE, self, Literal(self._dialect, pattern)
        )

    def ilike(self: "SQLValue", pattern: str) -> "SQLPredicate":
        """
        Generate a case-insensitive pattern-matching predicate.

        This is the one spelling in the framework that *means*
        case-insensitive, where :meth:`like` makes no such promise (its
        sensitivity is the backend's). Backends with a native ``ILIKE``
        (PostgreSQL, ClickHouse, Snowflake) render it; the rest are meant to
        emulate it as ``LOWER(x) LIKE LOWER(y)`` through the dialect, which
        folds ASCII rather than the full Unicode case the native operators do.
        Check the operation-groups survey for the per-backend state before
        relying on a backend that lacks the native form.

        Args:
            pattern: Pattern string with SQL LIKE wildcards

        Returns:
            SQLPredicate representing the case-insensitive pattern match

        Example:
            >>> col = Column(dialect, "email")
            >>> predicate = col.ilike("%@gmail.com")  # Matches regardless of case
            >>> # Generates: "email ILIKE ?" with params ("%@gmail.com",)
        """
        from .core import Literal
        from .predicates import LikeOperator, LikePredicate

        return LikePredicate(
            self._dialect, LikeOperator.ILIKE, self, Literal(self._dialect, pattern)
        )


class TypeCastingMixin:
    """Provides type casting capability to SQL value expressions.

    A type cast is a proper AST node (:class:`CastExpression`) whose single
    child is the wrapped expression — never decoration state stored on the
    casted expression. ``cast()`` therefore **wraps** ``self`` in a new node,
    exactly like every other operator-overload in this package builds a new
    parent node over its operands.

    Chained calls nest like any other expression:

    Example:
    >>> col = Column(dialect, "price")
    >>> expr = col.cast(IntegerType(col.dialect))
    >>> # Generates: CAST("price" AS INTEGER)
    >>> # PostgreSQL generates: "price"::INTEGER
    >>>
    >>> # Chained conversions (each cast nests the previous node)
    >>> expr3 = col.cast(MoneyType(col.dialect)).cast(NumericType(col.dialect))
    >>> # Generates: CAST(CAST(CAST("price" AS money) AS numeric) AS float8)
    >>> # PostgreSQL generates: "price"::money::numeric::float8
    """

    def cast(self: "SQLValue", target_type: str) -> "CastExpression":
        """Wrap this expression in a CAST node targeting *target_type*.

        Args:
            target_type: Target SQL type name (e.g., 'INTEGER', 'VARCHAR(100)',
            'NUMERIC(10,2)'). Type modifiers should be included in the
            type string.

        Returns:
            A new :class:`CastExpression` node wrapping this expression,
            inheriting this expression's dialect binding state.

        Note:
            The actual SQL syntax is determined by the dialect's
            format_cast_expression method. PostgreSQL uses expr::type syntax,
            while other databases use CAST(expr AS type) syntax.
        """
        from .core import CastExpression

        # Alias decorates the outermost rendered form: wrapping an aliased
        # expression in a CAST moves the alias onto the CAST node, so
        # `col.cast(IntegerType(...)).as_("v")` and `col.as_("v").cast(IntegerType(...))`
        # both render `CAST(col AS INTEGER) AS v`. The original expression
        # is only mutated when it is itself a temporary copy (the as_()
        # convention returns copies), so shared nodes stay untouched.
        alias = self.alias if isinstance(self, AliasableMixin) else None
        node = CastExpression(self._dialect, self, target_type, alias=alias)
        if alias is not None:
            self.alias = None
        return node


class IntervalMixin:
    """Marks a value as a **span** of time rather than a **point** in it.

    A date, a time and a date-time are points: they sit somewhere on the
    timeline. An interval is the distance between two of them, and arithmetic
    on the two is not the same -- a point moves by an interval, a point minus a
    point is an interval, but two points have no sum and an interval scales by a
    number rather than being added to.

    So the distinction has to be stated somewhere the arithmetic can read, and
    this is that statement. It carries no operations of its own: an interval
    does everything a temporal value does, plus this one fact about which it
    is.

    It exists because ``timestamp + interval`` and ``interval + interval`` are
    different operations and the gate that refuses the invalid ones has to know
    which it is holding. While an interval was wrapped in a value class the gate
    could ask about the wrapper; now that an interval *is* a node, the node says
    so by being one of these.
    """


class DateTimeMixin:
    """Temporal operations available on a value known to hold a date/time.

    Every method here wraps *this* expression in a proper AST node and hands
    rendering to the dialect (``format_extract_expression``,
    ``format_date_trunc_expression``, ``format_datetime_add_expression``, …).
    No SQL is built by this mixin, and the expression nodes it constructs
    already exist — this is a thin, dialect-neutral façade over them.

    The mixin is mixed into :class:`~...expression.column_types.TimestampColumn`
    only, so a numeric or string column cannot reach these operations.

    Chaining nests like any other expression::

        >>> col = TimestampColumn(dialect, "created_at")
        >>> col.date_trunc("month")
        >>> # -> DATE_TRUNC('month', "created_at")
        >>> col.date_trunc("day").extract("year")
        >>> # -> EXTRACT(year FROM DATE_TRUNC('day', "created_at"))

    Note:
        ``now()`` / ``current_date()`` / ``current_timestamp()`` are
        deliberately absent: they take no column and belong to the
        ``functions.datetime`` module, not to a column's own surface.

    Time zones, stated because they are not portable
    ------------------------------------------------
    Measured on MySQL 8.0/5.7/5.6, MariaDB 11.7, PostgreSQL 18.6, Firebird 5.0.4,
    Oracle 23c, ClickHouse 26.7 and SQL Server 2025, and the differences are
    load-bearing rather than cosmetic:

    * **MySQL everywhere drops the offset.** ``CAST('2026-01-01
      12:00:00+08:00' AS DATETIME)`` reads back ``12:00`` with no zone on 8.0,
      5.7 and 5.6 alike — the offset is parsed away rather than converted.
      ``CONVERT_TZ`` is the only conversion available and needs the zone tables
      loaded to name a region. Their introspection reports the column as plain
      ``timestamp``: there is no time-zone word in the type at all;
    * **SQL Server rejects the literal outright.** The same ``CAST`` is
      ``22007`` there, and the spelling that works is ``DATETIMEOFFSET``, which
      preserves the offset as ``2026-01-01 12:00:00.0000000 +08:00``. So a
      ``DATETIME`` on SQL Server and a ``DATETIME`` on MySQL fail in opposite
      ways — one refuses, one accepts and forgets;
    * **PostgreSQL renders a ``timestamptz`` through the *session* time zone.**
      One row holding ``2026-01-01 12:00:00+08:00`` reads back as
      ``04:00+00`` under ``SET TIME ZONE 'UTC'`` and ``12:00+08`` under
      ``Asia/Shanghai`` — five sessions, five strings. The *instant* does not
      move: ``extract(epoch FROM ts)`` is ``1767240000`` under both. So this is
      a rendering dependency and not a corruption, which is what makes it easy
      to miss: a comparison of two rendered strings from two sessions looks like
      a data difference and is not one;
    * **ClickHouse** converts on parse: ``parseDateTimeBestEffort`` on the same
      literal yields ``04:00``, and ``toDateTime(v, 'Asia/Shanghai')`` yields
      ``12:00`` attached to that zone. It has the zone word in the type;
    * **Firebird** has both, and the column's type decides. A plain
      ``TIMESTAMP`` reads back naive, and ``TIMESTAMP WITH TIME ZONE`` really
      does hold the zone — the same ``+08:00`` literal reads back with a
      ``tzstr('UTC+08:00')`` attached. What it has no form for is a *named*
      region: the offset is stored, the region is not.

    What follows for a caller: a naive ``datetime`` is portable everywhere here,
    and an aware one is not. The same field annotated with an aware datetime
    will store the instant on PostgreSQL and ClickHouse, the wall-clock string on
    MySQL, and fail to build at all on SQL Server. Deciding which of those a
    model means is the model author's, and this façade does not choose it by
    rendering a conversion the caller did not ask for.
    """

    def _temporal_node(self, node_class, *args, **kwargs):
        """Build *node_class* over this expression, hoisting the alias.

        Mirrors :meth:`TypeCastingMixin.cast`: the alias decorates the
        outermost rendered form, so ``col.as_("d").date_trunc("day")`` and
        ``col.date_trunc("day").as_("d")`` both render the same SQL. The
        receiver is only mutated when it is itself a temporary copy (the
        ``as_()`` convention returns copies).
        """
        alias = self.alias if isinstance(self, AliasableMixin) else None
        node = node_class(self._dialect, *args, alias=alias, **kwargs)
        if alias is not None:
            self.alias = None
        return node

    def extract(self, field: str) -> "ExtractExpression":
        """Extract one field as a number, e.g. ``col.extract("year")``."""
        from .datetime import ExtractExpression

        return self._temporal_node(ExtractExpression, field, self)

    def date_part(self, field: str) -> "DatePartExpression":
        """SQL-standard spelling of :meth:`extract`."""
        from .datetime import DatePartExpression

        return self._temporal_node(DatePartExpression, field, self)

    def date_trunc(self, field: str) -> "DateTruncExpression":
        """Truncate to *field*, e.g. ``col.date_trunc("month")``."""
        from .datetime import DateTruncExpression

        return self._temporal_node(DateTruncExpression, field, self)

    def date_add(self, value, unit: Optional[str] = None) -> "DateTimeAddExpression":
        """Add an interval, e.g. ``col.date_add(7, "day")``."""
        from .datetime import DateTimeAddExpression

        return self._temporal_node(
            DateTimeAddExpression, self, _as_interval(self._dialect, value, unit)
        )

    def date_sub(self, value, unit: Optional[str] = None) -> "DateTimeSubtractExpression":
        """Subtract an interval, e.g. ``col.date_sub(1, "month")``."""
        from .datetime import DateTimeSubtractExpression

        return self._temporal_node(
            DateTimeSubtractExpression, self, _as_interval(self._dialect, value, unit)
        )

    def date_diff(self, unit: str, end) -> "DateTimeDiffExpression":
        """Difference between this value and *end*, expressed in *unit*."""
        from .datetime import DateTimeDiffExpression

        return self._temporal_node(DateTimeDiffExpression, unit, self, end)


def _as_interval(dialect, value, unit: Optional[str]):
    """Coerce ``(value, unit)`` or an ``IntervalExpression`` to an interval.

    A bare number needs its unit; an already-built interval must not be given
    one, since that would be ambiguous.
    """
    from .datetime import IntervalExpression

    if isinstance(value, IntervalExpression):
        if unit is not None:
            raise ValueError("unit must not be provided when value is an IntervalExpression")
        return value
    if unit is None:
        raise ValueError("unit is required when value is numeric")
    return IntervalExpression(dialect, value, unit)


class ArrayMixin:
    """Array operations available on a value known to hold an array.

    Mixed into :class:`~...expression.column_types.ArrayColumn` only. The
    expression nodes and dialect formatters already exist; this is a thin
    façade so a caller does not have to thread the dialect by hand.
    """

    def array_length(self, dimension: int = 1) -> "FunctionCall":
        """Number of elements, e.g. ``col.array_length()``."""
        from .functions.array import array_length

        return array_length(self._dialect, self, dimension)

    def unnest(self, alias: Optional[str] = None) -> "FunctionCall":
        """Expand this array into rows, e.g. in a FROM clause."""
        from .functions.array import unnest

        return unnest(self._dialect, self)


class JSONAccessorMixin:
    """Path access for a value known to hold JSON.

    Mixed into **both** :class:`~...expression.column_types.JSONColumn` and
    :class:`~...expression.advanced_functions.JSONDocumentValue` — the latter is
    what :meth:`json_path` returns, so without it on both, chaining
    ``col.json_value("a").json_value("b")`` would break at the second call.

    Two shapes, matching the two JSON access operators:

    * :meth:`json_path` (``->>``) yields a **scalar** and ends the chain.
    * :meth:`json_value` (``->``) yields **JSON** and can be chained again.

    Keys accumulate into one path rather than nesting two expressions.
    That matters: nesting two paths re-anchors the second one at ``$`` and
    applies ``->`` to the previous result, which is wrong on every backend
    (``->`` on the text that ``->>`` returned, and ``$.b`` matching nothing).

    Example:
        >>> col = JSONColumn(dialect, "settings")
        >>> col.json_path("a", "b")          # -> "settings"->>'$.a.b'
        >>> col.json_path("tags", 0)         # -> "settings"->>'$.tags[0]'
        >>> col.json_value("a").json_value("b")   # -> "settings"->'$.a'->'$.b'
    """

    def _json_path(self, keys, as_text: bool, mode) -> "SQLValue":
        from .advanced_functions import (
            JSONDocumentValue,
            JSONTextValue,
        )

        alias = self.alias if isinstance(self, AliasableMixin) else None
        # The two operations yield different types, so they build different
        # nodes: `->>` is text and offers the text operations, `->` is a
        # document and offers the path accessors again.
        node_class = JSONTextValue if as_text else JSONDocumentValue
        node = node_class(
            self._dialect,
            self,
            build_json_path(*keys),
            operation="->>" if as_text else "->",
            alias=alias,
            mode=mode,
        )
        if alias is not None:
            self.alias = None
        return node

    def json_path(self, *keys, mode=None) -> "JSONTextValue":
        """Extract a scalar at *keys* (renders ``->>``).

        Args:
            *keys: Path segments. An ``int`` is an array index and renders
                as ``[n]``; a ``str`` is always an object key, so ``"0"``
                renders ``.0`` (a key literally named ``0``) — pass the int
                ``0`` for the first element. A string that already starts
                with ``[`` is passed through, so a caller can express a
                native path segment this helper does not model.
            mode: Optional :class:`JSONPathMode` (or its string value) to
                force arrow or function-based rendering.
        """
        return self._json_path(keys, as_text=True, mode=mode)

    def json_value(self, *keys, mode=None) -> "JSONDocumentValue":
        """Extract JSON at *keys* (renders ``->``), preserving the JSON type.

        Chainable: the result is itself a JSON expression, so further
        segments can be appended.
        """
        return self._json_path(keys, as_text=False, mode=mode)


def build_json_path(*keys) -> str:
    """Join path *keys* into a JSONPath rooted at ``$``.

    Array indices must render as ``[n]``: ``$.tags.0`` is an object key
    literally named ``0`` and matches nothing, while ``$.tags[0]`` is the
    first element. A segment that already looks like a native path segment
    (starts with ``[``) is passed through untouched so callers can express
    anything this helper does not cover.

    A ``str`` is **always** an object key, including one that looks like a
    number — ``"0"`` is a key named ``0``, not an index. The distinction is
    the type, not the spelling, so ``json_path("tags", 0)`` is the first
    element and ``json_path("tags", "0")`` is the key ``"0"``.

    Example:
        >>> build_json_path("a", "b")
        '$.a.b'
        >>> build_json_path("tags", 0)
        '$.tags[0]'
        >>> build_json_path("tags", "[0]")
        '$.tags[0]'
    """
    path = "$"
    for key in keys:
        if isinstance(key, bool):
            # bool is an int subclass; treating True as index 1 would be a
            # silent, baffling bug.
            raise TypeError(f"JSON path segment must be str or int, got bool: {key!r}")
        if isinstance(key, int):
            path += f"[{key}]"
        elif isinstance(key, str) and key.startswith("["):
            path += key
        else:
            path += f".{key}"
    return path
