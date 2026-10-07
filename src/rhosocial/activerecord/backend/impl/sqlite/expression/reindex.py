# src/rhosocial/activerecord/backend/impl/sqlite/expression/reindex.py
"""
SQLite-specific REINDEX expression.

This module provides SQLiteReindexExpression for rebuilding indexes.
"""

from typing import Optional, TYPE_CHECKING

from ....expression.bases import BaseExpression, SQLQueryAndParams
from ....expression.objects import Index, Table

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase


class SQLiteReindexExpression(BaseExpression):
    """SQLite REINDEX statement expression.

    REINDEX is a SQLite-specific statement for rebuilding indexes.
    It is not part of the SQL standard.

    SQLite 3.53.0+ supports REINDEX EXPRESSIONS to specifically rebuild
    expression indexes that may have become stale.

    Examples:
        # Rebuild all indexes on a table
        reindex = SQLiteReindexExpression(dialect, table=Table(dialect, "users"))

        # Rebuild a specific index
        reindex = SQLiteReindexExpression(dialect, index=Index(dialect, "idx_users_email"))

        # Rebuild all expression indexes (SQLite 3.53.0+)
        reindex = SQLiteReindexExpression(dialect, expressions=True)

        # Rebuild all indexes in the database
        reindex = SQLiteReindexExpression(dialect)
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index: Optional["Index"] = None,
        table: Optional["Table"] = None,
        expressions: bool = False,
    ):
        """Initialize a REINDEX expression.

        Args:
            dialect: The SQL dialect instance.
            index: Optional index to rebuild.
            table: Optional table to rebuild all indexes for.
            expressions: If True, rebuild all expression indexes (SQLite 3.53.0+).
                Mutually exclusive with index and table.

        Raises:
            ValueError: If both index and table are specified,
                or if expressions is True with other parameters.
        """
        if expressions and (index or table):
            raise ValueError("REINDEX EXPRESSIONS cannot be combined with index or table")
        if index and table:
            raise ValueError("Cannot specify both index and table for REINDEX")

        super().__init__(dialect)
        if index is not None and not isinstance(index, Index):
            raise TypeError(
                f"index must be an Index, "
                f"got {type(index).__name__}"
            )
        self.index = index
        if table is not None and not isinstance(table, Table):
            raise TypeError(
                f"table must be a Table, "
                f"got {type(table).__name__}"
            )
        self.table = table
        self.expressions = expressions

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL for REINDEX statement.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        return self._dialect.format_reindex_statement(self)
