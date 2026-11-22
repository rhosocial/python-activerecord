# src/rhosocial/activerecord/backend/impl/sqlite/suggestion/index_suggestion.py
"""SQLite's index suggestions."""
from rhosocial.activerecord.backend.suggestion.definitions import IndexStatementSuggestion, IndexTypeSuggestion

from typing import List

from rhosocial.activerecord.backend.suggestion.protocols import IndexSuggestionSupport


class SQLiteIndexSuggestionMixin(IndexSuggestionSupport):
    def suggest_index_types(self) -> List[str]:
        return IndexTypeSuggestion(types=["BTREE"])

    def suggest_create_index_statement(self):
        return IndexStatementSuggestion(statement=None)

    def suggest_drop_index_statement(self):
        return IndexStatementSuggestion(statement=None)
