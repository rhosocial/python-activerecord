# src/rhosocial/activerecord/backend/impl/sqlite/mixins/__init__.py
"""
SQLite-specific mixin implementations.

This package provides mixin classes that implement SQLite-specific
features for the ActiveRecord ORM.
"""

from .extension import SQLiteExtensionMixin
from .virtual_table import SQLiteVirtualTableMixin
from .pragma_mixin import SQLitePragmaMixin
from .reindex import SQLiteReindexMixin
from .maintenance import SQLiteMaintenanceMixin
from .introspection import SQLiteIntrospectionCapabilityMixin
from .datetime import SQLiteDateTimeMixin
from .ddl_column import SQLiteDDLColumnMixin
from .dml import SQLiteDMLMixin
from .ddl_view import SQLiteViewMixin
from .trigger import SQLiteTriggerMixin
from .transaction import SQLiteTransactionMixin
from .function import SQLiteFunctionMixin
from .fts5 import SQLiteFTS5Mixin
from .rtree import SQLiteRTreeMixin
from .geopoly import SQLiteGeopolyMixin
from .types import SQLiteTypeSupportMixin
from .literal import LiteralValueMixin
from .column_type import SQLiteColumnTypeMixin
from .data_type_suggestions import SQLiteDataTypeSuggestionsMixin
from .object_name import SQLiteObjectNameMixin
from .integer_auto_increment_column_suggestion import SQLiteIntegerAutoIncrementColumnSuggestionMixin
from .partition_retention_suggestion import SQLitePartitionRetentionSuggestionMixin
from .partition_build_suggestion import SQLitePartitionBuildSuggestionMixin
from .partition_add_suggestion import SQLitePartitionAddSuggestionMixin
from .partition_drop_suggestion import SQLitePartitionDropSuggestionMixin
from .partition_table_drop_suggestion import SQLitePartitionTableDropSuggestionMixin
from .partition_table_alter_suggestion import SQLitePartitionTableAlterSuggestionMixin
from .partition_split_suggestion import SQLitePartitionSplitSuggestionMixin
from .partition_merge_suggestion import SQLitePartitionMergeSuggestionMixin

__all__ = [
    'SQLiteIntegerAutoIncrementColumnSuggestionMixin',
    'SQLitePartitionRetentionSuggestionMixin',
    'SQLitePartitionBuildSuggestionMixin',
    'SQLitePartitionAddSuggestionMixin',
    'SQLitePartitionDropSuggestionMixin',
    'SQLitePartitionTableDropSuggestionMixin',
    'SQLitePartitionTableAlterSuggestionMixin',
    'SQLitePartitionSplitSuggestionMixin',
    'SQLitePartitionMergeSuggestionMixin',
    'SQLiteExtensionMixin',
    'SQLiteVirtualTableMixin',
    'SQLitePragmaMixin',
    'SQLiteReindexMixin',
    'SQLiteMaintenanceMixin',
    'SQLiteIntrospectionCapabilityMixin',
    'SQLiteDateTimeMixin',
    'SQLiteDDLColumnMixin',
    'SQLiteDMLMixin',
    'SQLiteViewMixin',
    'SQLiteTriggerMixin',
    'SQLiteTransactionMixin',
    'SQLiteFunctionMixin',
    'SQLiteFTS5Mixin',
    'SQLiteRTreeMixin',
    'SQLiteGeopolyMixin',
    'SQLiteTypeSupportMixin',
    'SQLiteObjectNameMixin',
    'LiteralValueMixin',
    'SQLiteColumnTypeMixin',
    'SQLiteDataTypeSuggestionsMixin',
]
