# .../mixins/create_table_like_mixin.py
"""Per-statement mixin for CreateTableLikeSupport. Members/order/signature mirror the protocol."""

from rhosocial.activerecord.backend.expression.statements import (
    TableCheckConstraint,
    TableForeignKeyConstraint,
)
from ...expression.statements.ddl_alter import AlterTableAction
from ...expression.objects import Table
from typing import Any, List, Tuple, TYPE_CHECKING
from enum import Enum

class CreateTableLikeMixin:
    def supports_create_table_like(self) -> bool:
            """Whether ``CREATE TABLE ... LIKE`` is supported.

            Defaults to ``False``. Backends that support the vendor extension
            override this to return ``True`` and inherit the generic
            :meth:`format_create_table_like_statement` rendering; backends with a
            different grammar override the formatter instead.
            """
            return False

    def format_create_table_like_statement(self, expr: "CreateTableLikeStatement") -> Tuple[str, tuple]:
            """Format ``CREATE TABLE ... LIKE`` (generic reusable implementation).

            Renders the common vendor form::

                CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <table> LIKE <source>

            Dialects that advertise :meth:`supports_create_table_like` inherit
            this rendering as-is (e.g. MySQL/MariaDB/Snowflake/BigQuery);
            dialects with a different grammar (PostgreSQL's column-list
            ``(LIKE ... [INCLUDING ...])`` clause, ClickHouse's ``AS``) override
            it. Dialects that do not support the form keep
            :meth:`supports_create_table_like` at ``False``.

            ``expr.like_options`` (PostgreSQL INCLUDING/EXCLUDING) is intentionally
            ignored here; PostgreSQL overrides this method.

            Args:
                expr: The LIKE expression carrying the target ``table`` and the
                    source ``like_table``.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``CreateTableLikeStatement.table`` is not a Table. Another
                object kind would have had its own name rendered as the table's.
                TypeError: ``CreateTableLikeStatement.like_table`` is not a Table.
                Another object kind would have had its own name rendered as the copied
                table's.
                UnsupportedFeatureError: If :meth:`supports_create_table_like` is
                    False for the dialect.
            """
            if not isinstance(expr.table, Table):
                raise TypeError(
                    f"CreateTableLikeStatement.table must be a Table, "
                    f"got {type(expr.table).__name__}"
                )

            if not isinstance(expr.like_table, Table):
                raise TypeError(
                    f"CreateTableLikeStatement.like_table must be a Table, "
                    f"got {type(expr.like_table).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError
            if not self.supports_create_table_like():
                raise UnsupportedFeatureError(self.name, "CREATE TABLE ... LIKE")
            temp_part = "TEMPORARY " if expr.temporary else ""
            not_exists_part = "IF NOT EXISTS " if expr.if_not_exists else ""
            table_sql, table_params = expr.table.to_sql()
            source_sql, source_params = expr.like_table.to_sql()
            parts = [
                f"CREATE {temp_part}TABLE {not_exists_part}{table_sql}",
                f"LIKE {source_sql}",
            ]
            return " ".join(parts), tuple(table_params) + tuple(source_params)
