# src/rhosocial/activerecord/backend/dialect/mixins/ddl_view.py
from typing import Any, List, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateViewExpression,
        DropViewExpression,
        TruncateExpression,
        CreateMaterializedViewExpression,
        DropMaterializedViewExpression,
        RefreshMaterializedViewExpression,
    )


class ViewMixin:
    """Mixin for view DDL support."""

    def supports_create_view(self) -> bool:
        """Whether CREATE VIEW is supported."""
        return True

    def supports_drop_view(self) -> bool:
        """Whether DROP VIEW is supported."""
        return True

    def supports_or_replace_view(self) -> bool:
        """Whether CREATE OR REPLACE VIEW is supported."""
        return False

    def supports_temporary_view(self) -> bool:
        """Whether TEMPORARY views are supported."""
        return False

    def supports_materialized_view(self) -> bool:
        """Whether materialized views are supported."""
        return False

    def supports_refresh_materialized_view(self) -> bool:
        """Whether REFRESH MATERIALIZED VIEW is supported."""
        return False

    def supports_materialized_view_tablespace(self) -> bool:
        """Whether tablespace specification for materialized views is supported."""
        return False

    def supports_materialized_view_storage_options(self) -> bool:
        """Whether storage options for materialized views are supported."""
        return False

    def supports_if_exists_view(self) -> bool:
        """Whether DROP VIEW IF EXISTS is supported."""
        return False

    def supports_view_check_option(self) -> bool:
        """Whether WITH CHECK OPTION is supported."""
        return False

    def supports_cascade_view(self) -> bool:
        """Whether DROP VIEW CASCADE is supported."""
        return False

    def format_create_view_statement(self, expr: "CreateViewExpression") -> Tuple[str, tuple]:
        """Format CREATE VIEW statement (generic implementation)."""
        from ...expression.statements import ViewCheckOption
        replace_part = "OR REPLACE " if expr.replace else ""
        temporary_part = "TEMPORARY " if expr.temporary else ""
        sql_parts = [f"CREATE {replace_part}{temporary_part}VIEW {self.format_identifier(expr.view_name)}"]
        all_params: List[Any] = []
        if expr.column_aliases:
            aliases_str = ", ".join(self.format_identifier(alias) for alias in expr.column_aliases)
            sql_parts.append(f"({aliases_str})")
        query_sql, query_params = expr.query.to_sql()
        sql_parts.append(f" AS ({query_sql})")
        all_params.extend(query_params)
        if expr.options.check_option == ViewCheckOption.LOCAL:
            sql_parts.append(" WITH LOCAL CHECK OPTION")
        elif expr.options.check_option == ViewCheckOption.CASCADED:
            sql_parts.append(" WITH CASCADED CHECK OPTION")
        return " ".join(sql_parts), tuple(all_params)

    def format_drop_view_statement(self, expr: "DropViewExpression") -> Tuple[str, tuple]:
        """Format DROP VIEW statement (generic implementation)."""
        if_exists_part = "IF EXISTS " if expr.if_exists else ""
        cascade_part = " CASCADE" if expr.cascade else ""
        sql = f"DROP VIEW {if_exists_part}{self.format_identifier(expr.view_name)}{cascade_part}"
        return sql.strip(), ()

    def format_create_materialized_view_statement(self, expr: "CreateMaterializedViewExpression") -> Tuple[str, tuple]:
        """Format CREATE MATERIALIZED VIEW statement."""
        if not self.supports_materialized_view():
            raise UnsupportedFeatureError(self.name, "CREATE MATERIALIZED VIEW")

        parts = ["CREATE MATERIALIZED VIEW"]
        parts.append(self.format_identifier(expr.view_name))

        if expr.column_aliases:
            cols = ", ".join(self.format_identifier(c) for c in expr.column_aliases)
            parts.append(f"({cols})")

        if expr.tablespace and self.supports_materialized_view_tablespace():
            parts.append(f"TABLESPACE {self.format_identifier(expr.tablespace)}")

        query_sql, query_params = expr.query.to_sql()
        parts.append(f"AS {query_sql}")

        if expr.with_data:
            parts.append("WITH DATA")
        else:
            parts.append("WITH NO DATA")

        return " ".join(parts), query_params

    def format_drop_materialized_view_statement(self, expr: "DropMaterializedViewExpression") -> Tuple[str, tuple]:
        """Format DROP MATERIALIZED VIEW statement."""
        if not self.supports_materialized_view():
            raise UnsupportedFeatureError(self.name, "DROP MATERIALIZED VIEW")

        parts = ["DROP MATERIALIZED VIEW"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.view_name))
        if expr.cascade:
            parts.append("CASCADE")
        return " ".join(parts), ()

    def format_refresh_materialized_view_statement(
        self, expr: "RefreshMaterializedViewExpression"
    ) -> Tuple[str, tuple]:
        """Format REFRESH MATERIALIZED VIEW statement."""
        if not self.supports_refresh_materialized_view():
            raise UnsupportedFeatureError(self.name, "REFRESH MATERIALIZED VIEW")

        parts = ["REFRESH MATERIALIZED VIEW"]
        if expr.concurrent:
            parts.append("CONCURRENTLY")
        parts.append(self.format_identifier(expr.view_name))
        if expr.with_data is not None:
            parts.append("WITH DATA" if expr.with_data else "WITH NO DATA")
        return " ".join(parts), ()


class TruncateMixin:
    """Mixin for TRUNCATE support."""

    def supports_truncate(self) -> bool:
        """Whether TRUNCATE is supported."""
        return True

    def supports_truncate_table_keyword(self) -> bool:
        """Whether TABLE keyword is supported."""
        return True

    def supports_truncate_restart_identity(self) -> bool:
        """Whether RESTART IDENTITY is supported."""
        return False

    def supports_truncate_cascade(self) -> bool:
        """Whether CASCADE option is supported."""
        return False

    def format_truncate_statement(self, expr: "TruncateExpression") -> Tuple[str, tuple]:
        """Format TRUNCATE statement (generic implementation)."""
        sql = f"TRUNCATE TABLE {self.format_identifier(expr.table)}"
        if expr.restart_identity:
            sql += " RESTART IDENTITY"
        if expr.cascade:
            sql += " CASCADE"
        return sql, ()
