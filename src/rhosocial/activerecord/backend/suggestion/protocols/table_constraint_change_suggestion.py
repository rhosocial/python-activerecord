# src/rhosocial/activerecord/backend/suggestion/protocols/table_constraint_change_suggestion.py
"""TableConstraintChangeSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.suggestion.protocols`.

Backend suggestion capability: the dialect answers how to apply a table-level
constraint change (which may need a multi-step strategy on some engines).
Minimal protocol (one ``suggest_*`` method, no ``supports``/``format``),
immutable tri-state value, no core mixin default -- per the spec (§9.4).
"""
from typing import Protocol, runtime_checkable

from ..definitions import TableConstraintChangeSuggestion


@runtime_checkable
class TableConstraintChangeSuggestionSupport(Protocol):
    """A dialect's suggested action chain for a table-constraint change."""

    def suggest_table_constraint_change(
        self, point: TableConstraintChangeSuggestion
    ) -> TableConstraintChangeSuggestion:
        """Answer ``point`` with an expression chain, ``False`` or ``None``."""
        ...  # pragma: no cover
