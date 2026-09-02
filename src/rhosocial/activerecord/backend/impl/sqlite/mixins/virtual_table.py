# src/rhosocial/activerecord/backend/impl/sqlite/mixins/virtual_table.py
"""
SQLite-specific Virtual Table implementation.

This module provides the SQLiteVirtualTableMixin class.
"""

from typing import Any, Dict, List, Optional, Set, Tuple

from .extension import SQLiteExtensionMixin

_KNOWN_VTABLE_MODULES: Set[str] = {
    "rtree", "fts5", "fts4", "fts3", "geopoly",
    "json_each", "json_tree", "generate_series",
    "csv", "dbstat", "dbpage", "wholenumber", "rtree_i32",
}


class SQLiteVirtualTableMixin(SQLiteExtensionMixin):
    """Mixin for SQLite virtual table support.

    Provides methods for creating and managing virtual tables
    including R-Tree, FTS5, Geopoly, and other virtual table modules.

    Version requirements:
    - Virtual tables (CREATE VIRTUAL TABLE): SQLite 3.8.8+
    - R-Tree: SQLite 3.6.0+
    - FTS5: SQLite 3.9.0+
    - Geopoly: SQLite 3.26.0+
    """

    # ========== Capability Detection ==========

    def supports_virtual_table(self) -> bool:
        """Whether virtual tables are supported."""
        version = self.version
        return version >= (3, 8, 8)

    def supports_rtree(self) -> bool:
        """Whether R-Tree virtual table is supported.

        Requires SQLITE_ENABLE_RTREE compile option.
        Falls back to version-based check if compile options not available.
        """
        compile_options = self.get_runtime_param("compile_options", {})
        if compile_options:
            return "ENABLE_RTREE" in compile_options
        version = self.version
        return version >= (3, 6, 0)

    def supports_fts5(self) -> bool:
        """Whether FTS5 virtual table is supported.

        Requires SQLITE_ENABLE_FTS5 compile option.
        Falls back to version-based check if compile options not available.
        """
        compile_options = self.get_runtime_param("compile_options", {})
        if compile_options:
            return "ENABLE_FTS5" in compile_options
        version = self.version
        return version >= (3, 9, 0)

    def supports_geopoly(self) -> bool:
        """Whether Geopoly virtual table is supported.

        Requires SQLITE_ENABLE_GEOPOLY compile option.
        Falls back to version-based check if compile options not available.
        """
        compile_options = self.get_runtime_param("compile_options", {})
        if compile_options:
            return "ENABLE_GEOPOLY" in compile_options
        version = self.version
        return version >= (3, 26, 0)

    def supports_math_functions(self) -> bool:
        """Whether built-in math functions are supported.

        SQLite 3.35.0+ includes built-in math functions, but they must be
        enabled at compile time. Runtime detection is needed for older versions.

        Returns:
            True if math functions are supported
        """
        version = self.version
        if version >= (3, 35, 0):
            return self.get_runtime_param("math_functions_available", True)
        return False

    def supports_json1_extension(self) -> bool:
        """Whether json1 extension is available.

        The json1 extension provides JSON functions. It was an optional
        extension in older SQLite versions. Starting from 3.38.0,
        it's built-in by default. Runtime detection is needed for
        older versions.

        Returns:
            True if json1 extension is available
        """
        version = self.version
        if version >= (3, 38, 0):
            return True
        return self.get_runtime_param("json1_available", False)

    def format_create_virtual_table(
        self,
        module: str,
        table: str,
        columns: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE statement.

        Args:
            module: Virtual table module (rtree, fts5, geopoly, etc.)
            table: Name of the virtual table
            columns: List of column names
            options: Optional module-specific options

        Returns:
            Tuple of (SQL string, parameters tuple)

        Raises:
            ValueError: If module name contains unsafe characters
        """
        if module not in _KNOWN_VTABLE_MODULES and not module.isidentifier():
            raise ValueError(f"Unsafe virtual table module name: {module!r}")
        name = self.format_identifier(table)
        cols = ", ".join(self.format_identifier(c) for c in columns)
        sql = f"CREATE VIRTUAL TABLE {name} USING {module}({cols})"
        return sql, ()

    def format_drop_virtual_table(
        self,
        table: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """Format DROP TABLE statement for a virtual table.

        Args:
            table: Name of the virtual table
            if_exists: Add IF EXISTS clause

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        name = self.format_identifier(table)
        if if_exists:
            return f"DROP TABLE IF EXISTS {name}", ()
        return f"DROP TABLE {name}", ()

    def format_match_predicate(
        self,
        expr,
    ) -> Tuple[str, tuple]:
        """Format full-text search MATCH predicate (delegates to FTS5Mixin)."""
        return self.format_fts5_match_expression(expr.table, expr.query, expr.columns, expr.negate)


