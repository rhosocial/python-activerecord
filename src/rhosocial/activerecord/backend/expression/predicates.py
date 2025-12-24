# src/rhosocial/activerecord/backend/expression/predicates.py
"""
Concrete implementations of SQL predicate expressions (e.g., WHERE clause conditions).
"""
from typing import Tuple, TYPE_CHECKING

from . import bases
from . import mixins
from .core import Literal

if TYPE_CHECKING:  # pragma: no cover
    from .bases import SQLValueExpression
    from ..dialect import SQLDialectBase


class ComparisonPredicate(bases.SQLPredicate):
    """Represents a comparison predicate (e.g., expr1 = expr2, expr1 > expr2)."""
    def __init__(self, dialect: "SQLDialectBase", op: str, left: "SQLValueExpression", right: "SQLValueExpression"):
        super().__init__(dialect)
        self.op = op
        self.left = left
        self.right = right

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to the dialect's format_comparison_predicate method with the whole expression
        return self.dialect.format_comparison_predicate(self.op, self.left, self.right)


class LogicalPredicate(bases.SQLPredicate):
    """Represents a logical predicate (e.g., pred1 AND pred2, NOT pred)."""
    def __init__(self, dialect: "SQLDialectBase", op: str, *predicates: "bases.SQLPredicate"):
        super().__init__(dialect)
        self.op = op
        self.predicates = list(predicates)

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to the dialect's format_logical_predicate method with the whole expression
        return self.dialect.format_logical_predicate(self.op, *self.predicates)


class LikePredicate(bases.SQLPredicate):
    """Represents a LIKE or ILIKE predicate."""
    def __init__(self, dialect: "SQLDialectBase", op: str, expr: "SQLValueExpression", pattern: "SQLValueExpression"):
        super().__init__(dialect)
        self.op = op
        self.expr = expr
        self.pattern = pattern

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to the dialect's format_like_predicate method with the whole expression
        return self.dialect.format_like_predicate(self.op, self.expr, self.pattern)


class InPredicate(bases.SQLPredicate):
    """Represents an IN predicate (e.g., expr IN (val1, val2) or expr IN (subquery))."""
    def __init__(self, dialect: "SQLDialectBase", expr: "SQLValueExpression", values: "bases.BaseExpression"):
        super().__init__(dialect)
        self.expr = expr
        self.values = values

    def to_sql(self) -> Tuple[str, tuple]:
        # Check if values is a Literal containing a collection and delegate to dialect
        if isinstance(self.values, Literal) and isinstance(self.values.value, (list, tuple, set)):
            # Delegate to dialect's format_in_predicate_with_literal_values with the whole expression
            return self.dialect.format_in_predicate_with_literal_values(self.expr, self.values.value)
        else:
            # Delegate to dialect's format_in_predicate with the whole expression
            return self.dialect.format_in_predicate(self.expr, self.values)


class BetweenPredicate(bases.SQLPredicate):
    """Represents a BETWEEN predicate (e.g., expr BETWEEN low AND high)."""
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", low: "bases.BaseExpression", high: "bases.BaseExpression"):
        super().__init__(dialect)
        self.expr = expr
        self.low = low
        self.high = high

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to the dialect's format_between_predicate method with the whole expression
        return self.dialect.format_between_predicate(self.expr, self.low, self.high)


class IsNullPredicate(bases.SQLPredicate):
    """Represents an IS NULL or IS NOT NULL predicate."""
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", is_not: bool = False):
        super().__init__(dialect)
        self.expr = expr
        self.is_not = is_not

    def to_sql(self) -> Tuple[str, tuple]:
        # Delegate to the dialect's format_is_null_predicate method with the whole expression
        return self.dialect.format_is_null_predicate(self.expr, self.is_not)
