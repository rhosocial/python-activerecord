# src/rhosocial/activerecord/backend/dialect/mixins/cte.py
"""Dialect mixin for Common Table Expression (``WITH`` clause) support."""
from typing import TYPE_CHECKING, Any, List, Tuple

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.query_sources import CTEClause, WithStatement


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

    def format_cte_clause(self, expr: "CTEClause") -> Tuple[str, tuple]:
        """Format a single CTE definition (name AS (query)).

        Args:
            expr: The ``CTEClause`` carrying ``name``, optional ``columns``, the
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

    def format_with_statement(self, stmt: "WithStatement") -> Tuple[str, tuple]:
        """Format a query with a ``WITH`` clause: ``WITH [RECURSIVE] cte [, ...] query``.

        The probes this construct consults used to be decorative: a dialect
        that declares no basic CTE support refused nothing and the clause
        rendered anyway, and a ``RECURSIVE`` request on a dialect without
        recursive CTEs was silently spelled. Both are refused by name now,
        where the construct is spelled.

        Each CTE definition renders through its own formatter
        (``format_cte_clause``), so a backend re-spells a single CTE there
        rather than re-implementing the composition around it.

        Args:
            stmt: The ``WithStatement`` carrying the ``ctes``, the
                ``recursive`` modifier, and the trailing ``query``.

        Returns:
            Tuple of (SQL string, parameters tuple) for the full statement.
            A statement with no CTE definitions renders the bare query.

        Raises:
            UnsupportedFeatureError: If CTEs are present but the dialect
                declares no basic CTE support, or ``recursive`` was
                requested on a dialect without recursive CTE support.
        """
        from ..exceptions import UnsupportedFeatureError

        if not stmt.ctes:
            query_sql, query_params = stmt.query.to_sql()
            return query_sql, tuple(query_params)
        if not self.supports_basic_cte():
            raise UnsupportedFeatureError(self.name, "WITH clause (basic CTE)")
        if stmt.recursive and not self.supports_recursive_cte():
            raise UnsupportedFeatureError(self.name, "WITH RECURSIVE clause")
        all_params: List[Any] = []
        cte_sql_parts: List[str] = []
        for cte in stmt.ctes:
            cte_sql, cte_params = cte.to_sql()
            cte_sql_parts.append(cte_sql)
            all_params.extend(cte_params)
        recursive_str = "RECURSIVE " if stmt.recursive else ""
        query_sql, query_params = stmt.query.to_sql()
        all_params.extend(query_params)
        return f"WITH {recursive_str}{', '.join(cte_sql_parts)} {query_sql}", tuple(all_params)
