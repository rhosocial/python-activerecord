# src/rhosocial/activerecord/backend/introspection/__init__.py
"""
Database introspection — types, exceptions, executor, and introspector base.

Quick start::

    from rhosocial.activerecord.backend.introspection import (
        AbstractIntrospector,
        AsyncAbstractIntrospector,
        IntrospectorBackendMixin,
        IntrospectorExecutor,
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
    SequenceInfo,
    ConstraintState,
    DerivedObjectState,
    IndexState,
    ItemKind,
    PartitionBound,
    PartitionScheme,
    PartitionState,
    SequenceState,
    StorageOptionsState,
    TableState,
    TriggerState,
)
from .errors import (
    IntrospectionError,
    IntrospectionNotSupportedError,
    IntrospectionQueryError,
    ObjectNotFoundError,
    IntrospectionCacheError,
)
from .executor import (
    IntrospectorExecutor,
    AsyncIntrospectorExecutor,
)
from .cache import InMemoryIntrospectionCache, IntrospectionCache
from .base import (
    IntrospectorMixin,
    IntrospectorBase,
    AbstractIntrospector,
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
    "SequenceInfo",
    # Neutral object state
    "TableState",
    "StorageOptionsState",
    "PartitionState",
    "PartitionBound",
    "PartitionScheme",
    "IndexState",
    "ConstraintState",
    "SequenceState",
    "TriggerState",
    "DerivedObjectState",
    "ItemKind",
    # Exceptions
    "IntrospectionError",
    "IntrospectionNotSupportedError",
    "IntrospectionQueryError",
    "ObjectNotFoundError",
    "IntrospectionCacheError",
    # Executor
    "IntrospectorExecutor",
    "AsyncIntrospectorExecutor",
    # Cache
    "IntrospectionCache",
    "InMemoryIntrospectionCache",
    # Core
    "IntrospectorMixin",
    "IntrospectorBase",
    "AbstractIntrospector",
    "AsyncAbstractIntrospector",
    "IntrospectorBackendMixin",
]
