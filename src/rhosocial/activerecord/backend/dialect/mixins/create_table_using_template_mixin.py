# .../mixins/create_table_using_template_mixin.py
"""Per-statement mixin for CreateTableUsingTemplateSupport. Members/order/signature mirror the protocol."""

from rhosocial.activerecord.backend.expression.statements import (
    TableCheckConstraint,
    TableForeignKeyConstraint,
)
from ...expression.statements.ddl_alter import AlterTableAction
from ...expression.objects import Table
from typing import Any, List, Tuple, TYPE_CHECKING
from enum import Enum

class CreateTableUsingTemplateMixin:
    def supports_create_table_using_template(self) -> bool:
            """Whether ``CREATE TABLE ... USING TEMPLATE`` is supported.

            Defaults to ``False``; only Snowflake implements it.
            """
            return False

    def format_create_table_from_template_statement(
            self, expr: "CreateTableFromTemplateStatement"
        ) -> Tuple[str, tuple]:
            """Format ``CREATE TABLE ... USING TEMPLATE`` (generic reusable implementation).

            Renders::

                CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <table>
                    USING TEMPLATE <template>

            Args:
                expr: The template expression carrying the target ``table`` and the
                    ``template`` query.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``CreateTableFromTemplateStatement.table`` is not a Table.
                Another object kind would have had its own name rendered as the table's.
                UnsupportedFeatureError: If
                    :meth:`supports_create_table_using_template` is False for the
                    dialect.
            """
            if not isinstance(expr.table, Table):
                raise TypeError(
                    f"CreateTableFromTemplateStatement.table must be a Table, "
                    f"got {type(expr.table).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError
            if not self.supports_create_table_using_template():
                raise UnsupportedFeatureError(self.name, "CREATE TABLE ... USING TEMPLATE")
            temp_part = "TEMPORARY " if expr.temporary else ""
            not_exists_part = "IF NOT EXISTS " if expr.if_not_exists else ""
            table_sql, table_params = expr.table.to_sql()
            template_sql, template_params = expr.template.to_sql()
            parts = [
                f"CREATE {temp_part}TABLE {not_exists_part}{table_sql}",
                f"USING TEMPLATE {template_sql}",
            ]
            return " ".join(parts), tuple(table_params) + tuple(template_params)
