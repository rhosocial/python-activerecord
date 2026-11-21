# src/rhosocial/activerecord/backend/impl/sqlite/suggestion/partition_table_alter_suggestion.py
"""SQLite's partition table alter suggestion.

SQLite has no table partitioning, so there is no mechanism to suggest for any
strategy. The answer is the explicit "unsupported" state (``False``), not
silence: the caller can report it as unavailable rather than guessing.
Unconditional, consults no probe.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionTableAlterSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionByClause


class SQLitePartitionTableAlterSuggestionMixin:
    """Answer SQLite's lack of partition partition table alter explicitly."""

    def suggest_partition_table_alter(
        self, strategy: "PartitionByClause", plan: object
    ) -> PartitionTableAlterSuggestion:
        return PartitionTableAlterSuggestion(False)
