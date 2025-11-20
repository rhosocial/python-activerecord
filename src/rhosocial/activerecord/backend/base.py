# src/rhosocial/activerecord/backend/base.py
"""
Refactored backend architecture with functional composition.

Architecture principles:
1. Functional Mixins: Shared logic grouped by feature
2. Composition over Inheritance: No sync->async inheritance
3. StorageBackend and AsyncStorageBackend are parallel ABCs
4. Each composes the same set of functional mixins
"""

import inspect
import logging
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager, asynccontextmanager
from typing import Any, Dict, Generator, Optional, Tuple, List, Union, AsyncGenerator, Sequence, Type

from .capabilities import DatabaseCapabilities
from .config import ConnectionConfig
from .dialect import SQLDialectBase, SQLExpressionBase, SQLBuilder, ReturningOptions
from .errors import ReturningNotSupportedError
from .transaction import TransactionManager, AsyncTransactionManager
from .typing import QueryResult, DatabaseType
from .type_registry import TypeRegistry
from .type_adapter import (
    SQLTypeAdapter,
    DateTimeAdapter,
    JSONAdapter,
    UUIDAdapter,
    EnumAdapter,
    BooleanAdapter,
    DecimalAdapter,
)


# ============================================================================
# Functional Mixins - Shared Logic Grouped by Feature
# Note: Mixins do NOT define __init__ to avoid MRO issues
# All initialization is done in StorageBackendBase
# ============================================================================

