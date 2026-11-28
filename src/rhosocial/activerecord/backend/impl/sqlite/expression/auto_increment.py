# src/rhosocial/activerecord/backend/impl/sqlite/expression/auto_increment.py
"""SQLite's ``AUTOINCREMENT`` tail -- a rowid-alias property, not the generic marker.

Kept separate from the core ``AutoIncrementClause`` so that node stays
fail-closed on dialects (SQLite included) whose ``supports_auto_increment_column()``
answers False. Only the backend's integer-key suggestion produces this node,
and only SQLite's dialect renders it.
"""
from typing import TYPE_CHECKING

from rhosocial.activerecord.backend.expression.bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...base import SQLDialectBase


class SQLiteAutoIncrementClause(BaseExpression):
    """The rowid-alias ``AUTOINCREMENT`` keyword, placed after PRIMARY KEY."""

    @property
    def format_method(self) -> str:
        return "format_sqlite_auto_increment_clause"

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)
