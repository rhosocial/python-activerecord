# src/rhosocial/activerecord/backend/dialect/mixins/ddl_database.py
"""Dialect mixin for DATABASE DDL support."""

from typing import Any, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements.ddl_database import (
        AlterDatabaseExpression,
        CreateDatabaseExpression,
        DropDatabaseExpression,
    )


class DatabaseMixin:
    """Mixin adding support for DATABASE DDL statements.

    Provides default capability switches (all False) and formatting methods
    that raise UnsupportedFeatureError. Backends override the relevant
    methods to provide actual SQL generation.
    """

    def supports_database(self) -> bool:
        """Whether the backend has a DATABASE concept at all.

        Defaults to False. SQLite, Firebird, BigQuery return False.
        """
        return False

    def supports_create_database(self) -> bool:
        """Whether CREATE DATABASE is supported. Defaults to False."""
        return False

    def supports_drop_database(self) -> bool:
        """Whether DROP DATABASE is supported. Defaults to False."""
        return False

    def supports_alter_database(self) -> bool:
        """Whether ALTER DATABASE is supported. Defaults to False."""
        return False

    def supports_database_if_not_exists(self) -> bool:
        """Whether CREATE DATABASE IF NOT EXISTS is supported. Defaults to False."""
        return False

    def supports_database_if_exists(self) -> bool:
        """Whether DROP DATABASE IF EXISTS is supported. Defaults to False."""
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

    def supports_database_force_drop(self) -> bool:
        """Whether FORCE / WITH (FORCE) drop is supported. Defaults to False."""
        return False

    def supports_undrop_database(self) -> bool:
        """Whether UNDROP DATABASE is supported. Defaults to False."""
        return False

    def supports_database_or_replace(self) -> bool:
        """Whether CREATE OR REPLACE DATABASE is supported. Defaults to False."""
        return False

    def format_create_database_statement(
        self, expr: "CreateDatabaseExpression"
    ) -> Tuple[str, tuple]:
        """Format a CREATE DATABASE statement.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                CREATE DATABASE or specific clauses.
        """
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
        parts.append(self.format_identifier(expr.database_name))

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

    def format_drop_database_statement(
        self, expr: "DropDatabaseExpression"
    ) -> Tuple[str, tuple]:
        """Format a DROP DATABASE statement.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                DROP DATABASE or specific clauses.
        """
        if not self.supports_drop_database():
            raise UnsupportedFeatureError(
                self.name, "DROP DATABASE",
                f"{self.name} does not support DROP DATABASE."
            )
        if expr.if_exists and not self.supports_database_if_exists():
            raise UnsupportedFeatureError(
                self.name, "DROP DATABASE IF EXISTS",
                f"{self.name} does not support DROP DATABASE IF EXISTS."
            )
        if expr.force and not self.supports_database_force_drop():
            raise UnsupportedFeatureError(
                self.name, "DROP DATABASE FORCE",
                f"{self.name} does not support FORCE for DROP DATABASE."
            )

        parts = ["DROP DATABASE"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.database_name))
        if expr.force:
            parts.append("WITH (FORCE)")

        return " ".join(parts), ()

    def format_alter_database_statement(
        self, expr: "AlterDatabaseExpression"
    ) -> Tuple[str, tuple]:
        """Format an ALTER DATABASE statement.

        Raises:
            UnsupportedFeatureError: If the dialect does not support
                ALTER DATABASE.
        """
        if not self.supports_alter_database():
            raise UnsupportedFeatureError(
                self.name, "ALTER DATABASE",
                f"{self.name} does not support ALTER DATABASE."
            )

        parts = ["ALTER DATABASE"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.database_name))

        from ...expression.statements.ddl_database import AlterDatabaseAction
        if expr.action == AlterDatabaseAction.RENAME_TO:
            parts.append(f"RENAME TO {self.format_identifier(expr.target)}")
        elif expr.action == AlterDatabaseAction.OWNER_TO:
            parts.append(f"OWNER TO {self.format_identifier(expr.target)}")
        elif expr.action == AlterDatabaseAction.CHARACTER_SET:
            parts.append(f"CHARACTER SET = '{expr.target}'")
        elif expr.action == AlterDatabaseAction.COLLATION:
            parts.append(f"COLLATE = '{expr.target}'")
        elif expr.action == AlterDatabaseAction.SWAP_WITH:
            parts.append(f"SWAP WITH {self.format_identifier(expr.target)}")
        elif expr.action == AlterDatabaseAction.SET_PROPERTY:
            props = ", ".join(f"{k} = '{v}'" for k, v in expr.properties.items())
            parts.append(f"SET {props}")
        elif expr.action == AlterDatabaseAction.UNSET_PROPERTY:
            props = ", ".join(expr.properties.keys())
            parts.append(f"UNSET {props}")
        elif expr.action == AlterDatabaseAction.ENABLE_REPLICATION:
            parts.append("ENABLE REPLICATION")
        elif expr.action == AlterDatabaseAction.DISABLE_REPLICATION:
            parts.append("DISABLE REPLICATION")
        elif expr.action == AlterDatabaseAction.ENABLE_FAILOVER:
            parts.append("ENABLE FAILOVER")
        elif expr.action == AlterDatabaseAction.DISABLE_FAILOVER:
            parts.append("DISABLE FAILOVER")

        return " ".join(parts), ()


__all__ = ["DatabaseMixin"]
