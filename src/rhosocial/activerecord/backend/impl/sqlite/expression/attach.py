# src/rhosocial/activerecord/backend/impl/sqlite/expression/attach.py
"""
SQLite-specific ATTACH DATABASE and DETACH DATABASE expressions.

This module provides SQLiteAttachExpression and SQLiteDetachExpression.
"""

from typing import TYPE_CHECKING

from ....expression.bases import BaseExpression

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase

__all__ = ["SQLiteAttachExpression", "SQLiteDetachExpression"]


class SQLiteAttachExpression(BaseExpression):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression.

        Declared rather than reached through a ``to_sql`` override: the node
        names its formatter and the dialect supplies it. A node that calls the
        dialect itself keeps the lookup inside the node, which is the direction
        this architecture removes.
        """
        return "format_attach_expression"
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
    ):
        """Initialize an ATTACH DATABASE expression.

        Args:
            dialect: The SQL dialect instance.
            database: The database file path to attach.
            schema: The schema name (alias) under which to attach it.

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
class SQLiteDetachExpression(BaseExpression):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression.

        Declared rather than reached through a ``to_sql`` override: the node
        names its formatter and the dialect supplies it. A node that calls the
        dialect itself keeps the lookup inside the node, which is the direction
        this architecture removes.
        """
        return "format_detach_expression"
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
    ):
        """Initialize a DETACH DATABASE expression.

        Args:
            dialect: The SQL dialect instance.
            schema: The schema name to detach.

        Raises:
            ValueError: If schema is empty.
        """
        if not schema:
            raise ValueError("DETACH DATABASE requires a schema name")
        super().__init__(dialect)
        self.schema = schema
