# src/rhosocial/activerecord/backend/impl/sqlite/mixins/fts5.py
"""
SQLite FTS5 support mixin.

Provides FTS5 capability detection and SQL formatting.
SQL generation logic is migrated from the FTS5Extension class,
eliminating the singleton delegation layer.
"""

from typing import List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

from .extension import SQLiteExtensionMixin

if TYPE_CHECKING:
    from ..expression.fts5 import (
        SQLiteFTS5CreateVirtualTable,
        SQLiteFTS5HighlightExpression,
        SQLiteFTS5RankExpression,
        SQLiteFTS5SnippetExpression,
    )


class SQLiteFTS5Mixin(SQLiteExtensionMixin):
    """Mixin for FTS5 full-text search support.

    Provides version-gated capability detection and SQL formatting
    for FTS5 virtual tables, MATCH predicates, ranking, highlight, and snippet.
    """

    def supports_fts5(self) -> bool:
        """Whether FTS5 virtual table is supported.

        Checks compile options first, falls back to version check.
        """
        compile_options = self.get_runtime_param("compile_options", {})
        if compile_options:
            return "ENABLE_FTS5" in compile_options
        return self.version >= (3, 9, 0)

    def supports_fts5_bm25(self) -> bool:
        """Whether BM25 ranking function is supported (available since FTS5 was introduced)."""
        return self.supports_fts5()

    def supports_fts5_highlight(self) -> bool:
        """Whether highlight() function is supported (available since FTS5 was introduced)."""
        return self.supports_fts5()

    def supports_fts5_snippet(self) -> bool:
        """Whether snippet() function is supported (available since FTS5 was introduced)."""
        return self.supports_fts5()

    def get_supported_fts5_tokenizers(self) -> List[str]:
        """Get list of supported FTS5 tokenizers."""
        tokenizers = ["unicode61", "ascii", "porter"]
        if self.supports_fts5() and self.version >= (3, 34, 0):
            tokenizers.append("trigram")
        return tokenizers

    # ========== SQL Formatting ==========

    def format_fts5_match_expression(
        self, table: str, query: str, columns: Optional[List[str]] = None, negate: bool = False
    ) -> tuple:
        """Format FTS5 MATCH expression.

        Args:
            table: Name of the FTS table
            query: Full-text search query
            columns: Optional list of columns to scope the search
            negate: Raises ValueError (FTS5 does not support NOT MATCH)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if negate:
            raise ValueError(
                "FTS5 does not support NOT MATCH syntax. Use query-level negation instead (e.g., 'python NOT java')."
            )

        if columns:
            match_query = " OR ".join(f"{c}:{query}" for c in columns)
        else:
            match_query = query

        sql = f"{self.format_identifier(table)} MATCH ?"
        return sql, (match_query,)

    def format_fts5_create_virtual_table(self, expr: "SQLiteFTS5CreateVirtualTable") -> tuple:
        """Format CREATE VIRTUAL TABLE statement for FTS5.

        Args:
            expr: SQLiteFTS5CreateVirtualTable instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if not self.supports_fts5():
            raise UnsupportedFeatureError(
                getattr(self, "name", "sqlite"), "FTS5", "FTS5 full-text search requires SQLite 3.9.0 or later."
            )

        def esc(value: str) -> str:
            return value.replace("'", "''")

        options = []

        if expr.tokenize:
            options.append(f"tokenize='{esc(expr.tokenize)}'")
        elif expr.tokenizer:
            if expr.tokenizer_options:
                opt_parts = [f"{k} {v}" for k, v in expr.tokenizer_options.items()]
                opts_str = " ".join(opt_parts)
                options.append(f"tokenize='{esc(f'{expr.tokenizer} {opts_str}')}'")
            else:
                options.append(f"tokenize='{esc(expr.tokenizer)}'")

        if expr.prefix:
            prefix_str = " ".join(str(p) for p in expr.prefix)
            options.append(f"prefix='{esc(prefix_str)}'")

        if expr.content:
            options.append(f"content='{esc(expr.content)}'")

        if expr.content_rowid:
            options.append(f"content_rowid='{esc(expr.content_rowid)}'")

        cols_str = ", ".join(self.format_identifier(c) for c in expr.columns)

        if options:
            opts_str = ", ".join(options)
            sql = f"CREATE VIRTUAL TABLE {self.format_identifier(expr.table)} USING fts5({cols_str}, {opts_str})"
        else:
            sql = f"CREATE VIRTUAL TABLE {self.format_identifier(expr.table)} USING fts5({cols_str})"

        return sql, ()

    def format_fts5_rank_expression(self, expr: "SQLiteFTS5RankExpression") -> tuple:
        """Format FTS5 ranking expression using bm25().

        Args:
            expr: SQLiteFTS5RankExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """

        def esc(value: str) -> str:
            return value.replace("'", "''")

        if expr.weights and expr.bm25_params:
            weight_str = ", ".join(str(w) for w in expr.weights)
            param_parts = []
            for k, v in expr.bm25_params.items():
                param_parts.extend([f"'{esc(k)}'", str(v)])
            param_str = ", ".join(param_parts)
            sql = f"bm25({self.format_identifier(expr.table)}, {weight_str}, {param_str})"
        elif expr.weights:
            weight_str = ", ".join(str(w) for w in expr.weights)
            sql = f"bm25({self.format_identifier(expr.table)}, {weight_str})"
        elif expr.bm25_params:
            param_parts = []
            for k, v in expr.bm25_params.items():
                param_parts.extend([f"'{esc(k)}'", str(v)])
            param_str = ", ".join(param_parts)
            sql = f"bm25({self.format_identifier(expr.table)}, {param_str})"
        else:
            sql = f"bm25({self.format_identifier(expr.table)})"

        return sql, ()

    def format_fts5_highlight_expression(self, expr: "SQLiteFTS5HighlightExpression") -> tuple:
        """Format highlight() function expression.

        Args:
            expr: SQLiteFTS5HighlightExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        sql = (
            f"highlight({self.format_identifier(expr.table)}, "
            f"{self.format_identifier(expr.column)}, ?, ?)"
        )
        return sql, (expr.prefix_marker, expr.suffix_marker)

    def format_fts5_snippet_expression(self, expr: "SQLiteFTS5SnippetExpression") -> tuple:
        """Format snippet() function expression.

        Args:
            expr: SQLiteFTS5SnippetExpression instance

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        sql = (
            f"snippet({self.format_identifier(expr.table)}, "
            f"{self.format_identifier(expr.column)}, ?, ?, ?, ?)"
        )
        return sql, (expr.prefix_marker, expr.suffix_marker, expr.ellipsis, expr.context_tokens)
