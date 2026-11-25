# src/rhosocial/activerecord/backend/suggestion/protocols/table_index_change_suggestion.py
"""TableIndexChangeSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.suggestion.protocols`.

Backend suggestion capability: the dialect answers how to apply a table-level
index change (create/drop/replace may need an ordered action chain).
Minimal protocol (one ``suggest_*`` method, no ``supports``/``format``),
immutable tri-state value, no core mixin default -- per the spec (§9.4).
"""
from typing import Protocol, runtime_checkable

from ..definitions import TableIndexChangeSuggestion


@runtime_checkable
class TableIndexChangeSuggestionSupport(Protocol):
    """A dialect's suggested action chain for a table-index change."""

    def suggest_table_index_change(
        self, point: TableIndexChangeSuggestion
    ) -> TableIndexChangeSuggestion:
        """Answer ``point`` with an expression chain, ``False`` or ``None``."""
        ...  # pragma: no cover
