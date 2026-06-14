# src/rhosocial/activerecord/backend/impl/sqlite/mixins/geopoly.py
"""
SQLite Geopoly support mixin.

Provides Geopoly capability detection and SQL formatting.
SQL generation logic is migrated from the GeopolyExtension class,
eliminating the singleton delegation layer.
"""

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

from .extension import SQLiteExtensionMixin


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

    def format_geopoly_create_virtual_table(self, expr) -> tuple:
        """Format CREATE VIRTUAL TABLE statement for Geopoly.

        Args:
            expr: GeopolyCreateVirtualTable instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if self.version < (3, 26, 0):
            raise UnsupportedFeatureError(
                getattr(self, "name", "sqlite"), "Geopoly", "Geopoly requires SQLite 3.26.0 or later."
            )

        cols = ", ".join(expr.extra_columns)
        if expr.content_table:
            sql = f'CREATE VIRTUAL TABLE "{expr.table_name}" USING geopoly({cols}, content="{expr.content_table}")'
        else:
            sql = f'CREATE VIRTUAL TABLE "{expr.table_name}" USING geopoly({cols})'

        return sql, ()

    def format_geopoly_contains_query(self, expr) -> tuple:
        """Format point-in-polygon query.

        Args:
            expr: GeopolyContainsExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        sql = f'SELECT * FROM "{expr.table_name}" WHERE geopoly_contains_point(_shape, ?, ?)'
        return sql, (expr.longitude, expr.latitude)

    def format_geopoly_area_expression(self, expr) -> tuple:
        """Format area calculation query.

        Args:
            expr: GeopolyAreaExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        sql = f'SELECT *, geopoly_area(_shape) as area FROM "{expr.table_name}"'
        return sql, ()
