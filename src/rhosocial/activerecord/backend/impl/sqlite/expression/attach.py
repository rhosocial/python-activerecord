# src/rhosocial/activerecord/backend/impl/sqlite/expression/attach.py
"""
SQLite-specific ATTACH DATABASE and DETACH DATABASE expressions.

This module provides SQLiteAttachExpression and SQLiteDetachExpression.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from ....expression.bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase

__all__ = ["SQLiteAttachExpression", "SQLiteDetachExpression"]


class SQLiteAttachExpression(BaseExpression):
    """SQLite ATTACH DATABASE statement expression.

    ATTACH DATABASE attaches another database file to the current
    connection under the given schema name, enabling cross-database
    queries. It is a SQLite-specific statement.

    SQLite ATTACH syntax:
        ATTACH DATABASE 'filename' AS schema_name

    Examples:
        # Attach a database file as the 'aux' schema
        attach = SQLiteAttachExpression(dialect, database="aux.db", schema="aux")
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        database: str,
        schema: str,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize an ATTACH DATABASE expression.

        Args:
            dialect: The SQL dialect instance.
            database: The database file path to attach.
            schema: The schema name (alias) under which to attach it.
            dialect_options: Additional database-specific options.

        Raises:
            ValueError: If database or schema is empty.
        """
        if not database:
            raise ValueError("ATTACH DATABASE requires a database filename")
        if not schema:
            raise ValueError("ATTACH DATABASE requires a schema name")
        super().__init__(dialect)
        self.database = database
        self.schema = schema
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL for the ATTACH DATABASE statement.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        return self._dialect.format_attach_statement(self)


class SQLiteDetachExpression(BaseExpression):
    """SQLite DETACH DATABASE statement expression.

    DETACH DATABASE detaches a previously attached database schema from
    the current connection. It is a SQLite-specific statement.

    SQLite DETACH syntax:
        DETACH DATABASE schema_name

    Examples:
        # Detach the 'aux' schema
        detach = SQLiteDetachExpression(dialect, schema="aux")
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: str,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a DETACH DATABASE expression.

        Args:
            dialect: The SQL dialect instance.
            schema: The schema name to detach.
            dialect_options: Additional database-specific options.

        Raises:
            ValueError: If schema is empty.
        """
        if not schema:
            raise ValueError("DETACH DATABASE requires a schema name")
        super().__init__(dialect)
        self.schema = schema
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL for the DETACH DATABASE statement.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        return self._dialect.format_detach_statement(self)