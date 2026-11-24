# src/rhosocial/activerecord/backend/impl/sqlite/suggestion/generated_value_suggestion.py
"""SQLite's database-generated-value suggestion.

SQLite declares an auto-generated integer key as ``INTEGER PRIMARY KEY
AUTOINCREMENT``. This is *not* the bare ``AUTO_INCREMENT`` marker —
``AutoIncrementColumnMixin.supports_auto_increment_column()`` is deliberately
False on SQLite — so this mixin does not consult that probe; it returns the
mechanism SQLite actually spells and leaves rendering to
:meth:`format_sqlite_auto_increment_clause`.
"""
from typing import TYPE_CHECKING

from ....suggestion import GeneratedValueSuggestion
from ..sqlite_auto_increment_clause import SQLiteAutoIncrementClause

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.types import DataType


class SQLiteGeneratedValueSuggestionMixin:
    """Suggest SQLite's rowid-alias auto-increment for a generated integer key."""

    def suggest_generated_value(self, default_type: "DataType") -> GeneratedValueSuggestion:
        return GeneratedValueSuggestion(
            state="generate",
            storage_type=default_type,
            clause=SQLiteAutoIncrementClause(self),
        )
