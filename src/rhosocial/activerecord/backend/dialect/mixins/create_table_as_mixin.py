# .../mixins/create_table_as_mixin.py
"""Per-statement mixin for CreateTableAsSupport. Members/order/signature mirror the protocol."""

from rhosocial.activerecord.backend.expression.statements import (
    TableCheckConstraint,
    TableForeignKeyConstraint,
)
from ...expression.statements.ddl_alter import AlterTableAction
from ...expression.objects import Table
from typing import Any, List, Tuple, TYPE_CHECKING
from enum import Enum

class CreateTableAsMixin:
    def supports_create_table_as(self) -> bool:
            """Whether ``CREATE TABLE ... AS <query>`` (CTAS) is supported.

            Defaults to ``True``: CTAS is broadly portable and the generic
            renderer emits the portable ``AS <query>`` form (no parentheses).
            """
            return True

    def supports_create_table_as_bind_parameters(self) -> bool:
            """Whether a CTAS body may carry bind parameters.

            Defaults to ``False``. A DDL statement carries no bind parameters
            unless the dialect says it can, and the body of a CTAS is the one
            DDL body that is a query, so this is the question this probe
            answers.

            The two differ by engine, and the answer is measured rather than
            assumed:

            * PostgreSQL accepts them -- the body is executed once, so a bound
              value is meaningful (19beta4: ``CREATE TABLE t AS SELECT $1 FROM
              s`` creates the table).
            * MySQL and MariaDB accept them; their "parameters" are
              interpolated client-side, so the value is baked into the text.
            * ClickHouse accepts them, for the same reason.
            * Oracle refuses them: Oracle's DDL statements never take bind
              variables, and the driver rejects the statement before the
              server sees it (``DPY-4009: 0 positional bind values are
              required but 1 were provided``).

            A dialect that does not answer refuses the statement by name, with
            the way out named -- build the query with an inlined literal.
            """
            return False

    def format_create_table_as_statement(self, expr: "CreateTableAsStatement") -> Tuple[str, tuple]:
            """Format ``CREATE TABLE ... AS <query>`` (generic CTAS implementation).

            Emits the portable form::

                CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <table>
                    [<storage options>] AS <query> [WITH [NO] DATA]

            The query is rendered **without parentheses** -- parenthesising is
            rejected by SQLite (and several other engines). ``WITH [NO] DATA`` is
            only appended when :attr:`CreateTableAsStatement.with_data` is set
            (PostgreSQL semantics).

            Args:
                expr: CreateTableAsStatement carrying the target table and query.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``CreateTableAsStatement.table`` is not a Table. Another
                object kind would have had its own name rendered as the table's.
            """
            if not isinstance(expr.table, Table):
                raise TypeError(
                    f"CreateTableAsStatement.table must be a Table, "
                    f"got {type(expr.table).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError

            from ...expression.statements.dql import QueryStatement

            wrapped = expr.as_query
            if isinstance(wrapped, QueryStatement) and wrapped.hints:
                raise TypeError(
                    f"{type(expr).__name__}: the embedded query carries optimizer hints. "
                    "A hint comment belongs to the outermost statement -- it is a comment "
                    "on the statement as a whole, and two blocks are rejected -- so the "
                    "hints must be given to this statement, not to the query it wraps."
                )

            if not self.supports_create_table_as():
                raise UnsupportedFeatureError(self.name, "CREATE TABLE ... AS")

            if (expr.with_data or expr.no_data) and not self.supports_with_data_clause():
                feature = "WITH DATA" if expr.with_data else "WITH NO DATA"
                raise UnsupportedFeatureError(
                    self.name, feature,
                    f"{self.name} does not support {feature} for CREATE TABLE AS."
                )

            all_params: List[Any] = []
            temp_part = "TEMPORARY " if expr.temporary else ""
            not_exists_part = "IF NOT EXISTS " if expr.if_not_exists else ""
            table_sql, table_params = expr.table.to_sql()
            all_params.extend(table_params)
            parts = [f"CREATE {temp_part}TABLE {not_exists_part}{table_sql}"]

            if expr.storage_options is not None:
                storage_sql, storage_params = expr.storage_options.to_sql()
                if storage_sql:
                    parts.append(storage_sql)
                    all_params.extend(storage_params)

            query_sql, query_params = expr.as_query.to_sql()
            if query_params and not self.supports_create_table_as_bind_parameters():
                self.refuse_ddl_bind_parameters("CREATE TABLE ... AS with bound parameters")
            parts.append(f"AS {query_sql}")
            all_params.extend(query_params)

            if expr.with_data:
                parts.append(" WITH DATA")
            elif expr.no_data:
                parts.append(" WITH NO DATA")

            return " ".join(parts), tuple(all_params)
