# src/rhosocial/activerecord/backend/introspection/__init__.py
"""
Database introspection — types, exceptions, executor, and introspector base.

Quick start::

    from rhosocial.activerecord.backend.introspection import (
        SyncAbstractIntrospector,
        AsyncAbstractIntrospector,
        IntrospectorBackendMixin,
        SyncIntrospectorExecutor,
        AsyncIntrospectorExecutor,
        DatabaseInfo, TableInfo, ColumnInfo, IndexInfo,
        ForeignKeyInfo, ViewInfo, TriggerInfo,
    )
"""

from .types import (
    IntrospectionScope,
    TableType,
    ColumnNullable,
    IndexType,
    ReferentialAction,
    DatabaseInfo,
    TableInfo,
    ColumnInfo,
    IndexInfo,
    IndexColumnInfo,
    ForeignKeyInfo,
    ViewInfo,
    TriggerInfo,
)
from .errors import (
    IntrospectionError,
    IntrospectionNotSupportedError,
    IntrospectionQueryError,
    ObjectNotFoundError,
    IntrospectionCacheError,
)
from .executor import (
    SyncIntrospectorExecutor,
    AsyncIntrospectorExecutor,
)
from .base import (
    IntrospectorMixin,
    SyncAbstractIntrospector,
    AsyncAbstractIntrospector,
)
from .backend_mixin import IntrospectorBackendMixin

__all__ = [
    # Enumerations
    "IntrospectionScope",
    "TableType",
    "ColumnNullable",
    "IndexType",
    "ReferentialAction",
    # Data structures
    "DatabaseInfo",
    "TableInfo",
    "ColumnInfo",
    "IndexInfo",
    "IndexColumnInfo",
    "ForeignKeyInfo",
    "ViewInfo",
    "TriggerInfo",
    # Exceptions
    "IntrospectionError",
    "IntrospectionNotSupportedError",
    "IntrospectionQueryError",
    "ObjectNotFoundError",
    "IntrospectionCacheError",
    # Executor
    "SyncIntrospectorExecutor",
    "AsyncIntrospectorExecutor",
    # Core
    "IntrospectorMixin",
    "SyncAbstractIntrospector",
    "AsyncAbstractIntrospector",
    "IntrospectorBackendMixin",
]
