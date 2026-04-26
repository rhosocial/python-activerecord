# src/rhosocial/activerecord/backend/impl/sqlite/expression/predicates.py
"""
SQLite-specific predicate expressions for FTS (Full-Text Search).

This module provides SQLiteMatchPredicate which is a SQLite-specific
predicate for full-text search operations.
"""

from typing import List, Optional, TYPE_CHECKING

from ....expression.bases import SQLPredicate

if TYPE_CHECKING:
    from ....backend.dialect.base import SQLDialectBase
    from ....backend.bases import SQLQueryAndParams


class SQLiteMatchPredicate(SQLPredicate):
    """SQLite FTS MATCH predicate expression.

    This predicate is used for full-text search operations in SQLite's
    FTS3/FTS4/FTS5 virtual tables. It delegates to the SQLite dialect's
    format_match_predicate method.

    Example (SQLite FTS5):
        >>> predicate = SQLiteMatchPredicate(dialect, table='docs', query='Python')
        >>> predicate.to_sql()
        ('"docs" MATCH ?', ('Python',))

        >>> predicate = SQLiteMatchPredicate(
        ...     dialect, table='docs', query='prog*', columns=['title']
        ... )
        >>> predicate.to_sql()
        ('"docs" MATCH ?', ('{title:}prog*',))

        >>> predicate = SQLiteMatchPredicate(
        ...     dialect, table='docs', query='python', negate=True
        ... )
        >>> predicate.to_sql()
        ('NOT "docs" MATCH ?', ('python',))
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
            negate: If True, negate the match (NOT MATCH).
        """
        super().__init__(dialect)
        self.table = table
        self.query = query
        self.columns = columns
        self.negate = negate

    def to_sql(self) -> "SQLQueryAndParams":
        """Format the MATCH predicate using SQLite dialect.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        return self.dialect.format_match_predicate(
            self.table,
            self.query,
            self.columns,
            self.negate,
        )