# src/rhosocial/activerecord/backend/impl/sqlite/mixins/rtree.py
"""
SQLite R-Tree support mixin.

Provides R-Tree capability detection and SQL formatting.
SQL generation logic is migrated from the RTreeExtension class,
eliminating the singleton delegation layer.
"""

from typing import Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

from .extension import SQLiteExtensionMixin

if TYPE_CHECKING:
    from ..expression.rtree import SQLiteRTreeCreateVirtualTable, SQLiteRTreeRangeQuery


class SQLiteRTreeMixin(SQLiteExtensionMixin):
    """Mixin for R-Tree spatial index support.

    Provides version-gated capability detection and SQL formatting
    for R-Tree virtual tables and range queries.
    """

    def supports_rtree(self) -> bool:
        """Whether R-Tree virtual table is supported.

        Checks compile options first, falls back to version check.
        """
        compile_options = self.get_runtime_param("compile_options", {})
        if compile_options:
            return "ENABLE_RTREE" in compile_options
        return self.version >= (3, 6, 0)

    # ========== SQL Formatting ==========

    def format_rtree_create_virtual_table(self, expr: "SQLiteRTreeCreateVirtualTable") -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE statement for R-Tree.

        Args:
            expr: SQLiteRTreeCreateVirtualTable instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if self.version < (3, 6, 0):
            raise UnsupportedFeatureError(
                getattr(self, "name", "sqlite"), "R-Tree", "R-Tree requires SQLite 3.6.0 or later."
            )

        id_col = self.format_identifier("id")
        cols = [id_col]
        for i in range(expr.dimensions):
            cols.append(self.format_identifier(f"min{i}"))
            cols.append(self.format_identifier(f"max{i}"))

        table = self.format_identifier(expr.table)
        cols_str = ", ".join(cols)

        parts = []

        if expr.content_rowid and not expr.content_table:
            self._validate_safe_identifier(expr.content_rowid)

        if expr.content_table:
            self._validate_safe_identifier(expr.content_table)
            parts.append(f"content='{self._escape_sql_string(expr.content_table)}'")
            if expr.content_rowid:
                self._validate_safe_identifier(expr.content_rowid)
                parts.append(f"content_rowid='{self._escape_sql_string(expr.content_rowid)}'")

        if parts:
            full = f"{cols_str}, {', '.join(parts)}"
        else:
            full = cols_str

        sql = f"CREATE VIRTUAL TABLE {table} USING rtree({full})"
        return sql, ()

    def format_rtree_range_query(self, expr: "SQLiteRTreeRangeQuery") -> Tuple[str, tuple]:
        """Format range query for R-Tree table.

        Args:
            expr: SQLiteRTreeRangeQuery instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        table = self.format_identifier(expr.table)
        conditions = []
        params = []
        for i, (min_val, max_val) in enumerate(expr.ranges):
            if expr.column_names and i < len(expr.column_names):
                min_col = self.format_identifier(expr.column_names[i][0])
                max_col = self.format_identifier(expr.column_names[i][1])
            else:
                min_col = f"{table}.{self.format_identifier(f'min{i}')}"
                max_col = f"{table}.{self.format_identifier(f'max{i}')}"
            conditions.append(f"{min_col} <= ? AND {max_col} >= ?")
            params.extend([max_val, min_val])

        sql = f"SELECT * FROM {table} WHERE {' AND '.join(conditions)}"
        return sql, tuple(params)
