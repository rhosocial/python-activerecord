# src/rhosocial/activerecord/backend/impl/sqlite/suggestion/partition_table_drop_suggestion.py
"""SQLite's partition table drop suggestion.

SQLite has no table partitioning, so there is no mechanism to suggest for any
strategy. The answer is the explicit "unsupported" state (``False``), not
silence: the caller can report it as unavailable rather than guessing.
Unconditional, consults no probe.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionTableDropSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionByClause


class SQLitePartitionTableDropSuggestionMixin:
    """Answer SQLite's lack of partition partition table drop explicitly."""

    def suggest_partition_table_drop(
        self, strategy: "PartitionByClause", plan: object
    ) -> PartitionTableDropSuggestion:
        return PartitionTableDropSuggestion(False)
