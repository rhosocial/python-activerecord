# src/rhosocial/activerecord/connection/manager.py
"""
Backend Manager Module.

Provides BackendManager class for managing multiple named backend groups.

NOTE: Despite the "connection" module naming, this module manages
**backend instances**, not connections. The module name "connection"
reflects the user-facing purpose: conveniently managing groups of
related ActiveRecord classes' backend instances and providing
connection convenience. The actual management target is the backend.

Design Intent:
    BackendManager orchestrates multiple BackendGroup instances, each
    representing a set of ActiveRecord classes that share a single
    backend (and therefore a single connection). This is useful when:

    1. An application connects to multiple databases — e.g., a main
       database for business data and a stats database for analytics.
    2. Different groups of models have independent connection lifecycles
       — one group may stay connected while another disconnects.
    3. Each group's models are logically related, sequential, and may
       share transactions within the group, while different groups
       operate on separate databases or connection scopes.

    Synchronous and asynchronous versions are fully parallel (same API
    with async/await), but MUST NOT be mixed: BackendManager with
    synchronous groups, AsyncBackendManager with asynchronous groups.
"""

from typing import Callable, Dict, List, Optional, Type, Union

from ..backend.base import StorageBackend, AsyncStorageBackend
from ..backend.config import ConnectionConfig
from ..interface import IActiveRecord, IAsyncActiveRecord
from .group import BackendGroup, AsyncBackendGroup


