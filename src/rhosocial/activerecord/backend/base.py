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
from typing import Any, Dict, Generator, Optional, Tuple, List, Union, AsyncGenerator

from .capabilities import DatabaseCapabilities
from .config import ConnectionConfig
from .dialect import SQLDialectBase, SQLExpressionBase, SQLBuilder, ReturningOptions
from .errors import ReturningNotSupportedError
from .transaction import TransactionManager, AsyncTransactionManager
from .type_converters import TypeRegistry
from .typing import QueryResult, DatabaseType, ColumnTypes


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


class TypeConversionMixin:
    """Mixin for type conversion operations."""

    @property
    def type_registry(self) -> TypeRegistry:
        """Get the type registry from the dialect."""
        return self.dialect.type_registry

    def register_converter(self, converter: Any, names: Optional[List[str]] = None,
                           types: Optional[List[Any]] = None) -> None:
        """Register a type converter with this backend's dialect."""
        self.dialect.register_converter(converter, names, types)


class SQLBuildingMixin:
    """Mixin for SQL building operations."""

    def create_expression(self, expression: str) -> SQLExpressionBase:
        """Create SQL expression."""
        return self.dialect.create_expression(expression)

    def build_sql(self, sql: str, params: Optional[Tuple] = None) -> Tuple[str, Tuple]:
        """Build SQL and parameters."""
        builder = SQLBuilder(self.dialect)
        return builder.build(sql, params)


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
        return stmt_type in ("SELECT", "EXPLAIN", "SHOW", "DESCRIBE", "DESC")

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
               column_types: Optional[ColumnTypes] = None,
               auto_commit: Optional[bool] = True,
               primary_key: Optional[str] = None) -> QueryResult:
        """Insert record."""
        cleaned_data = {
            k.strip('"').strip('`'): v
            for k, v in data.items()
        }

        fields = [self.dialect.format_identifier(field) for field in cleaned_data.keys()]
        values = list(cleaned_data.values())
        placeholders = [self.dialect.get_placeholder() for _ in fields]

        sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(placeholders)})"

        result = self.execute(sql, tuple(values), returning, column_types)

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
               column_types: Optional[ColumnTypes] = None,
               auto_commit: bool = True) -> QueryResult:
        """Update record."""
        set_items = [f"{self.dialect.format_identifier(k)} = {self.dialect.get_placeholder()}"
                     for k in data.keys()]
        values = list(data.values())

        sql = f"UPDATE {table} SET {','.join(set_items)} WHERE {where}"

        result = self.execute(sql, tuple(values) + params, returning, column_types)

        if auto_commit:
            self._handle_auto_commit_if_needed()

        return result

    def delete(self,
               table: str,
               where: str,
               params: Tuple,
               returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
               column_types: Optional[ColumnTypes] = None,
               auto_commit: bool = True) -> QueryResult:
        """Delete record."""
        sql = f"DELETE FROM {table} WHERE {where}"

        result = self.execute(sql, params, returning, column_types)

        if auto_commit:
            self._handle_auto_commit_if_needed()

        return result


# ============================================================================
# Base Configuration Class
# ============================================================================

