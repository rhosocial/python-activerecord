"""TableSuggestionSupport -- backend's preferred table statement forms."""
from typing import Protocol, runtime_checkable
from ..definitions import TableStatementSuggestion


@runtime_checkable
class TableSuggestionSupport(Protocol):
    def suggest_create_table_statement(self) -> 'TableStatementSuggestion':
        """Preferred CREATE TABLE statement class, or None for generic."""
        ...  # pragma: no cover

    def suggest_drop_table_statement(self) -> 'TableStatementSuggestion':
        """Preferred DROP TABLE statement class, or None for generic."""
        ...  # pragma: no cover
