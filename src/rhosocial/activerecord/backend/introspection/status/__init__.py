# src/rhosocial/activerecord/backend/introspection/status/__init__.py
"""
Server status introspection module.

This module provides data structures and abstract base classes for
database server status introspection, enabling unified status reporting
across different database backends.
"""

from .types import (
    StatusCategory,
    StatusItem,
    DatabaseBriefInfo,
    UserInfo,
    ConnectionInfo,
    StorageInfo,
    ServerOverview,
    SessionInfo,
    WALInfo,
    ReplicationInfo,
    ArchiveInfo,
    SecurityInfo,
    ExtensionInfo,
)
from .base import (
    StatusIntrospectorMixin,
    SyncAbstractStatusIntrospector,
    AsyncAbstractStatusIntrospector,
)

__all__ = [
    # Types
    "StatusCategory",
    "StatusItem",
    "DatabaseBriefInfo",
    "UserInfo",
    "ConnectionInfo",
    "StorageInfo",
    "ServerOverview",
    "SessionInfo",
    "WALInfo",
    "ReplicationInfo",
    "ArchiveInfo",
    "SecurityInfo",
    "ExtensionInfo",
    # Base classes
    "StatusIntrospectorMixin",
    "SyncAbstractStatusIntrospector",
    "AsyncAbstractStatusIntrospector",
]
