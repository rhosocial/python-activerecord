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
from .identifier import SQLiteIdentifierMixin
from .datetime import SQLiteDateTimeMixin
from .ddl_column import SQLiteDDLColumnMixin
from .dml import SQLiteDMLMixin
from .set_operation import SQLiteSetOperationMixin
from .view import SQLiteViewMixin
from .trigger import SQLiteTriggerMixin
from .transaction import SQLiteTransactionMixin
from .function import SQLiteFunctionMixin
from .fts5 import SQLiteFTS5Mixin
from .rtree import SQLiteRTreeMixin
from .geopoly import SQLiteGeopolyMixin
from .types import SQLiteTypeSupportMixin

__all__ = [
    'SQLiteExtensionMixin',
    'SQLiteVirtualTableMixin',
    'SQLitePragmaMixin',
    'SQLiteReindexMixin',
    'SQLiteMaintenanceMixin',
    'SQLiteIntrospectionCapabilityMixin',
    'SQLiteIdentifierMixin',
    'SQLiteDateTimeMixin',
    'SQLiteDDLColumnMixin',
    'SQLiteDMLMixin',
    'SQLiteSetOperationMixin',
    'SQLiteViewMixin',
    'SQLiteTriggerMixin',
    'SQLiteTransactionMixin',
    'SQLiteFunctionMixin',
    'SQLiteFTS5Mixin',
    'SQLiteRTreeMixin',
    'SQLiteGeopolyMixin',
    'SQLiteTypeSupportMixin',
]
