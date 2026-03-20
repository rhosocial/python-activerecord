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
from typing import Any, Union, List, TYPE_CHECKING, TypeVar

if TYPE_CHECKING:  # pragma: no cover
    from .bases import SQLValueExpression, SQLPredicate
    from .core import Literal
    from .predicates import ComparisonPredicate, InPredicate, IsNullPredicate, IsBooleanPredicate, LogicalPredicate, BetweenPredicate

T = TypeVar('T')


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
            Self with the alias applied, enabling method chaining

        Example:
            >>> col = Column(dialect, "first_name").as_("fname")
            >>> # When used in a query, this will generate: "first_name AS fname"
        """
        self.alias = alias
        return self


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
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "=", self, other_expr)

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
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "!=", self, other_expr)

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
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, ">", self, other_expr)

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
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, ">=", self, other_expr)

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
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "<", self, other_expr)

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
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "<=", self, other_expr)

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
        return IsNullPredicate(self.dialect, self)

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
        return IsNullPredicate(self.dialect, self, is_not=True)

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
        return IsBooleanPredicate(self.dialect, self, value=True, is_not=False)

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
        return IsBooleanPredicate(self.dialect, self, value=True, is_not=True)

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
        return IsBooleanPredicate(self.dialect, self, value=False, is_not=False)

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
        return IsBooleanPredicate(self.dialect, self, value=False, is_not=True)

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
        return InPredicate(self.dialect, self, Literal(self.dialect, tuple(values)))

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
        return LogicalPredicate(self.dialect, "NOT", InPredicate(self.dialect, self, Literal(self.dialect, tuple(values))))

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
        return BetweenPredicate(self.dialect, self, Literal(self.dialect, low), Literal(self.dialect, high))

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
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "+", self, other_expr)

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
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "-", self, other_expr)

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
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "*", self, other_expr)

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
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "/", self, other_expr)

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
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "%", self, other_expr)


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
        return LogicalPredicate(self.dialect, "AND", self, other)

    def __or__(self: "SQLPredicate", other: "SQLPredicate") -> "SQLPredicate":
        """
        Implement the logical OR operator (|) to generate SQL logical predicate.

        Args:
            other: Right operand, must be another SQLPredicate

        Returns:
            SQLPredicate representing the logical OR operation
        """
        from .predicates import LogicalPredicate
        return LogicalPredicate(self.dialect, "OR", self, other)

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
        return LogicalPredicate(self.dialect, "NOT", self)


class StringMixin:
    """
    Provides string-specific operations like LIKE and ILIKE for SQL expressions.

    This mixin adds string pattern matching capabilities to expressions, enabling
    SQL LIKE and ILIKE operations for pattern matching.

    Example:
        >>> col = Column(dialect, "name")
        >>> # Pattern matching
        >>> starts_with_a = col.like("A%")  # Generates: "name LIKE ?" with params ("A%",)
        >>> contains_substring = col.ilike("%hello%")  # Generates: "name ILIKE ?" with params ("%hello%",)
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
        return LikePredicate(self.dialect, "LIKE", self, Literal(self.dialect, pattern))

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
        return LikePredicate(self.dialect, "ILIKE", self, Literal(self.dialect, pattern))


class TypeCastingMixin:
    """Provides type casting capability to SQL value expressions.

    This mixin enables expressions to be cast to different SQL types using
    method chaining. Each call to cast() appends a target type to the
    _cast_types list, which is processed during to_sql() generation.

    The type conversions are applied in order, with the last conversion
    being the outermost CAST. This follows SQL standard nested type casting.

    Example:
    >>> col = Column(dialect, "price")
    >>> expr = col.cast("INTEGER")
    >>> # Generates: CAST("price" AS INTEGER)
    >>> # PostgreSQL generates: "price"::INTEGER
    >>>
    >>> # Chained conversions (each cast is nested)
    >>> col3 = Column(dialect, "amount")
    >>> expr3 = col3.cast("money").cast("numeric").cast("float8")
    >>> # Generates: CAST(CAST(CAST("amount" AS money) AS numeric) AS float8)
    >>> # PostgreSQL generates: "amount"::money::numeric::float8
    """

    @property
    def cast_types(self: "SQLValueExpression") -> List[str]:
        """Get the list of target types for casting."""
        return self._cast_types

    def cast(self: "SQLValueExpression", target_type: str) -> "SQLValueExpression":
        """Append a type cast to this expression.

        Appends the target type to the _cast_types list. Multiple calls
        result in nested type conversions. The actual CAST SQL is generated
        during to_sql() by the dialect's format_cast_expression method.

        Args:
            target_type: Target SQL type name (e.g., 'INTEGER', 'VARCHAR(100)',
            'NUMERIC(10,2)'). Type modifiers should be included in the
            type string.

        Returns:
            Self with the type cast appended, enabling method chaining.

        Example:
        >>> col = Column(dialect, "name")
        >>> expr = col.cast("VARCHAR(100)")
        >>> # Generates: CAST("name" AS VARCHAR(100))
        >>>
        >>> # Chained conversions
        >>> col2 = Column(dialect, "value")
        >>> expr2 = col2.cast("money").cast("numeric")
        >>> # Generates: CAST(CAST("value" AS money) AS numeric)

        Note:
        The actual SQL syntax is determined by the dialect's
        format_cast_expression method. PostgreSQL uses expr::type syntax,
        while other databases use CAST(expr AS type) syntax.
        """
        self._cast_types.append(target_type)
        return self
