# src/rhosocial/activerecord/backend/impl/sqlite/protocols.py
"""
SQLite-specific protocol definitions.

This module defines protocol interfaces for SQLite-specific features
that are not part of the standard SQL dialect protocols.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from .expression.attach import SQLiteAttachExpression, SQLiteDetachExpression
    from .expression.fts5 import (
        SQLiteFTS5CreateVirtualTable,
        SQLiteFTS5HighlightExpression,
        SQLiteFTS5RankExpression,
        SQLiteFTS5SnippetExpression,
    )
    from .expression.geopoly import (
        SQLiteGeopolyAreaExpression,
        SQLiteGeopolyContainsExpression,
        SQLiteGeopolyCreateVirtualTable,
    )
    from .expression.reindex import SQLiteReindexExpression
    from .expression.rtree import SQLiteRTreeCreateVirtualTable, SQLiteRTreeRangeQuery
    from .expression.vacuum import SQLiteAnalyzeExpression, SQLiteVacuumExpression


@runtime_checkable
class SQLiteExtensionSupport(Protocol):
    """Protocol for SQLite extension support in dialects/backends.

    Defines the interface for extension detection and feature checking.
    """

    def detect_extensions(self) -> Dict[str, Any]:
        """Detect all available extensions.

        Returns:
            Dictionary mapping extension names to their info
        """
        ...

    def is_extension_available(self, name: str) -> bool:
        """Check if a specific extension is available.

        Args:
            name: Extension name

        Returns:
            True if extension is available
        """
        ...

    def get_extension_info(self, name: str) -> Optional[Any]:
        """Get information about a specific extension.

        Args:
            name: Extension name

        Returns:
            Extension info, or None if not found
        """
        ...

    def check_extension_feature(self, ext_name: str, feature_name: str) -> bool:
        """Check if an extension feature is available.

        Args:
            ext_name: Extension name
            feature_name: Feature name

        Returns:
            True if feature is available
        """
        ...

    def get_supported_extension_features(self, ext_name: str) -> List[str]:
        """Get list of supported features for an extension.

        Args:
            ext_name: Extension name

        Returns:
            List of supported feature names
        """
        ...

    def set_runtime_param(self, key: str, value: Any) -> None:
        """Set a runtime parameter (detected after connection).

        Args:
            key: Parameter key
            value: Parameter value
        """
        ...

    def get_runtime_param(self, key: str, default: Any = None) -> Any:
        """Get a runtime parameter.

        Args:
            key: Parameter key
            default: Default value if key not found

        Returns:
            Parameter value, or default if not found
        """
        ...


@runtime_checkable
class SQLitePragmaSupport(Protocol):
    """Protocol for SQLite PRAGMA support in dialects/backends.

    Defines the interface for PRAGMA operations.
    """

    def get_pragma_info(self, name: str) -> Optional[Any]:
        """Get information about a specific PRAGMA.

        Args:
            name: PRAGMA name

        Returns:
            PragmaInfo, or None if not found
        """
        ...

    def get_pragma_sql(self, name: str, argument: Any = None) -> str:
        """Get SQL for reading a PRAGMA.

        Args:
            name: PRAGMA name
            argument: Optional argument

        Returns:
            SQL string
        """
        ...

    def set_pragma_sql(self, name: str, value: Any, argument: Any = None) -> str:
        """Get SQL for setting a PRAGMA.

        Args:
            name: PRAGMA name
            value: Value to set
            argument: Optional argument

        Returns:
            SQL string
        """
        ...

    def is_pragma_available(self, name: str) -> bool:
        """Check if a PRAGMA is available.

        Args:
            name: PRAGMA name

        Returns:
            True if available
        """
        ...

    def get_pragmas_by_category(self, category: Any) -> List[Any]:
        """Get all pragmas in a category.

        Args:
            category: PRAGMA category

        Returns:
            List of PragmaInfo for pragmas in the category
        """
        ...

    def get_all_pragma_infos(self) -> Dict[str, Any]:
        """Get information for all known pragmas.

        Returns:
            Dictionary mapping PRAGMA names to their info
        """
        ...


@runtime_checkable
class SQLiteVirtualTableSupport(Protocol):
    """Protocol for SQLite virtual table support.

    Defines the interface for virtual table operations including
    R-Tree, FTS5, Geopoly, and other virtual table modules.

    Reference: https://www.sqlite.org/vtab.html
    """

    # ========== Capability Detection ==========

    def supports_virtual_table(self) -> bool:
        """Whether virtual tables are supported (SQLite 3.8.8+)."""
        ...

    def supports_rtree(self) -> bool:
        """Whether R-Tree virtual table is supported (SQLite 3.6.0+)."""
        ...

    def supports_fts5(self) -> bool:
        """Whether FTS5 virtual table is supported (SQLite 3.9.0+)."""
        ...

    def supports_geopoly(self) -> bool:
        """Whether Geopoly virtual table is supported (SQLite 3.26.0+)."""
        ...

    def supports_math_functions(self) -> bool:
        """Whether built-in math functions are supported (SQLite 3.35.0+)."""
        ...

    def supports_json1_extension(self) -> bool:
        """Whether json1 extension is available (SQLite 3.38.0+ or runtime detection)."""
        ...

    # ========== Virtual Table SQL Formatting ==========

    def format_create_virtual_table(
        self,
        module: str,
        table_name: str,
        columns: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE statement.

        Args:
            module: Virtual table module (rtree, fts5, geopoly, etc.)
            table_name: Name of the virtual table
            columns: List of column names
            options: Optional module-specific options

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_drop_virtual_table(
        self,
        table_name: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """Format DROP TABLE statement for virtual table.

        Args:
            table_name: Name of the virtual table
            if_exists: Add IF EXISTS clause

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    # ========== FTS MATCH Predicate ==========

    def format_match_predicate(
        self,
        expr: Any,
    ) -> Tuple[str, tuple]:
        """Format full-text search MATCH predicate.

        This method formats a MATCH predicate for FTS virtual tables.
        Unlike standard SQL predicates, this is SQLite-specific.

        NOTE: negate is NOT supported for FTS5 (raises ValueError).
        Use query-level negation instead: 'python NOT java'.

        Args:
            expr: SQLiteMatchPredicate instance

        Returns:
            Tuple of (SQL string, parameters tuple)

        Raises:
            ValueError: If negate=True for FTS5
        """
        ...


