# src/rhosocial/activerecord/backend/impl/sqlite/suggestion/partition_retention_suggestion.py
"""SQLite's partition-retention suggestion.

SQLite has no table partitioning, so there is no retirement mechanism to suggest
for any strategy. The answer is the explicit "unsupported" state (``False``),
not silence: the caller can report that partition retention is unavailable here
rather than guessing. The mixin is unconditional and consults no probe.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionRetentionSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionByClause


class SQLitePartitionRetentionSuggestionMixin:
    """Answer SQLite's lack of partition retention explicitly."""

    def suggest_partition_retention(
        self, strategy: "PartitionByClause", plan: object
    ) -> PartitionRetentionSuggestion:
        return PartitionRetentionSuggestion(False)
