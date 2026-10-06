# src/rhosocial/activerecord/backend/dialect/mixins/ddl_schema.py
"""Dialect mixin for schema (namespace) DDL support."""
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError
from ...expression.objects import Schema

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import (
        CreateSchemaExpression,
        DropSchemaExpression,
    )


class SchemaMixin:
    """Mixin adding support for schema (namespace) DDL statements."""

    def supports_schema(self) -> bool:
        """Whether the database models named schema namespaces at all.

        A DDL-side switch: it answers whether schemas exist in the engine, which
        is what decides whether ``CREATE SCHEMA`` can be offered at all. Whether a
        name may be *qualified* with a schema is a separate question with its own
        switch on the naming side --
        :meth:`~.schema_namespace.NamespaceMixin.supports_schema_qualification` --
        and an engine may answer the two differently.

        Umbrella over the granular ``supports_create_schema`` /
        ``supports_drop_schema`` flags below. Backends without namespaces (SQLite,
        Firebird) keep this ``False``; PostgreSQL, SQL Server, Oracle, Snowflake
        and the MySQL family return ``True``.
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
            TypeError: ``CreateSchemaExpression.schema`` is not a Schema. Another
            object kind would have had its own name rendered as the schema's.
            UnsupportedFeatureError: If the dialect does not support
                CREATE SCHEMA or specific clauses.
        """
        if not isinstance(expr.schema, Schema):
            raise TypeError(
                f"CreateSchemaExpression.schema must be a Schema, "
                f"got {type(expr.schema).__name__}"
            )
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
        parts.append(expr.schema.to_sql()[0])
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
            TypeError: ``DropSchemaExpression.schema`` is not a Schema. Another
            object kind would have had its own name rendered as the schema's.
            UnsupportedFeatureError: If the dialect does not support
                DROP SCHEMA or specific clauses.
        """
        if not isinstance(expr.schema, Schema):
            raise TypeError(
                f"DropSchemaExpression.schema must be a Schema, "
                f"got {type(expr.schema).__name__}"
            )
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
        parts.append(expr.schema.to_sql()[0])
        if expr.cascade:
            parts.append("CASCADE")
        return " ".join(parts), ()
