# .../mixins/create_table_clone_mixin.py
"""Per-statement mixin for CreateTableCloneSupport. Members/order/signature mirror the protocol."""

from rhosocial.activerecord.backend.expression.statements import (
    TableCheckConstraint,
    TableForeignKeyConstraint,
)
from ...expression.statements.ddl_alter import AlterTableAction
from ...expression.objects import Table
from typing import Any, List, Tuple, TYPE_CHECKING
from enum import Enum

class CreateTableCloneMixin:
    def supports_create_table_clone(self) -> bool:
            """Whether ``CREATE TABLE ... CLONE/COPY`` is supported.

            Defaults to ``False``; backends with zero-copy clone (Snowflake,
            BigQuery, ClickHouse) override this to return ``True``.
            """
            return False

    def format_create_table_clone_statement(self, expr: "CreateTableCloneStatement") -> Tuple[str, tuple]:
            """Format ``CREATE TABLE ... CLONE/COPY`` (generic reusable implementation).

            Renders::

                CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <table> {CLONE|COPY} <source>
                    [COPY GRANTS]

            Backends with different grammar (ClickHouse ``CLONE AS``, BigQuery /
            Snowflake time-travel suffixes) override this method. Dialects that do
            not support the form keep :meth:`supports_create_table_clone` at
            ``False``.

            Args:
                expr: The clone expression carrying the target ``table``, the
                    ``source_table``, the ``mode`` (CLONE/COPY) and ``copy_grants``.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``CreateTableCloneStatement.table`` is not a Table. Another
                object kind would have had its own name rendered as the table's.
                TypeError: ``CreateTableCloneStatement.source_table`` is not a Table.
                Another object kind would have had its own name rendered as the
                source's.
                UnsupportedFeatureError: If :meth:`supports_create_table_clone` is
                    False for the dialect.
            """
            if not isinstance(expr.table, Table):
                raise TypeError(
                    f"CreateTableCloneStatement.table must be a Table, "
                    f"got {type(expr.table).__name__}"
                )

            if not isinstance(expr.source_table, Table):
                raise TypeError(
                    f"CreateTableCloneStatement.source_table must be a Table, "
                    f"got {type(expr.source_table).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError
            if not self.supports_create_table_clone():
                raise UnsupportedFeatureError(self.name, "CREATE TABLE ... CLONE/COPY")
            temp_part = "TEMPORARY " if expr.temporary else ""
            not_exists_part = "IF NOT EXISTS " if expr.if_not_exists else ""
            table_sql, table_params = expr.table.to_sql()
            source_sql, source_params = expr.source_table.to_sql()
            parts = [
                f"CREATE {temp_part}TABLE {not_exists_part}{table_sql}",
                f"{expr.mode.value} {source_sql}",
            ]
            if expr.copy_grants:
                parts.append("COPY GRANTS")
            return " ".join(parts), tuple(table_params) + tuple(source_params)
