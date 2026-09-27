# src/rhosocial/activerecord/backend/impl/sqlite/expression/dml.py
"""SQLite-specific DML expression classes."""

from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression.statements import InsertExpression

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


class SQLiteInsertExpression(InsertExpression):
    """A SQLite INSERT statement extending the generic one.

    SQLite supports the ``INSERT OR REPLACE`` / ``INSERT OR IGNORE`` conflict
    resolution forms, which have no direct generic equivalent. These are carried
    as typed flags here and rendered by ``SQLiteDMLMixin.format_insert_statement``.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        into,
        source,
        columns=None,
        *,
        on_conflict=None,
        returning=None,
        or_replace: bool = False,
        or_ignore: bool = False,
    ):
        super().__init__(
            dialect,
            into=into,
            source=source,
            columns=columns,
            on_conflict=on_conflict,
            returning=returning,
        )
        self.or_replace = or_replace
        self.or_ignore = or_ignore


__all__ = [
    "SQLiteInsertExpression",
]
