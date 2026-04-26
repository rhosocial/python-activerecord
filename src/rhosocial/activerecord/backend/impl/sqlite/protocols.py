# src/rhosocial/activerecord/backend/impl/sqlite/protocols.py
"""
SQLite-specific protocol definitions.

This module defines protocol interfaces for SQLite-specific features
that are not part of the standard SQL dialect protocols.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


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

    # ========== FTS5 Capability Detection ==========

    def supports_fts5_bm25(self) -> bool:
        """Whether BM25 ranking function is supported (SQLite 3.9.0+)."""
        ...

    def supports_fts5_highlight(self) -> bool:
        """Whether highlight() function is supported (SQLite 3.9.0+)."""
        ...

    def supports_fts5_snippet(self) -> bool:
        """Whether snippet() function is supported (SQLite 3.9.0+)."""
        ...

    def supports_fts5_offset(self) -> bool:
        """Whether offset() function is supported (SQLite 3.9.0+)."""
        ...

    def get_supported_fts5_tokenizers(self) -> List[str]:
        """Get list of supported FTS5 tokenizers."""
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

    # ========== FTS5 SQL Formatting ==========

    def format_fts5_create_virtual_table(
        self,
        table_name: str,
        columns: List[str],
        tokenizer: Optional[str] = None,
        tokenizer_options: Optional[Dict[str, Any]] = None,
        prefix: Optional[List[int]] = None,
        content: Optional[str] = None,
        content_rowid: Optional[str] = None,
        tokenize: Optional[str] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE statement for FTS5.

        Args:
            table_name: Name of the FTS5 virtual table
            columns: List of column names to be indexed
            tokenizer: Tokenizer name (e.g., 'unicode61', 'porter')
            tokenizer_options: Tokenizer options (e.g., {'remove_diacritics': 1})
            prefix: List of prefix lengths for prefix indexing
            content: Content table name (for external content FTS5)
            content_rowid: Column name for rowid in content table
            tokenize: Full tokenize specification string (alternative to tokenizer)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_fts5_match_expression(
        self,
        table_name: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ) -> Tuple[str, tuple]:
        """Format FTS5 MATCH expression for use in WHERE clause.

        Args:
            table_name: Name of the FTS5 virtual table
            query: Full-text search query string
            columns: Specific columns to search (None for all columns)
            negate: If True, negate the match (NOT MATCH)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_fts5_rank_expression(
        self,
        table_name: str,
        weights: Optional[List[float]] = None,
        bm25_params: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, tuple]:
        """Format FTS5 ranking expression using bm25().

        Args:
            table_name: Name of the FTS5 virtual table
            weights: Column weights for ranking (order matches column order)
            bm25_params: BM25 parameters (k1, b) for ranking customization

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_fts5_highlight_expression(
        self,
        table_name: str,
        column: str,
        query: str,
        prefix_marker: str = "<b>",
        suffix_marker: str = "</b>",
    ) -> Tuple[str, tuple]:
        """Format highlight() function expression.

        Args:
            table_name: Name of the FTS5 virtual table
            column: Column name to highlight
            query: Search query (for ranking)
            prefix_marker: HTML/text to prepend to matches
            suffix_marker: HTML/text to append to matches

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_fts5_snippet_expression(
        self,
        table_name: str,
        column: str,
        query: str,
        prefix_marker: str = "<b>",
        suffix_marker: str = "</b>",
        context_tokens: int = 10,
        ellipsis: str = "...",
    ) -> Tuple[str, tuple]:
        """Format snippet() function expression.

        Args:
            table_name: Name of the FTS5 virtual table
            column: Column name to snippet
            query: Search query (for ranking)
            prefix_marker: HTML/text to prepend to matches
            suffix_marker: HTML/text to append to matches
            context_tokens: Number of context tokens around match
            ellipsis: String to use as ellipsis marker

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_fts5_offset_expression(
        self,
        table_name: str,
        column: str,
    ) -> Tuple[str, tuple]:
        """Format offset() function expression.

        The offset() function returns the byte offset of the current
        match within the column content.

        Args:
            table_name: Name of the FTS5 virtual table
            column: Column name to get offsets for

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_fts5_drop_virtual_table(
        self,
        table_name: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """Format DROP TABLE statement for FTS5 virtual table.

        Args:
            table_name: Name of the FTS5 virtual table
            if_exists: Add IF EXISTS clause

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    # ========== FTS MATCH Predicate ==========

    def format_match_predicate(
        self,
        table: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ) -> Tuple[str, tuple]:
        """Format full-text search MATCH predicate.

        This method formats a MATCH predicate for FTS virtual tables.
        Unlike standard SQL predicates, this is SQLite-specific.

        Args:
            table: Name of the FTS table to match against
            query: Full-text search query string
            columns: Specific columns to search (None for all columns)
            negate: If True, negate the match (NOT MATCH)

        Returns:
            Tuple of (SQL string, parameters tuple)

        Example:
            >>> dialect.format_match_predicate('docs', 'python')
            ('"docs" MATCH ?', ('python',))

            >>> dialect.format_match_predicate(
            ...     'docs', 'python', columns=['title'], negate=True
            ... )
            ('NOT "docs" MATCH ?', ('python',))
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

    def format_reindex_statement(self, expr: Any) -> Tuple[str, tuple]:
        """Format REINDEX statement.

        Args:
            expr: SQLiteReindexExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
