# src/rhosocial/activerecord/connection/group.py
"""
Connection Group Module.

Provides ConnectionGroup and AsyncConnectionGroup classes for managing
database connections across multiple ActiveRecord models.

This module is independent of the Worker module and can be used in:
- Web applications (FastAPI, Flask, etc.)
- CLI tools
- Cron jobs
- Worker pools
"""

from dataclasses import dataclass, field
from typing import Type, List, Optional, Dict

from ..backend.base import StorageBackend, AsyncStorageBackend
from ..backend.config import ConnectionConfig


@dataclass
class ConnectionGroup:
    """
    Connection Group: Manages database connections for a group of Model classes.

    Suitable for Worker-level or Task-level centralized connection management,
    as well as standalone use in web applications, CLI tools, and cron jobs.

    Example:
        # Basic usage
        group = ConnectionGroup(
            name="main",
            models=[User, Post],
            config=MySQLConnectionConfig(host="localhost"),
            backend_class=MySQLBackend,
        )
        group.configure()
        # ... use models ...
        group.disconnect()

        # With context manager
        with ConnectionGroup(
            name="main",
            models=[User, Post],
            config=config,
            backend_class=MySQLBackend,
        ) as group:
            user = User.find_one(1)
    """

    name: str
    models: List[Type] = field(default_factory=list)
    config: Optional[ConnectionConfig] = None
    backend_class: Optional[Type[StorageBackend]] = None
    _backends: Dict[Type, StorageBackend] = field(default_factory=dict, init=False)
    _configured: bool = field(default=False, init=False)

    def add_model(self, model: Type) -> 'ConnectionGroup':
        """
        Add a Model class to the connection group.

        Args:
            model: ActiveRecord Model class

        Returns:
            Self for method chaining

        Raises:
            RuntimeError: If the group is already configured
        """
        if self._configured:
            raise RuntimeError(
                f"Cannot add model to configured ConnectionGroup '{self.name}'. "
                "Call disconnect() first to reconfigure."
            )
        self.models.append(model)
        return self

    def configure(self) -> None:
        """
        Configure connections for all models in the group.

        This calls Model.configure(config, backend_class) for each model.
        After configuration, models can be used for database operations.

        Raises:
            ValueError: If config or backend_class is not set
        """
        if self._configured:
            return  # Already configured, skip

        if self.config is None:
            raise ValueError(
                f"ConnectionConfig not set for ConnectionGroup '{self.name}'"
            )
        if self.backend_class is None:
            raise ValueError(
                f"Backend class not set for ConnectionGroup '{self.name}'"
            )

        for model in self.models:
            model.configure(self.config, self.backend_class)
            self._backends[model] = model.backend()

        self._configured = True

    def disconnect(self) -> None:
        """
        Disconnect all connections in the group.

        Safe to call multiple times. Errors during disconnection are caught
        and logged, but do not prevent other connections from being closed.
        """
        if not self._configured:
            return  # Not configured, nothing to disconnect

        for backend in list(self._backends.values()):
            try:
                backend.disconnect()
            except Exception:
                pass  # Ignore disconnection errors

        self._backends.clear()
        self._configured = False

    def get_backend(self, model: Type) -> Optional[StorageBackend]:
        """
        Get the Backend instance for a specific Model.

        Args:
            model: The Model class to get backend for

        Returns:
            StorageBackend instance or None if not configured
        """
        return self._backends.get(model)

    def is_configured(self) -> bool:
        """
        Check if the connection group has been configured.

        Returns:
            True if configure() has been called successfully
        """
        return self._configured

    def is_connected(self) -> bool:
        """
        Check if all connections in the group are valid.

        Uses backend.ping(reconnect=False) to check connection health
        without attempting reconnection.

        Returns:
            True if all connections are valid, False otherwise
        """
        if not self._configured:
            return False

        for backend in self._backends.values():
            try:
                if not backend.ping(reconnect=False):
                    return False
            except Exception:
                return False

        return True

    def ping(self) -> Dict[Type, bool]:
        """
        Check connection status for each Model individually.

        Returns:
            Dictionary mapping Model class to connection status (True/False)
        """
        result: Dict[Type, bool] = {}

        for model, backend in self._backends.items():
            try:
                result[model] = backend.ping(reconnect=False)
            except Exception:
                result[model] = False

        return result

    def __enter__(self) -> 'ConnectionGroup':
        """Context manager entry: configure connections."""
        self.configure()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit: disconnect all connections."""
        self.disconnect()


@dataclass
class AsyncConnectionGroup:
    """
    Async Connection Group: Manages database connections for a group of Model classes.

    Async version of ConnectionGroup, suitable for async applications.

    Example:
        async with AsyncConnectionGroup(
            name="main",
            models=[User, Post],
            config=config,
            backend_class=AsyncMySQLBackend,
        ) as group:
            user = await User.find_one(1)
    """

    name: str
    models: List[Type] = field(default_factory=list)
    config: Optional[ConnectionConfig] = None
    backend_class: Optional[Type[AsyncStorageBackend]] = None
    _backends: Dict[Type, AsyncStorageBackend] = field(default_factory=dict, init=False)
    _configured: bool = field(default=False, init=False)

    def add_model(self, model: Type) -> 'AsyncConnectionGroup':
        """
        Add a Model class to the connection group.

        Args:
            model: ActiveRecord Model class

        Returns:
            Self for method chaining

        Raises:
            RuntimeError: If the group is already configured
        """
        if self._configured:
            raise RuntimeError(
                f"Cannot add model to configured AsyncConnectionGroup '{self.name}'. "
                "Call disconnect() first to reconfigure."
            )
        self.models.append(model)
        return self

    async def configure(self) -> None:
        """
        Configure connections for all models in the group.

        This calls await Model.async_configure(config, backend_class) for each model.

        Raises:
            ValueError: If config or backend_class is not set
        """
        if self._configured:
            return  # Already configured, skip

        if self.config is None:
            raise ValueError(
                f"ConnectionConfig not set for AsyncConnectionGroup '{self.name}'"
            )
        if self.backend_class is None:
            raise ValueError(
                f"Backend class not set for AsyncConnectionGroup '{self.name}'"
            )

        for model in self.models:
            await model.configure(self.config, self.backend_class)
            self._backends[model] = model.backend()

        self._configured = True

    async def disconnect(self) -> None:
        """
        Disconnect all connections in the group.

        Safe to call multiple times. Errors during disconnection are caught
        and logged, but do not prevent other connections from being closed.
        """
        if not self._configured:
            return  # Not configured, nothing to disconnect

        for backend in list(self._backends.values()):
            try:
                await backend.disconnect()
            except Exception:
                pass  # Ignore disconnection errors

        self._backends.clear()
        self._configured = False

    def get_backend(self, model: Type) -> Optional[AsyncStorageBackend]:
        """
        Get the Backend instance for a specific Model.

        Args:
            model: The Model class to get backend for

        Returns:
            AsyncStorageBackend instance or None if not configured
        """
        return self._backends.get(model)

    def is_configured(self) -> bool:
        """
        Check if the connection group has been configured.

        Returns:
            True if configure() has been called successfully
        """
        return self._configured

    async def is_connected(self) -> bool:
        """
        Check if all connections in the group are valid.

        Uses backend.ping(reconnect=False) to check connection health
        without attempting reconnection.

        Returns:
            True if all connections are valid, False otherwise
        """
        if not self._configured:
            return False

        for backend in self._backends.values():
            try:
                if not await backend.ping(reconnect=False):
                    return False
            except Exception:
                return False

        return True

    async def ping(self) -> Dict[Type, bool]:
        """
        Check connection status for each Model individually.

        Returns:
            Dictionary mapping Model class to connection status (True/False)
        """
        result: Dict[Type, bool] = {}

        for model, backend in self._backends.items():
            try:
                result[model] = await backend.ping(reconnect=False)
            except Exception:
                result[model] = False

        return result

    async def __aenter__(self) -> 'AsyncConnectionGroup':
        """Async context manager entry: configure connections."""
        await self.configure()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit: disconnect all connections."""
        await self.disconnect()
