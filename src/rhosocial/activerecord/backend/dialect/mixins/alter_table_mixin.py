# .../mixins/alter_table_mixin.py
"""Per-statement mixin for AlterTableSupport. Members/order/signature mirror the protocol."""

from rhosocial.activerecord.backend.expression.statements import (
    TableCheckConstraint,
    TableForeignKeyConstraint,
)
from ...expression.statements.ddl_alter import AlterTableAction
from ...expression.objects import Table
from typing import Any, List, Tuple, TYPE_CHECKING
from enum import Enum

class AlterTableMixin:
    def supports_alter_table(self) -> bool:
            """Whether ALTER TABLE is supported.

            Defaults to True.
            """
            return True

    def supports_rename_table(self) -> bool:
            """Whether RENAME TABLE is supported.

            Defaults to True.
            """
            return True

    def supports_rename_column(self) -> bool:
            """Whether RENAME COLUMN is supported.

            Defaults to True.
            """
            return True

    def supports_alter_column_type(self) -> bool:
            """Whether altering column data type is supported.

            Defaults to True.
            """
            return True

    def supports_alter_column_properties(self) -> bool:
            """Whether ALTER COLUMN SET DEFAULT / DROP DEFAULT etc. is supported.

            Defaults to False.
            """
            return False

    def supports_alter_table_index_actions(self) -> bool:
            """Whether ADD/DROP INDEX via ALTER TABLE is supported.

            Defaults to False.
            """
            return False

    def supports_multi_action_alter_table(self) -> bool:
            """Whether ALTER TABLE supports multiple comma-separated actions.

            Defaults to True. SQL Server requires one action per statement.
            """
            return True

    def format_alter_table_statement(self, expr: "AlterTableStatement") -> Tuple[str, tuple]:
            """Format ALTER TABLE statement (generic implementation).

            When the dialect does not support multiple actions in one ALTER TABLE
            (e.g. SQL Server), a multi-action statement fails fast with
            UnsupportedFeatureError. An expression maps to one SQL statement, so
            joining actions with semicolons would hand cursor.execute() an
            unexecutable string; the caller must emit one AlterTableStatement per
            action instead.

            Args:
                expr: AlterTableStatement carrying the table name and the list of
                    actions to render.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``AlterTableStatement.table`` is not a Table. Another object
                kind would have had its own name rendered as the table's.
                TypeError: An entry of ``AlterTableStatement.actions`` is not an
                implementation of AlterTableAction. An entry of another kind has no
                action clause to dispatch on, so nothing would be rendered for it.
            """
            if not isinstance(expr.table, Table):
                raise TypeError(
                    f"AlterTableStatement.table must be a Table, "
                    f"got {type(expr.table).__name__}"
                )

            # AlterTableAction is an abstract base and cannot be instantiated, so
            # this reports that the entry is not an implementation of it
            # rather than naming a concrete type.
            for position, entry in enumerate(expr.actions):
                if not isinstance(entry, AlterTableAction):
                    raise TypeError(
                        f"AlterTableStatement.actions must hold AlterTableAction implementations, "
                        f"got {type(entry).__name__} at position {position}"
                    )
            all_params: List[Any] = []
            action_parts = []
            for action in expr.actions:
                action_part, action_params = action.to_sql()
                action_parts.append(action_part)
                all_params.extend(action_params)

            table_sql = expr.table.to_sql()[0]

            if not action_parts:
                return f"ALTER TABLE {table_sql}", ()

            if self.supports_multi_action_alter_table():
                combined = ", ".join(action_parts)
                return f"ALTER TABLE {table_sql} {combined}", tuple(all_params)

            # One expression produces one SQL statement (expression↔SQL is 1:1).
            # On a dialect that cannot combine actions, a multi-action statement
            # cannot be rendered as a single valid SQL — semicolon-joining would
            # emit two statements from one expression and hand an unexecutable
            # string to cursor.execute(). Fail fast and require the caller (the
            # migration planner) to split into one AlterTableStatement per action.
            if len(action_parts) > 1:
                from ..exceptions import UnsupportedFeatureError

                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER TABLE with multiple actions",
                    f"{self.name} cannot combine {len(action_parts)} actions in one "
                    f"ALTER TABLE. Emit one AlterTableStatement per action instead.",
                )
            return f"ALTER TABLE {table_sql} {action_parts[0]}", tuple(all_params)
