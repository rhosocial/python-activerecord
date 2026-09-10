# src/rhosocial/activerecord/backend/dialect/mixins/predicate.py
from typing import Any, List, Tuple, TYPE_CHECKING

from ...expression import bases
from ...expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.core import Literal


class PredicateMixin:
    """Mixin for SQL predicate formatting.

    Formatting functions receive the expression instance only; every value
    they need was collected at expression construction time.
    """

    def format_comparison_predicate(self, expr) -> Tuple[str, Tuple]:
        from ...expression.statements import QueryExpression

        left_sql, left_params = expr.left.to_sql()
        right_sql, right_params = expr.right.to_sql()
        if isinstance(expr.right, QueryExpression):
            right_sql = f"({right_sql})"
        return f"{left_sql} {expr.op} {right_sql}", left_params + right_params

    def format_logical_predicate(self, expr) -> Tuple[str, Tuple]:
        if expr.op.upper() == "NOT" and len(expr.predicates) == 1:
            sql, params = expr.predicates[0].to_sql()
            return f"NOT ({sql})", params
        parts = []
        all_params: List[Any] = []
        for predicate in expr.predicates:
            sql, params = predicate.to_sql()
            parts.append(sql)
            all_params.extend(params)
        return f" {expr.op} ".join(parts), tuple(all_params)

    def format_in_predicate(self, expr) -> Tuple[str, Tuple]:
        from ...expression.core import Literal

        expr_sql, expr_params = expr.expr.to_sql()
        # A Literal wrapping a collection renders as a value list; anything
        # else (e.g. a subquery) renders through its own to_sql().
        if isinstance(expr.values, Literal) and isinstance(expr.values.value, (list, tuple, set)):
            return self._format_in_value_list(expr_sql, expr_params, expr.values.value)
        values_sql, values_params = expr.values.to_sql()
        return f"{expr_sql} IN {values_sql}", expr_params + values_params

    def _format_in_value_list(self, expr_sql: str, expr_params: tuple, values) -> Tuple[str, Tuple]:
        """Render ``IN (…)"`` for a collection of bind values."""
        if not values:
            values_sql = "()"
            values_params: tuple = ()
        else:
            placeholders = ", ".join([self.get_parameter_placeholder()] * len(values))
            values_sql = f"({placeholders})"
            values_params = tuple(values)
        return f"{expr_sql} IN {values_sql}", expr_params + values_params

    def format_between_predicate(self, expr) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.expr.to_sql()
        low_sql, low_params = expr.low.to_sql()
        high_sql, high_params = expr.high.to_sql()
        return f"{expr_sql} BETWEEN {low_sql} AND {high_sql}", expr_params + low_params + high_params

    def format_is_null_predicate(self, expr) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.expr.to_sql()
        not_str = " NOT" if expr.is_not else ""
        return f"{expr_sql} IS{not_str} NULL", expr_params

    def format_is_boolean_predicate(self, expr) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.expr.to_sql()
        not_str = " NOT" if expr.is_not else ""
        bool_str = "TRUE" if expr.value else "FALSE"
        return f"{expr_sql} IS{not_str} {bool_str}", expr_params

    def format_exists_expression(self, expr) -> Tuple[str, Tuple]:
        subquery_sql, subquery_params = expr.subquery.to_sql()
        exists_clause = "NOT EXISTS" if expr.is_not else "EXISTS"
        return f"{exists_clause} {subquery_sql}", subquery_params

    def format_any_expression(self, expr) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.expr.to_sql()
        array_expr = expr.array_expr
        if hasattr(array_expr, "value") and isinstance(array_expr.value, (list, tuple)):
            array_sql = self.get_parameter_placeholder()
            array_params = (tuple(array_expr.value),)
        else:
            array_sql, array_params = array_expr.to_sql()
        return f"({expr_sql} {expr.op} ANY{array_sql})", tuple(list(expr_params) + list(array_params))

    def format_all_expression(self, expr) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.expr.to_sql()
        array_expr = expr.array_expr
        if hasattr(array_expr, "value") and isinstance(array_expr.value, (list, tuple)):
            array_sql = self.get_parameter_placeholder()
            array_params = (tuple(array_expr.value),)
        else:
            array_sql, array_params = array_expr.to_sql()
        return f"({expr_sql} {expr.op} ALL{array_sql})", tuple(list(expr_params) + list(array_params))

    def format_like_predicate(self, expr) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.expr.to_sql()
        pattern_sql, pattern_params = expr.pattern.to_sql()
        return f"{expr_sql} {expr.op} {pattern_sql}", expr_params + pattern_params
