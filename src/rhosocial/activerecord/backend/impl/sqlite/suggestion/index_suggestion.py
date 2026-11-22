# src/rhosocial/activerecord/backend/impl/sqlite/suggestion/index_suggestion.py
"""SQLite's index suggestions."""
from typing import List

from rhosocial.activerecord.backend.dialect.protocols import IndexSuggestionSupport


class SQLiteIndexSuggestionMixin(IndexSuggestionSupport):
    def suggest_index_types(self) -> List[str]:
        return ["BTREE"]

    def suggest_create_index_statement(self):
        return None

    def suggest_drop_index_statement(self):
        return None
