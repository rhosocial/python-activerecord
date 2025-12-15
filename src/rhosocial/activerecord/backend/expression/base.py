# src/rhosocial/activerecord/backend/expression/base.py
"""
Base classes and protocols for SQL expression building blocks.
"""
import abc
from typing import Any, Tuple, Union, List, Generic, TypeVar, Optional, Dict, Protocol
from ..dialect import SQLDialectBase, ExplainOptions

from .operators import BinaryArithmeticExpression, BinaryExpression
from .predicates import (
    IsNullPredicate,
    ComparisonPredicate,
    InPredicate,
    LogicalPredicate,
    BetweenPredicate,
)

T = TypeVar("T")

class ToSQLProtocol(Protocol):
    """
    Protocol for objects that can be converted into a SQL string and a tuple of parameters.

    Security Notice:
    1. For backend developers: Any code involving database interfaces or SQL formatting
       must strictly follow this protocol by separating SQL fragments and parameters
       to prevent SQL injection attacks.
    2. For application developers: When interacting with the database, always pass
       query parameters through the designated parameter mechanisms rather than
       directly concatenating values into SQL strings to prevent SQL injection.
    """
    def to_sql(self) -> Tuple[str, tuple]:
        """
        Converts the object into a SQL string and a tuple of parameters.
        """
        ... # Ellipsis indicates an abstract method in Protocol


# --- Base Classes ---

class BaseExpression(abc.ABC, ToSQLProtocol):
    """
    Abstract base class for any part of a SQL expression. Its main purpose is
    to be converted into a SQL string and a tuple of parameters via `to_sql`.
    """
    def __init__(self, dialect: SQLDialectBase):
        """
        Initializes the base SQL expression with a specific dialect.

        Args:
            dialect: The SQL dialect instance to use for formatting this expression.
        """
        self._dialect = dialect # Store the dialect instance

    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    @abc.abstractmethod
    def to_sql(self) -> Tuple[str, tuple]:
        """
        Converts the expression into a SQL string and a tuple of parameters,
        using the dialect bound at initialization.
        """
        raise NotImplementedError

    def is_null(self) -> "IsNullPredicate":
        # Deferred import to avoid circular dependency
        from .predicates import IsNullPredicate
        return IsNullPredicate(self.dialect, self)
    def is_not_null(self) -> "IsNullPredicate":
        from .predicates import IsNullPredicate
        return IsNullPredicate(self.dialect, self, is_not=True)


class SQLValueExpression(BaseExpression):
    """
    Abstract base class for SQL expressions that return a non-boolean value
    (e.g., integer, string, date).
    Provides arithmetic and comparison operators, as well as set membership operators.
    """
    def __init__(self, dialect: SQLDialectBase):
        """
        Initializes the base SQL value expression with a specific dialect.
        """
        super().__init__(dialect)

    # Arithmetic operators (will return BinaryArithmeticExpression)
    def __add__(self, other: Union["SQLValueExpression", Any]) -> "BinaryArithmeticExpression":
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "+", self, other_expr)
    
    def __sub__(self, other: Union["SQLValueExpression", Any]) -> "BinaryArithmeticExpression":
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "-", self, other_expr)
    
    def __mul__(self, other: Union["SQLValueExpression", Any]) -> "BinaryArithmeticExpression":
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "*", self, other_expr)
    
    def __truediv__(self, other: Union["SQLValueExpression", Any]) -> "BinaryArithmeticExpression":
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "/", self, other_expr)
    
    def __mod__(self, other: Union["SQLValueExpression", Any]) -> "BinaryArithmeticExpression":
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "%", self, other_expr)

    # Comparison operators (will return ComparisonPredicate)
    def __eq__(self, other: Union["SQLValueExpression", Any]) -> "ComparisonPredicate":  # type: ignore[override]
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "=", self, other_expr)
    
    def __ne__(self, other: Union["SQLValueExpression", Any]) -> "ComparisonPredicate":  # type: ignore[override]
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "!=", self, other_expr)
    
    def __gt__(self, other: Union["SQLValueExpression", Any]) -> "ComparisonPredicate":
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, ">", self, other_expr)
    
    def __ge__(self, other: Union["SQLValueExpression", Any]) -> "ComparisonPredicate":
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, ">=", self, other_expr)
    
    def __lt__(self, other: Union["SQLValueExpression", Any]) -> "ComparisonPredicate":
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "<", self, other_expr)
    
    def __le__(self, other: Union["SQLValueExpression", Any]) -> "ComparisonPredicate":
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "<=", self, other_expr)
    
    # Set membership operators (will return InPredicate or LogicalPredicate)
    def in_(self, values: list) -> "InPredicate":
        return InPredicate(self.dialect, self, Literal(self.dialect, tuple(values)))
    
    def not_in(self, values: list) -> "LogicalPredicate": 
        """
        NOT (in_ predicate) - Returns a LogicalPredicate wrapping an InPredicate.
        
        Note: The InPredicate is not a direct SQLPredicate subclass in the current design,
        but it's compatible for use with LogicalPredicate which expects predicates that
        implement the to_sql() protocol. This is by design to support nested predicate logic.
        """
        return LogicalPredicate(self.dialect, "NOT", InPredicate(self.dialect, self, Literal(self.dialect, tuple(values))))  # type: ignore[arg-type]


