# src/rhosocial/activerecord/backend/dialect/mixins/create_view_mixin.py
"""Per-statement mixin for CreateViewSupport. Members/order/signature mirror the protocol."""

from typing import Any, List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import MaterializedView, Table, View

class CreateViewMixin:
    def supports_create_view(self) -> bool:
            """Whether CREATE VIEW is supported (defaults to True)."""
            return True

    def supports_create_view_bind_parameters(self) -> bool:
            """Whether a view body may carry bind parameters.

            Defaults to ``False``. A view's definition is *stored and run again
            later*, so a bind that is meaningful while the statement executes
            has no meaning then; that is why PostgreSQL refuses one in its own
            words ("there is no parameter $1", 19beta4).

            The answer is measured rather than assumed. PostgreSQL refuses;
            MySQL and MariaDB accept, because their "parameters" are
            interpolated client-side and the value is baked into the stored
            definition; ClickHouse accepts for the same reason; SQL Server
            refuses; Oracle refuses, because Oracle's DDL statements never take
            bind variables and the driver rejects the statement before the
            server sees it (``DPY-4009``).

            A dialect that does not answer refuses the statement by name, with
            the way out named -- build the query with an inlined literal.
            """
            return False

    def supports_or_replace_view(self) -> bool:
            """Whether CREATE OR REPLACE VIEW is supported (defaults to False)."""
            return False

    def supports_create_or_replace_view(self) -> bool:
            """Whether CREATE OR REPLACE VIEW is supported (defaults to False)."""
            return False

    def supports_temporary_view(self) -> bool:
            """Whether TEMPORARY views are supported (defaults to False)."""
            return False

    def supports_if_not_exists_view(self) -> bool:
            """Whether CREATE VIEW IF NOT EXISTS is supported (defaults to False)."""
            return False

    def supports_view_check_option(self) -> bool:
            """Whether WITH CHECK OPTION is supported (defaults to False)."""
            return False

    def format_create_view_statement(self, expr: "CreateViewStatement") -> Tuple[str, tuple]:
            """Format a CREATE VIEW statement.

            Args:
                expr: The CreateViewStatement to render.

            Returns:
                A ``(sql, params)`` tuple where ``params`` holds the parameters
                collected from the view's query.

            Raises:
                TypeError: ``CreateViewStatement.view`` is not a View. Another object
                kind would have had its own name rendered as the view's.
            """
            if not isinstance(expr.view, View):
                raise TypeError(
                    f"CreateViewStatement.view must be a View, "
                    f"got {type(expr.view).__name__}"
                )
            from ...expression.statements import ViewCheckOption
            from ..exceptions import UnsupportedFeatureError
            replace_part = ""
            if expr.replace:
                if not self.supports_create_or_replace_view():
                    raise UnsupportedFeatureError(
                        self.name, "CREATE OR REPLACE VIEW",
                        f"{self.name} does not support CREATE OR REPLACE VIEW."
                    )
                replace_part = "OR REPLACE "
            temporary_part = "TEMPORARY " if expr.temporary else ""
            if_not_exists_part = ""
            if expr.if_not_exists:
                if not self.supports_if_not_exists_view():
                    raise UnsupportedFeatureError(
                        self.name, "CREATE VIEW IF NOT EXISTS",
                        f"{self.name} does not support CREATE VIEW IF NOT EXISTS."
                    )
                if_not_exists_part = "IF NOT EXISTS "
            if getattr(expr.query, "hints", ()):
                raise TypeError(
                    f"{type(expr).__name__}: the embedded query carries optimizer hints. "
                    "A hint comment belongs to the outermost statement, and this statement "
                    "is not planned at creation time, so a hint here would be inert and "
                    "would interrupt the statement text. Attach hints where the query is "
                    "actually run."
                )

            sql_parts = [
                f"CREATE {replace_part}{temporary_part}VIEW {if_not_exists_part}"
                f"{expr.view.to_sql()[0]}"
            ]
            all_params: List[Any] = []
            if expr.column_aliases:
                aliases_str = ", ".join(self.format_identifier(alias) for alias in expr.column_aliases)
                sql_parts.append(f"({aliases_str})")
            query_sql, query_params = expr.query.to_sql()
            if query_params and not self.supports_create_view_bind_parameters():
                self.refuse_ddl_bind_parameters("CREATE VIEW with bound parameters")
            sql_parts.append(f" AS {query_sql}")
            all_params.extend(query_params)
            if expr.options.check_option is not None:
                if not self.supports_view_check_option():
                    raise UnsupportedFeatureError(
                        self.name, "WITH CHECK OPTION",
                        f"{self.name} does not support WITH CHECK OPTION.",
                    )
                if expr.options.check_option == ViewCheckOption.LOCAL:
                    sql_parts.append(" WITH LOCAL CHECK OPTION")
                elif expr.options.check_option == ViewCheckOption.CASCADED:
                    sql_parts.append(" WITH CASCADED CHECK OPTION")
            return " ".join(sql_parts), tuple(all_params)
