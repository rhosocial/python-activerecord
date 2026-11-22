# src/rhosocial/activerecord/backend/dialect/mixins/drop_database_mixin.py
"""Per-statement mixin for DropDatabaseSupport. Members/order/signature mirror the protocol."""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Database

class DropDatabaseMixin:
    def supports_drop_database(self) -> bool:
            """Whether DROP DATABASE is supported. Defaults to False."""
            return False

    def supports_database_if_exists(self) -> bool:
            """Whether DROP DATABASE IF EXISTS is supported. Defaults to False."""
            return False

    def supports_database_force_drop(self) -> bool:
            """Whether FORCE / WITH (FORCE) drop is supported. Defaults to False."""
            return False

    def supports_undrop_database(self) -> bool:
            """Whether UNDROP DATABASE is supported. Defaults to False."""
            return False

    def format_drop_database_statement(
            self, expr: "DropDatabaseStatement"
        ) -> Tuple[str, tuple]:
            """Format a DROP DATABASE statement.

            Raises:
                TypeError: ``DropDatabaseStatement.database`` is not a Database.
                Another object kind would have had its own name rendered as the
                database's.
                UnsupportedFeatureError: If the dialect does not support
                    DROP DATABASE or specific clauses.
            """
            if not isinstance(expr.database, Database):
                raise TypeError(
                    f"DropDatabaseStatement.database must be a Database, "
                    f"got {type(expr.database).__name__}"
                )
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
            parts.append(expr.database.to_sql()[0])
            if expr.force:
                parts.append("WITH (FORCE)")

            return " ".join(parts), ()
