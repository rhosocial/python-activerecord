"""TableSuggestionSupport -- backend's preferred table statement forms."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class TableSuggestionSupport(Protocol):
    def suggest_create_table_statement(self):
        """Preferred CREATE TABLE statement class, or None for generic."""
        ...  # pragma: no cover

    def suggest_drop_table_statement(self):
        """Preferred DROP TABLE statement class, or None for generic."""
        ...  # pragma: no cover
