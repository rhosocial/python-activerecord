# src/rhosocial/activerecord/backend/impl/sqlite/expression/reindex.py
"""
SQLite-specific REINDEX expression.

This module provides SQLiteReindexExpression for rebuilding indexes.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from ....expression.bases import BaseExpression, SQLQueryAndParams

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
        reindex = SQLiteReindexExpression(dialect, table="users")

        # Rebuild a specific index
        reindex = SQLiteReindexExpression(dialect, index="idx_users_email")

        # Rebuild all expression indexes (SQLite 3.53.0+)
        reindex = SQLiteReindexExpression(dialect, expressions=True)

        # Rebuild all indexes in the database
        reindex = SQLiteReindexExpression(dialect)
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index: Optional[str] = None,
        table: Optional[str] = None,
        expressions: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a REINDEX expression.

        Args:
            dialect: The SQL dialect instance.
            index: Optional specific index name to rebuild.
            table: Optional table name to rebuild all indexes for.
            expressions: If True, rebuild all expression indexes (SQLite 3.53.0+).
                Mutually exclusive with index and table.
            dialect_options: Additional database-specific options.

        Raises:
            ValueError: If both index and table are specified,
                or if expressions is True with other parameters.
        """
        if expressions and (index or table):
            raise ValueError("REINDEX EXPRESSIONS cannot be combined with index or table")
        if index and table:
            raise ValueError("Cannot specify both index and table for REINDEX")

        super().__init__(dialect)
        self.index = index
        self.table = table
        self.expressions = expressions
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL for REINDEX statement.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        return self._dialect.format_reindex_statement(self)
