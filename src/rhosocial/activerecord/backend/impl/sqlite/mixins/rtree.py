# src/rhosocial/activerecord/backend/impl/sqlite/mixins/rtree.py
"""
SQLite R-Tree support mixin.

Provides R-Tree capability detection and SQL formatting.
SQL generation logic is migrated from the RTreeExtension class,
eliminating the singleton delegation layer.
"""

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

from .extension import SQLiteExtensionMixin


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

    def format_rtree_create_virtual_table(self, expr) -> tuple:
        """Format CREATE VIRTUAL TABLE statement for R-Tree.

        Args:
            expr: RTreeCreateVirtualTable instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if self.version < (3, 6, 0):
            raise UnsupportedFeatureError(
                getattr(self, "name", "sqlite"), "R-Tree", "R-Tree requires SQLite 3.6.0 or later."
            )

        cols = ["id"]
        for i in range(expr.dimensions):
            cols.extend([f"min{i}", f"max{i}"])

        if expr.content_table:
            if expr.content_rowid:
                sql = (
                    f'CREATE VIRTUAL TABLE "{expr.table_name}" USING rtree'
                    f'({", ".join(cols)}, content="{expr.content_table}", content_rowid="{expr.content_rowid}")'
                )
            else:
                sql = f'CREATE VIRTUAL TABLE "{expr.table_name}" USING rtree({", ".join(cols)}, content="{expr.content_table}")'
        else:
            sql = f'CREATE VIRTUAL TABLE "{expr.table_name}" USING rtree({", ".join(cols)})'

        return sql, ()

    def format_rtree_range_query(self, expr) -> tuple:
        """Format range query for R-Tree table.

        Args:
            expr: RTreeRangeQuery instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        conditions = []
        params = []
        for i, (min_val, max_val) in enumerate(expr.ranges):
            if expr.column_names:
                min_col, max_col = expr.column_names[i]
            else:
                min_col, max_col = f'"{expr.table_name}".min{i}', f'"{expr.table_name}".max{i}'
            conditions.append(f"{min_col} >= ? AND {max_col} <= ?")
            params.extend([min_val, max_val])

        sql = f'SELECT * FROM "{expr.table_name}" WHERE {" AND ".join(conditions)}'
        return sql, tuple(params)
