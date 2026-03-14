# src/rhosocial/activerecord/backend/impl/sqlite/protocols.py
"""
SQLite-specific protocol definitions.

This module defines protocol interfaces for SQLite-specific features
that are not part of the standard SQL dialect protocols.
"""
from typing import Any, Dict, List, Optional, Tuple, Protocol, runtime_checkable


@runtime_checkable
class FTS5Support(Protocol):
    """
    Protocol for FTS5 (Full-Text Search) support.

    FTS5 is a SQLite extension that provides full-text search capabilities.
    It is available since SQLite 3.9.0 (2015-11-02).

    Key features:
    - Full-text search with customizable tokenizers
    - BM25 ranking function for relevance scoring
    - Phrase queries, NEAR queries, AND/OR/NOT operators
    - Column filters and prefix queries
    """

    def supports_fts5(self) -> bool:
        """
        Whether FTS5 full-text search is supported.

        FTS5 is available since SQLite 3.9.0.

        Returns:
            True if FTS5 is supported
        """
        ...  # pragma: no cover

    def supports_fts5_bm25(self) -> bool:
        """
        Whether BM25 ranking function is supported.

        BM25 is the default ranking function in FTS5, available
        since SQLite 3.9.0.

        Returns:
            True if BM25 is supported
        """
        ...  # pragma: no cover

    def supports_fts5_highlight(self) -> bool:
        """
        Whether highlight() function is supported.

        The highlight() function returns a copy of the text with
        search terms surrounded by specified markers.

        Returns:
            True if highlight() is supported
        """
        ...  # pragma: no cover

    def supports_fts5_snippet(self) -> bool:
        """
        Whether snippet() function is supported.

        The snippet() function returns a fragment of text with
        search terms highlighted.

        Returns:
            True if snippet() is supported
        """
        ...  # pragma: no cover

    def supports_fts5_offset(self) -> bool:
        """
        Whether offset() function is supported.

        Returns the byte offset of the match within the original text.

        Returns:
            True if offset() is supported
        """
        ...  # pragma: no cover

    def get_supported_fts5_tokenizers(self) -> List[str]:
        """
        Get list of supported FTS5 tokenizers.

        Standard tokenizers:
        - 'unicode61': Default tokenizer, supports Unicode
        - 'ascii': Simple ASCII tokenizer
        - 'porter': Porter stemmer wrapper
        - 'trigram': Trigram tokenizer (since 3.34.0)

        Returns:
            List of supported tokenizer names
        """
        ...  # pragma: no cover

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
        """
        Format CREATE VIRTUAL TABLE statement for FTS5.

        Args:
            table_name: Name of the FTS5 virtual table
            columns: List of column names to be indexed
            tokenizer: Tokenizer name (e.g., 'unicode61', 'porter')
            tokenizer_options: Tokenizer options (e.g., {'remove_diacritics': 1})
            prefix: List of prefix lengths for prefix indexing
            content: Content table name (for contentless or external content FTS5)
            content_rowid: Column name for rowid in content table
            tokenize: Full tokenize specification string (alternative to tokenizer)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...  # pragma: no cover

    def format_fts5_match_expression(
        self,
        table_name: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ) -> Tuple[str, tuple]:
        """
        Format FTS5 MATCH expression for use in WHERE clause.

        Args:
            table_name: Name of the FTS5 virtual table
            query: Full-text search query string
            columns: Specific columns to search (None for all columns)
            negate: If True, negate the match (NOT MATCH)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...  # pragma: no cover

    def format_fts5_rank_expression(
        self,
        table_name: str,
        weights: Optional[List[float]] = None,
        bm25_params: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, tuple]:
        """
        Format FTS5 ranking expression using bm25().

        Args:
            table_name: Name of the FTS5 virtual table
            weights: Column weights for ranking (order matches column order)
            bm25_params: BM25 parameters (k1, b) for ranking customization

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...  # pragma: no cover

    def format_fts5_highlight_expression(
        self,
        table_name: str,
        column: str,
        query: str,
        prefix_marker: str = "<b>",
        suffix_marker: str = "</b>",
    ) -> Tuple[str, tuple]:
        """
        Format highlight() function expression.

        Args:
            table_name: Name of the FTS5 virtual table
            column: Column name to highlight
            query: Search query (for ranking)
            prefix_marker: HTML/text to prepend to matches
            suffix_marker: HTML/text to append to matches

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...  # pragma: no cover

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
        """
        Format snippet() function expression.

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
        ...  # pragma: no cover

    def format_fts5_drop_virtual_table(
        self,
        table_name: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """
        Format DROP TABLE statement for FTS5 virtual table.

        Args:
            table_name: Name of the FTS5 virtual table to drop
            if_exists: If True, add IF EXISTS clause

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...  # pragma: no cover
