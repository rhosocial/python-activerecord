# src/rhosocial/activerecord/backend/impl/dummy/backend.py
"""
Dummy Backend for SQL generation without a real database connection.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Type

from rhosocial.activerecord.backend.base import StorageBackend, AsyncStorageBackend
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.dialect import SQLDialectBase
from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.backend.transaction import TransactionManager, AsyncTransactionManager
from rhosocial.activerecord.backend.introspection.mixins import IntrospectionMixin, AsyncIntrospectionMixin
from rhosocial.activerecord.backend.introspection.types import (
    DatabaseInfo,
    TableInfo,
    ColumnInfo,
    IndexInfo,
    ForeignKeyInfo,
    ViewInfo,
    TriggerInfo,
)

from .dialect import DummyDialect


# Error message constants
DUMMY_BACKEND_ERROR_MSG = (
    "DummyBackend does not support real database operations. Did you forget to configure a concrete backend?"
)
ASYNC_DUMMY_BACKEND_ERROR_MSG = (
    "AsyncDummyBackend does not support real database operations. Did you forget to configure a concrete backend?"
)


class DummyIntrospectionMixin(IntrospectionMixin):
    """Dummy introspection mixin for DummyBackend.

    Provides mock implementations of introspection methods that return
    empty or minimal data. This is useful for testing SQL generation
    without requiring a real database connection.
    """

    def _query_database_info(self) -> DatabaseInfo:
        """Return mock database info."""
        return DatabaseInfo(
            name="dummy",
            version="0.0.0",
            version_tuple=(0, 0, 0),
            vendor="Dummy",
            size_bytes=None,
        )

    def _query_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """Return empty table list."""
        return []

    def _query_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[TableInfo]:
        """Return None as no tables exist in dummy backend."""
        return None

    def _query_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """Return empty column list."""
        return []

    def _query_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """Return empty index list."""
        return []

    def _query_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """Return empty foreign key list."""
        return []

    def _query_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """Return empty view list."""
        return []

    def _query_view_info(self, view_name: str, schema: Optional[str] = None) -> Optional[ViewInfo]:
        """Return None as no views exist in dummy backend."""
        return None

    def _query_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """Return empty trigger list."""
        return []


class AsyncDummyIntrospectionMixin(AsyncIntrospectionMixin):
    """Async dummy introspection mixin for AsyncDummyBackend.

    Provides mock implementations of introspection methods that return
    empty or minimal data. This is useful for testing SQL generation
    without requiring a real database connection.
    """

    async def _query_database_info(self) -> DatabaseInfo:
        """Return mock database info."""
        return DatabaseInfo(
            name="dummy",
            version="0.0.0",
            version_tuple=(0, 0, 0),
            vendor="Dummy",
            size_bytes=None,
        )

    async def _query_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """Return empty table list."""
        return []

    async def _query_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[TableInfo]:
        """Return None as no tables exist in dummy backend."""
        return None

    async def _query_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """Return empty column list."""
        return []

    async def _query_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """Return empty index list."""
        return []

    async def _query_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """Return empty foreign key list."""
        return []

    async def _query_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """Return empty view list."""
        return []

    async def _query_view_info(self, view_name: str, schema: Optional[str] = None) -> Optional[ViewInfo]:
        """Return None as no views exist in dummy backend."""
        return None

    async def _query_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """Return empty trigger list."""
        return []


class DummyBackend(DummyIntrospectionMixin, StorageBackend):
    """
    A dummy backend for ActiveRecord that generates SQL without connecting to a real database.
    All operations requiring a database connection will raise NotImplementedError.
    """

    def __init__(self, connection_config: Optional[ConnectionConfig] = None, **kwargs):
        # Ensure a default logger for DummyBackend if not explicitly provided
        if "logger" not in kwargs:
            kwargs["logger"] = logging.getLogger("dummy_backend")
        super().__init__(connection_config=connection_config or ConnectionConfig(), **kwargs)
        self._dialect = DummyDialect()

    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple[SQLTypeAdapter, Type]]:
        """
        Provides empty adapter suggestions as this backend does not perform real type conversion.
        """
        return {}

    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def connect(self) -> None:
        raise NotImplementedError(DUMMY_BACKEND_ERROR_MSG)

    def disconnect(self) -> None:
        pass  # Disconnecting a dummy backend is a no-op

    def ping(self, reconnect: bool = True) -> bool:
        raise NotImplementedError(DUMMY_BACKEND_ERROR_MSG)

    def _handle_error(self, error: Exception) -> None:
        # Re-raise the NotImplementedError or any other error that occurred.
        # This backend doesn't map specific database errors.
        if isinstance(error, NotImplementedError):
            raise error
        raise DatabaseError(f"An unexpected error occurred in DummyBackend: {error}") from error

    def get_server_version(self) -> Tuple[int, int, int]:
        # Return a dummy version, as this backend doesn't connect to a real server.
        return (0, 0, 0)  # Indicates a dummy/mock version

    def introspect_and_adapt(self) -> None:
        """Introspect backend and adapt backend instance.

        For DummyBackend, no adaptation is needed as it doesn't connect to a real server.
        This method exists to satisfy the interface contract.
        """
        pass

    def _get_cursor(self) -> Any:
        raise NotImplementedError(DUMMY_BACKEND_ERROR_MSG)

    def _execute_query(self, cursor: Any, sql: str, params: Optional[Tuple]) -> Any:
        raise NotImplementedError(DUMMY_BACKEND_ERROR_MSG)

    def _handle_auto_commit(self) -> None:
        pass  # No real database, so no commit needed

    @property
    def transaction_manager(self) -> TransactionManager:
        raise NotImplementedError(DUMMY_BACKEND_ERROR_MSG)


# Async Dummy Backend
class AsyncDummyBackend(AsyncDummyIntrospectionMixin, AsyncStorageBackend):
    """
    An async dummy backend for ActiveRecord that generates SQL without connecting to a real database.
    All operations requiring a database connection will raise NotImplementedError.
    """

    def __init__(self, connection_config: Optional[ConnectionConfig] = None, **kwargs):
        # Ensure a default logger for AsyncDummyBackend if not explicitly provided
        if "logger" not in kwargs:
            kwargs["logger"] = logging.getLogger("async_dummy_backend")
        super().__init__(connection_config=connection_config or ConnectionConfig(), **kwargs)
        self._dialect = DummyDialect()

    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple[SQLTypeAdapter, Type]]:
        return {}

    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    async def connect(self) -> None:
        raise NotImplementedError(ASYNC_DUMMY_BACKEND_ERROR_MSG)

    async def disconnect(self) -> None:
        pass  # Disconnecting a dummy backend is a no-op

    async def ping(self, reconnect: bool = True) -> bool:
        raise NotImplementedError(ASYNC_DUMMY_BACKEND_ERROR_MSG)

    async def _handle_error(self, error: Exception) -> None:
        if isinstance(error, NotImplementedError):
            raise error
        raise DatabaseError(f"An unexpected error occurred in AsyncDummyBackend: {error}") from error

    async def get_server_version(self) -> Tuple[int, int, int]:
        return (0, 0, 0)

    async def introspect_and_adapt(self) -> None:
        """Introspect backend and adapt backend instance.

        For AsyncDummyBackend, no adaptation is needed as it doesn't connect to a real server.
        This method exists to satisfy the interface contract.
        """
        pass

    async def _get_cursor(self) -> Any:
        raise NotImplementedError(ASYNC_DUMMY_BACKEND_ERROR_MSG)

    async def _execute_query(self, cursor: Any, sql: str, params: Optional[Tuple]) -> Any:
        raise NotImplementedError(ASYNC_DUMMY_BACKEND_ERROR_MSG)

    async def _handle_auto_commit(self) -> None:
        pass  # No real database, so no commit needed

    @property
    def transaction_manager(self) -> AsyncTransactionManager:
        raise NotImplementedError(ASYNC_DUMMY_BACKEND_ERROR_MSG)
