# src/rhosocial/activerecord/backend/base/__init__.py
from abc import ABC, abstractmethod

from .base import StorageBackendBase
from .connection import AsyncConnectionMixin, ConnectionMixin
from .execution import AsyncExecutionMixin, ExecutionMixin
from .hooks import AsyncExecutionHooksMixin, ExecutionHooksMixin
from .logging import LoggingMixin
from .operations import AsyncSQLOperationsMixin, SQLOperationsMixin
from .result_processing import ResultProcessingMixin
from .returning import ReturningClauseMixin
from .sql_building import SQLBuildingMixin
from .transaction_management import (
    AsyncTransactionManagementMixin,
    TransactionManagementMixin,
)
from .type_adaption import AsyncTypeAdaptionMixin, TypeAdaptionMixin


class StorageBackend(
    StorageBackendBase,
    LoggingMixin,
    TypeAdaptionMixin,
    SQLBuildingMixin,
    ReturningClauseMixin,
    ResultProcessingMixin,
    SQLOperationsMixin,
    ExecutionMixin,
    ExecutionHooksMixin,
    ConnectionMixin,
    TransactionManagementMixin,
    ABC,
):
    """Synchronous storage backend abstract base class."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    @abstractmethod
    def connect(self) -> None: ...
    @abstractmethod
    def disconnect(self) -> None: ...
    @abstractmethod
    def ping(self, reconnect: bool = True) -> bool: ...
    @abstractmethod
    def _handle_error(self, error: Exception) -> None: ...
    @abstractmethod
    def get_server_version(self) -> tuple: ...


class AsyncStorageBackend(
    StorageBackendBase,
    LoggingMixin,
    AsyncTypeAdaptionMixin,
    SQLBuildingMixin,
    ReturningClauseMixin,
    ResultProcessingMixin,
    AsyncSQLOperationsMixin,
    AsyncExecutionMixin,
    AsyncExecutionHooksMixin,
    AsyncConnectionMixin,
    AsyncTransactionManagementMixin,
    ABC,
):
    """Asynchronous storage backend abstract base class."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    @abstractmethod
    async def connect(self) -> None: ...
    @abstractmethod
    async def disconnect(self) -> None: ...
    @abstractmethod
    async def ping(self, reconnect: bool = True) -> bool: ...
    @abstractmethod
    async def _handle_error(self, error: Exception) -> None: ...
    @abstractmethod
    async def get_server_version(self) -> tuple: ...


__all__ = [
    "StorageBackend",
    "AsyncStorageBackend",
    "StorageBackendBase",
    "LoggingMixin",
    "TypeAdaptionMixin",
    "AsyncTypeAdaptionMixin",
    "SQLBuildingMixin",
    "ReturningClauseMixin",
    "ResultProcessingMixin",
    "SQLOperationsMixin",
    "AsyncSQLOperationsMixin",
    "ExecutionMixin",
    "AsyncExecutionMixin",
    "ExecutionHooksMixin",
    "AsyncExecutionHooksMixin",
    "ConnectionMixin",
    "AsyncConnectionMixin",
    "TransactionManagementMixin",
    "AsyncTransactionManagementMixin",
]