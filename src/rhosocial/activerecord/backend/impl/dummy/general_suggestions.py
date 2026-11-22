# src/rhosocial/activerecord/backend/impl/dummy/general_suggestions.py
"""Dummy dialect's non-type production suggestions."""
from typing import List, Optional

from rhosocial.activerecord.backend.suggestion.protocols import (
    JSONSuggestionSupport,
    StringConcatenationSuggestionSupport,
    TableSuggestionSupport,
    UpsertSuggestionSupport,
)


class DummyTableSuggestionMixin(TableSuggestionSupport):
    def suggest_create_table_statement(self): return None
    def suggest_drop_table_statement(self): return None


class DummyJSONSuggestionMixin(JSONSuggestionSupport):
    def suggest_json_access_operator(self) -> str: return "->"


class DummyUpsertSuggestionMixin(UpsertSuggestionSupport):
    def suggest_upsert_syntax_type(self) -> str: return "ON CONFLICT"


class DummyStringConcatenationSuggestionMixin(StringConcatenationSuggestionSupport):
    def suggest_concatenation_function(self) -> Optional[str]: return None
