# src/rhosocial/activerecord/backend/base/__init__.py
from abc import ABC, abstractmethod

from typing import Optional

from ..dialect.exceptions import UnsupportedFeatureError
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
from .batch_execution import AsyncBatchExecutionMixin, BatchExecutionMixin


class StorageBackend(
    StorageBackendBase,
    LoggingMixin,
    TypeAdaptionMixin,
    SQLBuildingMixin,
    ReturningClauseMixin,
    ResultProcessingMixin,
    SQLOperationsMixin,
    ExecutionMixin,
    BatchExecutionMixin,
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
    @abstractmethod
    def introspect_and_adapt(self) -> None: ...

    def get_current_schema(self) -> Optional[str]:
        """Return the namespace an unqualified name resolves against.

        A backend that can ask the server overrides this -- ``current_schema()``
        on PostgreSQL, ``SCHEMA_NAME()`` on SQL Server,
        ``SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA')`` on Oracle, and the database
        itself where there is no schema namespace of its own (MySQL, MariaDB,
        ClickHouse, Snowflake).

        Raises:
            UnsupportedFeatureError: The backend has no server-side notion to
                report, which is the case for SQLite and BigQuery. Default rather
                than abstract because that answer is legitimate: a backend
                without a namespace does not have to invent a method to say so,
                and requiring one would break every backend outside this
                repository for no gain.
        """
        raise UnsupportedFeatureError(
            dialect_name=self.dialect.name,
            feature_name="get_current_schema",
            suggestion=(
                "The server has no namespace to report; qualify names "
                "explicitly instead."
            ),
        )


class AsyncStorageBackend(
    StorageBackendBase,
    LoggingMixin,
    AsyncTypeAdaptionMixin,
    SQLBuildingMixin,
    ReturningClauseMixin,
    ResultProcessingMixin,
    AsyncSQLOperationsMixin,
    AsyncExecutionMixin,
    AsyncBatchExecutionMixin,
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
    @abstractmethod
    async def introspect_and_adapt(self) -> None: ...

    async def get_current_schema(self) -> Optional[str]:
        """Return the namespace an unqualified name resolves against.

        The async counterpart of :meth:`StorageBackend.get_current_schema`, with
        the same default: a backend that cannot ask the server inherits the
        error instead of having to provide one.

        Raises:
            UnsupportedFeatureError: The backend has no server-side notion to
                report.
        """
        raise UnsupportedFeatureError(
            dialect_name=self.dialect.name,
            feature_name="get_current_schema",
            suggestion=(
                "The server has no namespace to report; qualify names "
                "explicitly instead."
            ),
        )


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
    "BatchExecutionMixin",
    "AsyncBatchExecutionMixin",
    "ExecutionHooksMixin",
    "AsyncExecutionHooksMixin",
    "ConnectionMixin",
    "AsyncConnectionMixin",
    "TransactionManagementMixin",
    "AsyncTransactionManagementMixin",
]