@runtime_checkable
class SQLiteReindexSupport(Protocol):
    """Protocol for SQLite REINDEX statement support.

    SQLite supports the REINDEX statement for rebuilding indexes.

    Official Documentation:
    - REINDEX: https://www.sqlite.org/lang_reindex.html

    Version Requirements:
    - REINDEX: All SQLite versions
    - REINDEX EXPRESSIONS: SQLite 3.53.0+
    """

    def supports_reindex(self) -> bool:
        """Whether REINDEX statement is supported."""
        ...

    def supports_reindex_expressions(self) -> bool:
        """Whether REINDEX EXPRESSIONS is supported (SQLite 3.53.0+)."""
        ...

    def format_reindex_statement(self, expr: "SQLiteReindexExpression") -> Tuple[str, tuple]:
        """Format REINDEX statement.

        Args:
            expr: SQLiteReindexExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...


@runtime_checkable
class SQLiteMaintenanceSupport(Protocol):
    """Protocol for SQLite database-maintenance statement support.

    Covers VACUUM, ANALYZE, ATTACH DATABASE, and DETACH DATABASE.

    Version Requirements:
    - VACUUM / ANALYZE / ATTACH / DETACH: All SQLite versions (3.0+)
    - VACUUM INTO 'filename': SQLite 3.27.0+
    """

    def supports_vacuum(self) -> bool:
        """Whether VACUUM is supported."""
        ...

    def supports_vacuum_into(self) -> bool:
        """Whether VACUUM INTO 'filename' is supported (SQLite 3.27.0+)."""
        ...

    def supports_analyze(self) -> bool:
        """Whether ANALYZE is supported."""
        ...

    def supports_attach(self) -> bool:
        """Whether ATTACH DATABASE is supported."""
        ...

    def supports_detach(self) -> bool:
        """Whether DETACH DATABASE is supported."""
        ...

    def format_vacuum_statement(self, expr: "SQLiteVacuumExpression") -> Tuple[str, tuple]:
        """Format a VACUUM statement.

        Args:
            expr: SQLiteVacuumExpression instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...

    def format_analyze_statement(self, expr: "SQLiteAnalyzeExpression") -> Tuple[str, tuple]:
        """Format an ANALYZE statement.

        Args:
            expr: SQLiteAnalyzeExpression instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...

    def format_attach_statement(self, expr: "SQLiteAttachExpression") -> Tuple[str, tuple]:
        """Format an ATTACH DATABASE statement.

        Args:
            expr: SQLiteAttachExpression instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...

    def format_detach_statement(self, expr: "SQLiteDetachExpression") -> Tuple[str, tuple]:
        """Format a DETACH DATABASE statement.

        Args:
            expr: SQLiteDetachExpression instance.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...


@runtime_checkable
class SQLiteFTS5Support(Protocol):
    """Protocol for FTS5 full-text search support in SQLite dialects."""

    def supports_fts5(self) -> bool:
        """Whether FTS5 virtual table is supported."""
        ...

    def supports_fts5_bm25(self) -> bool:
        """Whether BM25 ranking function is supported."""
        ...

    def supports_fts5_highlight(self) -> bool:
        """Whether highlight() function is supported."""
        ...

    def supports_fts5_snippet(self) -> bool:
        """Whether snippet() function is supported."""
        ...

    def get_supported_fts5_tokenizers(self) -> List[str]:
        """Get list of supported FTS5 tokenizers."""
        ...

    def format_fts5_match_expression(
        self, table: str, query: str, columns: Optional[List[str]] = None, negate: bool = False
    ) -> Tuple[str, tuple]:
        """Format FTS5 MATCH expression."""
        ...

    def format_fts5_create_virtual_table(self, expr: "SQLiteFTS5CreateVirtualTable") -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE for FTS5."""
        ...

    def format_fts5_rank_expression(self, expr: "SQLiteFTS5RankExpression") -> Tuple[str, tuple]:
        """Format FTS5 ranking expression."""
        ...

    def format_fts5_highlight_expression(self, expr: "SQLiteFTS5HighlightExpression") -> Tuple[str, tuple]:
        """Format highlight() function expression."""
        ...

    def format_fts5_snippet_expression(self, expr: "SQLiteFTS5SnippetExpression") -> Tuple[str, tuple]:
        """Format snippet() function expression."""
        ...


