# src/rhosocial/activerecord/backend/impl/sqlite/suggestion/__init__.py
"""SQLite backend-suggestion implementations."""

from .data_type_suggestions import SQLiteDataTypeSuggestionsMixin
from .index_suggestion import SQLiteIndexSuggestionMixin
from .generated_value_suggestion import SQLiteGeneratedValueSuggestionMixin
from .partition_add_suggestion import SQLitePartitionAddSuggestionMixin
from .partition_build_suggestion import SQLitePartitionBuildSuggestionMixin
from .partition_drop_suggestion import SQLitePartitionDropSuggestionMixin
from .partition_merge_suggestion import SQLitePartitionMergeSuggestionMixin
from .partition_retention_suggestion import SQLitePartitionRetentionSuggestionMixin
from .partition_split_suggestion import SQLitePartitionSplitSuggestionMixin
from .partition_table_alter_suggestion import SQLitePartitionTableAlterSuggestionMixin
from .partition_table_drop_suggestion import SQLitePartitionTableDropSuggestionMixin

__all__ = [
    "SQLiteDataTypeSuggestionsMixin",
    "SQLiteIndexSuggestionMixin",
    "SQLiteGeneratedValueSuggestionMixin",
    "SQLitePartitionAddSuggestionMixin",
    "SQLitePartitionBuildSuggestionMixin",
    "SQLitePartitionDropSuggestionMixin",
    "SQLitePartitionMergeSuggestionMixin",
    "SQLitePartitionRetentionSuggestionMixin",
    "SQLitePartitionSplitSuggestionMixin",
    "SQLitePartitionTableAlterSuggestionMixin",
    "SQLitePartitionTableDropSuggestionMixin",
]
