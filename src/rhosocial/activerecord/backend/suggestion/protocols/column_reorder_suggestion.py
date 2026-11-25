# src/rhosocial/activerecord/backend/suggestion/protocols/column_reorder_suggestion.py
"""ColumnReorderSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.suggestion.protocols`.

Backend suggestion capability: the dialect answers how to reorder columns on
an order-sensitive engine, from the decision point handed to it. It answers
only the "how"; the caller owns the plan. Minimal protocol (one ``suggest_*``
method, no ``supports``/``format``), immutable tri-state value, no core mixin
default -- per the backend-suggestion spec (§9.4).
"""
from typing import Protocol, runtime_checkable

from ..definitions import ColumnReorderSuggestion


@runtime_checkable
class ColumnReorderSuggestionSupport(Protocol):
    """A dialect's suggested action chain for a column-reorder decision point."""

    def suggest_column_reorder(
        self, point: ColumnReorderSuggestion
    ) -> ColumnReorderSuggestion:
        """Answer ``point`` with an expression chain, ``False`` or ``None``.

        ``False`` means this backend cannot address the reorder automatically;
        ``None`` means no action is required. The protocol never renders SQL.
        """
        ...  # pragma: no cover
