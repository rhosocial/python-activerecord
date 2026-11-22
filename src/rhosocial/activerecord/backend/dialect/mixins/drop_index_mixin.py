# src/rhosocial/activerecord/backend/dialect/mixins/drop_index_mixin.py
"""Per-statement mixin for DropIndexSupport. Members/order/signature mirror the protocol."""

from typing import List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.bases import ToSQLProtocol
from rhosocial.activerecord.backend.expression.objects import Index, Table

class DropIndexMixin:
    def supports_drop_index(self) -> bool:
            """Whether DROP INDEX is supported.

            Defaults to True.
            """
            return True

    def supports_index_if_exists(self) -> bool:
            """Whether DROP INDEX IF EXISTS is supported.

            Defaults to False.
            """
            return False

    def supports_drop_index_on_table(self) -> bool:
            """Whether DROP INDEX accepts/requires the ``ON <table>`` clause.

            MySQL/MariaDB/SQL Server use ``DROP INDEX name ON table``;
            PostgreSQL/SQLite/Oracle drop indexes by name without ``ON``.
            When False, the generic ``format_drop_index_statement`` omits the
            ``ON <table>`` suffix even if the expression carries a table name.

            Defaults to True.
            """
            return True

    def format_drop_index_statement(self, expr: "DropIndexStatement") -> Tuple[str, tuple]:
            """Format DROP INDEX statement per SQL standard.

            Args:
                expr: DropIndexStatement carrying the index name, optional
                    ``if_exists`` flag, and optional table name.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``DropIndexStatement.index`` is not an Index. Another object
                kind would have had its own name rendered as the index's.
                TypeError: ``DropIndexStatement.table`` is not a Table. Another object
                kind would have had its own name rendered as the table's.
                UnsupportedFeatureError: If the dialect does not support
                    DROP INDEX IF EXISTS.
            """
            if not isinstance(expr.index, Index):
                raise TypeError(
                    f"DropIndexStatement.index must be an Index, "
                    f"got {type(expr.index).__name__}"
                )

            if expr.table is not None and not isinstance(expr.table, Table):
                raise TypeError(
                    f"DropIndexStatement.table must be a Table, "
                    f"got {type(expr.table).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError
            parts = ["DROP INDEX"]
            if expr.concurrent:
                if not self.supports_concurrent_index():
                    raise UnsupportedFeatureError(
                        self.name, "DROP INDEX CONCURRENTLY",
                        f"{self.name} does not support DROP INDEX CONCURRENTLY."
                    )
                parts.append("CONCURRENTLY")
            if expr.if_exists:
                if not self.supports_index_if_exists():
                    raise UnsupportedFeatureError(
                        self.name, "DROP INDEX IF EXISTS",
                        f"{self.name} does not support DROP INDEX IF EXISTS."
                    )
                parts.append("IF EXISTS")
            parts.append(expr.index.to_sql()[0])
            if expr.table and self.supports_drop_index_on_table():
                parts.append("ON")
                parts.append(expr.table.to_sql()[0])
            return " ".join(parts), ()
