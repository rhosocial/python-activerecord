# src/rhosocial/activerecord/backend/impl/dummy/backend.py
"""
Dummy Backend for SQL generation without a real database connection.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple, Type

from rhosocial.activerecord.backend.base import StorageBackend
from rhosocial.activerecord.backend.capabilities import DatabaseCapabilities, CapabilityCategory, CTECapability
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.dialect import SQLDialectBase
from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.backend.typing import QueryResult
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.backend.transaction import TransactionManager # Import for type hinting

from .dialect import DummyDialect

# Create a logger for the DummyBackend
dummy_backend_logger = logging.getLogger('dummy_backend')

class DummyBackend(StorageBackend):
    """
    A dummy backend for ActiveRecord that generates SQL without connecting to a real database.
    All operations requiring a database connection will raise NotImplementedError.
    """

    def __init__(self, connection_config: Optional[ConnectionConfig] = None, **kwargs):
        # DummyBackend doesn't really need connection_config but accept it for API compatibility
        super().__init__(connection_config=connection_config or ConnectionConfig(), **kwargs)
        self.logger = dummy_backend_logger
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

    # --- Methods from StorageBackend that will raise NotImplementedError ---
    # The inherited implementations of execute, execute_many, fetch_one, fetch_all
    # all rely on _execute_query or _get_cursor, so raising there is sufficient.
    # The base SQLOperationsMixin.insert/update/delete call self.execute,
    # so raising in self.execute is also sufficient.