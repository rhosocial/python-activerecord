# src/rhosocial/activerecord/backend/dialect/mixins/ddl_schema.py
"""Dialect mixin for schema (namespace) DDL support."""
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateSchemaExpression,
        DropSchemaExpression,
    )


class SchemaMixin:
    """Mixin adding support for schema (namespace) qualification and DDL."""

    def supports_schema(self) -> bool:
        """Whether a schema qualifier can be rendered and used on this backend.

        True means a ``schema_name`` given to an expression is accepted and
        reaches the server as a qualifier. What it *names* is defined by each
        backend and is not implied by this flag:

        - PostgreSQL, SQL Server, Oracle -- a schema inside the current database
        - Snowflake -- a schema, which belongs to a database, so a fully
          qualified name is ``database.schema.object``
        - BigQuery -- a dataset
        - MySQL, MariaDB, ClickHouse -- a database; MySQL and MariaDB spell it
          ``schema`` as a synonym for ``database``, and ClickHouse has no schema
          concept in the language at all

        False means the backend has no namespace layer to qualify into (SQLite,
        Firebird), and a ``schema_name`` is rejected rather than rendered into
        SQL the server would reject.

        This is not an umbrella switch over the ``supports_*_schema`` flags
        below, which are about DDL statements rather than qualification.
        """
        return False

    def supports_create_schema(self) -> bool:
        """Whether CREATE SCHEMA is supported.

        Defaults to False.
        """
        return False

    def supports_drop_schema(self) -> bool:
        """Whether DROP SCHEMA is supported.

        Defaults to False.
        """
        return False

    def supports_schema_if_not_exists(self) -> bool:
        """Whether CREATE SCHEMA IF NOT EXISTS is supported.

        Defaults to False.
        """
        return False

    def supports_schema_if_exists(self) -> bool:
        """Whether DROP SCHEMA IF EXISTS is supported.

        Defaults to False.
        """
        return False

    def supports_schema_cascade(self) -> bool:
        """Whether DROP SCHEMA CASCADE is supported.

        Defaults to False.
        """
        return False

    def supports_schema_authorization(self) -> bool:
        """Whether AUTHORIZATION clause is supported.

        Defaults to False.
        """
        return False

    def format_create_schema_statement(self, expr: "CreateSchemaExpression") -> Tuple[str, tuple]:
        """Format CREATE SCHEMA statement per SQL standard.

        Args:
            expr: CreateSchemaExpression carrying the schema name, optional
                ``if_not_exists`` flag, and optional ``authorization`` owner.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                CREATE SCHEMA or specific clauses.
        """
        if not self.supports_create_schema():
            raise UnsupportedFeatureError(
                self.name, "CREATE SCHEMA",
                f"{self.name} does not support CREATE SCHEMA."
            )
        if expr.if_not_exists and not self.supports_schema_if_not_exists():
            raise UnsupportedFeatureError(
                self.name, "CREATE SCHEMA IF NOT EXISTS",
                f"{self.name} does not support CREATE SCHEMA IF NOT EXISTS."
            )
        if expr.authorization and not self.supports_schema_authorization():
            raise UnsupportedFeatureError(
                self.name, "CREATE SCHEMA AUTHORIZATION",
                f"{self.name} does not support CREATE SCHEMA AUTHORIZATION."
            )
        parts = ["CREATE SCHEMA"]
        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")
        parts.append(self.format_identifier(expr.schema_name))
        if expr.authorization:
            parts.append(f"AUTHORIZATION {self.format_identifier(expr.authorization)}")
        return " ".join(parts), ()

    def format_drop_schema_statement(self, expr: "DropSchemaExpression") -> Tuple[str, tuple]:
        """Format DROP SCHEMA statement per SQL standard.

        Args:
            expr: DropSchemaExpression carrying the schema name, optional
                ``if_exists`` flag, and optional ``cascade`` flag.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                DROP SCHEMA or specific clauses.
        """
        if not self.supports_drop_schema():
            raise UnsupportedFeatureError(
                self.name, "DROP SCHEMA",
                f"{self.name} does not support DROP SCHEMA."
            )
        if expr.if_exists and not self.supports_schema_if_exists():
            raise UnsupportedFeatureError(
                self.name, "DROP SCHEMA IF EXISTS",
                f"{self.name} does not support DROP SCHEMA IF EXISTS."
            )
        if expr.cascade and not self.supports_schema_cascade():
            raise UnsupportedFeatureError(
                self.name, "DROP SCHEMA CASCADE",
                f"{self.name} does not support DROP SCHEMA CASCADE."
            )
        parts = ["DROP SCHEMA"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.schema_name))
        if expr.cascade:
            parts.append("CASCADE")
        return " ".join(parts), ()
