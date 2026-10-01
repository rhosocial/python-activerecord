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
    col1 + col2   # Creates BinaryArithmeticExpression with col1's dialect

    # Logical operations
    (col1 == 1) & (col2 == 2)  # Creates LogicalPredicate with left predicate's dialect

The dialect parameter is always inherited from the left-hand side operand,
ensuring consistent SQL generation across the expression tree.
"""

import copy
from typing import Any, Optional, Union, List, TYPE_CHECKING, TypeVar

if TYPE_CHECKING:  # pragma: no cover
    from .bases import SQLValueExpression, SQLPredicate
    from .core import CastExpression, FunctionCall, IntegerValueExpression
    from .datetime import (
        DatePartExpression,
        DateTimeAddExpression,
        DateTimeDiffExpression,
        DateTimeSubtractExpression,
        DateTruncExpression,
        ExtractExpression,
    )
    from .advanced_functions import JSONExpression

T = TypeVar("T")


class AliasableMixin:
    """Mixin class that provides aliasing capability to expressions.

    This mixin allows expressions to be given aliases for use in SQL queries,
    particularly useful in SELECT clauses and subqueries.

    Example:
        >>> Column(dialect, "name").as_("user_name")
        >>> # Results in: "name AS user_name" in SQL
    """

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
        if hasattr(new, "_cast_types"):
            new._cast_types = list(new._cast_types)
        return new


class ComparisonMixin:
    """
    Provides comparison operators (==, !=, >, <, etc.) and other boolean-producing methods.

    This mixin enables Python's comparison operators to generate SQL comparison predicates.
    When using these operators, the left operand's dialect is used for the resulting
    expression, ensuring consistent SQL generation across the expression tree.

    The mixin handles both expression-to-expression comparisons and expression-to-value
    comparisons by automatically wrapping non-expression values in Literal objects.

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
    """

    def __eq__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
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
        from .bases import SQLValueExpression

        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, "=", self, other_expr)

    def __ne__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
        """
        Implement the inequality operator (!=) to generate SQL inequality predicate.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLPredicate representing the inequality comparison
        """
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import SQLValueExpression

        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, "!=", self, other_expr)

    def __gt__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
        """
        Implement the greater-than operator (>) to generate SQL comparison predicate.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLPredicate representing the greater-than comparison
        """
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import SQLValueExpression

        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, ">", self, other_expr)

    def __ge__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
        """
        Implement the greater-or-equal operator (>=) to generate SQL comparison predicate.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLPredicate representing the greater-or-equal comparison
        """
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import SQLValueExpression

        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, ">=", self, other_expr)

    def __lt__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
        """
        Implement the less-than operator (<) to generate SQL comparison predicate.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLPredicate representing the less-than comparison
        """
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import SQLValueExpression

        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, "<", self, other_expr)

    def __le__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
        """
        Implement the less-or-equal operator (<=) to generate SQL comparison predicate.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLPredicate representing the less-or-equal comparison
        """
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import SQLValueExpression

        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self._dialect, other)
        return ComparisonPredicate(self._dialect, "<=", self, other_expr)

    def is_null(self: "SQLValueExpression") -> "SQLPredicate":
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

    def is_not_null(self: "SQLValueExpression") -> "SQLPredicate":
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

    def is_true(self: "SQLValueExpression") -> "SQLPredicate":
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

    def is_not_true(self: "SQLValueExpression") -> "SQLPredicate":
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

    def is_false(self: "SQLValueExpression") -> "SQLPredicate":
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

    def is_not_false(self: "SQLValueExpression") -> "SQLPredicate":
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

    def in_(self: "SQLValueExpression", values: List[Any]) -> "SQLPredicate":
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
        from .core import Literal
        from .predicates import InPredicate

        to_query_expression = getattr(values, "to_query_expression", None)
        if callable(to_query_expression):
            # An ActiveQuery-like object: render as an IN subquery.
            from .core import Subquery

            return InPredicate(self._dialect, self, Subquery(None, to_query_expression()))
        if hasattr(values, "to_sql"):
            # Already an expression (e.g. Subquery): pass through.
            return InPredicate(self._dialect, self, values)

        return InPredicate(self._dialect, self, Literal(self._dialect, tuple(values)))

    def not_in(self: "SQLValueExpression", values: List[Any]) -> "SQLPredicate":
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

    def between(self: "SQLValueExpression", low: Any, high: Any) -> "SQLPredicate":
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

    def __add__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLValueExpression":
        """
        Implement the addition operator (+) to generate SQL arithmetic expression.

        This method enables expressions like: `Column(...) + value` or `Column(...) + Column(...)`
        The resulting BinaryArithmeticExpression uses the left operand's dialect for SQL generation.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLValueExpression representing the addition operation

        Example:
            >>> col = Column(dialect, "price")
            >>> expr = col + 10  # Generates: "price + ?" with params (10,)
        """
        from .core import Literal
        from .operators import BinaryArithmeticExpression
        from .bases import SQLValueExpression

        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self._dialect, other)
        return BinaryArithmeticExpression(self._dialect, "+", self, other_expr)

    def __sub__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLValueExpression":
        """
        Implement the subtraction operator (-) to generate SQL arithmetic expression.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLValueExpression representing the subtraction operation
        """
        from .core import Literal
        from .operators import BinaryArithmeticExpression
        from .bases import SQLValueExpression

        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self._dialect, other)
        return BinaryArithmeticExpression(self._dialect, "-", self, other_expr)

    def __mul__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLValueExpression":
        """
        Implement the multiplication operator (*) to generate SQL arithmetic expression.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLValueExpression representing the multiplication operation
        """
        from .core import Literal
        from .operators import BinaryArithmeticExpression
        from .bases import SQLValueExpression

        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self._dialect, other)
        return BinaryArithmeticExpression(self._dialect, "*", self, other_expr)

    def __truediv__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLValueExpression":
        """
        Implement the division operator (/) to generate SQL arithmetic expression.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLValueExpression representing the division operation
        """
        from .core import Literal
        from .operators import BinaryArithmeticExpression
        from .bases import SQLValueExpression

        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self._dialect, other)
        return BinaryArithmeticExpression(self._dialect, "/", self, other_expr)

    def __mod__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLValueExpression":
        """
        Implement the modulo operator (%) to generate SQL arithmetic expression.

        Args:
            other: Right operand, can be another expression or a literal value

        Returns:
            SQLValueExpression representing the modulo operation
        """
        from .core import Literal
        from .operators import BinaryArithmeticExpression
        from .bases import SQLValueExpression

        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self._dialect, other)
        return BinaryArithmeticExpression(self._dialect, "%", self, other_expr)


class LogicalMixin:
    """
    Provides logical operators (&, |, ~) for SQL predicates.

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

    def __and__(self: "SQLPredicate", other: "SQLPredicate") -> "SQLPredicate":
        """
        Implement the logical AND operator (&) to generate SQL logical predicate.

        This method enables expressions like: `predicate1 & predicate2`
        The resulting LogicalPredicate uses the left operand's dialect for SQL generation.

        Args:
            other: Right operand, must be another SQLPredicate

        Returns:
            SQLPredicate representing the logical AND operation

        Example:
            >>> p1 = Column(dialect, "status") == "active"
            >>> p2 = Column(dialect, "age") >= 18
            >>> combined = p1 & p2  # Generates: "(status = ?) AND (age >= ?)"
        """
        from .predicates import LogicalPredicate

        return LogicalPredicate(self._dialect, "AND", self, other)

    def __or__(self: "SQLPredicate", other: "SQLPredicate") -> "SQLPredicate":
        """
        Implement the logical OR operator (|) to generate SQL logical predicate.

        Args:
            other: Right operand, must be another SQLPredicate

        Returns:
            SQLPredicate representing the logical OR operation
        """
        from .predicates import LogicalPredicate

        return LogicalPredicate(self._dialect, "OR", self, other)

    def __invert__(self: "SQLPredicate") -> "SQLPredicate":
        """
        Implement the logical NOT operator (~) to generate SQL logical predicate.

        Args:
            self: The predicate to negate

        Returns:
            SQLPredicate representing the logical NOT operation

        Example:
            >>> p = Column(dialect, "status") == "active"
            >>> negated = ~p  # Generates: "NOT (status = ?)"
        """
        from .predicates import LogicalPredicate

        return LogicalPredicate(self._dialect, "NOT", self)


