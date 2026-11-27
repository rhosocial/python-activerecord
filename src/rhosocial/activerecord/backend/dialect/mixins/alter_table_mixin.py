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
            """Format an ALTER TABLE statement carrying one action.

            One expression renders one statement, and that statement carries one
            action: the action is the unit the caller plans, authorizes and
            reports. The caller emits one ``AlterTableStatement`` per action and
            orders them itself.

            Args:
                expr: AlterTableStatement carrying the table name and the action
                    to render.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``AlterTableStatement.table`` is not a Table. Another object
                kind would have had its own name rendered as the table's.
                TypeError: ``AlterTableStatement.action`` is not an implementation
                of AlterTableAction. Another kind has no action clause to dispatch
                on, so nothing would be rendered for it.
            """
            if not isinstance(expr.table, Table):
                raise TypeError(
                    f"AlterTableStatement.table must be a Table, "
                    f"got {type(expr.table).__name__}"
                )

            # AlterTableAction is an abstract base and cannot be instantiated, so
            # this reports that the entry is not an implementation of it
            # rather than naming a concrete type.
            if not isinstance(expr.action, AlterTableAction):
                raise TypeError(
                    f"AlterTableStatement.action must be an AlterTableAction implementation, "
                    f"got {type(expr.action).__name__}"
                )

            action_sql, action_params = expr.action.to_sql()
            table_sql = expr.table.to_sql()[0]
            return f"ALTER TABLE {table_sql} {action_sql}", tuple(action_params)
