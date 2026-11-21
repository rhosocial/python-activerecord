# src/rhosocial/activerecord/backend/impl/sqlite/mixins/partition_build_suggestion.py
"""SQLite's partition build suggestion.

SQLite has no table partitioning, so there is no mechanism to suggest for any
strategy. The answer is the explicit "unsupported" state (``False``), not silence:
the caller can report it as unavailable rather than guessing. Unconditional,
consults no probe.
"""

from typing import TYPE_CHECKING

from ....suggestion import PartitionBuildSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import PartitionStrategy


class SQLitePartitionBuildSuggestionMixin:
    """Answer SQLite's lack of partition partition build explicitly."""

    def suggest_partition_build(
        self, strategy: "PartitionStrategy", plan: object
    ) -> PartitionBuildSuggestion:
        return PartitionBuildSuggestion(False)
