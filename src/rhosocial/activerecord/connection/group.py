# src/rhosocial/activerecord/connection/group.py
"""
Backend Group Module.

Provides BackendGroup and AsyncBackendGroup classes for managing
database backend instances across multiple ActiveRecord models.

NOTE: Despite the "connection" module naming, this module manages
**backend instances**, not connections. The module name "connection"
reflects the user-facing purpose: conveniently managing a group of
related ActiveRecord classes' backend instances and providing
connection convenience. The actual management target is the backend.

Design Intent:
    The core purpose of BackendGroup is to make multiple ActiveRecord
    classes share a single backend instance. All models in the same
    group operate on the same active connection simultaneously, which
    is essential when:

    1. Operations across models are logically related and sequential —
       e.g., creating an Order and its OrderItems within the same
       transaction.
    2. Models need a shared connection lifecycle — connect and
       disconnect together, avoiding partial states where some models
       are connected while others are not.
    3. Transaction consistency is required — since all models share
       one backend, they naturally participate in the same transaction
       scope.

    Synchronous and asynchronous versions are fully parallel (same API
    with async/await), but MUST NOT be mixed: BackendGroup with
    synchronous backends, AsyncBackendGroup with asynchronous backends.

This module does NOT manage connection timing. Users are responsible for
deciding when to connect and disconnect, with the following options:

1. Manual: Call ``backend.connect()`` / ``backend.introspect_and_adapt()``
   / ``backend.disconnect()`` directly.
2. Convenience: Use ``with backend.context() as ctx:`` for on-demand
   connection lifecycle control ("connect on demand, disconnect after use").

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
from ..interface import IActiveRecord, IAsyncActiveRecord


@dataclass
class BackendGroup:
    """
    Backend Group: Manages a shared backend instance for a group of Model classes.

    Despite the "connection" module naming, this class manages **backend
    instances**, not connections. The name "BackendGroup" reflects the
    actual management target: a group of related ActiveRecord classes
    sharing the same backend instance, with connection convenience provided.

    All models in the group share the same backend instance, meaning they
    operate on the same active connection simultaneously. This design is
    intentional for scenarios where:

    - Operations across models are logically related and sequential
      (e.g., creating an Order and its OrderItems together).
    - Models may participate in the same transaction, requiring a
      shared connection to ensure atomicity.
    - Models should share a unified connection lifecycle — connect and
      disconnect together rather than independently.

    This class does NOT manage connection timing. Users decide when to
    connect and disconnect using either manual calls or ``backend.context()``.

    IMPORTANT: Synchronous BackendGroup MUST be used with synchronous
    backends and models only. For async backends and models, use
    AsyncBackendGroup instead. Mixing sync and async is not supported.

    Example:
        # Basic usage
        group = BackendGroup(
            name="main",
            models=[User, Post],
            config=MySQLConnectionConfig(host="localhost"),
            backend_class=MySQLBackend,
        )
        group.configure()

        # Option 1: Manual connection management
        backend = group.get_backend()
        backend.connect()
        backend.introspect_and_adapt()
        user = User.find_one(1)
        backend.disconnect()

        # Option 2: On-demand connection via backend.context()
        with group.get_backend().context() as ctx:
            user = User.find_one(1)

        group.disconnect()  # Cleanup

        # With context manager (auto-configure on entry, cleanup on exit)
        with BackendGroup(
            name="main",
            models=[User, Post],
            config=config,
            backend_class=MySQLBackend,
        ) as group:
            with group.get_backend().context() as ctx:
                user = User.find_one(1)
    """

    name: str
    models: List[Type[IActiveRecord]] = field(default_factory=list)
    config: Optional[ConnectionConfig] = None
    backend_class: Optional[Type[StorageBackend]] = None
    _backend_instance: Optional[StorageBackend] = field(default=None, init=False)
    _configured: bool = field(default=False, init=False)

    def add_model(self, model: Type[IActiveRecord]) -> 'BackendGroup':
        """
        Add a Model class to the backend group.

        Args:
            model: ActiveRecord Model class

        Returns:
            Self for method chaining

        Raises:
            RuntimeError: If the group is already configured
        """
        if self._configured:
            raise RuntimeError(
                f"Cannot add model to configured BackendGroup '{self.name}'. "
                "Call disconnect() first to reconfigure."
            )
        self.models.append(model)
        return self

    def configure(self) -> None:
        """
        Configure the backend group without connecting.

        Creates a single backend instance and assigns it to all models,
        but does NOT establish a connection. Users are responsible for
        managing the connection lifecycle via ``backend.connect()`` /
        ``backend.disconnect()`` or ``backend.context()``.

        Raises:
            ValueError: If config or backend_class is not set
        """
        if self._configured:
            return  # Already configured, skip

        if self.config is None:
            raise ValueError(
                f"ConnectionConfig not set for BackendGroup '{self.name}'"
            )
        if self.backend_class is None:
            raise ValueError(
                f"Backend class not set for BackendGroup '{self.name}'"
            )

        # Create a single shared backend instance (not connected)
        self._backend_instance = self.backend_class(connection_config=self.config)

        # Assign the shared backend to each model
        for model in self.models:
            model.__connection_config__ = self.config
            model.__backend_class__ = self.backend_class
            model.__backend__ = self._backend_instance

        # Set logger if models are present
        if self.models:
            self._backend_instance.logger = self.models[0].get_logger()

        self._configured = True

    def disconnect(self) -> None:
        """
        Disconnect and clean up the backend group.

        Removes the backend instance from all models and clears the
        configured state. Safe to call multiple times.
        """
        if not self._configured or self._backend_instance is None:
            return

        # Clear model references
        for model in self.models:
            model.__backend__ = None

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
        Check if the backend group has been configured.

        Returns:
            True if configure() has been called successfully
        """
        return self._configured

    def is_connected(self) -> bool:
        """
        Check if the backend currently has an active connection.

        Note: This returns True only when the backend is explicitly
        connected (e.g., inside a ``backend.context()`` block or
        after manual ``connect()``).

        Returns:
            True if the connection is currently active, False otherwise
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

    def __enter__(self) -> 'BackendGroup':
        """Context manager entry: configure the group (without connecting)."""
        self.configure()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit: disconnect and clean up."""
        self.disconnect()


