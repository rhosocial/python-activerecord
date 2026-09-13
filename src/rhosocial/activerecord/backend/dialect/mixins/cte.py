# src/rhosocial/activerecord/backend/dialect/mixins/cte.py
"""Dialect mixin for Common Table Expression (``WITH`` clause) support."""
from typing import TYPE_CHECKING, Any, List, Optional, Dict, Tuple

if TYPE_CHECKING:  # pragma: no cover
    from ...expression import bases


class CTEMixin:
    """Mixin adding support for Common Table Expressions.

    Covers basic, recursive, and materialized CTEs as well as rendering of a
    complete ``WITH`` clause.
    """

    def supports_basic_cte(self) -> bool:
        """Whether basic CTEs are supported.

        Defaults to False.
        """
        return False

    def supports_recursive_cte(self) -> bool:
        """Whether recursive CTEs are supported.

        Defaults to False.
        """
        return False

    def supports_materialized_cte(self) -> bool:
        """Whether MATERIALIZED hint is supported.

        Defaults to False.
        """
        return False

    def supports_unconditional_cte_order_by(self) -> bool:
        """Whether ORDER BY is allowed inside CTE definitions.

        Most backends support this; SQL Server does not (requires TOP/OFFSET).
        Defaults to True.
        """
        return True

    def format_cte_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Format a single CTE definition (name AS (query)).

        Args:
            expr: CTE expression carrying ``name``, optional ``columns``, the
                ``materialized`` hint, and the ``query``.

        Returns:
            Tuple of (SQL string, parameters tuple) for the CTE definition.
        """
        from ...expression import bases

        query = expr.query
        if isinstance(query, bases.BaseExpression):
            query_sql, query_params = query.to_sql()
        elif isinstance(query, tuple) and len(query) == 2:
            query_sql = query[0]
            params_input = query[1]
            query_params = tuple(params_input) if isinstance(params_input, list) else params_input
        else:
            query_sql, query_params = str(query), ()
        materialized_hint = ""
        if expr.materialized is not None:
            materialized_hint = "MATERIALIZED " if expr.materialized else "NOT MATERIALIZED "
        name_part = self.format_identifier(expr.name)
        columns_part = f" ({', '.join(self.format_identifier(c) for c in expr.columns)})" if expr.columns else ""
        sql = f"{name_part}{columns_part} AS {materialized_hint}({query_sql})"
        return sql, query_params

    def format_with_query_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Format a complete query with a WITH clause.

        Args:
            expr: Query expression carrying ``ctes``, ``recursive``, and
                ``main_query``.

        Returns:
            Tuple of (SQL string, parameters tuple) for the full query.
        """
        all_params: List[Any] = []
        cte_sql_parts: List[str] = []
        for cte in expr.ctes:
            cte_sql, cte_params = cte.to_sql()
            cte_sql_parts.append(cte_sql)
            all_params.extend(cte_params)
        main_sql, main_params = expr.main_query.to_sql()
        all_params.extend(main_params)
        has_recursive = bool(expr.recursive)
        if not cte_sql_parts:
            return main_sql, tuple(all_params)
        with_clause = self._format_with_clause(cte_sql_parts, has_recursive)
        return f"{with_clause} {main_sql}", tuple(all_params)

    def _format_with_clause(self, ctes_sql: List[str], has_recursive: bool = False) -> str:
        """Helper to format complete WITH clause from list of CTE definitions.

        Args:
            ctes_sql: Rendered CTE definition strings.
            has_recursive: Whether to emit the ``RECURSIVE`` keyword.

        Returns:
            The rendered ``WITH`` clause, or an empty string when there are no
            CTE definitions.
        """
        if not ctes_sql:
            return ""
        recursive_str = "RECURSIVE " if has_recursive else ""
        return f"WITH {recursive_str}{', '.join(ctes_sql)}"
