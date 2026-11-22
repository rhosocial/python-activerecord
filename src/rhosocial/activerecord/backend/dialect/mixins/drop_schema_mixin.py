# src/rhosocial/activerecord/backend/dialect/mixins/drop_schema_mixin.py
"""Per-statement mixin for DropSchemaSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Schema

class DropSchemaMixin:
    def supports_drop_schema(self) -> bool:
            """Whether DROP SCHEMA is supported.

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

    def supports_schema_restrict(self) -> bool:
            """Whether DROP SCHEMA RESTRICT is supported.

            Defaults to False.
            """
            return False

    def format_drop_schema_statement(self, expr: "DropSchemaStatement") -> Tuple[str, tuple]:
            """Format DROP SCHEMA statement per SQL standard.

            Args:
                expr: DropSchemaStatement carrying the schema name, optional
                    ``if_exists`` flag, and optional ``cascade`` flag.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``DropSchemaStatement.schema`` is not a Schema. Another
                object kind would have had its own name rendered as the schema's.
                UnsupportedFeatureError: If the dialect does not support
                    DROP SCHEMA or specific clauses.
            """
            if not isinstance(expr.schema, Schema):
                raise TypeError(
                    f"DropSchemaStatement.schema must be a Schema, "
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
            if expr.restrict and not self.supports_schema_restrict():
                raise UnsupportedFeatureError(
                    self.name, "DROP SCHEMA RESTRICT",
                    f"{self.name} does not support DROP SCHEMA RESTRICT."
                )
            parts = ["DROP SCHEMA"]
            if expr.if_exists:
                parts.append("IF EXISTS")
            parts.append(expr.schema.to_sql()[0])
            if expr.cascade:
                parts.append("CASCADE")
            elif expr.restrict:
                parts.append("RESTRICT")
            return " ".join(parts), ()
