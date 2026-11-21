# src/rhosocial/activerecord/backend/impl/sqlite/mixins/partition_add_suggestion.py
"""SQLite's partition add suggestion.

SQLite has no table partitioning, so there is no mechanism to suggest for any
strategy. The answer is the explicit "unsupported" state (``False``), not silence:
the caller can report it as unavailable rather than guessing. Unconditional,
consults no probe.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionAddSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy


class SQLitePartitionAddSuggestionMixin:
    """Answer SQLite's lack of partition partition add explicitly."""

    def suggest_partition_add(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionAddSuggestion:
        return PartitionAddSuggestion(False)
