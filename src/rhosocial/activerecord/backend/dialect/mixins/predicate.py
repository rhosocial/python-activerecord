# src/rhosocial/activerecord/backend/dialect/mixins/predicate.py
from typing import Any, List, Tuple, TYPE_CHECKING

from ...expression import bases
from ...expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    pass


class PredicateMixin:
    """Mixin for SQL predicate formatting."""

    def format_comparison_predicate(
        self, op: str, left: "BaseExpression", right: "BaseExpression"
    ) -> Tuple[str, Tuple]:
        from ...expression.statements import QueryExpression
        left_sql, left_params = left.to_sql()
        right_sql, right_params = right.to_sql()
        if isinstance(right, QueryExpression):
            right_sql = f"({right_sql})"
        return f"{left_sql} {op} {right_sql}", left_params + right_params

    def format_logical_predicate(self, op: str, *predicates: "bases.SQLPredicate") -> Tuple[str, Tuple]:
        if op.upper() == "NOT" and len(predicates) == 1:
            sql, params = predicates[0].to_sql()
            return f"NOT ({sql})", params
        parts = []
        all_params: List[Any] = []
        for predicate in predicates:
            sql, params = predicate.to_sql()
            parts.append(sql)
            all_params.extend(params)
        return f" {op} ".join(parts), tuple(all_params)

    def format_in_predicate(self, expr: "BaseExpression", values: "BaseExpression") -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.to_sql()
        values_sql, values_params = values.to_sql()
        return f"{expr_sql} IN {values_sql}", expr_params + values_params

    def format_in_predicate_with_literal_values(
        self, expr: "BaseExpression", literal_values: tuple
    ) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.to_sql()
        if not literal_values:
            values_sql = "()"
            values_params: tuple = ()
        else:
            placeholders = ", ".join([self.get_parameter_placeholder()] * len(literal_values))
            values_sql = f"({placeholders})"
            values_params = tuple(literal_values)
        return f"{expr_sql} IN {values_sql}", expr_params + values_params

    def format_between_predicate(
        self, expr: "BaseExpression", low: "BaseExpression", high: "BaseExpression"
    ) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.to_sql()
        low_sql, low_params = low.to_sql()
        high_sql, high_params = high.to_sql()
        return f"{expr_sql} BETWEEN {low_sql} AND {high_sql}", expr_params + low_params + high_params

    def format_is_null_predicate(self, expr: "BaseExpression", is_not: bool) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.to_sql()
        not_str = " NOT" if is_not else ""
        return f"{expr_sql} IS{not_str} NULL", expr_params

    def format_is_boolean_predicate(self, expr: "BaseExpression", value: bool, is_not: bool) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.to_sql()
        not_str = " NOT" if is_not else ""
        bool_str = "TRUE" if value else "FALSE"
        return f"{expr_sql} IS{not_str} {bool_str}", expr_params

    def format_exists_expression(self, subquery: "BaseExpression", is_not: bool) -> Tuple[str, Tuple]:
        subquery_sql, subquery_params = subquery.to_sql()
        exists_clause = "NOT EXISTS" if is_not else "EXISTS"
        return f"{exists_clause} {subquery_sql}", subquery_params

    def format_any_expression(
        self, expr: "BaseExpression", op: str, array_expr: "BaseExpression"
    ) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.to_sql()
        if hasattr(array_expr, "value") and isinstance(array_expr.value, (list, tuple)):
            array_sql = self.get_parameter_placeholder()
            array_params = (tuple(array_expr.value),)
        else:
            array_sql, array_params = array_expr.to_sql()
        return f"({expr_sql} {op} ANY{array_sql})", tuple(list(expr_params) + list(array_params))

    def format_all_expression(
        self, expr: "BaseExpression", op: str, array_expr: "BaseExpression"
    ) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.to_sql()
        if hasattr(array_expr, "value") and isinstance(array_expr.value, (list, tuple)):
            array_sql = self.get_parameter_placeholder()
            array_params = (tuple(array_expr.value),)
        else:
            array_sql, array_params = array_expr.to_sql()
        return f"({expr_sql} {op} ALL{array_sql})", tuple(list(expr_params) + list(array_params))

    def format_like_predicate(
        self, op: str, expr: "BaseExpression", pattern: "BaseExpression"
    ) -> Tuple[str, Tuple]:
        expr_sql, expr_params = expr.to_sql()
        pattern_sql, pattern_params = pattern.to_sql()
        return f"{expr_sql} {op} {pattern_sql}", expr_params + pattern_params
