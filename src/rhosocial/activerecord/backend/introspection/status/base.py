# src/rhosocial/activerecord/backend/introspection/status/base.py
"""
Abstract base classes for server status introspection.

This module provides the abstract base classes for database server status
introspection, following the project's sync/async parity principle:

1. StatusIntrospectorMixin: Shared non-I/O logic
2. SyncAbstractStatusIntrospector: Synchronous status introspector
3. AsyncAbstractStatusIntrospector: Asynchronous status introspector

Design principles:
  - Sync and Async are separate and cannot coexist in the same class.
  - I/O methods have identical signatures between sync and async versions,
    differing only in async/await keywords.
  - Non-I/O methods are shared via mixin.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .types import (
    StatusItem,
    StatusCategory,
    ServerOverview,
    DatabaseBriefInfo,
    UserInfo,
    ConnectionInfo,
    StorageInfo,
    SessionInfo,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect.base import SQLDialectBase


class StatusIntrospectorMixin:
    """Mixin providing shared non-I/O functionality for status introspectors.

    This mixin contains:
    - Helper methods for organizing status items
    - Common parsing utilities
    - Category grouping logic

    Both SyncAbstractStatusIntrospector and AsyncAbstractStatusIntrospector
    inherit from this mixin to share all non-I/O logic.
    """

    @property
    def dialect(self) -> "SQLDialectBase":
        """Get the SQL dialect from the backend."""
        return self._backend.dialect

    def _group_items_by_category(
        self, items: List[StatusItem]
    ) -> Dict[StatusCategory, List[StatusItem]]:
        """Group status items by category.

        Args:
            items: List of StatusItem objects to group

        Returns:
            Dictionary mapping categories to lists of items
        """
        grouped: Dict[StatusCategory, List[StatusItem]] = {
            cat: [] for cat in StatusCategory
        }
        for item in items:
            grouped[item.category].append(item)
        return grouped

    def _format_bytes(self, size_bytes: Optional[int]) -> Optional[str]:
        """Format byte size to human-readable string.

        Args:
            size_bytes: Size in bytes

        Returns:
            Human-readable string (e.g., "1.5 GB")
        """
        if size_bytes is None:
            return None

        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        for unit in units:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def _get_vendor_name(self) -> str:
        """Get the database vendor name.

        Returns:
            Vendor name string (e.g., "SQLite", "MySQL", "PostgreSQL")
        """
        # Subclasses should override this method
        return "Unknown"


class SyncAbstractStatusIntrospector(StatusIntrospectorMixin, ABC):
    """Synchronous abstract base class for server status introspection.

    All methods are synchronous. Method names do NOT have an _async suffix.
    Subclasses must implement all abstract methods.
    """

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    @abstractmethod
    def get_overview(self) -> ServerOverview:
        """Get complete server status overview.

        Returns:
            ServerOverview object containing all status information
        """
        ...

    @abstractmethod
    def list_configuration(
        self, category: Optional[StatusCategory] = None
    ) -> List[StatusItem]:
        """List configuration parameters.

        Args:
            category: Optional category filter

        Returns:
            List of StatusItem objects for configuration parameters
        """
        ...

    @abstractmethod
    def list_performance_metrics(
        self, category: Optional[StatusCategory] = None
    ) -> List[StatusItem]:
        """List performance metrics.

        Args:
            category: Optional category filter

        Returns:
            List of StatusItem objects for performance metrics
        """
        ...

    @abstractmethod
    def get_connection_info(self) -> ConnectionInfo:
        """Get connection information.

        Returns:
            ConnectionInfo object with connection details
        """
        ...

    @abstractmethod
    def get_storage_info(self) -> StorageInfo:
        """Get storage information.

        Returns:
            StorageInfo object with storage details
        """
        ...

    @abstractmethod
    def list_databases(self) -> List[DatabaseBriefInfo]:
        """List databases/schemas.

        Returns:
            List of DatabaseBriefInfo objects
        """
        ...

    @abstractmethod
    def list_users(self) -> List[UserInfo]:
        """List users/roles.

        Returns:
            List of UserInfo objects
        """
        ...

    @abstractmethod
    def get_session_info(self) -> SessionInfo:
        """Get current session/connection information.

        Returns:
            SessionInfo object with session details like user, database,
            schema, SSL status, etc.
        """
        ...


class AsyncAbstractStatusIntrospector(StatusIntrospectorMixin, ABC):
    """Asynchronous abstract base class for server status introspection.

    All methods are async. Method names do NOT have an _async suffix,
    matching the pattern of AsyncAbstractIntrospector.
    Subclasses must implement all abstract methods.
    """

    def __init__(self, backend: Any) -> None:
        self._backend = backend

    @abstractmethod
    async def get_overview(self) -> ServerOverview:
        """Get complete server status overview.

        Returns:
            ServerOverview object containing all status information
        """
        ...

    @abstractmethod
    async def list_configuration(
        self, category: Optional[StatusCategory] = None
    ) -> List[StatusItem]:
        """List configuration parameters.

        Args:
            category: Optional category filter

        Returns:
            List of StatusItem objects for configuration parameters
        """
        ...

    @abstractmethod
    async def list_performance_metrics(
        self, category: Optional[StatusCategory] = None
    ) -> List[StatusItem]:
        """List performance metrics.

        Args:
            category: Optional category filter

        Returns:
            List of StatusItem objects for performance metrics
        """
        ...

    @abstractmethod
    async def get_connection_info(self) -> ConnectionInfo:
        """Get connection information.

        Returns:
            ConnectionInfo object with connection details
        """
        ...

    @abstractmethod
    async def get_storage_info(self) -> StorageInfo:
        """Get storage information.

        Returns:
            StorageInfo object with storage details
        """
        ...

    @abstractmethod
    async def list_databases(self) -> List[DatabaseBriefInfo]:
        """List databases/schemas.

        Returns:
            List of DatabaseBriefInfo objects
        """
        ...

    @abstractmethod
    async def list_users(self) -> List[UserInfo]:
        """List users/roles.

        Returns:
            List of UserInfo objects
        """
        ...

    @abstractmethod
    async def get_session_info(self) -> SessionInfo:
        """Get current session/connection information.

        Returns:
            SessionInfo object with session details like user, database,
            schema, SSL status, etc.
        """
        ...
