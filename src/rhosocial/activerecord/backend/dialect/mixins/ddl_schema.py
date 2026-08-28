# src/rhosocial/activerecord/backend/dialect/mixins/ddl_schema.py
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateSchemaExpression,
        DropSchemaExpression,
    )


class SchemaMixin:
    """Mixin for schema DDL support."""

    def supports_schema(self) -> bool:
        """Whether the database models named schema namespaces at all.

        Umbrella switch over the granular ``supports_*_schema`` flags below.
        Backends without namespaces (SQLite, Firebird) keep this False;
        PostgreSQL, SQL Server, Oracle, Snowflake and MySQL-family databases
        (where a schema is a database) return True.
        """
        return False

    def supports_create_schema(self) -> bool:
        """Whether CREATE SCHEMA is supported."""
        return False

    def supports_drop_schema(self) -> bool:
        """Whether DROP SCHEMA is supported."""
        return False

    def supports_schema_if_not_exists(self) -> bool:
        """Whether CREATE SCHEMA IF NOT EXISTS is supported."""
        return False

    def supports_schema_if_exists(self) -> bool:
        """Whether DROP SCHEMA IF EXISTS is supported."""
        return False

    def supports_schema_cascade(self) -> bool:
        """Whether DROP SCHEMA CASCADE is supported."""
        return False

    def supports_schema_authorization(self) -> bool:
        """Whether AUTHORIZATION clause is supported."""
        return False

    def format_create_schema_statement(self, expr: "CreateSchemaExpression") -> Tuple[str, tuple]:
        """Format CREATE SCHEMA statement per SQL standard."""
        parts = ["CREATE SCHEMA"]
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.schema_name))
        if expr.authorization:
            parts.append(f"AUTHORIZATION {self.format_identifier(expr.authorization)}")
        return " ".join(parts), ()

    def format_drop_schema_statement(self, expr: "DropSchemaExpression") -> Tuple[str, tuple]:
        """Format DROP SCHEMA statement per SQL standard."""
        parts = ["DROP SCHEMA"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.schema_name))
        if expr.cascade:
            parts.append("CASCADE")
        return " ".join(parts), ()
