# .../mixins/advanced_grouping_mixin.py
"""Per-feature mixin for AdvancedGroupingSupport. Members/order/signature mirror the protocol."""

from typing import TYPE_CHECKING, Any, List, Tuple
from ...expression.bases import ToSQLProtocol
from ...expression.query_parts import SortDirection

class AdvancedGroupingMixin:
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
            from ..exceptions import UnsupportedFeatureError

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
                for expr_item in expressions:
                    expr_sql, expr_params = expr_item.to_sql()
                    expr_parts.append(expr_sql)
                    all_params.extend(expr_params)
                inner_expr = ", ".join(expr_parts)
                sql = f"{operation.upper()}({inner_expr})"

            return sql, tuple(all_params)
