# src/rhosocial/activerecord/backend/dialect/mixins/join.py
from typing import Any, List, Optional, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.query_parts import JoinExpression


class LateralJoinMixin:
    """Mixin for LATERAL join support."""

    def supports_lateral_join(self) -> bool:
        """Whether LATERAL joins are supported."""
        return False

    def format_lateral_expression(
        self, expr_sql: str, expr_params: Tuple[Any, ...], alias: Optional[str], join_type: str
    ) -> Tuple[str, Tuple]:
        """Format LATERAL expression.

        Raises UnsupportedFeatureError when the dialect reports no LATERAL
        support.  Backends only override this method to translate LATERAL
        into an alternative syntax (e.g. CROSS APPLY).
        """
        if not self.supports_lateral_join():
            raise UnsupportedFeatureError(
                self.name,
                "LATERAL join",
                "Restructure the query with a plain subquery or a CTE instead.",
            )
        if alias is not None:
            sql = f"{join_type.upper()} JOIN LATERAL {expr_sql} AS {self.format_identifier(alias)}"
        else:
            sql = f"{join_type.upper()} JOIN LATERAL {expr_sql}"
        return sql, expr_params

    def format_table_function_expression(
        self,
        func_name: str,
        args_sql: List[str],
        args_params: Tuple[Any, ...],
        alias: Optional[str],
        column_names: Optional[List[str]],
    ) -> Tuple[str, Tuple]:
        """Format table-valued function expression."""
        args_str = ", ".join(args_sql)

        cols_sql = ""
        if column_names:
            cols_sql = f"({', '.join(self.format_identifier(name) for name in column_names)})"

        if alias is not None:
            sql = f"{func_name.upper()}({args_str}) AS {self.format_identifier(alias)}{cols_sql}"
        else:
            sql = f"{func_name.upper()}({args_str}){cols_sql}"
        return sql, args_params


class JoinMixin:
    """Mixin for JOIN clause support."""

    def supports_inner_join(self) -> bool:
        """Whether INNER JOIN is supported. Defaults to True."""
        return True

    def supports_left_join(self) -> bool:
        """Whether LEFT JOIN is supported. Defaults to True."""
        return True

    def supports_right_join(self) -> bool:
        """Whether RIGHT JOIN is supported. Defaults to False."""
        return False

    def supports_full_join(self) -> bool:
        """Whether FULL JOIN is supported. Defaults to False."""
        return False

    def supports_cross_join(self) -> bool:
        """Whether CROSS JOIN is supported. Defaults to True."""
        return True

    def supports_natural_join(self) -> bool:
        """Whether NATURAL JOIN is supported. Defaults to True."""
        return True

    def supports_straight_join(self) -> bool:
        """Whether MySQL STRAIGHT_JOIN is supported. Defaults to False."""
        return False

    def format_join_expression(self, join_expr: "JoinExpression") -> Tuple[str, Tuple]:
        """
        Generic implementation for formatting a JOIN expression.
        This method validates support for the given join type using protocol methods.
        """
        from ...expression import QueryExpression, JoinExpression

        join_type_upper = join_expr.join_type.upper()

        # Use split to handle cases like "LEFT OUTER JOIN"
        join_type_keyword = join_type_upper.split()[0]

        # Check for feature support
        if join_type_keyword == "INNER" and not self.supports_inner_join():
            raise UnsupportedFeatureError(self.name, "INNER JOIN")
        elif join_type_keyword == "LEFT" and not self.supports_left_join():
            raise UnsupportedFeatureError(self.name, "LEFT JOIN")
        elif join_type_keyword == "RIGHT" and not self.supports_right_join():
            raise UnsupportedFeatureError(self.name, "RIGHT JOIN")
        elif join_type_keyword == "FULL" and not self.supports_full_join():
            raise UnsupportedFeatureError(self.name, "FULL JOIN")
        elif join_type_keyword == "CROSS" and not self.supports_cross_join():
            raise UnsupportedFeatureError(self.name, "CROSS JOIN")

        if join_expr.natural and not self.supports_natural_join():
            raise UnsupportedFeatureError(self.name, "NATURAL JOIN")

        all_params = []

        # Format left and right sides of the join
        left_sql, left_params = join_expr.left_table.to_sql()
        if isinstance(join_expr.left_table, (QueryExpression, JoinExpression)):
            left_sql = f"({left_sql})"
        all_params.extend(left_params)

        right_sql, right_params = join_expr.right_table.to_sql()
        if isinstance(join_expr.right_table, (QueryExpression, JoinExpression)):
            right_sql = f"({right_sql})"
        all_params.extend(right_params)

        # Build the join clause
        join_parts = [left_sql]

        if join_expr.natural:
            join_parts.append("NATURAL")

        join_parts.append(join_type_upper)
        join_parts.append(right_sql)

        # Handle ON or USING clause, which are not used with NATURAL JOIN
        if not join_expr.natural:
            if join_expr.condition:
                cond_sql, cond_params = join_expr.condition.to_sql()
                join_parts.append(f"ON {cond_sql}")
                all_params.extend(cond_params)
            elif join_expr.using:
                using_cols = ", ".join(self.format_identifier(col) for col in join_expr.using)
                join_parts.append(f"USING ({using_cols})")
            elif "CROSS" not in join_type_upper:
                raise ValueError(f"{join_type_upper} requires a condition or USING clause.")

        sql = " ".join(join_parts)

        # Add alias for the joined result if provided
        if join_expr.alias:
            sql = f"({sql}) AS {self.format_identifier(join_expr.alias)}"

        return sql, tuple(all_params)