class IntegerValueMixin:
    """Operations on an **integer**-valued expression.

    Separate from :class:`StringValueMixin` because these *return* an integer
    rather than accept one. ``"name".length()`` is a legal string operation
    whose result is a number, and that number must not carry string
    operations — ``LENGTH(name).upper()`` is a type error in every backend.
    Putting the result in its own family is what makes the rule checkable
    instead of a convention.

    Members are the SQL integer functions that read a value and produce a
    count or a code. Arithmetic is on :class:`ArithmeticMixin`, which the
    integer value expression also carries.
    """

    if TYPE_CHECKING:  # pragma: no cover
        from .core import IntegerValueExpression

    def length(self) -> "IntegerValueExpression":
        """Number of characters. ``LENGTH(expr)``"""
        from .functions import string as _string

        return _string.length(self._dialect, self)

    def ascii(self) -> "IntegerValueExpression":
        """Code of the first character. ``ASCII(expr)``"""
        from .functions import string as _string

        return _string.ascii(self._dialect, self)

    def octet_length(self) -> "IntegerValueExpression":
        """Length in bytes. ``OCTET_LENGTH(expr)``"""
        from .functions import string as _string

        return _string.octet_length(self._dialect, self)

    def bit_length(self) -> "IntegerValueExpression":
        """Length in bits. ``BIT_LENGTH(expr)``"""
        from .functions import string as _string

        return _string.bit_length(self._dialect, self)

    def strpos(self, substring: str) -> "IntegerValueExpression":
        """1-based position of *substring*, or 0. ``STRPOS(expr, substring)``"""
        from .functions import string as _string

        return _string.strpos(self._dialect, self, substring)

    def position(self, substring: str) -> "IntegerValueExpression":
        """1-based position of *substring*. ``POSITION(substring IN expr)``"""
        from .functions import string as _string

        return _string.position(self._dialect, substring, self)



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
        >>> col.upper().substr(0, 3)      # SUBSTR(UPPER("name"), 1, 3)
        >>> col.length() > 5              # LENGTH("name") > ?
    """

    def _string_op(self, factory_name: str, *args, **kwargs):
        """Call a string factory and tag the result as a string value.

        Args:
            factory_name: Name of the function in ``functions.string``.
            args: Positional arguments forwarded to the factory.
            kwargs: Keyword arguments forwarded to the factory.

        Returns:
            A :class:`~...expression.core.StringValueExpression`.
        """
        from . import functions as _functions

        factory = getattr(_functions, factory_name)
        return factory(self._dialect, self, *args, **kwargs)

    # --- case ---

    def upper(self) -> "StringValueMixin":
        """Upper-case the string. ``UPPER(col)``"""
        return self._string_op("upper")

    def lower(self) -> "StringValueMixin":
        """Lower-case the string. ``LOWER(col)``"""
        return self._string_op("lower")

    def initcap(self) -> "StringValueMixin":
        """Capitalise the first letter of each word. ``INITCAP(col)``"""
        return self._string_op("initcap")

    def reverse(self) -> "StringValueMixin":
        """Reverse the string. ``REVERSE(col)``"""
        return self._string_op("reverse")

    def translate(self, from_chars: str, to_chars: str) -> "StringValueMixin":
        """Replace characters pairwise. ``TRANSLATE(col, from, to)``"""
        return self._string_op("translate", from_chars, to_chars)

    # --- slicing and padding ---

    def substr(self, start: int, length: Optional[int] = None) -> "StringValueMixin":
        """Substring, 1-based. ``SUBSTRING(col FROM start [FOR length])``"""
        return self._string_op("substring", start, length)

    def left(self, n: int) -> "StringValueMixin":
        """First *n* characters. ``LEFT(col, n)``"""
        return self._string_op("left", n)

    def right(self, n: int) -> "StringValueMixin":
        """Last *n* characters. ``RIGHT(col, n)``"""
        return self._string_op("right", n)

    def lpad(self, length: int, pad: Optional[str] = None) -> "StringValueMixin":
        """Left-pad to *length*. ``LPAD(col, length [, pad])``"""
        return self._string_op("lpad", length, pad)

    def rpad(self, length: int, pad: Optional[str] = None) -> "StringValueMixin":
        """Right-pad to *length*. ``RPAD(col, length [, pad])``"""
        return self._string_op("rpad", length, pad)

    def repeat(self, count: int) -> "StringValueMixin":
        """Repeat the string *count* times. ``REPEAT(col, count)``"""
        return self._string_op("repeat", count)

    def overlay(self, replacement: str, start: int, length: Optional[int] = None) -> "StringValueMixin":
        """Overwrite a span. ``OVERLAY(col PLACING replacement FROM start [FOR length])``"""
        return self._string_op("overlay", replacement, start, length)

    # --- search and replace ---

    def replace(self, pattern: str, replacement: str) -> "StringValueMixin":
        """Replace every occurrence. ``REPLACE(col, pattern, replacement)``"""
        return self._string_op("replace", pattern, replacement)

    def position(self, substring: str) -> "IntegerValueExpression":
        """Position of *substring* within the string.

        A legal string operation whose result is a number, so the result is an
        integer value and carries integer operations, not string ones.
        """
        return self._integer_op("position", substring)

    # --- operations that read a string and produce a number ---

    def _integer_op(self, factory_name: str, *args):
        """Call a string factory whose result is an integer.

        Args:
            factory_name: Name of the function in ``functions.string``.
            args: Positional arguments forwarded to the factory.

        Returns:
            An :class:`IntegerValueExpression`.
        """
        from . import functions as _functions

        factory = getattr(_functions, factory_name)
        return factory(self._dialect, self, *args)

    def length(self) -> "IntegerValueExpression":
        """Number of characters. ``LENGTH(expr)``"""
        return self._integer_op("length")

    def ascii(self) -> "IntegerValueExpression":
        """Code of the first character. ``ASCII(expr)``"""
        return self._integer_op("ascii")

    def octet_length(self) -> "IntegerValueExpression":
        """Length in bytes. ``OCTET_LENGTH(expr)``"""
        return self._integer_op("octet_length")

    def bit_length(self) -> "IntegerValueExpression":
        """Length in bits. ``BIT_LENGTH(expr)``"""
        return self._integer_op("bit_length")

    def strpos(self, substring: str) -> "IntegerValueExpression":
        """1-based position of *substring*, or 0. ``STRPOS(expr, substring)``"""
        return self._integer_op("strpos", substring)

    # --- whitespace ---

    def trim(self, chars: Optional[str] = None, direction: str = "BOTH") -> "StringValueMixin":
        """Trim whitespace or *chars*. ``TRIM([direction] [chars] FROM col)``

        Args:
            chars: Characters to trim; ``None`` trims spaces.
            direction: One of ``BOTH`` (default), ``LEADING``, ``TRAILING``.
        """
        return self._string_op("trim", chars=chars, direction=direction)

    # --- combination ---

    def concat(self, *others) -> "StringValueMixin":
        """Concatenate with other values. ``CONCAT(col, ...)``

        Note: SQL ``||`` is not used. Its meaning is dialect-dependent — it is
        logical OR by default in MySQL — so the portable function is the only
        spelling offered here.
        """
        from .functions import string as _string
        from .core import Literal

        operands = [self]
        for other in others:
            operands.append(other if hasattr(other, "to_sql") else Literal(self._dialect, other))
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
        from .core import Literal

        operands = [self]
        for other in others:
            operands.append(
                other if hasattr(other, "to_sql") else Literal(self._dialect, other)
            )
        return _string.concat_op(self._dialect, *operands)

    def coalesce(self, *others) -> "StringValueMixin":
        """First non-null value. ``COALESCE(col, ...)``"""
        from .functions import string as _string
        from .core import Literal

        operands = [self]
        for other in others:
            operands.append(other if hasattr(other, "to_sql") else Literal(self._dialect, other))
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

    def like(self: "SQLValueExpression", pattern: str) -> "SQLPredicate":
        """
        Generate a LIKE predicate for pattern matching (case-sensitive).

        This method enables SQL LIKE operations for pattern matching with wildcards:
        - % matches zero or more characters
        - _ matches a single character

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
        from .predicates import LikePredicate

        return LikePredicate(self._dialect, "LIKE", self, Literal(self._dialect, pattern))

    def ilike(self: "SQLValueExpression", pattern: str) -> "SQLPredicate":
        """
        Generate an ILIKE predicate for case-insensitive pattern matching.

        This method enables SQL ILIKE operations for case-insensitive pattern matching.
        Not all databases support ILIKE, but it's commonly available in PostgreSQL.

        Args:
            pattern: Pattern string with SQL LIKE wildcards

        Returns:
            SQLPredicate representing the ILIKE operation

        Example:
            >>> col = Column(dialect, "email")
            >>> predicate = col.ilike("%@gmail.com")  # Matches Gmail addresses regardless of case
            >>> # Generates: "email ILIKE ?" with params ("%@gmail.com",)
        """
        from .core import Literal
        from .predicates import LikePredicate

        return LikePredicate(self._dialect, "ILIKE", self, Literal(self._dialect, pattern))


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
    >>> expr = col.cast("INTEGER")
    >>> # Generates: CAST("price" AS INTEGER)
    >>> # PostgreSQL generates: "price"::INTEGER
    >>>
    >>> # Chained conversions (each cast nests the previous node)
    >>> expr3 = col.cast("money").cast("numeric").cast("float8")
    >>> # Generates: CAST(CAST(CAST("price" AS money) AS numeric) AS float8)
    >>> # PostgreSQL generates: "price"::money::numeric::float8
    """

    def cast(self: "SQLValueExpression", target_type: str) -> "CastExpression":
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
        # `col.cast("INTEGER").as_("v")` and `col.as_("v").cast("INTEGER")`
        # both render `CAST(col AS INTEGER) AS v`. The original expression
        # is only mutated when it is itself a temporary copy (the as_()
        # convention returns copies), so shared nodes stay untouched.
        alias = getattr(self, "alias", None)
        node = CastExpression(self._dialect, self, target_type, alias=alias)
        if alias is not None and hasattr(self, "alias"):
            self.alias = None
        return node


class DateTimeMixin:
    """Temporal operations available on a value known to hold a date/time.

    Every method here wraps *this* expression in a proper AST node and hands
    rendering to the dialect (``format_extract_expression``,
    ``format_date_trunc_expression``, ``format_datetime_add_expression``, …).
    No SQL is built by this mixin, and the expression nodes it constructs
    already exist — this is a thin, dialect-neutral façade over them.

    The mixin is mixed into :class:`~...expression.column_types.DateTimeColumn`
    only, so a numeric or string column cannot reach these operations.

    Chaining nests like any other expression::

        >>> col = DateTimeColumn(dialect, "created_at")
        >>> col.date_trunc("month")
        >>> # -> DATE_TRUNC('month', "created_at")
        >>> col.date_trunc("day").extract("year")
        >>> # -> EXTRACT(year FROM DATE_TRUNC('day', "created_at"))

    Note:
        ``now()`` / ``current_date()`` / ``current_timestamp()`` are
        deliberately absent: they take no column and belong to the
        ``functions.datetime`` module, not to a column's own surface.
    """

    def _temporal_node(self, node_class, *args, **kwargs):
        """Build *node_class* over this expression, hoisting the alias.

        Mirrors :meth:`TypeCastingMixin.cast`: the alias decorates the
        outermost rendered form, so ``col.as_("d").date_trunc("day")`` and
        ``col.date_trunc("day").as_("d")`` both render the same SQL. The
        receiver is only mutated when it is itself a temporary copy (the
        ``as_()`` convention returns copies).
        """
        alias = getattr(self, "alias", None)
        node = node_class(self._dialect, *args, alias=alias, **kwargs)
        if alias is not None and hasattr(self, "alias"):
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
    :class:`~...expression.advanced_functions.JSONExpression` — the latter is
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

    def _json_path(self, keys, as_text: bool, mode) -> "JSONExpression":
        from .advanced_functions import JSONExpression

        alias = getattr(self, "alias", None)
        node = JSONExpression(
            self._dialect,
            self,
            build_json_path(*keys),
            operation="->>" if as_text else "->",
            alias=alias,
            mode=mode,
        )
        if alias is not None and hasattr(self, "alias"):
            self.alias = None
        return node

    def json_path(self, *keys, mode=None) -> "JSONExpression":
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

    def json_value(self, *keys, mode=None) -> "JSONExpression":
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