class SQLPredicate(BaseExpression):
    """
    Abstract base class for SQL expressions that return a boolean value (predicates).
    Provides logical operators.
    """
    def __init__(self, dialect: "SQLDialectBase"):
        """
        Initializes the base SQL predicate with a specific dialect.
        """
        super().__init__(dialect)

    # Logical operators (will return LogicalPredicate)
    def __and__(self, other: "SQLPredicate") -> "LogicalPredicate":
        return LogicalPredicate(self.dialect, "AND", self, other)
    
    def __or__(self, other: "SQLPredicate") -> "LogicalPredicate":
        return LogicalPredicate(self.dialect, "OR", self, other)
    
    def __invert__(self) -> "LogicalPredicate":
        return LogicalPredicate(self.dialect, "NOT", self)


class ComparableExpression(SQLValueExpression):
    """
    Abstract base class for SQL expressions that represent a comparable type.
    Provides comparison-specific operations like BETWEEN.
    """
    def __init__(self, dialect: SQLDialectBase):
        """
        Initializes the base Comparable SQL expression with a specific dialect.

        Args:
            dialect: The SQL dialect instance to use for formatting this expression.
        """
        super().__init__(dialect)
    def between(self, low: Any, high: Any) -> "BetweenPredicate":
        return BetweenPredicate(self.dialect, self, Literal(self.dialect, low), Literal(self.dialect, high))


class Literal(SQLValueExpression): 
    """Represents a literal value in a SQL query."""
    def __init__(self, dialect: SQLDialectBase, value: Any):
        """
        Initializes a Literal SQL expression.

        Args:
            dialect: The SQL dialect to use for formatting this expression.
            value: The literal value to be represented in SQL.
        """
        super().__init__(dialect)
        self.value = value
    def to_sql(self) -> Tuple[str, tuple]:
        if isinstance(self.value, (list, tuple, set)):
            if not self.value: return "()", ()
            return f"({', '.join([self.dialect.get_placeholder()] * len(self.value))})", tuple(self.value)
        return self.dialect.get_placeholder(), (self.value,)
    def __repr__(self) -> str: return f"Literal({self.value!r})"


class StringExpression(SQLValueExpression):
    """
    Abstract base class for SQL expressions that represent a string type.
    Provides string-specific operations like LIKE and ILIKE.
    """
    def __init__(self, dialect: SQLDialectBase):
        """
        Initializes the base String SQL expression with a specific dialect.

        Args:
            dialect: The SQL dialect instance to use for formatting this expression.
        """
        super().__init__(dialect)
    def like(self, pattern: str) -> "BinaryExpression":
        return BinaryExpression(self.dialect, "LIKE", self, Literal(self.dialect, pattern))

    def ilike(self, pattern: str) -> "BinaryExpression":
        return BinaryExpression(self.dialect, "ILIKE", self, Literal(self.dialect, pattern))