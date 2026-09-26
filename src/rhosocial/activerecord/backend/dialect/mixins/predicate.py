# src/rhosocial/activerecord/backend/dialect/mixins/predicate.py
"""Predicate formatting helpers for the SQL dialect layer.

Renders comparison, logical, membership, null/boolean, existence, quantified,
and pattern predicates into ``(sql, params)`` tuples.
"""
from typing import Any, List, Tuple, TYPE_CHECKING

from ...expression.advanced_functions import AllExpression, AnyExpression, ExistsExpression
from ...expression.predicates import (
    BetweenPredicate,
    ComparisonPredicate,
    InPredicate,
    IsBooleanPredicate,
    IsNullPredicate,
    LikePredicate,
    LogicalPredicate,
)

if TYPE_CHECKING:  # pragma: no cover
    pass


class PredicateMixin:
    """Mixin for formatting SQL predicate expressions.

    Formatting functions receive the expression instance only; every value
    they need was collected at expression construction time.
    """

    def format_comparison_predicate(self, expr: ComparisonPredicate) -> Tuple[str, tuple]:
        """Format a comparison predicate (``left <op> right``).

        Args:
            expr: Comparison expression exposing ``left``, ``op``, and
                ``right``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from ...expression.statements import QueryExpression

        left_sql, left_params = expr.left.to_sql()
        right_sql, right_params = expr.right.to_sql()
        if isinstance(expr.right, QueryExpression):
            right_sql = f"({right_sql})"
        return f"{left_sql} {expr.op} {right_sql}", left_params + right_params

    def format_logical_predicate(self, expr: LogicalPredicate) -> Tuple[str, tuple]:
        """Format a logical predicate (AND/OR/NOT).

        Args:
            expr: Logical expression exposing ``op`` and ``predicates``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
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

    def format_in_predicate(self, expr: InPredicate) -> Tuple[str, tuple]:
        """Format an ``IN`` predicate.

        Args:
            expr: Membership expression exposing ``expr`` and ``values``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from ...expression.core import Literal

        expr_sql, expr_params = expr.expr.to_sql()
        # A Literal wrapping a collection renders as a value list; anything
        # else (e.g. a subquery) renders through its own to_sql().
        if isinstance(expr.values, Literal) and isinstance(expr.values.value, (list, tuple, set)):
            return self._format_in_value_list(expr_sql, expr_params, expr.values)
        values_sql, values_params = expr.values.to_sql()
        return f"{expr_sql} IN {values_sql}", expr_params + values_params

    def _format_in_value_list(self, expr_sql: str, expr_params: tuple, literal) -> Tuple[str, Tuple]:
        """Render ``IN (…)`` for a :class:`Literal` wrapping a collection.

        The whole ``Literal`` is passed in rather than just its ``value``
        because its ``inline_literals`` switch has to be honoured: DDL
        preparation sets that flag on every literal it finds (PostgreSQL rejects
        bind parameters in DDL), and dropping it here is the only reason ``IN``
        could not previously be used inside a CHECK constraint. Rendering goes
        through ``format_literal`` so escaping and quoting match every other
        inline literal.
        """
        values = literal.value
        if not values:
            return f"{expr_sql} IN ()", expr_params
        if literal.inline_literals:
            rendered = ", ".join(self.format_literal(value) for value in values)
            return f"{expr_sql} IN ({rendered})", expr_params
        placeholders = ", ".join([self.get_parameter_placeholder()] * len(values))
        return f"{expr_sql} IN ({placeholders})", expr_params + tuple(values)

    def format_between_predicate(self, expr: BetweenPredicate) -> Tuple[str, tuple]:
        """Format a ``BETWEEN`` predicate.

        Args:
            expr: Range expression exposing ``expr``, ``low``, and ``high``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        expr_sql, expr_params = expr.expr.to_sql()
        low_sql, low_params = expr.low.to_sql()
        high_sql, high_params = expr.high.to_sql()
        return f"{expr_sql} BETWEEN {low_sql} AND {high_sql}", expr_params + low_params + high_params

    def format_is_null_predicate(self, expr: IsNullPredicate) -> Tuple[str, tuple]:
        """Format an ``IS [NOT] NULL`` predicate.

        Args:
            expr: Null check expression exposing ``expr`` and ``is_not``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        expr_sql, expr_params = expr.expr.to_sql()
        not_str = " NOT" if expr.is_not else ""
        return f"{expr_sql} IS{not_str} NULL", expr_params

    def format_is_boolean_predicate(self, expr: IsBooleanPredicate) -> Tuple[str, tuple]:
        """Format an ``IS [NOT] TRUE/FALSE`` predicate.

        Args:
            expr: Boolean check expression exposing ``expr``, ``is_not``,
                and ``value``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        expr_sql, expr_params = expr.expr.to_sql()
        not_str = " NOT" if expr.is_not else ""
        bool_str = "TRUE" if expr.value else "FALSE"
        return f"{expr_sql} IS{not_str} {bool_str}", expr_params

    def format_exists_expression(self, expr: ExistsExpression) -> Tuple[str, tuple]:
        """Format an ``[NOT] EXISTS`` expression.

        Args:
            expr: Existence expression exposing ``subquery`` and ``is_not``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        subquery_sql, subquery_params = expr.subquery.to_sql()
        exists_clause = "NOT EXISTS" if expr.is_not else "EXISTS"
        return f"{exists_clause} {subquery_sql}", subquery_params

    def format_any_expression(self, expr: AnyExpression) -> Tuple[str, tuple]:
        """Format a quantified ``ANY`` comparison expression.

        Args:
            expr: Quantified expression exposing ``expr``, ``array_expr``,
                and ``op``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        expr_sql, expr_params = expr.expr.to_sql()
        array_expr = expr.array_expr
        if hasattr(array_expr, "value") and isinstance(array_expr.value, (list, tuple)):
            array_sql = self.get_parameter_placeholder()
            array_params = (tuple(array_expr.value),)
        else:
            array_sql, array_params = array_expr.to_sql()
        return f"({expr_sql} {expr.op} ANY{array_sql})", tuple(list(expr_params) + list(array_params))

    def format_all_expression(self, expr: AllExpression) -> Tuple[str, tuple]:
        """Format a quantified ``ALL`` comparison expression.

        Args:
            expr: Quantified expression exposing ``expr``, ``array_expr``,
                and ``op``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        expr_sql, expr_params = expr.expr.to_sql()
        array_expr = expr.array_expr
        if hasattr(array_expr, "value") and isinstance(array_expr.value, (list, tuple)):
            array_sql = self.get_parameter_placeholder()
            array_params = (tuple(array_expr.value),)
        else:
            array_sql, array_params = array_expr.to_sql()
        return f"({expr_sql} {expr.op} ALL{array_sql})", tuple(list(expr_params) + list(array_params))

    def format_like_predicate(self, expr: LikePredicate) -> Tuple[str, tuple]:
        """Format a ``LIKE`` predicate.

        Args:
            expr: Pattern expression exposing ``expr``, ``op``, and
                ``pattern``.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        expr_sql, expr_params = expr.expr.to_sql()
        pattern_sql, pattern_params = expr.pattern.to_sql()
        return f"{expr_sql} {expr.op} {pattern_sql}", expr_params + pattern_params
