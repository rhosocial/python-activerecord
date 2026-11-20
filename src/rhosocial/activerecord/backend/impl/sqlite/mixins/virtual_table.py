# src/rhosocial/activerecord/backend/impl/sqlite/mixins/virtual_table.py
"""
SQLite-specific Virtual Table implementation.

This module provides the SQLiteVirtualTableMixin class.
"""

from typing import Tuple, TYPE_CHECKING

from .extension import SQLiteExtensionMixin

if TYPE_CHECKING:
    from ..expression.fts5 import SQLiteFTS5MatchPredicate
    from ..expression.virtual_table import CreateVirtualTableStatement, DropVirtualTableStatement


class SQLiteVirtualTableMixin(SQLiteExtensionMixin):
    """Mixin for SQLite virtual table support.

    Provides the statements that create and drop a virtual table, and the
    probes that are about the virtual-table mechanism itself. The module-
    specific probes are declared here because the protocol declares them, but
    the answers are computed by the module that owns each feature --
    ``SQLiteFTS5Mixin``, ``SQLiteRTreeMixin`` and ``SQLiteGeopolyMixin`` -- so
    there is one copy of each check rather than one per class.

    Version requirements:
    - Virtual tables (CREATE VIRTUAL TABLE): SQLite 3.8.8+
    """

    # ========== Capability Detection ==========

    def supports_virtual_table(self) -> bool:
        """Whether virtual tables are supported."""
        return self.version_at_least((3, 8, 8))

    def supports_rtree(self) -> bool:
        """Whether R-Tree virtual table is supported.

        The compile-option check belongs to :class:`SQLiteRTreeMixin`; this
        answers the protocol's question by asking it rather than repeating it.
        """
        from .rtree import SQLiteRTreeMixin

        return SQLiteRTreeMixin.supports_rtree(self)

    def supports_fts5(self) -> bool:
        """Whether FTS5 virtual table is supported."""
        from .fts5 import SQLiteFTS5Mixin

        return SQLiteFTS5Mixin.supports_fts5(self)

    def supports_geopoly(self) -> bool:
        """Whether Geopoly virtual table is supported."""
        from .geopoly import SQLiteGeopolyMixin

        return SQLiteGeopolyMixin.supports_geopoly(self)

    def supports_math_functions(self) -> bool:
        """Whether built-in math functions are supported.

        SQLite 3.35.0+ includes built-in math functions, but they must be
        enabled at compile time. Runtime detection is needed for older versions.

        Returns:
            True if math functions are supported
        """
        if self.version_at_least((3, 35, 0)):
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
        if self.version_at_least((3, 38, 0)):
            return True
        return self.get_runtime_param("json1_available", False)

    def format_create_virtual_table_statement(
        self,
        expr: "CreateVirtualTableStatement",
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE statement.

        Args:
            expr: CreateVirtualTableStatement instance

        Returns:
            Tuple of (SQL string, parameters tuple)

        Raises:
            ValueError: If module name contains unsafe characters
        """
        # The virtual table modules SQLite ships, plus the two spellings of the
        # R-Tree index width. Any other module name must be a plain identifier,
        # so the check is "known, or a name that cannot contain anything else".
        known_modules = {
            "rtree", "fts5", "fts4", "fts3", "geopoly",
            "json_each", "json_tree", "generate_series",
            "csv", "dbstat", "dbpage", "wholenumber", "rtree_i32",
        }
        if expr.module not in known_modules and not expr.module.isidentifier():
            raise ValueError(f"Unsafe virtual table module name: {expr.module!r}")
        name = expr.table.to_sql()[0]
        cols = ", ".join(self.format_identifier(c) for c in expr.columns)
        sql = f"CREATE VIRTUAL TABLE {name} USING {expr.module}({cols})"
        return sql, ()

    def format_drop_virtual_table_statement(
        self,
        expr: "DropVirtualTableStatement",
    ) -> Tuple[str, tuple]:
        """Format DROP TABLE statement for a virtual table.

        Args:
            expr: DropVirtualTableStatement instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        name = expr.table.to_sql()[0]
        if expr.if_exists:
            return f"DROP TABLE IF EXISTS {name}", ()
        return f"DROP TABLE {name}", ()

    def format_match_predicate(
        self,
        expr: "SQLiteFTS5MatchPredicate",
    ) -> Tuple[str, tuple]:
        """Format full-text search MATCH predicate (delegates to FTS5Mixin)."""
        return self.format_fts5_match_expression(expr)


