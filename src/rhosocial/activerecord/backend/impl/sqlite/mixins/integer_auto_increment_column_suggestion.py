# src/rhosocial/activerecord/backend/impl/sqlite/mixins/integer_auto_increment_column_suggestion.py
"""SQLite's integer auto-increment column suggestion.

The answer is unconditional: SQLite always declares an auto-generated integer
key as ``INTEGER PRIMARY KEY AUTOINCREMENT``. Note this is *not* the bare
``AUTO_INCREMENT`` marker -- ``AutoIncrementMixin.supports_auto_increment_column()``
is deliberately False on SQLite -- so this mixin does not consult that probe;
it returns the mechanism SQLite actually spells and leaves rendering to
:meth:`format_sqlite_auto_increment_clause`.
"""

from typing import TYPE_CHECKING

from ....suggestion import IntegerAutoIncrementColumnSuggestion
from ..sqlite_auto_increment_clause import SQLiteAutoIncrementClause

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.types._base import DataType


class SQLiteIntegerAutoIncrementColumnSuggestionMixin:
    """Suggest SQLite's rowid-alias auto-increment for an integer key."""

    def suggest_integer_auto_increment_column(
        self, default_type: "DataType"
    ) -> IntegerAutoIncrementColumnSuggestion:
        return IntegerAutoIncrementColumnSuggestion(
            default_type, SQLiteAutoIncrementClause(self)
        )
