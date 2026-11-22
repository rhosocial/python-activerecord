# src/rhosocial/activerecord/backend/impl/sqlite/suggestion/general_suggestions.py
"""SQLite's non-type production suggestions."""
from rhosocial.activerecord.backend.suggestion.definitions import ConcatenationFunctionSuggestion, IntrospectionScopeSuggestion, JSONAccessOperatorSuggestion, TableStatementSuggestion, UpsertSyntaxSuggestion

from typing import List, Optional

from rhosocial.activerecord.backend.suggestion.protocols import (
    IntrospectionSuggestionSupport,
    JSONSuggestionSupport,
    StringConcatenationSuggestionSupport,
    TableSuggestionSupport,
    UpsertSuggestionSupport,
)


class SQLiteTableSuggestionMixin(TableSuggestionSupport):
    def suggest_create_table_statement(self): return TableStatementSuggestion(statement=None)
    def suggest_drop_table_statement(self): return TableStatementSuggestion(statement=None)


class SQLiteJSONSuggestionMixin(JSONSuggestionSupport):
    def suggest_json_access_operator(self) -> str: return JSONAccessOperatorSuggestion(operator="->")


class SQLiteUpsertSuggestionMixin(UpsertSuggestionSupport):
    def suggest_upsert_syntax_type(self) -> str: return UpsertSyntaxSuggestion(syntax="ON CONFLICT")


class SQLiteIntrospectionSuggestionMixin(IntrospectionSuggestionSupport):
    def suggest_introspection_scopes(self) -> List["IntrospectionScope"]:
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope
        scopes = [IntrospectionScope.DATABASE, IntrospectionScope.TABLE, IntrospectionScope.COLUMN,
                  IntrospectionScope.INDEX, IntrospectionScope.VIEW, IntrospectionScope.TRIGGER]
        if self.supports_foreign_key_introspection():
            scopes.append(IntrospectionScope.FOREIGN_KEY)
        return IntrospectionScopeSuggestion(scopes=scopes)


class SQLiteStringConcatenationSuggestionMixin(StringConcatenationSuggestionSupport):
    def suggest_concatenation_function(self) -> Optional[str]:
        declared = getattr(self, "STRING_CONCATENATION", None)
        return ConcatenationFunctionSuggestion(function=declared if isinstance(declared, str) else None)