class LoggingMixin:
    """Mixin for logging functionality."""

    @property
    def logger(self) -> logging.Logger:
        """Get current logger instance."""
        return self._logger

    @logger.setter
    def logger(self, logger: Optional[logging.Logger]) -> None:
        """Set logger instance."""
        if logger is not None and not isinstance(logger, logging.Logger):
            raise ValueError("logger must be an instance of logging.Logger")
        self._logger = logger or logging.getLogger('storage')

    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log message using current logger."""
        current_frame = inspect.currentframe().f_back
        stack_level = 1
        while current_frame:
            if current_frame.f_globals['__name__'] != 'storage':
                break
            current_frame = current_frame.f_back
            stack_level += 1
        if current_frame:
            stack_level += 1
        self.logger.log(level, msg, *args, stacklevel=stack_level, **kwargs)


class CapabilityMixin:
    """Mixin for database capability management."""

    @property
    def capabilities(self) -> DatabaseCapabilities:
        """Get database capabilities."""
        if self._capabilities is None:
            self._capabilities = self._initialize_capabilities()
        return self._capabilities

    @abstractmethod
    def _initialize_capabilities(self) -> DatabaseCapabilities:
        """Initialize database capabilities (to be implemented by concrete backends)."""
        pass


class TypeAdaptionMixin:
    """
    Provides robust, decoupled type adaptation capabilities for storage backends.

    Architectural Principle: Separation of Concerns
    -----------------------------------------------
    This mixin's methods are designed to be called *explicitly by the
    application/ORM layer* (the "caller") and are decoupled from the backend's
    own execution methods (`insert`, `execute`, etc.).

    Why this separation?
    This design provides critical flexibility. For instance, in a database
    migration scenario, data read from one database is already in a
    database-compatible format. It can be passed directly to another database's
    `insert` or `execute_many` method without any intermediate Python-level
    type conversion, maximizing performance. The execution methods are "dumb"
    by design and trust that the caller has provided compatible data.

    It plays a dual role for the caller:
    1.  **`prepare_parameters` (Input Preparation)**: The caller uses this to
        convert Python-native types (like `datetime`) into database-compatible
        types before passing them to methods like `insert()` or `execute()`.
    2.  **`_process_result_set` (Output Processing)**: Used internally by `execute()`
        to convert data retrieved from the database (e.g., from a `SELECT` or
        `RETURNING` clause) back into Python types, guided by the
        `column_adapters` parameter.
    3.  **`adapter_registry` (Discovery)**: A public registry to help callers
        discover and retrieve available `SQLTypeAdapter` instances. The core
        methods (`prepare_parameters`, `_process_result_set`) are decoupled
        from this and rely on the adapters explicitly passed to them.
    """
    # Mixins do NOT define __init__ to avoid MRO issues.
    # Initialization is handled in StorageBackendBase.

    def _register_default_adapters(self) -> None:
        adapters = [
            DateTimeAdapter(), JSONAdapter(), UUIDAdapter(), EnumAdapter(),
            BooleanAdapter(), DecimalAdapter(),
        ]
        for adapter in adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type)
        self.logger.debug("Registered all standard type adapters.")

    def prepare_parameters(
        self,
        params: Union[Dict[str, Any], Sequence[Any]],
        param_adapters: Union[Dict[str, Tuple[SQLTypeAdapter, Type]], Sequence[Optional[Tuple[SQLTypeAdapter, Type]]]]
    ) -> Union[Dict[str, Any], Tuple[Any, ...]]:
        """
        Converts Python parameters to database-compatible types based on the provided adapters.

        This method follows the principle of complete decoupling and does not access
        `self.adapter_registry`. All information required for conversion (adapter instance
        and target database type) must be explicitly provided by the caller through
        the `param_adapters` parameter.

        :param params: A dictionary or sequence containing the original Python values.
        :param param_adapters: A dictionary or sequence corresponding to the structure of `params`.
               - For a dictionary: `{'param_name': (adapter_instance, target_db_type)}`
               - For a sequence: `[(adapter_instance, target_db_type), ...]`
        :return: A dictionary or tuple containing the converted values.
        """
        if not params or not param_adapters:
            return tuple(params) if isinstance(params, Sequence) else params

        if isinstance(params, dict) and isinstance(param_adapters, dict):
            converted_params = params.copy()
            for key, adapter_info in param_adapters.items():
                if key in converted_params and adapter_info and converted_params[key] is not None:
                    adapter, db_type = adapter_info
                    original_value = converted_params[key]
                    converted_params[key] = adapter.to_database(original_value, db_type)
            return converted_params

        if isinstance(params, Sequence) and isinstance(param_adapters, Sequence):
            if len(params) != len(param_adapters):
                raise ValueError("Length of params and param_adapters must match for sequence-based conversion.")

            converted_params = list(params)
            for i, adapter_info in enumerate(param_adapters):
                if adapter_info and converted_params[i] is not None:
                    adapter, db_type = adapter_info
                    original_value = converted_params[i]
                    converted_params[i] = adapter.to_database(original_value, db_type)
            return tuple(converted_params)

        raise TypeError("Unsupported types for params and param_adapters. "
                        "Provide either two dicts or two sequences.")

    def _process_result_set(
        self,
        cursor,
        is_select: bool,
        need_returning: bool,
        column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None
    ) -> Optional[List[Dict]]:
        """
        Converts the result set returned from the database to specified Python types
        based on the provided adapters.

        This method is part of the `execute` call stack and follows the principle of
        complete decoupling by not accessing `self.adapter_registry`. All information
        required for conversion (adapter instance and target Python type) must be
        explicitly provided by the caller through the `column_adapters` parameter.

        :param cursor: The database cursor object.
        :param is_select: Whether it is a SELECT query.
        :param need_returning: Whether to process the result of a RETURNING clause.
        :param column_adapters: A dictionary mapping column names to `(adapter_instance, target_py_type)` tuples.
        :return: A list of dictionaries containing the converted values.
        """
        if not (is_select or need_returning): return None
        try:
            rows = cursor.fetchall()
            if not rows: return []
            column_names = [desc[0] for desc in cursor.description]
            column_adapters = column_adapters or {}
            converted_results = []
            for row in rows:
                converted_row = {}
                row_dict = dict(zip(column_names, row))
                for key, value in row_dict.items():
                    if value is None:
                        converted_row[key] = None
                        continue

                    adapter_info = column_adapters.get(key)
                    if adapter_info:
                        adapter, py_type = adapter_info
                        converted_row[key] = adapter.from_database(value, py_type)
                    else:
                        converted_row[key] = value
                converted_results.append(converted_row)
            return converted_results
        except Exception as e:
            self.logger.error(f"Error processing result set: {str(e)}", exc_info=True)
            raise

    @abstractmethod
    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple[SQLTypeAdapter, Type]]:
        """
        Provides default type adapter suggestions to the consuming application layer.

        Concrete backend implementations must override this method to provide
        their specific suggestions. These suggestions guide the application
        layer on how to convert Python types to database-compatible types
        and vice-versa, based on the backend's `TypeRegistry`.
        
        It's important to note that these suggestions represent a curated default view and
        may not expose every adapter registered within the backend's internal `TypeRegistry`
        (e.g., if multiple `db_type` mappings exist for a single `py_type`). The consuming
        layer should be aware of this potential divergence.

        Returns:
            Dict[Type, Tuple[SQLTypeAdapter, Type]]: A dictionary where keys are
            original Python types (`TypeRegistry`'s `py_type`), and values are
            tuples containing a `SQLTypeAdapter` instance and the target
            Python type (`TypeRegistry`'s `db_type`) expected by the driver.
        """
        pass


class AsyncTypeAdaptionMixin(TypeAdaptionMixin):
    """
    Provides asynchronous type adaptation for DML operations.

    This mixin overrides `_process_result_set` to make it an async method,
    handling asynchronous cursor operations like `fetchall()`.
    `prepare_parameters` remains synchronous as it's a CPU-bound operation
    and is inherited directly from `TypeAdaptionMixin`.
    """
    async def _process_result_set(
        self,
        cursor,
        is_select: bool,
        need_returning: bool,
        column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None
    ) -> Optional[List[Dict]]:
        if not (is_select or need_returning): return None
        try:
            rows = await cursor.fetchall() # Make fetchall awaitable
            if not rows: return []
            column_names = [desc[0].strip('"') for desc in cursor.description]
            column_adapters = column_adapters or {}
            converted_results = []
            for row in rows:
                converted_row = {}
                # aiosqlite.Row objects behave like sqlite3.Row, allowing dict-like access
                # and iterable behavior for zip.
                row_dict = dict(zip(column_names, row))
                for key, value in row_dict.items():
                    if value is None:
                        converted_row[key] = None
                        continue

                    adapter_info = column_adapters.get(key)
                    if adapter_info:
                        adapter, py_type = adapter_info
                        converted_row[key] = adapter.from_database(value, py_type)
                    else:
                        converted_row[key] = value
                converted_results.append(converted_row)
            return converted_results
        except Exception as e:
            self.logger.error(f"Error processing async result set: {str(e)}", exc_info=True)
            raise



class SQLBuildingMixin:
    """Mixin for SQL building operations."""

    def create_expression(self, expression: str) -> SQLExpressionBase:
        """Create SQL expression."""
        return self.dialect.create_expression(expression)

    def build_sql(self, sql: str, params: Optional[Tuple] = None) -> Tuple[str, Tuple]:
        """Build SQL and parameters."""
        builder = SQLBuilder(self.dialect)
        return builder.build(sql, params)

    def _prepare_sql_and_params(self, sql: str, params: Optional[Tuple]) -> Tuple[str, Optional[Tuple]]:
        """Process SQL and parameters for execution."""
        if params:
            return self.build_sql(sql, params)
        return sql, params


class QueryAnalysisMixin:
    """Mixin for SQL query analysis."""

    def _get_statement_type(self, sql: str) -> str:
        """Get the SQL statement type (SELECT, INSERT, etc.)."""
        sql_stripped = sql.strip()
        if not sql_stripped:
            return ""
        parts = sql_stripped.split(None, 1)
        return parts[0].upper()

    def _is_select_statement(self, stmt_type: str) -> bool:
        """Check if statement is a SELECT query or similar read-only operation."""
        return stmt_type in ("SELECT", "EXPLAIN", "SHOW", "DESCRIBE", "DESC", "PRAGMA")

    def _is_dml_statement(self, stmt_type: str) -> bool:
        """Check if statement is a DML operation (INSERT, UPDATE, DELETE)."""
        return stmt_type in ("INSERT", "UPDATE", "DELETE")


class ReturningClauseMixin:
    """Mixin for RETURNING clause processing."""

    def _process_returning_options(self,
                                   returning: Optional[Union[bool, List[str], ReturningOptions]]) -> ReturningOptions:
        """Process returning parameter into ReturningOptions object."""
        if returning is None:
            return ReturningOptions(enabled=False)
        elif isinstance(returning, bool):
            return ReturningOptions.from_legacy(returning)
        elif isinstance(returning, list):
            return ReturningOptions.columns_only(returning)
        elif isinstance(returning, ReturningOptions):
            return returning
        else:
            raise ValueError(f"Unsupported returning type: {type(returning)}")

    def _prepare_returning_clause(self, sql: str, options: ReturningOptions, stmt_type: str) -> str:
        """Check compatibility and format RETURNING clause."""
        handler = self.dialect.returning_handler
        if not handler.is_supported and not options.force:
            error_msg = (
                f"RETURNING clause not supported by this database. "
                f"Use force=True to attempt anyway if you understand the limitations."
            )
            self.log(logging.WARNING, error_msg)
            raise ReturningNotSupportedError(error_msg)

        self._check_returning_compatibility(options)

        if options.has_column_specification():
            returning_clause = handler.format_advanced_clause(
                options.columns,
                options.expressions,
                options.aliases,
                options.dialect_options
            )
        else:
            returning_clause = handler.format_clause(None)

        sql += " " + returning_clause
        self.log(logging.DEBUG, f"Added RETURNING clause: {sql}")
        return sql

    def _check_returning_compatibility(self, options: ReturningOptions) -> None:
        """Perform database-specific compatibility checks (to be overridden)."""
        pass


class ResultProcessingMixin:
    """Mixin for query result processing."""

    def _log_query_completion(self, stmt_type: str, cursor, data: Optional[List[Dict]], duration: float) -> None:
        """Log query completion metrics."""
        if stmt_type in ("INSERT", "UPDATE", "DELETE"):
            rowcount = getattr(cursor, 'rowcount', 0)
            lastrowid = getattr(cursor, 'lastrowid', None)
            self.log(logging.INFO,
                     f"{stmt_type} affected {rowcount} rows, "
                     f"last_insert_id={lastrowid}, duration={duration:.3f}s")
        elif stmt_type in ("SELECT", "EXPLAIN", "SHOW", "DESCRIBE", "DESC"):
            row_count = len(data) if data is not None else 0
            self.log(logging.INFO, f"{stmt_type} returned {row_count} rows, duration={duration:.3f}s")

    def _build_query_result(self, cursor, data: Optional[List[Dict]], duration: float) -> QueryResult:
        """Build QueryResult object from execution results."""
        return QueryResult(
            data=data,
            affected_rows=getattr(cursor, 'rowcount', 0),
            last_insert_id=getattr(cursor, 'lastrowid', None),
            duration=duration
        )


class SQLOperationsMixin:
    """Mixin for high-level SQL operations (INSERT, UPDATE, DELETE)."""

    def insert(self,
               table: str,
               data: Dict,
               returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
               column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None,
               auto_commit: Optional[bool] = True,
               primary_key: Optional[str] = None) -> QueryResult:
        """
        Inserts a record into the database.

        Args:
            table (str): The name of the table to insert into.
            data (Dict): A dictionary of column names to values.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible. This method will NOT perform any type
                adaptation on inputs. The caller is responsible for pre-processing
                complex Python types (e.g., `datetime`, `UUID`) into database-native
                types, typically by using the `prepare_parameters` method from
                `TypeAdaptionMixin`.
            returning (Optional[Union[bool, List[str], ReturningOptions]]):
                Options for the RETURNING clause to get data back from the insert
                statement.
            column_adapters (Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]]):
                A map used for processing the output data if a RETURNING clause is used.
            auto_commit (Optional[bool]): If True, commits the transaction if one
                is not already active. Defaults to True.
            primary_key (Optional[str]): The name of the primary key field.

        Returns:
            QueryResult: A QueryResult object containing the results of the operation.
        """
        cleaned_data = {
            k.strip('"').strip('`'): v
            for k, v in data.items()
        }

        fields = [self.dialect.format_identifier(field) for field in cleaned_data.keys()]
        values = list(cleaned_data.values())
        placeholders = [self.dialect.get_placeholder() for _ in fields]

        sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(placeholders)})"

        result = self.execute(sql, tuple(values), returning, column_adapters)

        if auto_commit:
            self._handle_auto_commit_if_needed()

        if returning and result.data:
            cleaned_data = []
            for row in result.data:
                cleaned_row = {
                    k.strip('"').strip('`'): v
                    for k, v in row.items()
                }
                cleaned_data.append(cleaned_row)
            result.data = cleaned_data

        return result

    def update(self,
               table: str,
               data: Dict,
               where: str,
               params: Tuple,
               returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
               column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None,
               auto_commit: bool = True) -> QueryResult:
        """
        Updates records in the database.

        Args:
            table (str): The name of the table to update.
            data (Dict): A dictionary of column names to new values.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible. This method will NOT perform any type
                adaptation on inputs.
            where (str): The WHERE clause for the update statement.
            params (Tuple): A tuple of parameters for the WHERE clause.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible.
            returning (Optional[Union[bool, List[str], ReturningOptions]]):
                Options for a RETURNING clause.
            column_adapters (Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]]):
                A map used for processing output from a RETURNING clause.
            auto_commit (bool): If True, commits the transaction if not already active.

        Returns:
            QueryResult: A QueryResult object containing the results of the operation.
        """
        set_items = [f"{self.dialect.format_identifier(k)} = {self.dialect.get_placeholder()}"
                     for k in data.keys()]
        values = list(data.values())

        sql = f"UPDATE {table} SET {','.join(set_items)} WHERE {where}"

        result = self.execute(sql, tuple(values) + params, returning, column_adapters)

        if auto_commit:
            self._handle_auto_commit_if_needed()

        return result

    def delete(self,
               table: str,
               where: str,
               params: Tuple,
               returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
               column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None,
               auto_commit: bool = True) -> QueryResult:
        """
        Deletes records from the database.

        Args:
            table (str): The name of the table to delete from.
            where (str): The WHERE clause for the delete statement.
            params (Tuple): A tuple of parameters for the WHERE clause.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible.
            returning (Optional[Union[bool, List[str], ReturningOptions]]):
                Options for a RETURNING clause.
            column_adapters (Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]]):
                A map used for processing output from a RETURNING clause.
            auto_commit (bool): If True, commits the transaction if not already active.

        Returns:
            QueryResult: A QueryResult object containing the results of the operation.
        """
        sql = f"DELETE FROM {table} WHERE {where}"

        result = self.execute(sql, params, returning, column_adapters)

        if auto_commit:
            self._handle_auto_commit_if_needed()

        return result


class AsyncSQLOperationsMixin:
    """Mixin for high-level asynchronous SQL operations."""

    async def insert(self,
                     table: str,
                     data: Dict,
                     returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
                     column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None,
                     auto_commit: Optional[bool] = True,
                     primary_key: Optional[str] = None) -> QueryResult:
        """
        Inserts a record into the database asynchronously.

        Args:
            table: The name of the table to insert into.
            data: A dictionary of column names to values. IMPORTANT: These values
                are expected to be pre-adapted and database-compatible. This
                method will not perform any type adaptation on inputs.
            returning: Options for the RETURNING clause to get data back from
                the insert statement.
            column_adapters: A map used for processing the output data if a
                RETURNING clause is used.
            auto_commit: If True, commits the transaction if one is not already active.
            primary_key: The name of the primary key field.

        Returns:
            A QueryResult object containing the results of the operation.
        """
        cleaned_data = {
            k.strip('"').strip('`'): v
            for k, v in data.items()
        }

        fields = [self.dialect.format_identifier(field) for field in cleaned_data.keys()]
        values = list(cleaned_data.values())
        placeholders = [self.dialect.get_placeholder() for _ in fields]

        sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(placeholders)})"

        result = await self.execute(sql, tuple(values), returning, column_adapters)

        if auto_commit:
            await self._handle_auto_commit_if_needed()

        if returning and result.data:
            cleaned_data = []
            for row in result.data:
                cleaned_row = {
                    k.strip('"').strip('`'): v
                    for k, v in row.items()
                }
                cleaned_data.append(cleaned_row)
            result.data = cleaned_data

        return result

    async def update(self,
                     table: str,
                     data: Dict,
                     where: str,
                     params: Tuple,
                     returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
                     column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None,
                     auto_commit: bool = True) -> QueryResult:
        """
        Updates records in the database asynchronously.

        Args:
            table (str): The name of the table to update.
            data (Dict): A dictionary of column names to new values.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible. This method will NOT perform any type
                adaptation on inputs.
            where (str): The WHERE clause for the update statement.
            params (Tuple): A tuple of parameters for the WHERE clause.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible.
            returning (Optional[Union[bool, List[str], ReturningOptions]]):
                Options for a RETURNING clause.
            column_adapters (Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]]):
                A map used for processing output from a RETURNING clause.
            auto_commit (bool): If True, commits the transaction if not already active.

        Returns:
            QueryResult: A QueryResult object containing the results of the operation.
        """
        set_items = [f"{self.dialect.format_identifier(k)} = {self.dialect.get_placeholder()}"
                     for k in data.keys()]
        values = list(data.values())

        sql = f"UPDATE {table} SET {','.join(set_items)} WHERE {where}"

        result = await self.execute(sql, tuple(values) + params, returning, column_adapters)

        if auto_commit:
            await self._handle_auto_commit_if_needed()

        return result

    async def delete(self,
                     table: str,
                     where: str,
                     params: Tuple,
                     returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
                     column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None,
                     auto_commit: bool = True) -> QueryResult:
        """
        Deletes records from the database asynchronously.

        Args:
            table: The name of the table to delete from.
            where: The WHERE clause for the delete statement.
            params: A tuple of parameters for the WHERE clause. IMPORTANT: These
                values are expected to be pre-adapted and database-compatible.
            returning: Options for a RETURNING clause.
            column_adapters: A map used for processing output from a RETURNING clause.
            auto_commit: If True, commits the transaction if not already active.

        Returns:
            A QueryResult object containing the results of the operation.
        """
        sql = f"DELETE FROM {table} WHERE {where}"

        result = await self.execute(sql, params, returning, column_adapters)

        if auto_commit:
            await self._handle_auto_commit_if_needed()

        return result


# ============================================================================
# Base Configuration Class
# ============================================================================

class StorageBackendBase(ABC):
    """Minimal base for configuration and connection state only."""

    def _register_default_adapters(self) -> None:
        adapters = [
            DateTimeAdapter(), JSONAdapter(), UUIDAdapter(), EnumAdapter(),
            BooleanAdapter(), DecimalAdapter(),
        ]
        for adapter in adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type)
        self.logger.debug("Registered all standard type adapters.")

    def __init__(self, **kwargs) -> None:
        """Initialize storage backend with all required attributes."""
        # Configuration
        if "connection_config" not in kwargs or kwargs["connection_config"] is None:
            self.config = ConnectionConfig(**kwargs)
        else:
            self.config = kwargs["connection_config"]

        # Connection state
        self._connection = None
        self._transaction_level = 0
        self._transaction_manager = None
        self._cursor = None
        self._server_version_cache = None

        # Logger (for LoggingMixin)
        self._logger: Optional[logging.Logger] = kwargs.get('logger', logging.getLogger('storage'))

        # Capabilities (for CapabilityMixin)
        self._capabilities = None

        # Type Adaptation (for TypeAdaptionMixin)
        # Architectural Note: This registry is completely independent of the dialect.
        # It maps (Python Type, DBAPI Type) to a SQLTypeAdapter.
        self.adapter_registry = TypeRegistry()
        self._register_default_adapters()
        self.logger.info("Initialized TypeAdaptionMixin with SQLTypeAdapter registry.")

    @property
    @abstractmethod
    def dialect(self) -> SQLDialectBase:
        """Get SQL dialect."""
        pass


# ============================================================================
# Synchronous Storage Backend (Composition of all mixins)
# ============================================================================

class StorageBackend(
    StorageBackendBase,
    LoggingMixin,
    CapabilityMixin,
    TypeAdaptionMixin,
    SQLBuildingMixin,
    QueryAnalysisMixin,
    ReturningClauseMixin,
    ResultProcessingMixin,
    SQLOperationsMixin,
    ABC
):
    """
    Synchronous storage backend abstract base class.

    Composes all functional mixins to provide full backend capabilities.
    Concrete backends (SQLite, MySQL, PostgreSQL) inherit from this.
    """

    def __init__(self, **kwargs) -> None:
        """Initialize all mixin components."""
        super().__init__(**kwargs)

    # ========================================================================
    # Abstract Methods - Must be implemented by concrete backends
    # ========================================================================

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def ping(self, reconnect: bool = True) -> bool:
        """Check if connection is valid."""
        pass

    @abstractmethod
    def _handle_error(self, error: Exception) -> None:
        """Handle database errors."""
        pass

    @abstractmethod
    def get_server_version(self) -> tuple:
        """Get database server version as (major, minor, patch)."""
        pass

    # ========================================================================
    # Connection Management
    # ========================================================================

    @property
    def connection(self) -> Any:
        """Get current connection."""
        if self._connection is None:
            self.connect()
        return self._connection

    # ========================================================================
    # Core Execute Method - Template Method Pattern
    # ========================================================================

    def execute(
            self,
            sql: str,
            params: Optional[Tuple] = None,
            returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
            column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None) -> Optional[QueryResult]:
        """
        Executes a SQL statement.

        Args:
            sql (str): The SQL statement to execute.
            params (Optional[Tuple]): A tuple of parameters for the SQL statement.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible. No type adaptation is performed on `params`.
            returning (Optional[Union[bool, List[str], ReturningOptions]]):
                Options for the RETURNING clause to get data back from the statement.
            column_adapters (Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]]):
                A map used for processing the result set (e.g., from a SELECT or a
                RETURNING clause) to convert database types back into Python types.

        Architectural Note:
        -------------------
        This method is the low-level execution engine. It strictly separates
        input and output processing:
        - `params` (Input): This tuple is expected to contain values that are
          *already* database-compatible. No type adaptation is performed on
          `params`. The caller is responsible for pre-processing inputs,
          typically by using `prepare_parameters()`.
        - `column_adapters` (Output): This dictionary is used *only* for
          processing the result set (e.g., from a SELECT or a RETURNING
          clause) to convert database types back into Python types.
        """
        start_time = time.perf_counter()

        self.log(logging.DEBUG, f"Executing SQL: {sql}, parameters: {params}")

        try:
            # Ensure active connection
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            # Parse statement type
            stmt_type = self._get_statement_type(sql)
            is_select = self._is_select_statement(stmt_type)
            is_dml = self._is_dml_statement(stmt_type)

            # Process returning parameter
            returning_options = self._process_returning_options(returning)
            need_returning = bool(returning_options) and is_dml

            # Handle RETURNING clause if needed
            if need_returning:
                sql = self._prepare_returning_clause(sql, returning_options, stmt_type)

            # Get cursor
            cursor = self._get_cursor()

            # Process SQL and parameters (note: parameters are assumed to be pre-converted)
            final_sql, final_params = self._prepare_sql_and_params(sql, params)

            # Execute query
            cursor = self._execute_query(cursor, final_sql, final_params)

            # Process results
            data = self._process_result_set(cursor, is_select, need_returning, column_adapters)

            # Calculate duration
            duration = time.perf_counter() - start_time

            # Log completion
            self._log_query_completion(stmt_type, cursor, data, duration)

            # Build result
            result = self._build_query_result(cursor, data, duration)

            # Handle auto-commit
            self._handle_auto_commit_if_needed()

            return result

        except Exception as e:
            self.log(logging.ERROR, f"Error executing query: {str(e)}")
            return self._handle_execution_error(e)

    # ========================================================================
    # Hook Methods - Can be overridden by concrete backends
    # ========================================================================

    def _get_cursor(self):
        """Get or create a cursor for query execution."""
        return self._cursor or self._connection.cursor()

    def _execute_query(self, cursor, sql: str, params: Optional[Tuple]):
        """Execute the query with prepared SQL and parameters."""
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor

    def _handle_auto_commit_if_needed(self) -> None:
        """Handle auto-commit if not in transaction."""
        if not self.in_transaction:
            self._handle_auto_commit()

    def _handle_auto_commit(self) -> None:
        """Handle auto commit (to be overridden by concrete backends)."""
        pass

    def _handle_execution_error(self, error: Exception):
        """Handle database-specific errors during query execution."""
        self._handle_error(error)

    # ========================================================================
    # Batch Operations
    # ========================================================================

    def execute_many(self, sql: str, params_list: List[Tuple]) -> Optional[QueryResult]:
        """
        Executes a SQL statement against a list of parameter tuples.

        Args:
            sql: The SQL statement to execute.
            params_list: A list of tuples, where each tuple contains the
                parameters for one execution of the statement.

        IMPORTANT: This method adheres to the "separation of concerns" principle.
        The `params_list` is expected to be a list of tuples, where each value
        is already database-compatible. This method will NOT perform any type
        adaptation. The caller is responsible for pre-processing complex Python
        types, typically by using `prepare_parameters` on each set of parameters
        before creating `params_list`.

        Returns:
            A QueryResult object, typically containing only `affected_rows`
            and `duration`, as `executemany` does not return data.
        """
        self.log(logging.INFO, f"Executing batch operation: {sql} with {len(params_list)} parameter sets")
        start_time = time.perf_counter()
        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._get_cursor() # Reuse _get_cursor
            final_sql = self._prepare_sql_and_params(sql, None)[0] # Just need the SQL, params are in params_list

            cursor.executemany(final_sql, params_list) # Direct call to executemany
            duration = time.perf_counter() - start_time

            self._handle_auto_commit_if_needed()

            return QueryResult(
                affected_rows=cursor.rowcount,
                duration=duration
            )
        except Exception as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            return self._handle_execution_error(e)

    # ========================================================================
    # Fetch Operations
    # ========================================================================

    def fetch_one(self, sql: str, params: Optional[Tuple] = None,
                  column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None) -> Optional[Dict]:
        """
        Fetches a single record from the database.

        Args:
            sql (str): The SQL query to execute.
            params (Optional[Tuple]): A tuple of parameters for the query.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible.
            column_adapters (Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]]):
                A map used for processing the output data from the query.

        IMPORTANT: The `params` tuple is expected to contain values that are
        already database-compatible. The caller is responsible for pre-processing
        inputs, typically by using `prepare_parameters`. The `column_adapters`
        are used for processing the output.
        """
        result = self.execute(sql, params, ReturningOptions.all_columns(), column_adapters)
        return result.data[0] if result and result.data else None

    def fetch_all(self, sql: str, params: Optional[Tuple] = None,
                  column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None) -> List[Dict]:
        """
        Fetches all matching records from the database.

        Args:
            sql (str): The SQL query to execute.
            params (Optional[Tuple]): A tuple of parameters for the query.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible.
            column_adapters (Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]]):
                A map used for processing the output data from the query.

        IMPORTANT: The `params` tuple is expected to contain values that are
        already database-compatible. The caller is responsible for pre-processing
        inputs, typically by using `prepare_parameters`. The `column_adapters`
        are used for processing the output.
        """
        result = self.execute(sql, params, ReturningOptions.all_columns(), column_adapters)
        return result.data or []

    # ========================================================================
    # Transaction Management
    # ========================================================================

    @property
    @abstractmethod
    def transaction_manager(self) -> TransactionManager:
        """Get the transaction manager (to be implemented by concrete backends)."""
        pass

    def begin_transaction(self) -> None:
        """Begin transaction."""
        self.log(logging.INFO, "Beginning transaction")
        self.transaction_manager.begin()

    def commit_transaction(self) -> None:
        """Commit transaction."""
        self.log(logging.INFO, "Committing transaction")
        self.transaction_manager.commit()

    def rollback_transaction(self) -> None:
        """Rollback transaction."""
        self.log(logging.INFO, "Rolling back transaction")
        self.transaction_manager.rollback()

    @property
    def in_transaction(self) -> bool:
        """Check if in transaction."""
        is_active = self.transaction_manager.is_active if self._transaction_manager else False
        self.log(logging.DEBUG, f"Checking transaction status: {is_active}")
        return is_active

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Transaction context manager."""
        with self.transaction_manager.transaction() as t:
            yield t

    # ========================================================================
    # Context Manager Support
    # ========================================================================

    def __enter__(self):
        if not self._connection:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __del__(self):
        """Ensure resource cleanup on destruction."""
        self.disconnect()

    # ========================================================================
    # Properties
    # ========================================================================

    @property
    def supports_returning(self) -> bool:
        """Whether RETURNING clause is supported."""
        return False


