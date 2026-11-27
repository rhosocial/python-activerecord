# .../mixins/alter_table_mixin.py
"""Per-statement mixin for AlterTableSupport. Members/order/signature mirror the protocol."""

from ...expression.statements.ddl_alter import AlterTableAction
from ...expression.objects import Table
from typing import Any, List, Tuple

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

    def supports_alter_column_default(self) -> bool:
            """Whether ALTER COLUMN SET DEFAULT / DROP DEFAULT is supported.

            Defaults to False.
            """
            return False

    def supports_alter_column_nullability(self) -> bool:
            """Whether ALTER COLUMN SET NOT NULL / DROP NOT NULL is supported.

            Defaults to False.
            """
            return False

    def supports_alter_table_index_actions(self) -> bool:
            """Whether ADD/DROP INDEX via ALTER TABLE is supported.

            Defaults to False.
            """
            return False

    def format_alter_table_statement(self, expr: "AlterTableStatement") -> Tuple[str, tuple]:
            """Format ALTER TABLE statement (generic implementation).

            One expression renders one statement, and that statement carries one
            action. A multi-action statement fails fast with
            ``UnsupportedFeatureError``: comma-joining the actions would hide each
            one from the caller's plan (its own phase, permission and destructive
            check), and semicolon-joining would hand ``cursor.execute()`` two
            statements from one expression. The caller emits one
            ``AlterTableStatement`` per action and orders them itself.

            Args:
                expr: AlterTableStatement carrying the table name and the action
                    to render.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``AlterTableStatement.table`` is not a Table. Another object
                kind would have had its own name rendered as the table's.
                TypeError: An entry of ``AlterTableStatement.actions`` is not an
                implementation of AlterTableAction. An entry of another kind has no
                action clause to dispatch on, so nothing would be rendered for it.
                UnsupportedFeatureError: ``AlterTableStatement.actions`` holds more
                than one action.
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

            # One expression produces one SQL statement carrying one action
            # (expression↔SQL is 1:1). Comma-joining would hide each action from
            # the caller's plan -- its own phase, permission and destructive
            # check -- and semicolon-joining would emit two statements from one
            # expression. Fail fast and require one AlterTableStatement per
            # action.
            if len(action_parts) > 1:
                from ..exceptions import UnsupportedFeatureError

                raise UnsupportedFeatureError(
                    self.name,
                    "ALTER TABLE with multiple actions",
                    f"{self.name} renders one action per statement. Emit one "
                    f"AlterTableStatement per action and order them in the caller.",
                )
            return f"ALTER TABLE {table_sql} {action_parts[0]}", tuple(all_params)
