# src/rhosocial/activerecord/backend/impl/sqlite/expression/fts5.py
"""
SQLite-specific FTS5 expression classes.

This module provides expression classes for FTS5 full-text search operations,
including virtual table creation, ranking, highlight, and snippet.

For FTS5 MATCH predicates, use SQLiteMatchPredicate from the predicates module.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ....expression.bases import BaseExpression, SQLValueExpression, SQLQueryAndParams

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase


class SQLiteFTS5CreateVirtualTable(BaseExpression):
    """FTS5 CREATE VIRTUAL TABLE statement expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: str,
        columns: List[str],
        tokenizer: Optional[str] = None,
        tokenizer_options: Optional[Dict[str, Any]] = None,
        prefix: Optional[List[int]] = None,
        content: Optional[str] = None,
        content_rowid: Optional[str] = None,
        tokenize: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.table = table
        self.columns = columns
        self.tokenizer = tokenizer
        self.tokenizer_options = tokenizer_options
        self.prefix = prefix
        self.content = content
        self.content_rowid = content_rowid
        self.tokenize = tokenize

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_fts5_create_virtual_table(self)


class SQLiteFTS5RankExpression(SQLValueExpression):
    """FTS5 BM25 ranking expression for relevance scoring in ORDER BY clauses."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: str,
        weights: Optional[List[float]] = None,
        bm25_params: Optional[Dict[str, float]] = None,
    ):
        super().__init__(dialect)
        self.table = table
        self.weights = weights
        self.bm25_params = bm25_params

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_fts5_rank_expression(self)


class SQLiteFTS5HighlightExpression(SQLValueExpression):
    """FTS5 highlight() function expression for marking matched terms."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: str,
        column: str,
        prefix_marker: str = "<b>",
        suffix_marker: str = "</b>",
    ):
        super().__init__(dialect)
        self.table = table
        self.column = column
        self.prefix_marker = prefix_marker
        self.suffix_marker = suffix_marker

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_fts5_highlight_expression(self)


class SQLiteFTS5SnippetExpression(SQLValueExpression):
    """FTS5 snippet() function expression for showing context around matched terms."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: str,
        column: str,
        prefix_marker: str = "<b>",
        suffix_marker: str = "</b>",
        context_tokens: int = 10,
        ellipsis: str = "...",
    ):
        super().__init__(dialect)
        self.table = table
        self.column = column
        self.prefix_marker = prefix_marker
        self.suffix_marker = suffix_marker
        self.context_tokens = context_tokens
        self.ellipsis = ellipsis

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_fts5_snippet_expression(self)
