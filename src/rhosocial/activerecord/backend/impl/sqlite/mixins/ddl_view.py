# src/rhosocial/activerecord/backend/impl/sqlite/mixins/ddl_view.py
"""
SQLite-specific View implementation.

This module provides the SQLiteViewMixin class.
"""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.statements import (
        CreateViewStatement,
        DropViewStatement,
        CreateMaterializedViewStatement,
        DropMaterializedViewStatement,
        RefreshMaterializedViewStatement,
    )

_SUGGESTION_MATERIALIZED_VIEW = "SQLite does not support materialized views."
_SUGGESTION_MATERIALIZED_VIEW_ALT = (
    "SQLite does not support materialized views. Consider using regular views "
    "or creating tables to store precomputed results."
)


class SQLiteViewMixin:
    """SQLite view DDL formatting (basic views, no materialized views)."""

    def supports_create_view(self) -> bool:
        """SQLite supports CREATE VIEW."""
        return True

    def supports_create_view_bind_parameters(self) -> bool:
        """SQLite stores a view's text, so a bind in it has no meaning later.

        The placeholder would be stored in the view's SQL and left unbound
        when the view is read, so the body is refused rather than stored
        broken.
        """
        return False

    def supports_drop_view(self) -> bool:
        """SQLite supports DROP VIEW."""
        return True

    def supports_or_replace_view(self) -> bool:
        """SQLite supports CREATE OR REPLACE VIEW."""
        return True

    def supports_create_or_replace_view(self) -> bool:
        """SQLite supports CREATE OR REPLACE VIEW."""
        return True

    def supports_if_not_exists_view(self) -> bool:
        """SQLite supports CREATE VIEW IF NOT EXISTS."""
        return True

    def supports_temporary_view(self) -> bool:
        """SQLite supports TEMPORARY views."""
        return True

    def supports_materialized_view(self) -> bool:
        """SQLite does not support materialized views."""
        return False

    def supports_refresh_materialized_view(self) -> bool:
        """SQLite does not support REFRESH MATERIALIZED VIEW."""
        return False

    def supports_materialized_view_tablespace(self) -> bool:
        """SQLite does not support tablespace for materialized views."""
        return False

    def supports_materialized_view_storage_options(self) -> bool:
        """SQLite does not support storage options for materialized views."""
        return False

    def supports_if_exists_view(self) -> bool:
        """SQLite supports DROP VIEW IF EXISTS."""
        return True

    def supports_view_check_option(self) -> bool:
        """SQLite does not support WITH CHECK OPTION."""
        return False

    def supports_cascade_view(self) -> bool:
        """SQLite does not support CASCADE for DROP VIEW."""
        return False

    def supports_with_data_clause(self) -> bool:
        """SQLite has no WITH [NO] DATA clause (no materialized views, and
        ``CREATE TABLE ... AS`` is always populated)."""
        return False

    def format_create_view_statement(self, expr: "CreateViewStatement") -> Tuple[str, tuple]:
        """Format CREATE VIEW statement for SQLite."""
        parts = ["CREATE"]
        if expr.temporary:
            parts.append("TEMPORARY")
        if expr.replace and self.supports_create_or_replace_view():
            parts.append("VIEW IF NOT EXISTS")
        elif expr.if_not_exists and self.supports_if_not_exists_view():
            parts.append("VIEW IF NOT EXISTS")
        else:
            parts.append("VIEW")
        parts.append(expr.view.to_sql()[0])

        if expr.column_aliases:
            cols = ", ".join(self.format_identifier(c) for c in expr.column_aliases)
            parts.append(f"({cols})")

        query_sql, query_params = expr.query.to_sql()
        parts.append(f"AS {query_sql}")

        if query_params:
            import warnings
            warnings.warn(
                "SQLite does not allow parameters in VIEW definitions. "
                "The query contains parameters which will cause a runtime error. "
                "Use RawSQLPredicate to inline literal values instead.",
                UserWarning,
                stacklevel=3,
            )

        return " ".join(parts), query_params

    def format_drop_view_statement(self, expr: "DropViewStatement") -> Tuple[str, tuple]:
        """Format DROP VIEW statement for SQLite.

        SQLite does not accept CASCADE or RESTRICT on DROP VIEW; asking for
        either raises rather than dropping the request.
        """
        if expr.cascade:
            raise UnsupportedFeatureError(
                self.name, "DROP VIEW CASCADE",
                "SQLite does not support DROP VIEW CASCADE.",
            )
        if expr.restrict:
            raise UnsupportedFeatureError(
                self.name, "DROP VIEW RESTRICT",
                "SQLite does not support DROP VIEW RESTRICT.",
            )
        parts = ["DROP VIEW"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(expr.view.to_sql()[0])
        return " ".join(parts), ()

    def format_create_materialized_view_statement(self, expr: "CreateMaterializedViewStatement") -> Tuple[str, tuple]:
        """Format CREATE MATERIALIZED VIEW statement - not supported by SQLite."""
        raise UnsupportedFeatureError(self.name, "CREATE MATERIALIZED VIEW", _SUGGESTION_MATERIALIZED_VIEW_ALT)

    def format_drop_materialized_view_statement(self, expr: "DropMaterializedViewStatement") -> Tuple[str, tuple]:
        """Format DROP MATERIALIZED VIEW statement - not supported by SQLite."""
        raise UnsupportedFeatureError(self.name, "DROP MATERIALIZED VIEW", _SUGGESTION_MATERIALIZED_VIEW)

    def format_refresh_materialized_view_statement(
        self, expr: "RefreshMaterializedViewStatement"
    ) -> Tuple[str, tuple]:
        """Format REFRESH MATERIALIZED VIEW statement - not supported by SQLite."""
        raise UnsupportedFeatureError(self.name, "REFRESH MATERIALIZED VIEW", _SUGGESTION_MATERIALIZED_VIEW)


# =============================================================================
# SQLiteTriggerMixin — Trigger DDL support
# =============================================================================

