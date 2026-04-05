# src/rhosocial/activerecord/connection/manager.py
"""
Connection Manager Module.

Provides ConnectionManager class for managing multiple named connection groups.
"""

from typing import Dict, List, Optional, Type

from ..backend.base import StorageBackend, AsyncStorageBackend
from ..backend.config import ConnectionConfig
from .group import ConnectionGroup, AsyncConnectionGroup


class ConnectionManager:
    """
    Connection Manager: Manages multiple named connection groups.

    Suitable for applications that need to connect to multiple databases,
    such as main database + statistics database, or master-slave setups.

    Example:
        manager = ConnectionManager()

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

        # Configure all
        manager.configure_all()

        # ... use models ...

        # Disconnect all
        manager.disconnect_all()

        # Or use as context manager
        with ConnectionManager() as manager:
            manager.create_group(...)
            # ... use models ...
    """

    def __init__(self):
        self._groups: Dict[str, ConnectionGroup] = {}

    def create_group(
        self,
        name: str,
        config: ConnectionConfig,
        backend_class: Type[StorageBackend],
        models: Optional[List[Type]] = None,
    ) -> ConnectionGroup:
        """
        Create and register a new connection group.

        Args:
            name: Unique name for the connection group
            config: Connection configuration
            backend_class: Backend class to use
            models: Optional list of Model classes to include

        Returns:
            The created ConnectionGroup instance

        Raises:
            ValueError: If a group with the same name already exists
        """
        if name in self._groups:
            raise ValueError(f"ConnectionGroup '{name}' already exists")

        group = ConnectionGroup(
            name=name,
            models=models or [],
            config=config,
            backend_class=backend_class,
        )
        self._groups[name] = group
        return group

    def get_group(self, name: str) -> Optional[ConnectionGroup]:
        """
        Get a connection group by name.

        Args:
            name: Name of the connection group

        Returns:
            ConnectionGroup instance or None if not found
        """
        return self._groups.get(name)

    def has_group(self, name: str) -> bool:
        """
        Check if a connection group exists.

        Args:
            name: Name of the connection group

        Returns:
            True if the group exists
        """
        return name in self._groups

    def remove_group(self, name: str, disconnect: bool = True) -> bool:
        """
        Remove a connection group from the manager.

        Args:
            name: Name of the connection group
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
        Configure all connection groups.

        Calls configure() on each registered group.
        """
        for group in self._groups.values():
            group.configure()

    def disconnect_all(self) -> None:
        """
        Disconnect all connection groups.

        Calls disconnect() on each registered group.
        """
        for group in self._groups.values():
            group.disconnect()

    def is_connected(self) -> bool:
        """
        Check if all connection groups have valid connections.

        Returns:
            True if all groups report connected, False otherwise
        """
        return all(group.is_connected() for group in self._groups.values())

    def get_group_names(self) -> List[str]:
        """
        Get names of all registered connection groups.

        Returns:
            List of group names
        """
        return list(self._groups.keys())

    def __enter__(self) -> 'ConnectionManager':
        """Context manager entry: configure all groups."""
        self.configure_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit: disconnect all groups."""
        self.disconnect_all()

    def __len__(self) -> int:
        """Return the number of registered connection groups."""
        return len(self._groups)

    def __contains__(self, name: str) -> bool:
        """Check if a connection group exists by name."""
        return name in self._groups


class AsyncConnectionManager:
    """
    Async Connection Manager: Manages multiple named async connection groups.

    Async version of ConnectionManager, suitable for async applications.

    Example:
        async with AsyncConnectionManager() as manager:
            manager.create_group(
                name="main",
                config=config,
                backend_class=AsyncMySQLBackend,
                models=[User, Post],
            )
            # ... use models ...
    """

    def __init__(self):
        self._groups: Dict[str, AsyncConnectionGroup] = {}

    def create_group(
        self,
        name: str,
        config: ConnectionConfig,
        backend_class: Type[AsyncStorageBackend],
        models: Optional[List[Type]] = None,
    ) -> AsyncConnectionGroup:
        """
        Create and register a new async connection group.

        Args:
            name: Unique name for the connection group
            config: Connection configuration
            backend_class: Async backend class to use
            models: Optional list of Model classes to include

        Returns:
            The created AsyncConnectionGroup instance

        Raises:
            ValueError: If a group with the same name already exists
        """
        if name in self._groups:
            raise ValueError(f"AsyncConnectionGroup '{name}' already exists")

        group = AsyncConnectionGroup(
            name=name,
            models=models or [],
            config=config,
            backend_class=backend_class,
        )
        self._groups[name] = group
        return group

    def get_group(self, name: str) -> Optional[AsyncConnectionGroup]:
        """
        Get an async connection group by name.

        Args:
            name: Name of the connection group

        Returns:
            AsyncConnectionGroup instance or None if not found
        """
        return self._groups.get(name)

    def has_group(self, name: str) -> bool:
        """
        Check if an async connection group exists.

        Args:
            name: Name of the connection group

        Returns:
            True if the group exists
        """
        return name in self._groups

    async def remove_group(self, name: str, disconnect: bool = True) -> bool:
        """
        Remove an async connection group from the manager.

        Args:
            name: Name of the connection group
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
        Configure all async connection groups.

        Calls await configure() on each registered group.
        """
        for group in self._groups.values():
            await group.configure()

    async def disconnect_all(self) -> None:
        """
        Disconnect all async connection groups.

        Calls await disconnect() on each registered group.
        """
        for group in self._groups.values():
            await group.disconnect()

    async def is_connected(self) -> bool:
        """
        Check if all async connection groups have valid connections.

        Returns:
            True if all groups report connected, False otherwise
        """
        for group in self._groups.values():
            if not await group.is_connected():
                return False
        return True

    def get_group_names(self) -> List[str]:
        """
        Get names of all registered async connection groups.

        Returns:
            List of group names
        """
        return list(self._groups.keys())

    async def __aenter__(self) -> 'AsyncConnectionManager':
        """Async context manager entry: configure all groups."""
        await self.configure_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit: disconnect all groups."""
        await self.disconnect_all()

    def __len__(self) -> int:
        """Return the number of registered async connection groups."""
        return len(self._groups)

    def __contains__(self, name: str) -> bool:
        """Check if an async connection group exists by name."""
        return name in self._groups
