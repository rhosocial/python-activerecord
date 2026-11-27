# src/rhosocial/activerecord/backend/dialect/mixins/materialized_view_mixin.py
"""Per-statement mixin for MaterializedViewSupport. Members/order/signature mirror the protocol."""

from typing import Any, List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import MaterializedView, Table, View

class MaterializedViewMixin:
    def supports_materialized_view(self) -> bool:
            """Whether materialized views are supported (defaults to False)."""
            return False

    def supports_materialized_view_bind_parameters(self) -> bool:
            """Whether a materialized view body may carry bind parameters.

            Defaults to ``False``. A materialized view's definition is *stored
            and run again later*, so a bind that is meaningful while the
            statement executes has no meaning then; that is why PostgreSQL
            refuses one in its own words ("materialized views may not be
            defined using bound parameters", 19beta4).

            The answer is measured rather than assumed. PostgreSQL refuses;
            ClickHouse accepts, because its "parameters" are interpolated
            client-side and the value is baked into the stored definition;
            Oracle refuses, because Oracle's DDL statements never take bind
            variables and the driver rejects the statement before the server
            sees it (``DPY-4009``).

            A dialect that does not answer refuses the statement by name, with
            the way out named -- build the query with an inlined literal.
            """
            return False

    def supports_refresh_materialized_view(self) -> bool:
            """Whether REFRESH MATERIALIZED VIEW is supported (defaults to False)."""
            return False

    def supports_materialized_view_tablespace(self) -> bool:
            """Whether tablespace for materialized views is supported (defaults to False)."""
            return False

    def supports_materialized_view_storage_options(self) -> bool:
            """Whether storage options for materialized views are supported (defaults to False)."""
            return False

    def supports_materialized_view_restrict(self) -> bool:
            """Whether DROP MATERIALIZED VIEW RESTRICT is supported (defaults to False)."""
            return False

    def supports_with_data_clause(self) -> bool:
            """Whether the ``WITH [NO] DATA`` population clause is supported.

            The clause is shared by ``CREATE TABLE ... AS``, ``CREATE MATERIALIZED
            VIEW`` and ``REFRESH MATERIALIZED VIEW``; the probe is declared once, by
            :class:`MaterializedViewSupport`, and consulted by all three consumers.
            Defaults to False.
            """
            return False

    def format_create_materialized_view_statement(self, expr: "CreateMaterializedViewStatement") -> Tuple[str, tuple]:
            """Format a CREATE MATERIALIZED VIEW statement.

            Args:
                expr: The CreateMaterializedViewStatement to render.

            Returns:
                A ``(sql, params)`` tuple where ``params`` holds the parameters
                collected from the view's query.

            Raises:
                TypeError: ``CreateMaterializedViewStatement.view`` is not a
                MaterializedView. A plain view would render as a well-formed CREATE
                MATERIALIZED VIEW over that view's name.
                UnsupportedFeatureError: If the dialect does not support
                    materialized views.
            """
            if not isinstance(expr.view, MaterializedView):
                raise TypeError(
                    f"CreateMaterializedViewStatement.view must be a MaterializedView, "
                    f"got {type(expr.view).__name__}"
                )
            if not self.supports_materialized_view():
                raise UnsupportedFeatureError(self.name, "CREATE MATERIALIZED VIEW")
            if (expr.with_data or expr.no_data) and not self.supports_with_data_clause():
                feature = "WITH DATA" if expr.with_data else "WITH NO DATA"
                raise UnsupportedFeatureError(
                    self.name, feature,
                    f"{self.name} does not support {feature} for materialized views."
                )

            if getattr(expr.query, "hints", ()):
                raise TypeError(
                    f"{type(expr).__name__}: the embedded query carries optimizer hints. "
                    "A hint comment belongs to the outermost statement -- it is a comment "
                    "on the statement as a whole, and two blocks are rejected -- so the "
                    "hints must be given to this statement, not to the query it wraps."
                )

            parts = ["CREATE MATERIALIZED VIEW"]
            parts.append(expr.view.to_sql()[0])

            if expr.column_aliases:
                cols = ", ".join(self.format_identifier(c) for c in expr.column_aliases)
                parts.append(f"({cols})")

            if expr.tablespace:
                if not self.supports_materialized_view_tablespace():
                    raise UnsupportedFeatureError(
                        self.name, "MATERIALIZED VIEW TABLESPACE",
                        f"{self.name} does not support TABLESPACE for materialized views."
                    )
                parts.append(f"TABLESPACE {self.format_identifier(expr.tablespace)}")

            query_sql, query_params = expr.query.to_sql()
            if query_params and not self.supports_materialized_view_bind_parameters():
                self.refuse_ddl_bind_parameters("CREATE MATERIALIZED VIEW with bound parameters")
            parts.append(f"AS {query_sql}")

            if expr.with_data:
                parts.append("WITH DATA")
            elif expr.no_data:
                parts.append("WITH NO DATA")

            return " ".join(parts), query_params

    def format_drop_materialized_view_statement(self, expr: "DropMaterializedViewStatement") -> Tuple[str, tuple]:
            """Format a DROP MATERIALIZED VIEW statement.

            Args:
                expr: The DropMaterializedViewStatement to render.

            Returns:
                A ``(sql, params)`` tuple; ``params`` is always empty.

            Raises:
                TypeError: ``DropMaterializedViewStatement.view`` is not a
                MaterializedView. A plain view would render as a well-formed DROP
                MATERIALIZED VIEW over that view's name.
                UnsupportedFeatureError: If the dialect does not support
                    materialized views.
            """
            if not isinstance(expr.view, MaterializedView):
                raise TypeError(
                    f"DropMaterializedViewStatement.view must be a MaterializedView, "
                    f"got {type(expr.view).__name__}"
                )
            if not self.supports_materialized_view():
                raise UnsupportedFeatureError(self.name, "DROP MATERIALIZED VIEW")

            parts = ["DROP MATERIALIZED VIEW"]
            if expr.if_exists:
                parts.append("IF EXISTS")
            parts.append(expr.view.to_sql()[0])
            if expr.cascade:
                parts.append("CASCADE")
            elif expr.restrict:
                if not self.supports_materialized_view_restrict():
                    raise UnsupportedFeatureError(
                        self.name, "DROP MATERIALIZED VIEW RESTRICT",
                        f"{self.name} does not support DROP MATERIALIZED VIEW RESTRICT."
                    )
                parts.append("RESTRICT")
            return " ".join(parts), ()

    def format_refresh_materialized_view_statement(
            self, expr: "RefreshMaterializedViewStatement"
        ) -> Tuple[str, tuple]:
            """Format a REFRESH MATERIALIZED VIEW statement.

            Args:
                expr: The RefreshMaterializedViewStatement to render.

            Returns:
                A ``(sql, params)`` tuple; ``params`` is always empty.

            Raises:
                TypeError: ``RefreshMaterializedViewStatement.view`` is not a
                MaterializedView. A plain view would render as a well-formed REFRESH
                MATERIALIZED VIEW over that view's name.
                UnsupportedFeatureError: If the dialect does not support refreshing
                    materialized views.
            """
            if not isinstance(expr.view, MaterializedView):
                raise TypeError(
                    f"RefreshMaterializedViewStatement.view must be a MaterializedView, "
                    f"got {type(expr.view).__name__}"
                )
            if not self.supports_refresh_materialized_view():
                raise UnsupportedFeatureError(self.name, "REFRESH MATERIALIZED VIEW")
            if (expr.with_data or expr.no_data) and not self.supports_with_data_clause():
                feature = "WITH DATA" if expr.with_data else "WITH NO DATA"
                raise UnsupportedFeatureError(
                    self.name, feature,
                    f"{self.name} does not support {feature} for materialized views."
                )

            parts = ["REFRESH MATERIALIZED VIEW"]
            if expr.concurrent:
                parts.append("CONCURRENTLY")
            parts.append(expr.view.to_sql()[0])
            if expr.with_data:
                parts.append("WITH DATA")
            elif expr.no_data:
                parts.append("WITH NO DATA")
            return " ".join(parts), ()
