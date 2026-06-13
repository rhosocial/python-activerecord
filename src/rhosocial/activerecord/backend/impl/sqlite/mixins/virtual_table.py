# src/rhosocial/activerecord/backend/impl/sqlite/mixins/virtual_table.py
"""
SQLite-specific Virtual Table implementation.

This module provides the SQLiteVirtualTableMixin class.
"""

from typing import Any, Dict, List, Optional, Tuple
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

from ..extension.extensions import (
    get_fts5_extension,
)
from .extension import SQLiteExtensionMixin

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

    # ========== FTS5 Capability Detection ==========

    def supports_fts5_bm25(self) -> bool:
        """Whether BM25 ranking function is supported.

        BM25 is the default ranking function in FTS5, available
        since SQLite 3.9.0.

        Returns:
            True if BM25 is supported
        """
        return self.check_extension_feature("fts5", "bm25_ranking")

    def supports_fts5_highlight(self) -> bool:
        """Whether highlight() function is supported.

        The highlight() function returns a copy of the text with
        search terms surrounded by specified markers.

        Returns:
            True if highlight() is supported
        """
        return self.check_extension_feature("fts5", "highlight")

    def supports_fts5_snippet(self) -> bool:
        """Whether snippet() function is supported.

        The snippet() function returns a fragment of text with
        search terms highlighted.

        Returns:
            True if snippet() is supported
        """
        return self.check_extension_feature("fts5", "snippet")

    def get_supported_fts5_tokenizers(self) -> List[str]:
        """Get list of supported FTS5 tokenizers.

        Standard tokenizers:
        - 'unicode61': Default tokenizer, supports Unicode (since 3.9.0)
        - 'ascii': Simple ASCII tokenizer (since 3.9.0)
        - 'porter': Porter stemmer wrapper (since 3.9.0)
        - 'trigram': Trigram tokenizer (since 3.34.0)

        Returns:
            List of supported tokenizer names
        """
        tokenizers = ["unicode61", "ascii", "porter"]
        if self.check_extension_feature("fts5", "trigram_tokenizer"):
            tokenizers.append("trigram")
        return tokenizers

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
        if module.lower() == "rtree":
            return self._format_rtree_create(table_name, columns, options)
        elif module.lower() == "fts5":
            return self._format_fts5_create(table_name, columns, options)
        elif module.lower() == "geopoly":
            return self._format_geopoly_create(table_name, columns, options)
        else:
            raise ValueError(f"Unknown virtual table module: {module}")

    def _format_rtree_create(
        self,
        table_name: str,
        columns: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE for R-Tree."""
        from .extension.extensions.rtree import get_rtree_extension

        version = self.version
        if version < (3, 6, 0):
            raise UnsupportedFeatureError(
                getattr(self, "name", "sqlite"), "R-Tree", "R-Tree requires SQLite 3.6.0 or later."
            )

        rtree = get_rtree_extension()
        dimensions = options.get("dimensions", 2) if options else 2
        return rtree.format_create_virtual_table(
            table_name=table_name,
            dimensions=dimensions,
        )

    def _format_fts5_create(
        self,
        table_name: str,
        columns: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE for FTS5."""
        return self.format_fts5_create_virtual_table(
            table_name=table_name,
            columns=columns,
            **(options or {}),
        )

    def _format_geopoly_create(
        self,
        table_name: str,
        columns: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE for Geopoly."""
        from .extension.extensions.geopoly import get_geopoly_extension

        version = self.version
        if version < (3, 26, 0):
            raise UnsupportedFeatureError(
                getattr(self, "name", "sqlite"), "Geopoly", "Geopoly requires SQLite 3.26.0 or later."
            )

        geopoly = get_geopoly_extension()
        extra_cols = []
        for c in columns:
            if c != "_shape":
                extra_cols.append(c)
        extra_columns = extra_cols if extra_cols else None
        return geopoly.format_create_virtual_table(
            table_name=table_name,
            content_table=options.get("content") if options else None,
            extra_columns=extra_columns,
        )

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
        quoted = self.format_identifier(table_name)
        if if_exists:
            return f"DROP TABLE IF EXISTS {quoted}", ()
        return f"DROP TABLE {quoted}", ()

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
        if not self.supports_fts5():
            raise UnsupportedFeatureError(
                getattr(self, "name", "sqlite"), "FTS5", "FTS5 full-text search requires SQLite 3.9.0 or later."
            )

        fts5 = get_fts5_extension()
        return fts5.format_create_virtual_table(
            table_name=table_name,
            columns=columns,
            tokenizer=tokenizer,
            tokenizer_options=tokenizer_options,
            prefix=prefix,
            content=content,
            content_rowid=content_rowid,
            tokenize=tokenize,
        )

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
        fts5 = get_fts5_extension()
        return fts5.format_match_expression(
            table_name=table_name,
            query=query,
            columns=columns,
            negate=negate,
        )

    def format_match_predicate(
        self,
        table: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ) -> Tuple[str, tuple]:
        """Format full-text search MATCH predicate for FTS.

        This method delegates to format_fts5_match_expression for
        the actual formatting logic.

        Args:
            table: Name of the FTS table
            query: Full-text search query string
            columns: Specific columns to search (None for all columns)
            negate: If True, negate the match (NOT MATCH)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return self.format_fts5_match_expression(
            table_name=table,
            query=query,
            columns=columns,
            negate=negate,
        )

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
        fts5 = get_fts5_extension()
        return fts5.format_rank_expression(
            table_name=table_name,
            weights=weights,
            bm25_params=bm25_params,
        )

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
        fts5 = get_fts5_extension()
        return fts5.format_highlight_expression(
            table_name=table_name,
            column=column,
            query=query,
            prefix_marker=prefix_marker,
            suffix_marker=suffix_marker,
        )

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
        fts5 = get_fts5_extension()
        return fts5.format_snippet_expression(
            table_name=table_name,
            column=column,
            query=query,
            prefix_marker=prefix_marker,
            suffix_marker=suffix_marker,
            context_tokens=context_tokens,
            ellipsis=ellipsis,
        )

    def format_fts5_drop_virtual_table(
        self,
        table_name: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """Format DROP TABLE statement for FTS5 virtual table.

        Args:
            table_name: Name of the FTS5 virtual table to drop
            if_exists: If True, add IF EXISTS clause

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        fts5 = get_fts5_extension()
        return fts5.format_drop_virtual_table(
            table_name=table_name,
            if_exists=if_exists,
        )


