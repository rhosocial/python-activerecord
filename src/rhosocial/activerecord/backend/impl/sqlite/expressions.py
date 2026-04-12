# src/rhosocial/activerecord/backend/impl/sqlite/expressions.py
"""
SQLite-specific expressions.

This module defines SQLite-specific expression classes that extend the
base expressions with SQLite-specific parameters and features.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING

from ...expression.bases import BaseExpression, SQLQueryAndParams
from ...expression.introspection import (
    ColumnInfoExpression,
    TableListExpression,
)

if TYPE_CHECKING:
    from ...dialect import SQLDialectBase


@dataclass
class SQLiteColumnInfoExpression(ColumnInfoExpression):
    """SQLite column information expression.

    Extends ColumnInfoExpression with SQLite-specific parameters.

    Attributes:
        use_xinfo_pragma: Whether to use PRAGMA table_xinfo instead of table_info.
        PRAGMA table_xinfo includes hidden columns and is available in SQLite 3.26.0+.
    """

    use_xinfo_pragma: bool = False

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        super().__post_init__()
        self._params["use_xinfo_pragma"] = self.use_xinfo_pragma


@dataclass
class SQLiteTableListExpression(TableListExpression):
    """SQLite table list expression.

    Extends TableListExpression with SQLite-specific parameters.

    Attributes:
        use_table_list_pragma: Whether to use PRAGMA table_list instead of
        querying sqlite_master. PRAGMA table_list is available in SQLite 3.37.0+.
    """

    use_table_list_pragma: bool = False

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        super().__post_init__()
        self._params["use_table_list_pragma"] = self.use_table_list_pragma


class SQLiteReindexExpression(BaseExpression):
    """SQLite REINDEX statement expression.

    REINDEX is a SQLite-specific statement for rebuilding indexes.
    It is not part of the SQL standard.

    SQLite 3.53.0+ supports REINDEX EXPRESSIONS to specifically rebuild
    expression indexes that may have become stale.

    Examples:
        # Rebuild all indexes on a table
        reindex = SQLiteReindexExpression(dialect, table_name="users")

        # Rebuild a specific index
        reindex = SQLiteReindexExpression(dialect, index_name="idx_users_email")

        # Rebuild all expression indexes (SQLite 3.53.0+)
        reindex = SQLiteReindexExpression(dialect, expressions=True)

        # Rebuild all indexes in the database
        reindex = SQLiteReindexExpression(dialect)
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        index_name: Optional[str] = None,
        table_name: Optional[str] = None,
        expressions: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a REINDEX expression.

        Args:
            dialect: The SQL dialect instance.
            index_name: Optional specific index name to rebuild.
            table_name: Optional table name to rebuild all indexes for.
            expressions: If True, rebuild all expression indexes (SQLite 3.53.0+).
                Mutually exclusive with index_name and table_name.
            dialect_options: Additional database-specific options.

        Raises:
            ValueError: If both index_name and table_name are specified,
                or if expressions is True with other parameters.
        """
        if expressions and (index_name or table_name):
            raise ValueError(
                "REINDEX EXPRESSIONS cannot be combined with index_name or table_name"
            )
        if index_name and table_name:
            raise ValueError(
                "Cannot specify both index_name and table_name for REINDEX"
            )

        super().__init__(dialect)
        self.index_name = index_name
        self.table_name = table_name
        self.expressions = expressions
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL for REINDEX statement.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        return self._dialect.format_reindex_statement(self)
