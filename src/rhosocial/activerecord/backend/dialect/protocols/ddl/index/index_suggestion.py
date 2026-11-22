# src/rhosocial/activerecord/backend/dialect/protocols/ddl/index/index_suggestion.py
"""IndexSuggestionSupport -- backend's index-related production suggestions.

The core declares only the protocol; each backend supplies its own answers:
which index types it offers, and which statement classes it prefers for
CREATE/DROP INDEX. Suggestions are values, not SQL.
"""
from typing import List, Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    pass


@runtime_checkable
class IndexSuggestionSupport(Protocol):
    """Index production suggestions (types + preferred statement forms)."""

    def suggest_index_types(self) -> List[str]:
        """Index type names this backend offers, e.g. ``["BTREE"]``."""
        ...  # pragma: no cover

    def suggest_create_index_statement(self):
        """Preferred CREATE INDEX statement class, or None for the generic one."""
        ...  # pragma: no cover

    def suggest_drop_index_statement(self):
        """Preferred DROP INDEX statement class, or None for the generic one."""
        ...  # pragma: no cover
