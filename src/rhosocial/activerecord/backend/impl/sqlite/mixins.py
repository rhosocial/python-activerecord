# src/rhosocial/activerecord/backend/impl/sqlite/mixins.py
"""
SQLite-specific mixin implementations.

This module provides mixin classes that implement SQLite-specific features
defined in the protocols module.
"""
from typing import Any, Dict, List, Optional, Tuple


class FTS5Mixin:
    """
    Mixin for FTS5 (Full-Text Search) support in SQLite.

    FTS5 is a virtual table module that provides full-text search capabilities.
    It is available since SQLite 3.9.0 (2015-11-02).

    This mixin provides methods for:
    - Creating and dropping FTS5 virtual tables
    - Formatting MATCH expressions for full-text queries
    - Ranking results using bm25()
    - Highlighting and snippet extraction
    """

    def supports_fts5(self) -> bool:
        """
        Whether FTS5 full-text search is supported.

        FTS5 is available since SQLite 3.9.0.

        Returns:
            True if FTS5 is supported
        """
        return self.version >= (3, 9, 0)

    def supports_fts5_bm25(self) -> bool:
        """
        Whether BM25 ranking function is supported.

        BM25 is the default ranking function in FTS5, available
        since SQLite 3.9.0.

        Returns:
            True if BM25 is supported
        """
        return self.supports_fts5()

    def supports_fts5_highlight(self) -> bool:
        """
        Whether highlight() function is supported.

        The highlight() function returns a copy of the text with
        search terms surrounded by specified markers.

        Returns:
            True if highlight() is supported
        """
        return self.supports_fts5()

    def supports_fts5_snippet(self) -> bool:
        """
        Whether snippet() function is supported.

        The snippet() function returns a fragment of text with
        search terms highlighted.

        Returns:
            True if snippet() is supported
        """
        return self.supports_fts5()

    def supports_fts5_offset(self) -> bool:
        """
        Whether offset() function is supported.

        Returns the byte offset of the match within the original text.

        Returns:
            True if offset() is supported
        """
        return self.supports_fts5()

    def get_supported_fts5_tokenizers(self) -> List[str]:
        """
        Get list of supported FTS5 tokenizers.

        Standard tokenizers:
        - 'unicode61': Default tokenizer, supports Unicode (since 3.9.0)
        - 'ascii': Simple ASCII tokenizer (since 3.9.0)
        - 'porter': Porter stemmer wrapper (since 3.9.0)
        - 'trigram': Trigram tokenizer (since 3.34.0)

        Returns:
            List of supported tokenizer names
        """
        tokenizers = ['unicode61', 'ascii', 'porter']
        if self.version >= (3, 34, 0):
            tokenizers.append('trigram')
        return tokenizers

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

        Example:
            # Basic FTS5 table
            sql, params = dialect.format_fts5_create_virtual_table(
                'documents', ['title', 'content']
            )
            # CREATE VIRTUAL TABLE "documents" USING fts5(title, content)

            # With Porter stemmer tokenizer
            sql, params = dialect.format_fts5_create_virtual_table(
                'documents', ['title', 'content'],
                tokenizer='porter'
            )
            # CREATE VIRTUAL TABLE "documents" USING fts5(title, content, tokenize='porter')

            # With unicode61 and options
            sql, params = dialect.format_fts5_create_virtual_table(
                'documents', ['title', 'content'],
                tokenizer='unicode61',
                tokenizer_options={'remove_diacritics': 1}
            )
            # CREATE VIRTUAL TABLE "documents" USING fts5(title, content,
            #     tokenize='unicode61 remove_diacritics 1')

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

        Raises:
            UnsupportedFeatureError: If FTS5 is not supported
        """
        if not self.supports_fts5():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
            raise UnsupportedFeatureError(
                self.name,
                "FTS5",
                "FTS5 full-text search requires SQLite 3.9.0 or later."
            )

        options = []

        if tokenize:
            options.append(f"tokenize='{tokenize}'")
        elif tokenizer:
            if tokenizer_options:
                opt_parts = []
                for k, v in tokenizer_options.items():
                    opt_parts.append(f"{k} {v}")
                opts_str = " ".join(opt_parts)
                options.append(f"tokenize='{tokenizer} {opts_str}'")
            else:
                options.append(f"tokenize='{tokenizer}'")

        if prefix:
            prefix_str = " ".join(str(p) for p in prefix)
            options.append(f"prefix='{prefix_str}'")

        if content:
            options.append(f"content='{content}'")

        if content_rowid:
            options.append(f"content_rowid='{content_rowid}'")

        cols_str = ", ".join(self.format_identifier(c) for c in columns)

        if options:
            opts_str = ", ".join(options)
            sql = f"CREATE VIRTUAL TABLE {self.format_identifier(table_name)} USING fts5({cols_str}, {opts_str})"
        else:
            sql = f"CREATE VIRTUAL TABLE {self.format_identifier(table_name)} USING fts5({cols_str})"

        return sql, ()

    def format_fts5_match_expression(
        self,
        table_name: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ) -> Tuple[str, tuple]:
        """
        Format FTS5 MATCH expression for use in WHERE clause.

        Example:
            # Match against all columns
            sql, params = dialect.format_fts5_match_expression(
                'documents', 'sqlite AND database'
            )
            # "documents" MATCH 'sqlite AND database'

            # Match against specific columns
            sql, params = dialect.format_fts5_match_expression(
                'documents', 'sqlite', columns=['title']
            )
            # "documents" MATCH '{title}: sqlite'

            # Negated match
            sql, params = dialect.format_fts5_match_expression(
                'documents', 'sqlite', negate=True
            )
            # "documents" NOT MATCH 'sqlite'

        Args:
            table_name: Name of the FTS5 virtual table
            query: Full-text search query string
            columns: Specific columns to search (None for all columns)
            negate: If True, negate the match (NOT MATCH)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if columns:
            col_prefix = " OR ".join(f"{c}:" for c in columns)
            match_query = f"{{{col_prefix}}} {query}"
        else:
            match_query = query

        if negate:
            sql = f"{self.format_identifier(table_name)} NOT MATCH ?"
        else:
            sql = f"{self.format_identifier(table_name)} MATCH ?"

        return sql, (match_query,)

    def format_fts5_rank_expression(
        self,
        table_name: str,
        weights: Optional[List[float]] = None,
        bm25_params: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, tuple]:
        """
        Format FTS5 ranking expression using bm25().

        BM25 is the default ranking algorithm for FTS5. It calculates
        relevance scores based on term frequency and document length.

        Example:
            # Default ranking
            sql, params = dialect.format_fts5_rank_expression('documents')
            # bm25("documents")

            # With column weights
            sql, params = dialect.format_fts5_rank_expression(
                'documents', weights=[10.0, 1.0]
            )
            # bm25("documents", 10.0, 1.0)

            # With BM25 parameters
            sql, params = dialect.format_fts5_rank_expression(
                'documents', bm25_params={'k1': 1.5, 'b': 0.75}
            )
            # bm25("documents", 'k1', 1.5, 'b', 0.75)

        Args:
            table_name: Name of the FTS5 virtual table
            weights: Column weights for ranking (order matches column order)
            bm25_params: BM25 parameters (k1, b) for ranking customization

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        params = []

        if weights and bm25_params:
            weight_str = ", ".join(str(w) for w in weights)
            param_parts = []
            for k, v in bm25_params.items():
                param_parts.extend([f"'{k}'", str(v)])
            param_str = ", ".join(param_parts)
            sql = f"bm25({self.format_identifier(table_name)}, {weight_str}, {param_str})"
        elif weights:
            weight_str = ", ".join(str(w) for w in weights)
            sql = f"bm25({self.format_identifier(table_name)}, {weight_str})"
        elif bm25_params:
            param_parts = []
            for k, v in bm25_params.items():
                param_parts.extend([f"'{k}'", str(v)])
            param_str = ", ".join(param_parts)
            sql = f"bm25({self.format_identifier(table_name)}, {param_str})"
        else:
            sql = f"bm25({self.format_identifier(table_name)})"

        return sql, tuple(params)

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

        The highlight() function returns a copy of the text with all
        instances of the search terms surrounded by the specified markers.

        Example:
            sql, params = dialect.format_fts5_highlight_expression(
                'documents', 'content', 'sqlite', '<mark>', '</mark>'
            )
            # highlight("documents", 0, '<mark>', '</mark>')

        Args:
            table_name: Name of the FTS5 virtual table
            column: Column name to highlight
            query: Search query (for determining which column index)
            prefix_marker: HTML/text to prepend to matches
            suffix_marker: HTML/text to append to matches

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        sql = f"highlight({self.format_identifier(table_name)}, " \
              f"(SELECT value FROM json_each(fts5_encoded(?)) LIMIT 1), " \
              f"?, ?)"
        return sql, (query, prefix_marker, suffix_marker)

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

        The snippet() function returns a fragment of text with the
        first occurrence of each search term highlighted.

        Example:
            sql, params = dialect.format_fts5_snippet_expression(
                'documents', 'content', 'sqlite database',
                context_tokens=15
            )
            # snippet("documents", 0, '<b>', '</b>', '...', 15)

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
        sql = f"snippet({self.format_identifier(table_name)}, " \
              f"(SELECT value FROM json_each(fts5_encoded(?)) LIMIT 1), " \
              f"?, ?, ?, ?)"
        return sql, (query, prefix_marker, suffix_marker, ellipsis, context_tokens)

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
        if if_exists:
            sql = f"DROP TABLE IF EXISTS {self.format_identifier(table_name)}"
        else:
            sql = f"DROP TABLE {self.format_identifier(table_name)}"
        return sql, ()
