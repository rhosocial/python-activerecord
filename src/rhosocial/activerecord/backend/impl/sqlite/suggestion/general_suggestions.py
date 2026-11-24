# src/rhosocial/activerecord/backend/impl/sqlite/suggestion/general_suggestions.py
"""SQLite's non-type production suggestions."""
from rhosocial.activerecord.backend.suggestion.definitions import (
    ConcatenationFunctionSuggestion,
    CreateTableLayoutSuggestion,
    IntrospectionScopeSuggestion,
    JSONAccessOperatorSuggestion,
    UpsertSyntaxSuggestion,
)

from typing import List, Optional

from rhosocial.activerecord.backend.suggestion.protocols import (
    CreateTableLayoutSuggestionSupport,
    IntrospectionSuggestionSupport,
    JSONSuggestionSupport,
    StringConcatenationSuggestionSupport,
    UpsertSuggestionSupport,
)


class SQLiteCreateTableLayoutSuggestionMixin(CreateTableLayoutSuggestionSupport):
    def suggest_create_table_layout(self):
        # SQLite renders neither inline indexes nor inline comments in CREATE TABLE.
        return CreateTableLayoutSuggestion(
            strategy="split", inline_index=False, inline_comment=False, state="actions"
        )


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
