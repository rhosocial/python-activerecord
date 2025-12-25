# src/rhosocial/activerecord/backend/expression/mixins.py
"""
Mixin classes that provide operator-overloading capabilities to expression classes.

This module uses deferred local imports within its methods to prevent
circular dependency issues, as it needs to instantiate concrete expression
classes (like `ComparisonPredicate`) which in turn depend on the base classes.
"""
from typing import Any, Union, List, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .bases import SQLValueExpression, SQLPredicate
    from .core import Literal
    from .predicates import ComparisonPredicate, InPredicate, IsNullPredicate, LogicalPredicate, BetweenPredicate


class ComparisonMixin:
    """Provides comparison operators (==, !=, >, <, etc.) and other boolean-producing methods."""

    def __eq__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import SQLValueExpression
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "=", self, other_expr)

    def __ne__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import SQLValueExpression
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "!=", self, other_expr)

    def __gt__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import SQLValueExpression
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, ">", self, other_expr)

    def __ge__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import SQLValueExpression
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, ">=", self, other_expr)

    def __lt__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import SQLValueExpression
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "<", self, other_expr)

    def __le__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLPredicate":
        from .core import Literal
        from .predicates import ComparisonPredicate
        from .bases import SQLValueExpression
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return ComparisonPredicate(self.dialect, "<=", self, other_expr)

    def is_null(self: "SQLValueExpression") -> "SQLPredicate":
        from .predicates import IsNullPredicate
        return IsNullPredicate(self.dialect, self)

    def is_not_null(self: "SQLValueExpression") -> "SQLPredicate":
        from .predicates import IsNullPredicate
        return IsNullPredicate(self.dialect, self, is_not=True)

    def in_(self: "SQLValueExpression", values: List[Any]) -> "SQLPredicate":
        from .core import Literal
        from .predicates import InPredicate
        return InPredicate(self.dialect, self, Literal(self.dialect, tuple(values)))

    def not_in(self: "SQLValueExpression", values: List[Any]) -> "SQLPredicate":
        from .core import Literal
        from .predicates import InPredicate, LogicalPredicate
        return LogicalPredicate(self.dialect, "NOT", InPredicate(self.dialect, self, Literal(self.dialect, tuple(values))))
    
    def between(self: "SQLValueExpression", low: Any, high: Any) -> "SQLPredicate":
        from .core import Literal
        from .predicates import BetweenPredicate
        return BetweenPredicate(self.dialect, self, Literal(self.dialect, low), Literal(self.dialect, high))

class ArithmeticMixin:
    """Provides arithmetic operators (+, -, *, /, %)."""

    def __add__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLValueExpression":
        from .core import Literal
        from .operators import BinaryArithmeticExpression
        from .bases import SQLValueExpression
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "+", self, other_expr)

    def __sub__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLValueExpression":
        from .core import Literal
        from .operators import BinaryArithmeticExpression
        from .bases import SQLValueExpression
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "-", self, other_expr)

    def __mul__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLValueExpression":
        from .core import Literal
        from .operators import BinaryArithmeticExpression
        from .bases import SQLValueExpression
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "*", self, other_expr)

    def __truediv__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLValueExpression":
        from .core import Literal
        from .operators import BinaryArithmeticExpression
        from .bases import SQLValueExpression
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "/", self, other_expr)

    def __mod__(self: "SQLValueExpression", other: Union["SQLValueExpression", Any]) -> "SQLValueExpression":
        from .core import Literal
        from .operators import BinaryArithmeticExpression
        from .bases import SQLValueExpression
        other_expr = other if isinstance(other, SQLValueExpression) else Literal(self.dialect, other)
        return BinaryArithmeticExpression(self.dialect, "%", self, other_expr)


class LogicalMixin:
    """Provides logical operators (&, |, ~)."""

    def __and__(self: "SQLPredicate", other: "SQLPredicate") -> "SQLPredicate":
        from .predicates import LogicalPredicate
        return LogicalPredicate(self.dialect, "AND", self, other)

    def __or__(self: "SQLPredicate", other: "SQLPredicate") -> "SQLPredicate":
        from .predicates import LogicalPredicate
        return LogicalPredicate(self.dialect, "OR", self, other)

    def __invert__(self: "SQLPredicate") -> "SQLPredicate":
        from .predicates import LogicalPredicate
        return LogicalPredicate(self.dialect, "NOT", self)


class StringMixin:
    """Provides string-specific operations like LIKE and ILIKE."""

    def like(self: "SQLValueExpression", pattern: str) -> "SQLPredicate":
        from .core import Literal
        from .predicates import LikePredicate
        return LikePredicate(self.dialect, "LIKE", self, Literal(self.dialect, pattern))

    def ilike(self: "SQLValueExpression", pattern: str) -> "SQLPredicate":
        from .core import Literal
        from .predicates import LikePredicate
        return LikePredicate(self.dialect, "ILIKE", self, Literal(self.dialect, pattern))
