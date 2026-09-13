# src/rhosocial/activerecord/backend/dialect/mixins/grouping.py
"""Dialect mixin for advanced SQL grouping constructs.

Declares support for and formats ROLLUP, CUBE, and GROUPING SETS operations,
raising UnsupportedFeatureError for operations the dialect does not support.
"""
from typing import Tuple

from ..exceptions import UnsupportedFeatureError
from ...expression import bases


class AdvancedGroupingMixin:
    """Mixin for advanced grouping operations (ROLLUP, CUBE, GROUPING SETS).

    Dialects override the ``supports_*`` probes to advertise which grouping
    constructs they implement; the default implementation reports none.
    """

    def supports_rollup(self) -> bool:
        """Whether ROLLUP grouping is supported. Defaults to False."""
        return False

    def supports_cube(self) -> bool:
        """Whether CUBE grouping is supported. Defaults to False."""
        return False

    def supports_grouping_sets(self) -> bool:
        """Whether GROUPING SETS are supported. Defaults to False."""
        return False

    def format_grouping_clause(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Format a grouping expression (ROLLUP, CUBE, or GROUPING SETS).

        Args:
            expr: The GroupingClause node containing the operation and the
                grouped expressions.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.

        Raises:
            UnsupportedFeatureError: If the dialect does not support the
                requested grouping operation.
        """
        operation = expr.operation
        expressions = expr.expressions
        # Check feature support based on operation type
        if operation.upper() == "ROLLUP":
            if not self.supports_rollup():
                raise UnsupportedFeatureError(self.name, "ROLLUP")
        elif operation.upper() == "CUBE":
            if not self.supports_cube():
                raise UnsupportedFeatureError(self.name, "CUBE")
        elif operation.upper() == "GROUPING SETS":
            if not self.supports_grouping_sets():
                raise UnsupportedFeatureError(self.name, "GROUPING SETS")

        all_params = []
        if operation.upper() == "GROUPING SETS":
            # For GROUPING SETS, expressions is a list of lists
            sets_parts = []
            for expr_list in expressions:
                expr_parts = []
                for expr in expr_list:
                    expr_sql, expr_params = expr.to_sql()
                    expr_parts.append(expr_sql)
                    all_params.extend(expr_params)
                sets_parts.append(f"({', '.join(expr_parts)})")
            inner_expr = ", ".join(sets_parts)
            sql = f"{operation.upper()}({inner_expr})"
        else:
            # For ROLLUP and CUBE, expressions is a simple list
            expr_parts = []
            for expr in expressions:
                expr_sql, expr_params = expr.to_sql()
                expr_parts.append(expr_sql)
                all_params.extend(expr_params)
            inner_expr = ", ".join(expr_parts)
            sql = f"{operation.upper()}({inner_expr})"

        return sql, tuple(all_params)
