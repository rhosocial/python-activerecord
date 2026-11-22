# src/rhosocial/activerecord/backend/impl/dummy/general_suggestions.py
"""Dummy dialect's non-type production suggestions."""
from rhosocial.activerecord.backend.suggestion.definitions import ConcatenationFunctionSuggestion, JSONAccessOperatorSuggestion, TableStatementSuggestion, UpsertSyntaxSuggestion

from typing import List, Optional

from rhosocial.activerecord.backend.suggestion.protocols import (
    JSONSuggestionSupport,
    StringConcatenationSuggestionSupport,
    TableSuggestionSupport,
    UpsertSuggestionSupport,
)


class DummyTableSuggestionMixin(TableSuggestionSupport):
    def suggest_create_table_statement(self): return TableStatementSuggestion(statement=None)
    def suggest_drop_table_statement(self): return TableStatementSuggestion(statement=None)


class DummyJSONSuggestionMixin(JSONSuggestionSupport):
    def suggest_json_access_operator(self) -> str: return JSONAccessOperatorSuggestion(operator="->")


class DummyUpsertSuggestionMixin(UpsertSuggestionSupport):
    def suggest_upsert_syntax_type(self) -> str: return UpsertSyntaxSuggestion(syntax="ON CONFLICT")


class DummyStringConcatenationSuggestionMixin(StringConcatenationSuggestionSupport):
    def suggest_concatenation_function(self) -> Optional[str]: return ConcatenationFunctionSuggestion(function=None)
