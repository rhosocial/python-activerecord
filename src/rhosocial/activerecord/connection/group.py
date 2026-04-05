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
from typing import Type, List, Optional

from ..backend.base import StorageBackend, AsyncStorageBackend
from ..backend.config import ConnectionConfig


@dataclass
class ConnectionGroup:
    """
    Connection Group: Manages a shared database connection for a group of Model classes.

    All models in the group share the same backend instance, ensuring that
    transactions work correctly across multiple models.

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
    _backend_instance: Optional[StorageBackend] = field(default=None, init=False)
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
        Configure a shared connection for all models in the group.

        Creates a single backend instance and assigns it to all models,
        ensuring that transactions work correctly across multiple models.

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

        # Create a single shared backend instance
        self._backend_instance = self.backend_class(connection_config=self.config)

        # Assign the shared backend to each model
        for model in self.models:
            model.__connection_config__ = self.config
            model.__backend_class__ = self.backend_class
            model.__backend__ = self._backend_instance

        # Connect and introspect
        if self.models:
            self._backend_instance.logger = self.models[0].get_logger()
        self._backend_instance.connect()
        self._backend_instance.introspect_and_adapt()

        self._configured = True

    def disconnect(self) -> None:
        """
        Disconnect the shared connection.

        Safe to call multiple times. Errors during disconnection are caught
        and logged.
        """
        if not self._configured or self._backend_instance is None:
            return

        try:
            self._backend_instance.disconnect()
        except Exception:
            pass  # Ignore disconnection errors

        self._backend_instance = None
        self._configured = False

    def get_backend(self) -> Optional[StorageBackend]:
        """
        Get the shared Backend instance.

        Returns:
            StorageBackend instance or None if not configured
        """
        return self._backend_instance

    def is_configured(self) -> bool:
        """
        Check if the connection group has been configured.

        Returns:
            True if configure() has been called successfully
        """
        return self._configured

    def is_connected(self) -> bool:
        """
        Check if the connection is valid.

        Uses backend.ping(reconnect=False) to check connection health
        without attempting reconnection.

        Returns:
            True if the connection is valid, False otherwise
        """
        if not self._configured or self._backend_instance is None:
            return False

        try:
            return self._backend_instance.ping(reconnect=False)
        except Exception:
            return False

    def ping(self) -> bool:
        """
        Check connection status.

        Returns:
            True if connected, False otherwise
        """
        return self.is_connected()

    def __enter__(self) -> 'ConnectionGroup':
        """Context manager entry: configure connections."""
        self.configure()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit: disconnect the connection."""
        self.disconnect()


@dataclass
class AsyncConnectionGroup:
    """
    Async Connection Group: Manages a shared database connection for a group of Model classes.

    All models in the group share the same backend instance, ensuring that
    transactions work correctly across multiple models.

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
    _backend_instance: Optional[AsyncStorageBackend] = field(default=None, init=False)
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
        Configure a shared connection for all models in the group.

        Creates a single backend instance and assigns it to all models,
        ensuring that transactions work correctly across multiple models.

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

        # Create a single shared backend instance
        self._backend_instance = self.backend_class(connection_config=self.config)

        # Assign the shared backend to each model
        for model in self.models:
            model.__connection_config__ = self.config
            model.__backend_class__ = self.backend_class
            model.__backend__ = self._backend_instance

        # Connect and introspect
        if self.models:
            self._backend_instance.logger = self.models[0].get_logger()
        await self._backend_instance.connect()
        await self._backend_instance.introspect_and_adapt()

        self._configured = True

    async def disconnect(self) -> None:
        """
        Disconnect the shared connection.

        Safe to call multiple times. Errors during disconnection are caught
        and logged.
        """
        if not self._configured or self._backend_instance is None:
            return

        try:
            await self._backend_instance.disconnect()
        except Exception:
            pass  # Ignore disconnection errors

        self._backend_instance = None
        self._configured = False

    def get_backend(self) -> Optional[AsyncStorageBackend]:
        """
        Get the shared Backend instance.

        Returns:
            AsyncStorageBackend instance or None if not configured
        """
        return self._backend_instance

    def is_configured(self) -> bool:
        """
        Check if the connection group has been configured.

        Returns:
            True if configure() has been called successfully
        """
        return self._configured

    async def is_connected(self) -> bool:
        """
        Check if the connection is valid.

        Uses backend.ping(reconnect=False) to check connection health
        without attempting reconnection.

        Returns:
            True if the connection is valid, False otherwise
        """
        if not self._configured or self._backend_instance is None:
            return False

        try:
            return await self._backend_instance.ping(reconnect=False)
        except Exception:
            return False

    async def ping(self) -> bool:
        """
        Check connection status.

        Returns:
            True if connected, False otherwise
        """
        return await self.is_connected()

    async def __aenter__(self) -> 'AsyncConnectionGroup':
        """Async context manager entry: configure connections."""
        await self.configure()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit: disconnect the connection."""
        await self.disconnect()