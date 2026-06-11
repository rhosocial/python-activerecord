# src/rhosocial/activerecord/backend/dialect/mixins/grouping.py
from typing import List, Tuple

from ..exceptions import UnsupportedFeatureError
from ...expression import bases


class AdvancedGroupingMixin:
    """Mixin for advanced grouping operations (ROLLUP, CUBE, GROUPING SETS)."""

    def supports_rollup(self) -> bool:
        """Whether ROLLUP is supported."""
        return False

    def supports_cube(self) -> bool:
        """Whether CUBE is supported."""
        return False

    def supports_grouping_sets(self) -> bool:
        """Whether GROUPING SETS are supported."""
        return False

    def format_grouping_expression(
        self, operation: str, expressions: List["bases.BaseExpression"]
    ) -> Tuple[str, tuple]:
        """
        Formats a grouping expression (ROLLUP, CUBE, GROUPING SETS).

        Args:
            operation: The grouping operation ('ROLLUP', 'CUBE', or 'GROUPING SETS').
            expressions: List of expressions to group by.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
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
