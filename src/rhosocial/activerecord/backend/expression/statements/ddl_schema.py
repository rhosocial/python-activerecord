# src/rhosocial/activerecord/backend/expression/statements/ddl_schema.py
"""Schema DDL statement expressions."""

from typing import Any, Dict, Optional, TYPE_CHECKING

from ..bases import BaseExpression, SQLQueryAndParams

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
            schema_name="my_schema"
        )

        # Schema with authorization
        create_schema = CreateSchemaExpression(
            dialect,
            schema_name="app_schema",
            authorization="app_user"
        )

        # Safe schema creation
        create_schema = CreateSchemaExpression(
            dialect,
            schema_name="reporting",
            if_not_exists=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema_name: str,
        if_not_exists: bool = False,
        authorization: Optional[str] = None,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.schema_name = schema_name
        self.if_not_exists = if_not_exists
        self.authorization = authorization
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_create_schema_statement(self)


class DropSchemaExpression(BaseExpression):
    """
    Represents a DROP SCHEMA statement.

    Examples:
        # Basic schema drop
        drop_schema = DropSchemaExpression(
            dialect,
            schema_name="old_schema"
        )

        # Safe drop with IF EXISTS
        drop_schema = DropSchemaExpression(
            dialect,
            schema_name="test_schema",
            if_exists=True
        )

        # Cascade drop (removes all objects in schema)
        drop_schema = DropSchemaExpression(
            dialect,
            schema_name="legacy",
            cascade=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema_name: str,
        if_exists: bool = False,
        cascade: bool = False,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.schema_name = schema_name
        self.if_exists = if_exists
        self.cascade = cascade
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        return self.dialect.format_drop_schema_statement(self)
