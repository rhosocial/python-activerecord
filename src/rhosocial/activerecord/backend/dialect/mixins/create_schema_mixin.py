# src/rhosocial/activerecord/backend/dialect/mixins/create_schema_mixin.py
"""Per-statement mixin for CreateSchemaSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Schema

class CreateSchemaMixin:
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

    def supports_schema_if_not_exists(self) -> bool:
            """Whether CREATE SCHEMA IF NOT EXISTS is supported.

            Defaults to False.
            """
            return False

    def supports_schema_authorization(self) -> bool:
            """Whether AUTHORIZATION clause is supported.

            Defaults to False.
            """
            return False

    def format_create_schema_statement(self, expr: "CreateSchemaStatement") -> Tuple[str, tuple]:
            """Format CREATE SCHEMA statement per SQL standard.

            Args:
                expr: CreateSchemaStatement carrying the schema name, optional
                    ``if_not_exists`` flag, and optional ``authorization`` owner.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``CreateSchemaStatement.schema`` is not a Schema. Another
                object kind would have had its own name rendered as the schema's.
                UnsupportedFeatureError: If the dialect does not support
                    CREATE SCHEMA or specific clauses.
            """
            if not isinstance(expr.schema, Schema):
                raise TypeError(
                    f"CreateSchemaStatement.schema must be a Schema, "
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