# ============================================================================
# Asynchronous Storage Backend (Same composition, async methods)
# ============================================================================

class AsyncStorageBackend(
    StorageBackendBase,
    LoggingMixin,
    CapabilityMixin,
    AsyncTypeAdaptionMixin, # <--- Change this
    SQLBuildingMixin,
    QueryAnalysisMixin,
    ReturningClauseMixin,
    ResultProcessingMixin,
    AsyncSQLOperationsMixin,
    ABC
):
    """
    Asynchronous storage backend abstract base class.

    Composes the same functional mixins as StorageBackend.
    All I/O methods are async versions.
    """

    def __init__(self, **kwargs) -> None:
        """Initialize all mixin components."""
        super().__init__(**kwargs)

    # ========================================================================
    # Abstract Methods - Must be implemented by concrete async backends
    # ========================================================================

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection asynchronously."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection asynchronously."""
        pass

    @abstractmethod
    async def ping(self, reconnect: bool = True) -> bool:
        """Check if connection is valid asynchronously."""
        pass

    @abstractmethod
    async def _handle_error(self, error: Exception) -> None:
        """Handle database errors asynchronously."""
        pass

    @abstractmethod
    async def get_server_version(self) -> tuple:
        """Get database server version asynchronously."""
        pass

    # ========================================================================
    # Connection Management
    # ========================================================================

    @property
    async def connection(self) -> Any:
        """Get current connection asynchronously."""
        if self._connection is None:
            await self.connect()
        return self._connection

    # ========================================================================
    # Core Execute Method - Async Template Method Pattern
    # ========================================================================

    async def execute(
            self,
            sql: str,
            params: Optional[Tuple] = None,
            returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
            column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None) -> Optional[QueryResult]:
        """
        Executes a SQL statement asynchronously.

        Args:
            sql (str): The SQL statement to execute.
            params (Optional[Tuple]): A tuple of parameters for the SQL statement.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible. No type adaptation is performed on `params`.
            returning (Optional[Union[bool, List[str], ReturningOptions]]):
                Options for the RETURNING clause to get data back from the statement.
            column_adapters (Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]]):
                A map used for processing the result set (e.g., from a SELECT or a
                RETURNING clause) to convert database types back into Python types.

        Architectural Note:
        -------------------
        This method is the low-level execution engine. It strictly separates
        input and output processing:
        - `params` (Input): This tuple is expected to contain values that are
          *already* database-compatible. No type adaptation is performed on
          `params`. The caller is responsible for pre-processing inputs,
          typically by using `prepare_parameters()`.
        - `column_adapters` (Output): This dictionary is used *only* for
          processing the result set (e.g., from a SELECT or a RETURNING
          clause) to convert database types back into Python types.
        """
        start_time = time.perf_counter()

        self.log(logging.DEBUG, f"Executing SQL: {sql}, parameters: {params}")

        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                await self.connect()

            stmt_type = self._get_statement_type(sql)
            is_select = self._is_select_statement(stmt_type)
            is_dml = self._is_dml_statement(stmt_type)

            returning_options = self._process_returning_options(returning)
            need_returning = bool(returning_options) and is_dml

            if need_returning:
                sql = self._prepare_returning_clause(sql, returning_options, stmt_type)

            cursor = await self._get_cursor()

            final_sql, final_params = self._prepare_sql_and_params(sql, params)

            cursor = await self._execute_query(cursor, final_sql, final_params)

            data = await self._process_result_set(cursor, is_select, need_returning, column_adapters)

            duration = time.perf_counter() - start_time

            self._log_query_completion(stmt_type, cursor, data, duration)

            result = self._build_query_result(cursor, data, duration)

            await self._handle_auto_commit_if_needed()

            return result

        except Exception as e:
            self.log(logging.ERROR, f"Error executing query: {str(e)}")
            return await self._handle_execution_error(e)

    # ========================================================================
    # Hook Methods - Async versions
    # ========================================================================

    async def _get_cursor(self):
        """Get or create a cursor asynchronously."""
        return self._cursor or await self._connection.cursor()

    async def _execute_query(self, cursor, sql: str, params: Optional[Tuple]):
        """Execute query asynchronously."""
        if params:
            await cursor.execute(sql, params)
        else:
            await cursor.execute(sql)
        return cursor

    async def _handle_auto_commit_if_needed(self) -> None:
        """Handle auto-commit asynchronously."""
        if not self.in_transaction:
            await self._handle_auto_commit()

    @abstractmethod
    async def _handle_auto_commit(self) -> None:
        """Handle auto commit asynchronously (to be overridden by concrete backends)."""
        pass

    async def _handle_execution_error(self, error: Exception):
        """Handle database-specific errors during query execution."""
        await self._handle_error(error)

    # ========================================================================
    # Batch Operations
    # ========================================================================

    async def execute_many(self, sql: str, params_list: List[Union[Tuple, Dict]]) -> Optional[QueryResult]:
        """
        Executes a SQL statement against a list of parameter sets asynchronously.

        Args:
            sql: The SQL statement to execute.
            params_list: A list of parameter sets (tuples or dicts). Each set
                corresponds to one execution of the statement.

        IMPORTANT: This method adheres to the "separation of concerns" principle.
        The values within `params_list` are expected to be already
        database-compatible. This method will NOT perform any type adaptation.
        The caller is responsible for pre-processing complex Python types,
        typically by using `prepare_parameters` on each parameter set before
        creating `params_list`.

        Returns:
            A QueryResult object, typically containing only `affected_rows`
            and `duration`, as `executemany` does not return data.
        """
        self.log(logging.DEBUG, f"Executing many SQL: {sql}")
        start_time = time.perf_counter()

        try:
            if not self._connection:
                await self.connect()

            cursor = await self._get_cursor()
            await cursor.executemany(sql, params_list)
            await self._handle_auto_commit_if_needed()

            duration = time.perf_counter() - start_time
            return QueryResult(
                affected_rows=cursor.rowcount,
                duration=duration
            )
        except Exception as e:
            self.log(logging.ERROR, f"Error executing many: {str(e)}")
            return await self._handle_execution_error(e)

    # ========================================================================
    # Fetch Operations
    # ========================================================================

    async def fetch_one(self, sql: str, params: Optional[Tuple] = None,
                        column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None) -> Optional[Dict]:
        """
        Fetches a single record from the database asynchronously.

        Args:
            sql (str): The SQL query to execute.
            params (Optional[Tuple]): A tuple of parameters for the query.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible.
            column_adapters (Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]]):
                A map used for processing the output data from the query.

        IMPORTANT: The `params` tuple is expected to contain values that are
        already database-compatible. The caller is responsible for pre-processing
        inputs, typically by using `prepare_parameters`. The `column_adapters`
        are used for processing the output.
        """
        result = await self.execute(sql, params, ReturningOptions.all_columns(), column_adapters)
        return result.data[0] if result and result.data else None

    async def fetch_all(self, sql: str, params: Optional[Tuple] = None,
                        column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None) -> List[Dict]:
        """
        Fetches all matching records from the database asynchronously.

        Args:
            sql (str): The SQL query to execute.
            params (Optional[Tuple]): A tuple of parameters for the query.
                IMPORTANT: These values are expected to be pre-adapted and
                database-compatible.
            column_adapters (Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]]):
                A map used for processing the output data from the query.

        IMPORTANT: The `params` tuple is expected to contain values that are
        already database-compatible. The caller is responsible for pre-processing
        inputs, typically by using `prepare_parameters`. The `column_adapters`
        are used for processing the output.
        """
        result = await self.execute(sql, params, ReturningOptions.all_columns(), column_adapters)
        return result.data or []

    # ========================================================================
    # Transaction Management
    # ========================================================================

    @property
    @abstractmethod
    def transaction_manager(self) -> AsyncTransactionManager:
        """Get the async transaction manager (to be implemented by concrete backends)."""
        pass

    async def begin_transaction(self) -> None:
        """Begin transaction asynchronously."""
        self.log(logging.INFO, "Beginning transaction")
        await self.transaction_manager.begin()

    async def commit_transaction(self) -> None:
        """Commit transaction asynchronously."""
        self.log(logging.INFO, "Committing transaction")
        await self.transaction_manager.commit()

    async def rollback_transaction(self) -> None:
        """Rollback transaction asynchronously."""
        self.log(logging.INFO, "Rolling back transaction")
        await self.transaction_manager.rollback()

    @property
    def in_transaction(self) -> bool:
        """Check if in transaction."""
        is_active = self.transaction_manager.is_active if self._transaction_manager else False
        self.log(logging.DEBUG, f"Checking transaction status: {is_active}")
        return is_active

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None, None]:
        """Async transaction context manager."""
        await self.begin_transaction()
        try:
            yield
        except Exception:
            await self.rollback_transaction()
            raise
        else:
            await self.commit_transaction()

    # ========================================================================
    # Async Context Manager Support
    # ========================================================================

    async def __aenter__(self):
        if not self._connection:
            await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    # ========================================================================
    # Properties
    # ========================================================================

    @property
    def supports_returning(self) -> bool:
        """Whether RETURNING clause is supported."""
        return False
