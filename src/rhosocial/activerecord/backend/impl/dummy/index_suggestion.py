# src/rhosocial/activerecord/backend/impl/dummy/index_suggestion.py
"""Dummy dialect's index suggestions."""
from typing import List

from rhosocial.activerecord.backend.suggestion.protocols import IndexSuggestionSupport


class DummyIndexSuggestionMixin(IndexSuggestionSupport):
    def suggest_index_types(self) -> List[str]:
        return ["BTREE", "HASH", "GIN", "GIST", "SPGIST", "BRIN"]

    def suggest_create_index_statement(self):
        return None

    def suggest_drop_index_statement(self):
        return None
