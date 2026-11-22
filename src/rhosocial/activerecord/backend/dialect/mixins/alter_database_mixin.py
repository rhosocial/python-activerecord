# src/rhosocial/activerecord/backend/dialect/mixins/alter_database_mixin.py
"""Per-statement mixin for AlterDatabaseSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Database

class AlterDatabaseMixin:
    def supports_alter_database(self) -> bool:
            """Whether ALTER DATABASE is supported. Defaults to False."""
            return False

    def format_alter_database_statement(
            self, expr: "AlterDatabaseStatement"
        ) -> Tuple[str, tuple]:
            """Format an ALTER DATABASE statement.

            Raises:
                TypeError: ``AlterDatabaseStatement.database`` is not a Database. A
                table or a view would be named here and the statement would alter it.
                UnsupportedFeatureError: If the dialect does not support
                    ALTER DATABASE.
            """
            if not isinstance(expr.database, Database):
                raise TypeError(
                    f"AlterDatabaseStatement.database must be a Database, "
                    f"got {type(expr.database).__name__}"
                )
            if not self.supports_alter_database():
                raise UnsupportedFeatureError(
                    self.name, "ALTER DATABASE",
                    f"{self.name} does not support ALTER DATABASE."
                )

            parts = ["ALTER DATABASE"]
            if expr.if_exists:
                parts.append("IF EXISTS")
            parts.append(expr.database.to_sql()[0])

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