class StorageBackendBase(ABC):
    """Minimal base for configuration and connection state only."""

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
    TypeConversionMixin,
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
            column_types: Optional[ColumnTypes] = None) -> Optional[QueryResult]:
        """
        Execute SQL statement with enhanced RETURNING clause support.

        This is a template method that implements the common flow for all databases.
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

            # Process SQL and parameters
            final_sql, final_params = self._prepare_sql_and_params(sql, params)

            # Execute query
            cursor = self._execute_query(cursor, final_sql, final_params)

            # Process results
            data = self._process_result_set(cursor, is_select, need_returning, column_types)

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

    def _prepare_sql_and_params(self, sql: str, params: Optional[Tuple]) -> Tuple[str, Optional[Tuple]]:
        """Process SQL and parameters for execution."""
        if params:
            return self.build_sql(sql, params)
        return sql, params

    def _execute_query(self, cursor, sql: str, params: Optional[Tuple]):
        """Execute the query with prepared SQL and parameters."""
        if params:
            processed_params = tuple(
                self.dialect.to_database(value, None)
                for value in params
            )
            cursor.execute(sql, processed_params)
        else:
            cursor.execute(sql)
        return cursor

    def _process_result_set(self, cursor, is_select: bool, need_returning: bool,
                            column_types: Optional[ColumnTypes]) -> Optional[List[Dict]]:
        """Process query result set with type conversion."""
        if not (is_select or need_returning):
            return None

        try:
            rows = cursor.fetchall()
            self.log(logging.DEBUG, f"Fetched {len(rows)} rows")

            if not rows:
                return []

            # Apply type conversions if specified
            if column_types:
                self.log(logging.DEBUG, "Applying type conversions")
                result = []

                if hasattr(rows[0], 'items'):  # Dict-like rows
                    for row in rows:
                        converted_row = self._convert_row_dict(row, column_types)
                        result.append(converted_row)
                else:  # Tuple-like rows
                    column_names = [desc[0] for desc in cursor.description]
                    for row in rows:
                        converted_row = self._convert_row_tuple(row, column_names, column_types)
                        result.append(converted_row)

                return result
            else:
                # No type conversion needed
                if hasattr(rows[0], 'items'):
                    return [dict(row) for row in rows]
                else:
                    column_names = [desc[0] for desc in cursor.description]
                    return [dict(zip(column_names, row)) for row in rows]
        except Exception as e:
            self.log(logging.ERROR, f"Error processing result set: {str(e)}")
            raise

    def _convert_row_dict(self, row: Dict, column_types: ColumnTypes) -> Dict:
        """Convert a dict-like row with type specifications."""
        converted_row = {}
        for key, value in row.items():
            converted_row[key] = self._convert_value(value, column_types.get(key))
        return converted_row

    def _convert_row_tuple(self, row: Tuple, column_names: List[str],
                           column_types: ColumnTypes) -> Dict:
        """Convert a tuple-like row with type specifications."""
        converted_row = {}
        for i, value in enumerate(row):
            key = column_names[i]
            converted_row[key] = self._convert_value(value, column_types.get(key))
        return converted_row

    def _convert_value(self, value: Any, type_spec: Any) -> Any:
        """Convert a single value based on type specification."""
        if type_spec is None:
            return value
        elif isinstance(type_spec, DatabaseType):
            return self.dialect.from_database(value, type_spec)
        elif isinstance(type_spec, str):
            converter = self.dialect.type_registry.find_converter_by_name(type_spec)
            if converter:
                return converter.from_database(value, type_spec)
            return value
        else:
            try:
                return type_spec.from_database(value, None)
            except (AttributeError, TypeError):
                return self.dialect.from_database(value, type_spec)

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
        """Execute batch operations (default implementation)."""
        self.log(logging.INFO,
                 f"execute_many: Executing statements individually (backend doesn't support batch operations)")
        start_time = time.perf_counter()
        affected_rows = 0

        for params in params_list:
            result = self.execute(sql, params)
            if result:
                affected_rows += result.affected_rows

        duration = time.perf_counter() - start_time
        return QueryResult(affected_rows=affected_rows, duration=duration)

    # ========================================================================
    # Fetch Operations
    # ========================================================================

    def fetch_one(self, sql: str, params: Optional[Tuple] = None,
                  column_types: Optional[ColumnTypes] = None) -> Optional[Dict]:
        """Fetch single record."""
        result = self.execute(sql, params, ReturningOptions.all_columns(), column_types)
        return result.data[0] if result and result.data else None

    def fetch_all(self, sql: str, params: Optional[Tuple] = None,
                  column_types: Optional[ColumnTypes] = None) -> List[Dict]:
        """Fetch multiple records."""
        result = self.execute(sql, params, ReturningOptions.all_columns(), column_types)
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
    TypeConversionMixin,
    SQLBuildingMixin,
    QueryAnalysisMixin,
    ReturningClauseMixin,
    ResultProcessingMixin,
    SQLOperationsMixin,
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
            column_types: Optional[ColumnTypes] = None) -> Optional[QueryResult]:
        """Execute SQL statement asynchronously."""
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

            data = await self._process_result_set(cursor, is_select, need_returning, column_types)

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

    @abstractmethod
    async def _get_cursor(self):
        """Get or create a cursor asynchronously."""
        pass

    @abstractmethod
    async def _execute_query(self, cursor, sql: str, params: Optional[Tuple]):
        """Execute query asynchronously."""
        pass

    @abstractmethod
    async def _process_result_set(self, cursor, is_select: bool, need_returning: bool,
                                  column_types: Optional[ColumnTypes]) -> Optional[List[Dict]]:
        """Process result set asynchronously."""
        pass

    @abstractmethod
    async def _handle_auto_commit_if_needed(self) -> None:
        """Handle auto-commit asynchronously."""
        pass

    @abstractmethod
    async def _handle_execution_error(self, error: Exception):
        """Handle execution errors asynchronously."""
        pass

    # ========================================================================
    # Fetch Operations
    # ========================================================================

    async def fetch_one(self, sql: str, params: Optional[Tuple] = None,
                        column_types: Optional[ColumnTypes] = None) -> Optional[Dict]:
        """Fetch single record asynchronously."""
        result = await self.execute(sql, params, ReturningOptions.all_columns(), column_types)
        return result.data[0] if result and result.data else None

    async def fetch_all(self, sql: str, params: Optional[Tuple] = None,
                        column_types: Optional[ColumnTypes] = None) -> List[Dict]:
        """Fetch multiple records asynchronously."""
        result = await self.execute(sql, params, ReturningOptions.all_columns(), column_types)
        return result.data or []

    # ========================================================================
    # Transaction Management
    # ========================================================================

    @property
    @abstractmethod
    def transaction_manager(self) -> AsyncTransactionManager:
        """Get the async transaction manager (to be implemented by concrete backends)."""
        pass

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None, None]:
        """Async transaction context manager."""
        async with self.transaction_manager.transaction() as t:
            yield t

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