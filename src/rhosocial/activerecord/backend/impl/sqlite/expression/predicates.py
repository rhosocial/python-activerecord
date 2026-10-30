# src/rhosocial/activerecord/backend/impl/sqlite/expression/predicates.py
"""
SQLite-specific predicate expressions for FTS (Full-Text Search).

This module provides SQLiteMatchPredicate which is a SQLite-specific
predicate for full-text search operations.
"""

from typing import List, Optional, TYPE_CHECKING

from ....expression.bases import SQLPredicate

if TYPE_CHECKING:
    from ......dialect.base import SQLDialectBase


class SQLiteMatchPredicate(SQLPredicate):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression."""
        return "format_match_predicate"
    """SQLite FTS MATCH predicate expression.

    This predicate is used for full-text search operations in SQLite's
    FTS3/FTS4/FTS5 virtual tables. It delegates to the SQLite dialect's
    format_match_predicate method.

    NOTE: negate=True is NOT supported for FTS5 (raises ValueError).
    Use query-level negation instead: 'python NOT java'.

    Example (SQLite FTS5):
        >>> predicate = SQLiteMatchPredicate(dialect, table='docs', query='Python')
        >>> predicate.to_sql()
        ('"docs" MATCH ?', ('Python',))

        >>> predicate = SQLiteMatchPredicate(
        ...     dialect, table='docs', query='prog*', columns=['title']
        ... )
        >>> predicate.to_sql()
        ('"docs" MATCH ?', ('title:prog*',))
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ):
        """Initialize SQLiteMatchPredicate.

        Args:
            dialect: The SQLite dialect instance.
            table: Name of the FTS table to match against.
            query: Full-text search query string.
            columns: Specific columns to search (None for all columns).
            negate: Raises ValueError for FTS5 (not supported by FTS5).
        """
        super().__init__(dialect)
        self.table = table
        self.query = query
        self.columns = columns
        self.negate = negate
