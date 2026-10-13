# src/rhosocial/activerecord/backend/dialect/mixins/cte.py
"""Dialect mixin for Common Table Expression (``WITH`` clause) support."""
from typing import TYPE_CHECKING, Any, List, Tuple

if TYPE_CHECKING:  # pragma: no cover
    from ...expression import bases
    from ...expression.query_sources import WithClause


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

        Raises:
            UnsupportedFeatureError: If a ``MATERIALIZED`` / ``NOT MATERIALIZED``
                hint was requested and the dialect's ``supports_materialized_cte``
                probe declines it.
        """
        from ...expression import bases

        if expr.materialized or expr.not_materialized:
            if not self.supports_materialized_cte():
                feature = (
                    "MATERIALIZED CTE" if expr.materialized else "NOT MATERIALIZED CTE"
                )
                from ..exceptions import UnsupportedFeatureError

                raise UnsupportedFeatureError(
                    self.name, feature,
                    f"{self.name} does not support the {feature} hint.",
                )

        query = expr.query
        if isinstance(query, bases.BaseExpression):
            query_sql, query_params = query.to_sql()
        elif isinstance(query, tuple) and len(query) == 2:
            query_sql = query[0]
            params_input = query[1]
            query_params = tuple(params_input) if isinstance(params_input, list) else params_input
        else:
            query_sql, query_params = str(query), ()
        if expr.materialized:
            materialized_hint = "MATERIALIZED "
        elif expr.not_materialized:
            materialized_hint = "NOT MATERIALIZED "
        else:
            materialized_hint = ""
        name_part = self.format_identifier(expr.name)
        columns_part = f" ({', '.join(self.format_identifier(c) for c in expr.columns)})" if expr.columns else ""
        sql = f"{name_part}{columns_part} AS {materialized_hint}({query_sql})"
        return sql, query_params

    def format_with_clause(self, clause: "WithClause") -> Tuple[str, tuple]:
        """Format a ``WITH`` clause: ``WITH [RECURSIVE] cte [, cte ...]``.

        The probes this clause consults used to be decorative: a dialect
        that declares no basic CTE support refused nothing and the clause
        rendered anyway, and a ``RECURSIVE`` request on a dialect without
        recursive CTEs was silently spelled. Both are refused by name now.

        Args:
            clause: The ``WithClause`` carrying the CTE definitions and the
                ``RECURSIVE`` modifier.

        Returns:
            Tuple of (SQL string, parameters tuple); empty SQL when the
            clause carries no CTE definitions.

        Raises:
            UnsupportedFeatureError: If the dialect declares no basic CTE
                support, or ``RECURSIVE`` was requested on a dialect
                without recursive CTE support.
        """
        from ..exceptions import UnsupportedFeatureError

        if not clause.ctes:
            return "", ()
        if not self.supports_basic_cte():
            raise UnsupportedFeatureError(self.name, "WITH clause (basic CTE)")
        if clause.recursive and not self.supports_recursive_cte():
            raise UnsupportedFeatureError(self.name, "WITH RECURSIVE clause")
        all_params: List[Any] = []
        cte_sql_parts: List[str] = []
        for cte in clause.ctes:
            cte_sql, cte_params = cte.to_sql()
            cte_sql_parts.append(cte_sql)
            all_params.extend(cte_params)
        recursive_str = "RECURSIVE " if clause.recursive else ""
        return f"WITH {recursive_str}{', '.join(cte_sql_parts)}", tuple(all_params)

    def format_with_query_expression(self, expr: "bases.BaseExpression") -> Tuple[str, tuple]:
        """Format a complete query with a WITH clause.

        The clause itself is a :class:`WithClause` node, so its spelling
        goes through the dialect's public ``format_with_clause`` — a
        backend overrides that one formatter to re-spell the clause,
        instead of re-implementing the composition around it.

        Args:
            expr: Query expression carrying ``ctes``, ``recursive``, and
                ``main_query``.

        Returns:
            Tuple of (SQL string, parameters tuple) for the full query.
        """
        from ...expression.query_sources import WithClause

        clause = WithClause(
            expr.dialect, ctes=expr.ctes, recursive=bool(expr.recursive)
        )
        with_sql, with_params = self.format_with_clause(clause)
        main_sql, main_params = expr.main_query.to_sql()
        if not with_sql:
            return main_sql, tuple(with_params) + tuple(main_params)
        return f"{with_sql} {main_sql}", tuple(with_params) + tuple(main_params)
