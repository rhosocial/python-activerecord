# src/rhosocial/activerecord/backend/expression/statements/ddl_schema.py
"""Schema DDL statement expressions."""

from typing import Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..objects import Schema

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class CreateSchemaExpression(BaseExpression):
    """
    Represents a CREATE SCHEMA statement.

    Schemas are database namespaces that contain tables, views, and other objects.
    Support varies by database:
    - PostgreSQL: Full schema support with AUTHORIZATION
    - MySQL: CREATE SCHEMA is synonym for CREATE DATABASE
    - SQLite: Not supported (database file is the entire database)

    Examples:
        # Basic schema creation
        create_schema = CreateSchemaExpression(
            dialect,
            schema=Schema(dialect, "my_schema")
        )

        # Schema with authorization
        create_schema = CreateSchemaExpression(
            dialect,
            schema=Schema(dialect, "app_schema"),
            authorization="app_user"
        )

        # Safe schema creation
        create_schema = CreateSchemaExpression(
            dialect,
            schema=Schema(dialect, "reporting"),
            if_not_exists=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: "Schema",
        if_not_exists: bool = False,
        authorization: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.schema = schema
        self.if_not_exists = if_not_exists
        self.authorization = authorization

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_create_schema_statement"


class DropSchemaExpression(BaseExpression):
    """
    Represents a DROP SCHEMA statement.

    Examples:
        # Basic schema drop
        drop_schema = DropSchemaExpression(
            dialect,
            schema=Schema(dialect, "old_schema")
        )

        # Safe drop with IF EXISTS
        drop_schema = DropSchemaExpression(
            dialect,
            schema=Schema(dialect, "test_schema"),
            if_exists=True
        )

        # Cascade drop (removes all objects in schema)
        drop_schema = DropSchemaExpression(
            dialect,
            schema=Schema(dialect, "legacy"),
            cascade=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: "Schema",
        if_exists: bool = False,
        cascade: bool = False,
    ):
        super().__init__(dialect)
        self.schema = schema
        self.if_exists = if_exists
        self.cascade = cascade

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_drop_schema_statement"