@dataclass
class AsyncBackendGroup:
    """
    Async Backend Group: Manages a shared backend instance for a group of Model classes.

    Despite the "connection" module naming, this class manages **backend
    instances**, not connections. The name "AsyncBackendGroup" reflects the
    actual management target: a group of related ActiveRecord classes
    sharing the same backend instance, with connection convenience provided.

    All models in the group share the same backend instance, meaning they
    operate on the same active connection simultaneously. This design is
    intentional for scenarios where:

    - Operations across models are logically related and sequential
      (e.g., creating an Order and its OrderItems together).
    - Models may participate in the same transaction, requiring a
      shared connection to ensure atomicity.
    - Models should share a unified connection lifecycle — connect and
      disconnect together rather than independently.

    This class does NOT manage connection timing. Users decide when to
    connect and disconnect using either manual calls or ``backend.context()``.

    IMPORTANT: AsyncBackendGroup MUST be used with asynchronous backends
    and models only. For synchronous backends and models, use BackendGroup
    instead. Mixing sync and async is not supported.

    Example:
        group = AsyncBackendGroup(
            name="main",
            models=[AsyncUser, AsyncPost],
            config=config,
            backend_class=AsyncMySQLBackend,
        )
        await group.configure()

        # Option 1: Manual connection management
        backend = group.get_backend()
        await backend.connect()
        await backend.introspect_and_adapt()
        user = await AsyncUser.find_one(1)
        await backend.disconnect()

        # Option 2: On-demand connection via backend.context()
        async with group.get_backend().context() as ctx:
            user = await AsyncUser.find_one(1)

        await group.disconnect()
    """

    name: str
    models: List[Type[IAsyncActiveRecord]] = field(default_factory=list)
    config: Optional[ConnectionConfig] = None
    backend_class: Optional[Type[AsyncStorageBackend]] = None
    _backend_instance: Optional[AsyncStorageBackend] = field(default=None, init=False)
    _configured: bool = field(default=False, init=False)

    def add_model(self, model: Type[IAsyncActiveRecord]) -> 'AsyncBackendGroup':
        """
        Add a Model class to the backend group.

        Args:
            model: ActiveRecord Model class

        Returns:
            Self for method chaining

        Raises:
            RuntimeError: If the group is already configured
        """
        if self._configured:
            raise RuntimeError(
                f"Cannot add model to configured AsyncBackendGroup '{self.name}'. "
                "Call disconnect() first to reconfigure."
            )
        self.models.append(model)
        return self

    async def configure(self) -> None:
        """
        Configure the backend group without connecting.

        Creates a single backend instance and assigns it to all models,
        but does NOT establish a connection. Users are responsible for
        managing the connection lifecycle via ``backend.connect()`` /
        ``backend.disconnect()`` or ``backend.context()``.

        Raises:
            ValueError: If config or backend_class is not set
        """
        if self._configured:
            return  # Already configured, skip

        if self.config is None:
            raise ValueError(
                f"ConnectionConfig not set for AsyncBackendGroup '{self.name}'"
            )
        if self.backend_class is None:
            raise ValueError(
                f"Backend class not set for AsyncBackendGroup '{self.name}'"
            )

        # Create a single shared backend instance (not connected)
        self._backend_instance = self.backend_class(connection_config=self.config)

        # Assign the shared backend to each model
        for model in self.models:
            model.__connection_config__ = self.config
            model.__backend_class__ = self.backend_class
            model.__backend__ = self._backend_instance

        # Set logger if models are present
        if self.models:
            self._backend_instance.logger = self.models[0].get_logger()

        self._configured = True

    async def disconnect(self) -> None:
        """
        Disconnect and clean up the backend group.

        Removes the backend instance from all models and clears the
        configured state. Safe to call multiple times.
        """
        if not self._configured or self._backend_instance is None:
            return

        # Clear model references
        for model in self.models:
            model.__backend__ = None

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
        Check if the backend group has been configured.

        Returns:
            True if configure() has been called successfully
        """
        return self._configured

    async def is_connected(self) -> bool:
        """
        Check if the backend currently has an active connection.

        Note: This returns True only when the backend is explicitly
        connected (e.g., inside an ``async with backend.context()``
        block or after manual ``connect()``).

        Returns:
            True if the connection is currently active, False otherwise
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

    async def __aenter__(self) -> 'AsyncBackendGroup':
        """Async context manager entry: configure the group (without connecting)."""
        await self.configure()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit: disconnect and clean up."""
        await self.disconnect()
