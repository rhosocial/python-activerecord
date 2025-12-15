# src/rhosocial/activerecord/backend/impl/dummy/backend.py
"""
Dummy Backend for SQL generation without a real database connection.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple, Type

from rhosocial.activerecord.backend.base import StorageBackend, AsyncStorageBackend
from rhosocial.activerecord.backend.capabilities import DatabaseCapabilities, CapabilityCategory, CTECapability
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.dialect import SQLDialectBase
from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.backend.result import QueryResult
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.backend.transaction import TransactionManager, AsyncTransactionManager

from .dialect import DummyDialect


class DummyBackend(StorageBackend):
    """
    A dummy backend for ActiveRecord that generates SQL without connecting to a real database.
    All operations requiring a database connection will raise NotImplementedError.
    """

    def __init__(self, connection_config: Optional[ConnectionConfig] = None, **kwargs):
        # Ensure a default logger for DummyBackend if not explicitly provided
        if 'logger' not in kwargs:
            kwargs['logger'] = logging.getLogger('dummy_backend')
        super().__init__(connection_config=connection_config or ConnectionConfig(), **kwargs)
        self._dialect = DummyDialect()

    def _initialize_capabilities(self) -> DatabaseCapabilities:
        """
        Initializes dummy capabilities.
        For to_sql testing, we need to declare support for some features.
        """
        capabilities = DatabaseCapabilities()
        capabilities.add_cte([CTECapability.BASIC_CTE])
        return capabilities

    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple[SQLTypeAdapter, Type]]:
        """
        Provides empty adapter suggestions as this backend does not perform real type conversion.
        """
        return {}

    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def connect(self) -> None:
        raise NotImplementedError("DummyBackend does not support real database operations. Did you forget to configure a concrete backend?")

    def disconnect(self) -> None:
        pass # Disconnecting a dummy backend is a no-op

    def ping(self, reconnect: bool = True) -> bool:
        raise NotImplementedError("DummyBackend does not support real database operations. Did you forget to configure a concrete backend?")

    def _handle_error(self, error: Exception) -> None:
        # Re-raise the NotImplementedError or any other error that occurred.
        # This backend doesn't map specific database errors.
        if isinstance(error, NotImplementedError):
            raise error
        raise DatabaseError(f"An unexpected error occurred in DummyBackend: {error}") from error

    def get_server_version(self) -> Tuple[int, int, int]:
        # Return a dummy version, as this backend doesn't connect to a real server.
        return (0, 0, 0) # Indicates a dummy/mock version

    def _get_cursor(self) -> Any:
        raise NotImplementedError("DummyBackend does not support real database operations. Did you forget to configure a concrete backend?")

    def _execute_query(self, cursor: Any, sql: str, params: Optional[Tuple]) -> Any:
        raise NotImplementedError("DummyBackend does not support real database operations. Did you forget to configure a concrete backend?")

    def _handle_auto_commit(self) -> None:
        pass # No real database, so no commit needed

    @property
    def transaction_manager(self) -> TransactionManager:
        raise NotImplementedError("DummyBackend does not support real database operations. Did you forget to configure a concrete backend?")

# Async Dummy Backend
class AsyncDummyBackend(AsyncStorageBackend):
    """
    An async dummy backend for ActiveRecord that generates SQL without connecting to a real database.
    All operations requiring a database connection will raise NotImplementedError.
    """

    def __init__(self, connection_config: Optional[ConnectionConfig] = None, **kwargs):
        # Ensure a default logger for AsyncDummyBackend if not explicitly provided
        if 'logger' not in kwargs:
            kwargs['logger'] = logging.getLogger('async_dummy_backend')
        super().__init__(connection_config=connection_config or ConnectionConfig(), **kwargs)
        self._dialect = DummyDialect()

    def _initialize_capabilities(self) -> DatabaseCapabilities:
        return DatabaseCapabilities()

    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple[SQLTypeAdapter, Type]]:
        return {}

    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    async def connect(self) -> None:
        raise NotImplementedError("AsyncDummyBackend does not support real database operations. Did you forget to configure a concrete backend?")

    async def disconnect(self) -> None:
        pass

    async def ping(self, reconnect: bool = True) -> bool:
        raise NotImplementedError("AsyncDummyBackend does not support real database operations. Did you forget to configure a concrete backend?")

    async def _handle_error(self, error: Exception) -> None:
        if isinstance(error, NotImplementedError):
            raise error
        raise DatabaseError(f"An unexpected error occurred in AsyncDummyBackend: {error}") from error

    async def get_server_version(self) -> Tuple[int, int, int]:
        return (0, 0, 0)

    async def _get_cursor(self) -> Any:
        raise NotImplementedError("AsyncDummyBackend does not support real database operations. Did you forget to configure a concrete backend?")

    async def _execute_query(self, cursor: Any, sql: str, params: Optional[Tuple]) -> Any:
        raise NotImplementedError("AsyncDummyBackend does not support real database operations. Did you forget to configure a concrete backend?")

    async def _handle_auto_commit(self) -> None:
        pass

    @property
    def transaction_manager(self) -> AsyncTransactionManager:
        raise NotImplementedError("AsyncDummyBackend does not support real database operations. Did you forget to configure a concrete backend?")