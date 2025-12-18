# src/rhosocial/activerecord/backend/expression_/predicates.py
"""
Concrete implementations of SQL predicate expressions (e.g., WHERE clause conditions).
"""
from typing import Tuple, Any, TYPE_CHECKING

from . import bases
from . import mixins
from .core import Literal

# if TYPE_CHECKING:
#     from .bases import BaseExpression, SQLValueExpression
#     from ..dialect import SQLDialectBase


class ComparisonPredicate(mixins.LogicalMixin, bases.SQLPredicate):
    """Represents a comparison predicate (e.g., expr1 = expr2, expr1 > expr2)."""
    def __init__(self, dialect: "SQLDialectBase", op: str, left: "SQLValueExpression", right: "SQLValueExpression"):
        super().__init__(dialect)
        self.op = op
        self.left = left
        self.right = right

    def to_sql(self) -> Tuple[str, tuple]:
        left_sql, left_params = self.left.to_sql()
        right_sql, right_params = self.right.to_sql()
        return self.dialect.format_comparison_predicate(self.op, left_sql, right_sql, left_params, right_params)


class LogicalPredicate(mixins.LogicalMixin, bases.SQLPredicate):
    """Represents a logical predicate (e.g., pred1 AND pred2, NOT pred)."""
    def __init__(self, dialect: "SQLDialectBase", op: str, *predicates: "bases.SQLPredicate"):
        super().__init__(dialect)
        self.op = op
        self.predicates = list(predicates)

    def to_sql(self) -> Tuple[str, tuple]:
        predicates_sql_and_params = [(p.to_sql()) for p in self.predicates]
        return self.dialect.format_logical_predicate(self.op, *predicates_sql_and_params)


class LikePredicate(mixins.LogicalMixin, bases.SQLPredicate):
    """Represents a LIKE or ILIKE predicate."""
    def __init__(self, dialect: "SQLDialectBase", op: str, expr: "SQLValueExpression", pattern: "SQLValueExpression"):
        super().__init__(dialect)
        self.op = op
        self.expr = expr
        self.pattern = pattern

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()
        pattern_sql, pattern_params = self.pattern.to_sql()
        return self.dialect.format_like_predicate(self.op, expr_sql, pattern_sql, expr_params, pattern_params)


class InPredicate(mixins.LogicalMixin, bases.SQLPredicate):
    """Represents an IN predicate (e.g., expr IN (val1, val2) or expr IN (subquery))."""
    def __init__(self, dialect: "SQLDialectBase", expr: "SQLValueExpression", values: "bases.BaseExpression"):
        super().__init__(dialect)
        self.expr = expr
        self.values = values

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()
        
        # Check if values is a Literal containing a collection and expand it
        if isinstance(self.values, Literal) and isinstance(self.values.value, (list, tuple, set)):
            if not self.values.value: # Handle empty list case for IN ()
                values_sql = "()"
                values_params = ()
            else:
                placeholders = ", ".join([self.dialect.get_placeholder()] * len(self.values.value))
                values_sql = f"({placeholders})"
                values_params = tuple(self.values.value)
        else:
            values_sql, values_params = self.values.to_sql()
            
        return self.dialect.format_in_predicate(expr_sql, values_sql, expr_params, values_params)


class BetweenPredicate(mixins.LogicalMixin, bases.SQLPredicate):
    """Represents a BETWEEN predicate (e.g., expr BETWEEN low AND high)."""
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", low: "bases.BaseExpression", high: "bases.BaseExpression"):
        super().__init__(dialect)
        self.expr = expr
        self.low = low
        self.high = high

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()
        low_sql, low_params = self.low.to_sql()
        high_sql, high_params = self.high.to_sql()
        return self.dialect.format_between_predicate(expr_sql, low_sql, high_sql, expr_params, low_params, high_params)


class IsNullPredicate(mixins.LogicalMixin, bases.SQLPredicate):
    """Represents an IS NULL or IS NOT NULL predicate."""
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", is_not: bool = False):
        super().__init__(dialect)
        self.expr = expr
        self.is_not = is_not

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()
        return self.dialect.format_is_null_predicate(expr_sql, self.is_not, expr_params)
