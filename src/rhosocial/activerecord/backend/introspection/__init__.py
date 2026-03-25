# src/rhosocial/activerecord/backend/introspection/__init__.py
"""
Database introspection types, exceptions, protocols and mixins.

This module provides data structures for database introspection,
as well as protocols and mixins for backend implementations.

Usage:
    from rhosocial.activerecord.backend.introspection import (
        DatabaseInfo, TableInfo, ColumnInfo, IndexInfo,
        ForeignKeyInfo, ViewInfo, TriggerInfo,
        BackendIntrospectionSupport, IntrospectionMixin,
    )
"""

from .types import (
    # Enumerations
    IntrospectionScope,
    TableType,
    ColumnNullable,
    IndexType,
    ReferentialAction,
    # Data structures
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
from .protocols import (
    BackendIntrospectionSupport,
    AsyncBackendIntrospectionSupport,
)
from .mixins import (
    IntrospectionMixin,
    AsyncIntrospectionMixin,
)

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
    # Protocols
    "BackendIntrospectionSupport",
    "AsyncBackendIntrospectionSupport",
    # Mixins
    "IntrospectionMixin",
    "AsyncIntrospectionMixin",
]
