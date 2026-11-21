# src/rhosocial/activerecord/backend/impl/sqlite/suggestion/partition_drop_suggestion.py
"""SQLite's partition drop suggestion.

SQLite has no table partitioning, so there is no mechanism to suggest for any
strategy. The answer is the explicit "unsupported" state (``False``), not silence:
the caller can report it as unavailable rather than guessing. Unconditional,
consults no probe.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionDropSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy


class SQLitePartitionDropSuggestionMixin:
    """Answer SQLite's lack of partition partition drop explicitly."""

    def suggest_partition_drop(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionDropSuggestion:
        return PartitionDropSuggestion(False)
