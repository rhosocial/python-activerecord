# src/rhosocial/activerecord/backend/impl/sqlite/expression/fts5.py
"""
SQLite-specific FTS5 expression classes.

This module provides expression classes for FTS5 full-text search operations,
including virtual table creation, ranking, highlight, and snippet.

For FTS5 MATCH predicates, use SQLiteMatchPredicate from the predicates module.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ....expression.bases import BaseExpression, SQLPredicate, SQLValue
from rhosocial.activerecord.backend.expression.objects import Table

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase


#: The HTML a highlighted match is wrapped in when the caller names none.
#:
#: FTS5's ``highlight`` and ``snippet`` both take the pair of markers as
#: arguments rather than as a dialect decision: they are literal text spliced
#: into the returned string, not SQL, so the dialect has no say in them. The
#: two expressions ask one question -- what wraps a match -- and answer it
#: with one pair, so the markers are defined once and both read them. Per
#: ``.claude/rules/constants.md`` a value read from more than one function,
#: where the readings must agree, takes a module-level constant and a test
#: that pins it -- see
#: ``tests/rhosocial/activerecord_test/feature/rules/test_shared_defaults.py``.
HIGHLIGHT_PREFIX_MARKER: str = "<b>"

#: The HTML that closes a highlighted match. The partner of
#: :data:`HIGHLIGHT_PREFIX_MARKER`: a pair the two FTS5 expressions share.
HIGHLIGHT_SUFFIX_MARKER: str = "</b>"


class SQLiteFTS5MatchPredicate(SQLPredicate):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression."""
        return "format_fts5_match_expression"
    """SQLite FTS5 MATCH predicate expression.

    Wraps the parameters for an FTS5 MATCH expression so the format method
    receives a single expression object instead of individual arguments.

    Example:
        >>> expr = SQLiteFTS5MatchPredicate(dialect, table='docs', query='Python')
        >>> expr.to_sql()
        ('"docs" MATCH ?', ('Python',))
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ):
        super().__init__(dialect)
        self.table = table
        self.query = query
        self.columns = columns
        self.negate = negate
class SQLiteFTS5CreateVirtualTable(BaseExpression):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression."""
        return "format_fts5_create_virtual_table"
    """FTS5 CREATE VIRTUAL TABLE statement expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        columns: List[str],
        tokenizer: Optional[str] = None,
        tokenizer_options: Optional[Dict[str, Any]] = None,
        prefix: Optional[List[int]] = None,
        content: Optional[str] = None,
        content_rowid: Optional[str] = None,
        tokenize: Optional[str] = None,
    ):
        super().__init__(dialect)
        if not isinstance(table, Table):
            raise TypeError(
                f"table must be a Table, "
                f"got {type(table).__name__}"
            )
        self.table = table
        self.columns = columns
        self.tokenizer = tokenizer
        self.tokenizer_options = tokenizer_options
        self.prefix = prefix
        self.content = content
        self.content_rowid = content_rowid
        self.tokenize = tokenize
class SQLiteFTS5RankExpression(SQLValue):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression."""
        return "format_fts5_rank_expression"
    """FTS5 BM25 ranking expression for relevance scoring in ORDER BY clauses."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        weights: Optional[List[float]] = None,
        bm25_params: Optional[Dict[str, float]] = None,
    ):
        super().__init__(dialect)
        if not isinstance(table, Table):
            raise TypeError(
                f"table must be a Table, "
                f"got {type(table).__name__}"
            )
        self.table = table
        self.weights = weights
        self.bm25_params = bm25_params
class SQLiteFTS5HighlightExpression(SQLValue):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression."""
        return "format_fts5_highlight_expression"
    """FTS5 highlight() function expression for marking matched terms."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        column: str,
        prefix_marker: str = HIGHLIGHT_PREFIX_MARKER,
        suffix_marker: str = HIGHLIGHT_SUFFIX_MARKER,
    ):
        super().__init__(dialect)
        if not isinstance(table, Table):
            raise TypeError(
                f"table must be a Table, "
                f"got {type(table).__name__}"
            )
        self.table = table
        self.column = column
        self.prefix_marker = prefix_marker
        self.suffix_marker = suffix_marker
class SQLiteFTS5SnippetExpression(SQLValue):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression."""
        return "format_fts5_snippet_expression"
    """FTS5 snippet() function expression for showing context around matched terms."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        column: str,
        prefix_marker: str = HIGHLIGHT_PREFIX_MARKER,
        suffix_marker: str = HIGHLIGHT_SUFFIX_MARKER,
        context_tokens: int = 10,
        ellipsis: str = "...",
    ):
        super().__init__(dialect)
        if not isinstance(table, Table):
            raise TypeError(
                f"table must be a Table, "
                f"got {type(table).__name__}"
            )
        self.table = table
        self.column = column
        self.prefix_marker = prefix_marker
        self.suffix_marker = suffix_marker
        self.context_tokens = context_tokens
        self.ellipsis = ellipsis
