# src/rhosocial/activerecord/backend/impl/sqlite/mixins/geopoly.py
"""
SQLite Geopoly support mixin.

Provides Geopoly capability detection and SQL formatting.
SQL generation logic is migrated from the GeopolyExtension class,
eliminating the singleton delegation layer.
"""

from typing import Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

from .extension import SQLiteExtensionMixin

if TYPE_CHECKING:
    from ..expression.geopoly import (
        SQLiteGeopolyAreaExpression,
        SQLiteGeopolyContainsExpression,
        SQLiteGeopolyCreateVirtualTable,
    )


class SQLiteGeopolyMixin(SQLiteExtensionMixin):
    """Mixin for Geopoly polygon geometry support.

    Provides version-gated capability detection and SQL formatting
    for Geopoly virtual tables, point-in-polygon queries, and area calculations.
    """

    def supports_geopoly(self) -> bool:
        """Whether Geopoly virtual table is supported.

        Checks compile options first, falls back to version check.
        """
        compile_options = self.get_runtime_param("compile_options", {})
        if compile_options:
            return "ENABLE_GEOPOLY" in compile_options
        return self.version >= (3, 26, 0)

    # ========== SQL Formatting ==========

    def format_geopoly_create_virtual_table(self, expr: "SQLiteGeopolyCreateVirtualTable") -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE statement for Geopoly.

        Args:
            expr: SQLiteGeopolyCreateVirtualTable instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if self.version < (3, 26, 0):
            raise UnsupportedFeatureError(
                getattr(self, "name", "sqlite"), "Geopoly", "Geopoly requires SQLite 3.26.0 or later."
            )

        table = self.format_identifier(expr.table_name)
        cols = ", ".join(self.format_identifier(c) for c in expr.extra_columns) if expr.extra_columns else ""
        if expr.content_table:
            self._validate_safe_identifier(expr.content_table)
            sql = f"CREATE VIRTUAL TABLE {table} USING geopoly({cols}, content='{self._escape_sql_string(expr.content_table)}')"
            return sql, ()
        elif not cols:
            sql = f"CREATE VIRTUAL TABLE {table} USING geopoly()"
            return sql, ()
        else:
            sql = f"CREATE VIRTUAL TABLE {table} USING geopoly({cols})"
            return sql, ()

    def format_geopoly_contains_query(self, expr: "SQLiteGeopolyContainsExpression") -> Tuple[str, tuple]:
        """Format point-in-polygon query.

        Args:
            expr: SQLiteGeopolyContainsExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        table = self.format_identifier(expr.table_name)
        sql = f"SELECT * FROM {table} WHERE geopoly_contains_point(_shape, ?, ?)"
        return sql, (expr.longitude, expr.latitude)

    def format_geopoly_area_expression(self, expr: "SQLiteGeopolyAreaExpression") -> Tuple[str, tuple]:
        """Format area calculation query.

        Args:
            expr: SQLiteGeopolyAreaExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        table = self.format_identifier(expr.table_name)
        sql = f"SELECT *, geopoly_area(_shape) as area FROM {table}"
        return sql, ()
