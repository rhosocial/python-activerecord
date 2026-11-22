# src/rhosocial/activerecord/backend/dialect/mixins/create_database_mixin.py
"""Per-statement mixin for CreateDatabaseSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Database

class CreateDatabaseMixin:
    def supports_database(self) -> bool:
            """Whether the backend has a DATABASE concept at all.

            Defaults to False. SQLite, Firebird, BigQuery return False.
            """
            return False

    def supports_create_database(self) -> bool:
            """Whether CREATE DATABASE is supported. Defaults to False."""
            return False

    def supports_database_if_not_exists(self) -> bool:
            """Whether CREATE DATABASE IF NOT EXISTS is supported. Defaults to False."""
            return False

    def supports_database_owner(self) -> bool:
            """Whether OWNER/AUTHORIZATION clause is supported. Defaults to False."""
            return False

    def supports_database_encoding(self) -> bool:
            """Whether CHARACTER SET/ENCODING clause is supported. Defaults to False."""
            return False

    def supports_database_collation(self) -> bool:
            """Whether COLLATION clause is supported. Defaults to False."""
            return False

    def supports_database_comment(self) -> bool:
            """Whether COMMENT clause is supported. Defaults to False."""
            return False

    def supports_database_tablespace(self) -> bool:
            """Whether TABLESPACE clause is supported. Defaults to False."""
            return False

    def supports_database_template(self) -> bool:
            """Whether TEMPLATE clause is supported. Defaults to False."""
            return False

    def supports_database_connection_limit(self) -> bool:
            """Whether CONNECTION LIMIT clause is supported. Defaults to False."""
            return False

    def supports_database_or_replace(self) -> bool:
            """Whether CREATE OR REPLACE DATABASE is supported. Defaults to False."""
            return False

    def format_create_database_statement(
            self, expr: "CreateDatabaseStatement"
        ) -> Tuple[str, tuple]:
            """Format a CREATE DATABASE statement.

            Raises:
                TypeError: ``CreateDatabaseStatement.database`` is not a Database.
                Another object kind would have had its own name rendered as the
                database's.
                UnsupportedFeatureError: If the dialect does not support
                    CREATE DATABASE or specific clauses.
            """
            if not isinstance(expr.database, Database):
                raise TypeError(
                    f"CreateDatabaseStatement.database must be a Database, "
                    f"got {type(expr.database).__name__}"
                )
            if not self.supports_create_database():
                raise UnsupportedFeatureError(
                    self.name, "CREATE DATABASE",
                    f"{self.name} does not support CREATE DATABASE."
                )
            if expr.if_not_exists and not self.supports_database_if_not_exists():
                raise UnsupportedFeatureError(
                    self.name, "CREATE DATABASE IF NOT EXISTS",
                    f"{self.name} does not support CREATE DATABASE IF NOT EXISTS."
                )
            if expr.or_replace and not self.supports_database_or_replace():
                raise UnsupportedFeatureError(
                    self.name, "CREATE OR REPLACE DATABASE",
                    f"{self.name} does not support CREATE OR REPLACE DATABASE."
                )
            if expr.owner and not self.supports_database_owner():
                raise UnsupportedFeatureError(
                    self.name, "CREATE DATABASE OWNER",
                    f"{self.name} does not support OWNER clause for CREATE DATABASE."
                )
            if expr.encoding and not self.supports_database_encoding():
                raise UnsupportedFeatureError(
                    self.name, "CREATE DATABASE ENCODING",
                    f"{self.name} does not support ENCODING clause for CREATE DATABASE."
                )
            if expr.collation and not self.supports_database_collation():
                raise UnsupportedFeatureError(
                    self.name, "CREATE DATABASE COLLATION",
                    f"{self.name} does not support COLLATION clause for CREATE DATABASE."
                )
            if expr.comment and not self.supports_database_comment():
                raise UnsupportedFeatureError(
                    self.name, "CREATE DATABASE COMMENT",
                    f"{self.name} does not support COMMENT clause for CREATE DATABASE."
                )
            if expr.tablespace and not self.supports_database_tablespace():
                raise UnsupportedFeatureError(
                    self.name, "CREATE DATABASE TABLESPACE",
                    f"{self.name} does not support TABLESPACE clause for CREATE DATABASE."
                )
            if expr.template and not self.supports_database_template():
                raise UnsupportedFeatureError(
                    self.name, "CREATE DATABASE TEMPLATE",
                    f"{self.name} does not support TEMPLATE clause for CREATE DATABASE."
                )
            if expr.connection_limit is not None and not self.supports_database_connection_limit():
                raise UnsupportedFeatureError(
                    self.name, "CREATE DATABASE CONNECTION LIMIT",
                    f"{self.name} does not support CONNECTION LIMIT clause for CREATE DATABASE."
                )

            parts = ["CREATE"]
            if expr.or_replace:
                parts.append("OR REPLACE")
            parts.append("DATABASE")
            if expr.if_not_exists:
                parts.append("IF NOT EXISTS")
            parts.append(expr.database.to_sql()[0])

            if expr.encoding:
                parts.append(f"ENCODING = '{expr.encoding}'")
            if expr.collation:
                parts.append(f"LC_COLLATE = '{expr.collation}'")
            if expr.template:
                parts.append(f"TEMPLATE = {self.format_identifier(expr.template)}")
            if expr.owner:
                parts.append(f"OWNER = {self.format_identifier(expr.owner)}")
            if expr.connection_limit is not None:
                parts.append(f"CONNECTION LIMIT = {expr.connection_limit}")
            if expr.tablespace:
                parts.append(f"TABLESPACE = {self.format_identifier(expr.tablespace)}")
            if expr.comment:
                escaped_comment = expr.comment.replace("'", "''")
                parts.append(f"COMMENT = '{escaped_comment}'")

            return " ".join(parts), ()
