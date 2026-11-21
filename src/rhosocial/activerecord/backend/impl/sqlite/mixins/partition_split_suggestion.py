# src/rhosocial/activerecord/backend/impl/sqlite/mixins/partition_split_suggestion.py
"""SQLite's partition split suggestion.

SQLite has no table partitioning, so there is no mechanism to suggest for any
strategy. The answer is the explicit "unsupported" state (``False``), not
silence: the caller can report it as unavailable rather than guessing.
Unconditional, consults no probe.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionSplitSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy


class SQLitePartitionSplitSuggestionMixin:
    """Answer SQLite's lack of partition partition split explicitly."""

    def suggest_partition_split(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionSplitSuggestion:
        return PartitionSplitSuggestion(False)
