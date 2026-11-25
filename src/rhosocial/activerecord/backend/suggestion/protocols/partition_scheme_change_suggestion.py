# src/rhosocial/activerecord/backend/suggestion/protocols/partition_scheme_change_suggestion.py
"""PartitionSchemeChangeSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.suggestion.protocols`.

Backend suggestion capability: the dialect answers how to move a table from
one partitioning scheme to another. This is the migration-time counterpart of
``PartitionTableAlterSuggestion``: the latter answers a caller-supplied
strategy, while this one is driven by the old/new declarations in the point.
Minimal protocol (one ``suggest_*`` method, no ``supports``/``format``),
immutable tri-state value, no core mixin default -- per the spec (§9.4).
"""
from typing import Protocol, runtime_checkable

from ..definitions import PartitionSchemeChangeSuggestion


@runtime_checkable
class PartitionSchemeChangeSuggestionSupport(Protocol):
    """A dialect's suggested action chain for a partition-scheme change."""

    def suggest_partition_scheme_change(
        self, point: PartitionSchemeChangeSuggestion
    ) -> PartitionSchemeChangeSuggestion:
        """Answer ``point`` with an expression chain, ``False`` or ``None``."""
        ...  # pragma: no cover
