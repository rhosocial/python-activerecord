# .../mixins/drop_table_mixin.py
"""Per-statement mixin for DropTableSupport. Members/order/signature mirror the protocol."""

from rhosocial.activerecord.backend.expression.statements import (
    TableCheckConstraint,
    TableForeignKeyConstraint,
)
from ...expression.statements.ddl_alter import AlterTableAction
from ...expression.objects import Table
from typing import Any, List, Tuple, TYPE_CHECKING
from enum import Enum

class DropTableMixin:
    def supports_drop_table(self) -> bool:
            """Whether DROP TABLE is supported.

            Defaults to True.
            """
            return True

    def supports_if_exists_table(self) -> bool:
            """Whether DROP TABLE IF EXISTS is supported.

            Defaults to False.
            """
            return False

    def supports_drop_table_cascade(self) -> bool:
            """Whether DROP TABLE accepts the CASCADE keyword (SQL-standard form).

            Defaults to True (optimistic) so that DummyDialect exercises the full
            generic rendering path; actual backends override to reflect whether the
            CASCADE token is valid syntax for their DROP TABLE statement. The
            switch governs syntax only and is silent on whether the database truly
            drops dependent objects (e.g. MySQL/MariaDB parse-but-ignore CASCADE
            still report True).

            Oracle-specific CASCADE CONSTRAINTS / PURGE handling lives in the Oracle
            backend protocol and overrides format_drop_table_statement; this default
            only renders the standard CASCADE token.
            """
            return True

    def supports_drop_table_restrict(self) -> bool:
            """Whether DROP TABLE accepts the RESTRICT keyword.

            Defaults to True (optimistic); backends that do not recognize RESTRICT
            override to False, in which case the generic helper raises
            UnsupportedFeatureError when a caller asks for restrict behavior.
            """
            return True

    def supports_purge_on_drop_table(self) -> bool:
            """Whether DROP TABLE accepts the PURGE option (bypass the recycle bin).

            Defaults to False; Oracle (and compatible dialects) override to True.
            When a caller requests ``purge`` and this is False, the generic helper
            raises ``UnsupportedFeatureError`` instead of silently dropping it.
            """
            return False

    def format_drop_table_statement(self, expr: "DropTableStatement") -> Tuple[str, tuple]:
            """Format DROP TABLE statement (generic implementation).

            Renders ``DROP TABLE [IF EXISTS] <table> [CASCADE | RESTRICT]`` with
            capability gating: if the dialect reports ``supports_drop_table_cascade``
            (resp. ``supports_drop_table_restrict``) as False, asking for the
            corresponding behavior raises ``UnsupportedFeatureError`` instead of
            emitting a token the database would reject (or silently drop).

            Backend-specific cascade forms that have no cross-vendor commonality
            (e.g. Oracle's CASCADE CONSTRAINTS plus PURGE) are NOT handled here;
            backends override this method to render their own form.

            Args:
                expr: DropTableStatement carrying the table reference, optional
                    ``if_exists`` flag, and optional ``cascade`` flag.

            Returns:
                Tuple of (SQL string, parameters tuple) for the statement.

            Raises:
                TypeError: ``DropTableStatement.table`` is not a Table. Another object
                kind would have had its own name rendered as the table's.
                UnsupportedFeatureError: If CASCADE or RESTRICT is requested but not
                    supported by the dialect.
            """
            if not isinstance(expr.table, Table):
                raise TypeError(
                    f"DropTableStatement.table must be a Table, "
                    f"got {type(expr.table).__name__}"
                )
            from ..exceptions import UnsupportedFeatureError

            parts = ["DROP TABLE"]
            if expr.if_exists:
                if not self.supports_if_exists_table():
                    raise UnsupportedFeatureError(
                        self.name,
                        "DROP TABLE IF EXISTS",
                    )
                parts.append("IF EXISTS")
            table_sql, table_params = expr.table.to_sql()
            parts.append(table_sql)
            if expr.cascade:
                if not self.supports_drop_table_cascade():
                    raise UnsupportedFeatureError(
                        self.name,
                        "DROP TABLE ... CASCADE",
                    )
                parts.append("CASCADE")
            elif expr.restrict:
                if not self.supports_drop_table_restrict():
                    raise UnsupportedFeatureError(
                        self.name,
                        "DROP TABLE ... RESTRICT",
                    )
                parts.append("RESTRICT")
            if expr.purge:
                if not self.supports_purge_on_drop_table():
                    raise UnsupportedFeatureError(
                        self.name,
                        "DROP TABLE ... PURGE",
                    )
                parts.append("PURGE")
            return " ".join(parts), table_params