class BackendManager:
    """
    Backend Manager: Manages multiple named backend groups.

    Suitable for applications that need to connect to multiple databases,
    such as main database + statistics database, or master-slave setups.

    Each group managed by this class contains ActiveRecord models that
    share a single backend instance — they operate on the same active
    connection simultaneously. This enables transactional consistency
    and unified connection lifecycle within each group, while different
    groups maintain independent backends and connection scopes.

    Despite the "connection" module naming, this class manages **backend
    instances**, not connections. It provides convenience for connection
    management but does not interfere with connection timing.

    IMPORTANT: Synchronous BackendManager MUST be used with synchronous
    backends and models only. For async backends and models, use
    AsyncBackendManager instead. Mixing sync and async is not supported.

    Example:
        manager = BackendManager()

        # Create groups
        manager.create_group(
            name="main",
            config=MySQLConnectionConfig(host="db-master"),
            backend_class=MySQLBackend,
            models=[User, Post],
        )
        manager.create_group(
            name="stats",
            config=SQLiteConnectionConfig(database="/data/stats.db"),
            backend_class=SQLiteBackend,
            models=[Log, Metric],
        )

        # Configure all (creates backends but does NOT connect)
        manager.configure_all()

        # Use backend.context() for on-demand connections
        with manager.get_group("main").get_backend().context() as ctx:
            user = User.find_one(1)

        # Disconnect all (cleanup)
        manager.disconnect_all()

        # Or use as context manager
        with BackendManager() as manager:
            manager.create_group(...)
            with manager.get_group("main").get_backend().context() as ctx:
                user = User.find_one(1)
    """

    def __init__(self):
        self._groups: Dict[str, BackendGroup] = {}

    def create_group(
        self,
        name: str,
        config: Union[ConnectionConfig, Callable[..., ConnectionConfig]],
        backend_class: Type[StorageBackend],
        models: Optional[List[Type[IActiveRecord]]] = None,
    ) -> BackendGroup:
        """
        Create and register a new backend group.

        Args:
            name: Unique name for the backend group
            config: Connection configuration, or a callable that returns one
                (e.g., a named connection function)
            backend_class: Backend class to use
            models: Optional list of ActiveRecord Model classes to include

        Returns:
            The created BackendGroup instance

        Raises:
            ValueError: If a group with the same name already exists
        """
        if name in self._groups:
            raise ValueError(f"BackendGroup '{name}' already exists")

        group = BackendGroup(
            name=name,
            models=models or [],
            config=config,
            backend_class=backend_class,
        )
        self._groups[name] = group
        return group

    def get_group(self, name: str) -> Optional[BackendGroup]:
        """
        Get a backend group by name.

        Args:
            name: Name of the backend group

        Returns:
            BackendGroup instance or None if not found
        """
        return self._groups.get(name)

    def has_group(self, name: str) -> bool:
        """
        Check if a backend group exists.

        Args:
            name: Name of the backend group

        Returns:
            True if the group exists
        """
        return name in self._groups

    def remove_group(self, name: str, disconnect: bool = True) -> bool:
        """
        Remove a backend group from the manager.

        Args:
            name: Name of the backend group
            disconnect: Whether to disconnect before removing

        Returns:
            True if the group was removed, False if not found
        """
        group = self._groups.pop(name, None)
        if group is None:
            return False

        if disconnect and group.is_configured():
            group.disconnect()

        return True

    def configure_all(self) -> None:
        """
        Configure all backend groups.

        Calls configure() on each registered group. This creates
        backends but does NOT establish connections. Use each group's
        ``get_backend().context()`` for on-demand connections.
        """
        for group in self._groups.values():
            group.configure()

    def disconnect_all(self) -> None:
        """
        Disconnect all backend groups.

        Calls disconnect() on each registered group.
        """
        for group in self._groups.values():
            group.disconnect()

    def is_connected(self) -> bool:
        """
        Check if all backend groups have active connections.

        Note: With the context-based lifecycle, this returns True only
        when backends are explicitly connected.

        Returns:
            True if all groups report connected, False otherwise
        """
        return all(group.is_connected() for group in self._groups.values())

    def get_group_names(self) -> List[str]:
        """
        Get names of all registered backend groups.

        Returns:
            List of group names
        """
        return list(self._groups.keys())

    def __enter__(self) -> 'BackendManager':
        """Context manager entry: configure all groups (without connecting)."""
        self.configure_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit: disconnect all groups."""
        self.disconnect_all()

    def __len__(self) -> int:
        """Return the number of registered backend groups."""
        return len(self._groups)

    def __contains__(self, name: str) -> bool:
        """Check if a backend group exists by name."""
        return name in self._groups


class AsyncBackendManager:
    """
    Async Backend Manager: Manages multiple named async backend groups.

    Async version of BackendManager, suitable for async applications.

    Each group managed by this class contains ActiveRecord models that
    share a single backend instance — they operate on the same active
    connection simultaneously. This enables transactional consistency
    and unified connection lifecycle within each group, while different
    groups maintain independent backends and connection scopes.

    Despite the "connection" module naming, this class manages **backend
    instances**, not connections. It provides convenience for connection
    management but does not interfere with connection timing.

    IMPORTANT: AsyncBackendManager MUST be used with asynchronous backends
    and models only. For synchronous backends and models, use
    BackendManager instead. Mixing sync and async is not supported.

    Example:
        async with AsyncBackendManager() as manager:
            manager.create_group(
                name="main",
                config=config,
                backend_class=AsyncMySQLBackend,
                models=[AsyncUser, AsyncPost],
            )
            async with manager.get_group("main").get_backend().context() as ctx:
                user = await AsyncUser.find_one(1)
    """

    def __init__(self):
        self._groups: Dict[str, AsyncBackendGroup] = {}

    def create_group(
        self,
        name: str,
        config: Union[ConnectionConfig, Callable[..., ConnectionConfig]],
        backend_class: Type[AsyncStorageBackend],
        models: Optional[List[Type[IAsyncActiveRecord]]] = None,
    ) -> AsyncBackendGroup:
        """
        Create and register a new async backend group.

        Args:
            name: Unique name for the backend group
            config: Connection configuration, or a callable that returns one
                (e.g., a named connection function)
            backend_class: Async backend class to use
            models: Optional list of async ActiveRecord Model classes to include

        Returns:
            The created AsyncBackendGroup instance

        Raises:
            ValueError: If a group with the same name already exists
        """
        if name in self._groups:
            raise ValueError(f"AsyncBackendGroup '{name}' already exists")

        group = AsyncBackendGroup(
            name=name,
            models=models or [],
            config=config,
            backend_class=backend_class,
        )
        self._groups[name] = group
        return group

    def get_group(self, name: str) -> Optional[AsyncBackendGroup]:
        """
        Get an async backend group by name.

        Args:
            name: Name of the backend group

        Returns:
            AsyncBackendGroup instance or None if not found
        """
        return self._groups.get(name)

    def has_group(self, name: str) -> bool:
        """
        Check if an async backend group exists.

        Args:
            name: Name of the backend group

        Returns:
            True if the group exists
        """
        return name in self._groups

    async def remove_group(self, name: str, disconnect: bool = True) -> bool:
        """
        Remove an async backend group from the manager.

        Args:
            name: Name of the backend group
            disconnect: Whether to disconnect before removing

        Returns:
            True if the group was removed, False if not found
        """
        group = self._groups.pop(name, None)
        if group is None:
            return False

        if disconnect and group.is_configured():
            await group.disconnect()

        return True

    async def configure_all(self) -> None:
        """
        Configure all async backend groups.

        Calls await configure() on each registered group. This creates
        backends but does NOT establish connections. Use each group's
        ``get_backend().context()`` for on-demand connections.
        """
        for group in self._groups.values():
            await group.configure()

    async def disconnect_all(self) -> None:
        """
        Disconnect all async backend groups.

        Calls await disconnect() on each registered group.
        """
        for group in self._groups.values():
            await group.disconnect()

    async def is_connected(self) -> bool:
        """
        Check if all async backend groups have active connections.

        Note: With the context-based lifecycle, this returns True only
        when backends are explicitly connected.

        Returns:
            True if all groups report connected, False otherwise
        """
        for group in self._groups.values():
            if not await group.is_connected():
                return False
        return True

    def get_group_names(self) -> List[str]:
        """
        Get names of all registered async backend groups.

        Returns:
            List of group names
        """
        return list(self._groups.keys())

    async def __aenter__(self) -> 'AsyncBackendManager':
        """Async context manager entry: configure all groups (without connecting)."""
        await self.configure_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit: disconnect all groups."""
        await self.disconnect_all()

    def __len__(self) -> int:
        """Return the number of registered async backend groups."""
        return len(self._groups)

    def __contains__(self, name: str) -> bool:
        """Check if an async backend group exists by name."""
        return name in self._groups
