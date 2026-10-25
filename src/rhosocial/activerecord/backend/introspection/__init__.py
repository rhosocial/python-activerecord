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
        IntrospectionDatabaseInfo, IntrospectionTableInfo, IntrospectionColumnInfo, IndexInfo,
        IntrospectionForeignKeyInfo, IntrospectionViewInfo, IntrospectionTriggerInfo,
    )
"""

from .types import (
    IntrospectionScope,
    TableType,
    ColumnNullable,
    IndexType,
    ReferentialAction,
    IntrospectionDatabaseInfo,
    IntrospectionTableInfo,
    IntrospectionColumnInfo,
    IndexInfo,
    IndexColumnInfo,
    IntrospectionForeignKeyInfo,
    IntrospectionViewInfo,
    IntrospectionTriggerInfo,
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
from .cache import InMemoryIntrospectionCache, IntrospectionCache
from .base import (
    IntrospectorMixin,
    IntrospectorBase,
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
    "IntrospectionDatabaseInfo",
    "IntrospectionTableInfo",
    "IntrospectionColumnInfo",
    "IndexInfo",
    "IndexColumnInfo",
    "IntrospectionForeignKeyInfo",
    "IntrospectionViewInfo",
    "IntrospectionTriggerInfo",
    # Exceptions
    "IntrospectionError",
    "IntrospectionNotSupportedError",
    "IntrospectionQueryError",
    "ObjectNotFoundError",
    "IntrospectionCacheError",
    # Executor
    "SyncIntrospectorExecutor",
    "AsyncIntrospectorExecutor",
    # Cache
    "IntrospectionCache",
    "InMemoryIntrospectionCache",
    # Core
    "IntrospectorMixin",
    "IntrospectorBase",
    "SyncAbstractIntrospector",
    "AsyncAbstractIntrospector",
    "IntrospectorBackendMixin",
]
