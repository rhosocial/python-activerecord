# src/rhosocial/activerecord/backend/expression/predicates.py
"""
SQL predicate expressions (e.g., WHERE clause conditions).
"""
from typing import Tuple, Any, TYPE_CHECKING
from ..dialect import SQLDialectBase

if TYPE_CHECKING:
    from .base import SQLPredicate, BaseExpression, SQLValueExpression, StringExpression


class ComparisonPredicate:
    """Represents a comparison predicate (e.g., expr1 = expr2, expr1 > expr2)."""
    def __init__(self, dialect: SQLDialectBase, op: str, left: "SQLValueExpression", right: "SQLValueExpression"):
        """
        Initializes a comparison predicate.

        Args:
            dialect: The SQL dialect instance.
            op: The comparison operator (e.g., "=", ">", "<").
            left: The left-hand side expression.
            right: The right-hand side expression.
        """
        self._dialect = dialect
        self.op = op
        self.left = left
        self.right = right
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def to_sql(self) -> Tuple[str, tuple]:
        left_sql, left_params = self.left.to_sql()
        right_sql, right_params = self.right.to_sql()

        return self.dialect.format_comparison_predicate(self.op, left_sql, right_sql, left_params, right_params)


class LogicalPredicate:
    """Represents a logical predicate (e.g., pred1 AND pred2, NOT pred)."""
    def __init__(self, dialect: SQLDialectBase, op: str, *predicates: "SQLPredicate"):
        """
        Initializes a logical predicate.

        Args:
            dialect: The SQL dialect instance.
            op: The logical operator (e.g., "AND", "OR", "NOT").
            *predicates: Positional arguments representing the predicates to combine.
        """
        self._dialect = dialect
        self.op = op
        self.predicates = list(predicates)
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def to_sql(self) -> Tuple[str, tuple]:
        predicates_sql_and_params = []
        for pred in self.predicates:
            pred_sql, pred_params = pred.to_sql()
            predicates_sql_and_params.append((pred_sql, pred_params))

        return self.dialect.format_logical_predicate(self.op, *predicates_sql_and_params)


class LikePredicate:
    """Represents a LIKE or ILIKE predicate."""
    def __init__(self, dialect: SQLDialectBase, op: str, expr: "StringExpression", pattern: "SQLValueExpression"):
        """
        Initializes a LIKE/ILIKE predicate.

        Args:
            dialect: The SQL dialect instance.
            op: The LIKE operator ("LIKE" or "ILIKE").
            expr: The expression to match against.
            pattern: The pattern expression.
        """
        self._dialect = dialect
        self.op = op
        self.expr = expr
        self.pattern = pattern
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()
        pattern_sql, pattern_params = self.pattern.to_sql()

        return self.dialect.format_like_predicate(self.op, expr_sql, pattern_sql, expr_params, pattern_params)


class InPredicate:
    """Represents an IN predicate (e.g., expr IN (val1, val2) or expr IN (subquery))."""
    def __init__(self, dialect: SQLDialectBase, expr: "SQLValueExpression", values: "BaseExpression"):
        """
        Initializes an IN predicate.

        Args:
            dialect: The SQL dialect instance.
            expr: The expression to check for inclusion.
            values: The set of values or a subquery to check against.
        """
        self._dialect = dialect
        self.expr = expr
        self.values = values
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()
        values_sql, values_params = self.values.to_sql()

        return self.dialect.format_in_predicate(expr_sql, values_sql, expr_params, values_params)


class BetweenPredicate:
    """Represents a BETWEEN predicate (e.g., expr BETWEEN low AND high)."""
    def __init__(self, dialect: SQLDialectBase, expr: "BaseExpression", low: "BaseExpression", high: "BaseExpression"):
        """
        Initializes a BETWEEN predicate.

        Args:
            dialect: The SQL dialect instance.
            expr: The expression to check.
            low: The lower bound of the range.
            high: The upper bound of the range.
        """
        self._dialect = dialect
        self.expr = expr
        self.low = low
        self.high = high
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()
        low_sql, low_params = self.low.to_sql()
        high_sql, high_params = self.high.to_sql()

        return self.dialect.format_between_predicate(expr_sql, low_sql, high_sql, expr_params, low_params, high_params)


class IsNullPredicate:
    """Represents an IS NULL or IS NOT NULL predicate."""
    def __init__(self, dialect: SQLDialectBase, expr: "BaseExpression", is_not: bool = False):
        """
        Initializes an IS NULL/IS NOT NULL predicate.

        Args:
            dialect: The SQL dialect instance.
            expr: The expression to check for NULLity.
            is_not: If True, formats as IS NOT NULL.
        """
        self._dialect = dialect
        self.expr = expr
        self.is_not = is_not
    
    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def to_sql(self) -> Tuple[str, tuple]:
        expr_sql, expr_params = self.expr.to_sql()

        return self.dialect.format_is_null_predicate(expr_sql, self.is_not, expr_params)