@runtime_checkable
class SQLiteRTreeSupport(Protocol):
    """Protocol for R-Tree spatial index support in SQLite dialects."""

    def supports_rtree(self) -> bool:
        """Whether R-Tree virtual table is supported."""
        ...

    def format_rtree_create_virtual_table(self, expr: "SQLiteRTreeCreateVirtualTable") -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE for R-Tree."""
        ...

    def format_rtree_range_query(self, expr: "SQLiteRTreeRangeQuery") -> Tuple[str, tuple]:
        """Format R-Tree range query."""
        ...


@runtime_checkable
class SQLiteGeopolySupport(Protocol):
    """Protocol for Geopoly polygon geometry support in SQLite dialects."""

    def supports_geopoly(self) -> bool:
        """Whether Geopoly virtual table is supported."""
        ...

    def format_geopoly_create_virtual_table(self, expr: "SQLiteGeopolyCreateVirtualTable") -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE for Geopoly."""
        ...

    def format_geopoly_contains_query(self, expr: "SQLiteGeopolyContainsExpression") -> Tuple[str, tuple]:
        """Format Geopoly point-in-polygon query."""
        ...

    def format_geopoly_area_expression(self, expr: "SQLiteGeopolyAreaExpression") -> Tuple[str, tuple]:
        """Format Geopoly area calculation."""
        ...


@runtime_checkable
class SQLiteJSON1Support(Protocol):
    """Protocol for JSON1 extension support in SQLite dialects."""

    def supports_json1_extension(self) -> bool:
        """Whether json1 extension is available."""
        ...
