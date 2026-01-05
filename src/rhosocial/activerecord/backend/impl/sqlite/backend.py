# src/rhosocial/activerecord/backend/impl/sqlite/backend.py
"""
SQLite-specific implementation of the StorageBackend.

This module provides the concrete implementation for interacting with SQLite databases,
handling connections, queries, transactions, and type adaptations tailored for SQLite's
specific behaviors and SQL dialect.
"""
import logging
import re
import sqlite3
import sys
import time
from sqlite3 import ProgrammingError
from typing import Optional, Tuple, List, Any, Dict, Union, Type

from .adapters import SQLiteBlobAdapter, SQLiteJSONAdapter, SQLiteUUIDAdapter
from .config import SQLiteConnectionConfig
from ...options import InsertOptions, UpdateOptions, DeleteOptions
from ...result import QueryResult
from .dialect import SQLiteDialect, SQLDialectBase
from .transaction import SQLiteTransactionManager
from ...base import StorageBackend
from ...capabilities import (
    DatabaseCapabilities,
    CTECapability,
    JSONCapability,
    TransactionCapability,
    BulkOperationCapability,
    JoinCapability,
    ConstraintCapability,
    AggregateFunctionCapability,
    DateTimeFunctionCapability,
    StringFunctionCapability,
    MathematicalFunctionCapability,
    ALL_SET_OPERATIONS,
    ALL_WINDOW_FUNCTIONS,
    ALL_RETURNING_FEATURES
)
from ...options import ExecutionOptions
from ...errors import ConnectionError, IntegrityError, OperationalError, QueryError, DeadlockError, DatabaseError, \
    ReturningNotSupportedError, JsonOperationNotSupportedError
from ...result import QueryResult
from ...type_adapter import SQLTypeAdapter
from ...expression.statements import ReturningClause


class SQLiteBackend(StorageBackend):
    # Default PRAGMA settings
    DEFAULT_PRAGMAS = {
        "foreign_keys": "ON",
        "journal_mode": "WAL",
        "synchronous": "FULL",
        "wal_autocheckpoint": "1000",
        "wal_checkpoint": "FULL"
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cursor = None
        self._dialect = SQLiteDialect()

        # Check if we need to convert a legacy config to the new SQLiteConnectionConfig
        if "connection_config" in kwargs and kwargs["connection_config"] is not None:
            if not isinstance(kwargs["connection_config"], SQLiteConnectionConfig):
                # Create a new SQLiteConnectionConfig from the given config
                old_config = kwargs["connection_config"]

                # Extract SQLite specific parameters
                pragmas = {}
                if hasattr(old_config, 'pragmas'):
                    pragmas = old_config.pragmas

                # Create new config
                self.config = SQLiteConnectionConfig(
                    host=old_config.host,
                    port=old_config.port,
                    database=old_config.database,
                    username=old_config.username,
                    password=old_config.password,
                    driver_type=old_config.driver_type,
                    pragmas=pragmas,
                    delete_on_close=getattr(old_config, 'delete_on_close', False),
                    options=old_config.options,
                )
            else:
                self.config = kwargs["connection_config"]
        else:
            # Use SQLiteConnectionConfig directly
            self.config = SQLiteConnectionConfig(**kwargs)

        # Register SQLite-specific adapters
        self._register_sqlite_adapters()

    def _initialize_capabilities(self) -> DatabaseCapabilities:
        """Initialize SQLite capabilities based on version.
        
        This method declares the capabilities that SQLite supports, taking into
        account version-specific feature availability. The capability system
        allows tests and application code to check for feature support before
        using features, preventing runtime errors on SQLite versions that
        don't support certain features.
        """
        capabilities = DatabaseCapabilities()
        version = self.get_server_version()

        # Basic capabilities supported by most versions
        capabilities.add_set_operation(ALL_SET_OPERATIONS)
        capabilities.add_join_operation([
            JoinCapability.INNER_JOIN,
            JoinCapability.LEFT_OUTER_JOIN,
            JoinCapability.CROSS_JOIN
        ])
        capabilities.add_transaction(TransactionCapability.SAVEPOINT)
        capabilities.add_bulk_operation(BulkOperationCapability.BATCH_OPERATIONS)
        capabilities.add_constraint([
            ConstraintCapability.PRIMARY_KEY,
            ConstraintCapability.FOREIGN_KEY,
            ConstraintCapability.UNIQUE,
            ConstraintCapability.NOT_NULL,
            ConstraintCapability.DEFAULT
        ])
        capabilities.add_datetime_function(DateTimeFunctionCapability.STRFTIME)
        capabilities.add_aggregate_function(AggregateFunctionCapability.GROUP_CONCAT)

        # CTEs supported from 3.8.3+
        if version >= (3, 8, 3):
            capabilities.add_cte([
                CTECapability.BASIC_CTE,
                CTECapability.RECURSIVE_CTE
            ])

        # JSON operations supported from 3.9.0+
        if version >= (3, 9, 0):
            capabilities.add_json([
                JSONCapability.JSON_EXTRACT,
                JSONCapability.JSON_CONTAINS,
                JSONCapability.JSON_EXISTS,
                JSONCapability.JSON_KEYS,
                JSONCapability.JSON_ARRAY,
                JSONCapability.JSON_OBJECT
            ])
            
        # UPSERT (ON CONFLICT) supported from 3.24.0+
        if version >= (3, 24, 0):
            capabilities.add_bulk_operation(BulkOperationCapability.UPSERT)

        # Window functions supported from 3.25.0+
        if version >= (3, 25, 0):
            capabilities.add_window_function(ALL_WINDOW_FUNCTIONS)

        # RETURNING clause and built-in math functions supported from 3.35.0+
        if version >= (3, 35, 0):
            capabilities.add_returning(ALL_RETURNING_FEATURES)
            capabilities.add_mathematical_function([
                MathematicalFunctionCapability.ABS,
                MathematicalFunctionCapability.ROUND,
                MathematicalFunctionCapability.CEIL,
                MathematicalFunctionCapability.FLOOR,
                MathematicalFunctionCapability.POWER,
                MathematicalFunctionCapability.SQRT
            ])

        # STRICT tables supported from 3.37.0+
        if version >= (3, 37, 0):
            capabilities.add_constraint(ConstraintCapability.STRICT_TABLES)

        # Additional JSON functions from 3.38.0+
        if version >= (3, 38, 0):
            capabilities.add_json([
                JSONCapability.JSON_SET,
                JSONCapability.JSON_INSERT,
                JSONCapability.JSON_REPLACE,
                JSONCapability.JSON_REMOVE
            ])

        # RIGHT and FULL OUTER JOIN supported from 3.39.0+
        if version >= (3, 39, 0):
            capabilities.add_join_operation([
                JoinCapability.RIGHT_OUTER_JOIN,
                JoinCapability.FULL_OUTER_JOIN
            ])
            
        # CONCAT functions supported from 3.44.0+
        if version >= (3, 44, 0):
            capabilities.add_string_function([
                StringFunctionCapability.CONCAT,
                StringFunctionCapability.CONCAT_WS
            ])
            
        # JSONB support from 3.45.0+
        if version >= (3, 45, 0):
            capabilities.add_json(JSONCapability.JSONB_SUPPORT)

        return capabilities

    def _register_sqlite_adapters(self):
        """Register SQLite-specific type adapters to the adapter_registry."""
        sqlite_adapters = [
            SQLiteBlobAdapter(),
            SQLiteJSONAdapter(),
            SQLiteUUIDAdapter(),
        ]
        for adapter in sqlite_adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    # Register with override allowed for backend-specific converters
                    self.adapter_registry.register(adapter, py_type, db_type, allow_override=True)
        self.logger.debug("Registered SQLite-specific type adapters.")

    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple['SQLTypeAdapter', Type]]:
        """
        [Backend Implementation] Provides default type adapter suggestions for SQLite.

        This method defines a curated set of type adapter suggestions for common Python
        types, mapping them to their typical SQLite-compatible representations as
        demonstrated in test fixtures. It explicitly retrieves necessary `SQLTypeAdapter`
        instances from the backend's `adapter_registry`. If an adapter for a specific
        (Python type, DB driver type) pair is not registered, no suggestion will be
        made for that Python type.

        Returns:
            Dict[Type, Tuple[SQLTypeAdapter, Type]]: A dictionary where keys are
            original Python types (`TypeRegistry`'s `py_type`), and values are
            tuples containing a `SQLTypeAdapter` instance and the target
            Python type (`TypeRegistry`'s `db_type`) expected by the driver.
        """
        suggestions: Dict[Type, Tuple['SQLTypeAdapter', Type]] = {}

        # Define a list of desired Python type to DB driver type mappings.
        # This list reflects types seen in test fixtures and common usage,
        # along with their preferred database-compatible Python types for the driver.
        # Types that are natively compatible with the DB driver (e.g., Python str, int, float)
        # and for which no specific conversion logic is needed are omitted from this list.
        # The consuming layer should assume pass-through behavior for any Python type
        # that does not have an explicit adapter suggestion.
        #
        # Exception: If a user requires specific processing for a natively compatible type
        # (e.g., custom serialization/deserialization for JSON strings beyond basic conversion),
        # they would need to implement and register their own specialized adapter.
        # This backend's default suggestions do not cater to such advanced processing needs.
        from datetime import date, datetime, time
        from decimal import Decimal
        from uuid import UUID
        from enum import Enum

        type_mappings = [
            (bool, int),        # Python bool -> DB driver int (SQLite INTEGER)
            (datetime, str),    # Python datetime -> DB driver str (SQLite TEXT)
            (date, str),        # Python date -> DB driver str (SQLite TEXT)
            (time, str),        # Python time -> DB driver str (SQLite TEXT)
            (Decimal, float),   # Python Decimal -> DB driver float (SQLite DECIMAL)
            (UUID, str),        # Python UUID -> DB driver str (SQLite TEXT)
            (dict, str),        # Python dict -> DB driver str (SQLite TEXT for JSON)
            (list, str),        # Python list -> DB driver str (SQLite TEXT for JSON)
            # (bytes, bytes),   # Python bytes -> DB driver bytes (SQLite BLOB) - Handled as pass-through by default if no explicit adapter.
            (Enum, str),        # Python Enum -> DB driver str (SQLite TEXT)
        ]

        # Iterate through the defined mappings and retrieve adapters from the registry.
        for py_type, db_type in type_mappings:
            adapter = self.adapter_registry.get_adapter(py_type, db_type)
            if adapter:
                suggestions[py_type] = (adapter, db_type)
            else:
                # Log a debug message if a specific adapter is expected but not found.
                self.logger.debug(f"No adapter found for ({py_type.__name__}, {db_type.__name__}). "
                                  "Suggestion will not be provided for this type.")

        return suggestions


    @property
    def pragmas(self) -> Dict[str, str]:
        """Get current pragma settings

        Returns:
            Dict[str, str]: Current pragma settings
        """
        # With the new config, pragmas are directly accessible
        return self.config.pragmas.copy()

    def set_pragma(self, pragma_key: str, pragma_value: Any) -> None:
        """Set a pragma parameter at runtime

        Args:
            pragma_key: Pragma parameter name
            pragma_value: Pragma parameter value

        Raises:
            ConnectionError: If pragma cannot be set
        """
        pragma_value_str = str(pragma_value)
        self.config.pragmas[pragma_key] = pragma_value_str

        # If connected, apply the pragma immediately
        if self._connection:
            pragma_statement = f"PRAGMA {pragma_key} = {pragma_value_str}"
            self.log(logging.DEBUG, f"Setting pragma: {pragma_statement}")

            try:
                self._connection.execute(pragma_statement)
            except sqlite3.Error as e:
                error_msg = f"Failed to set pragma {pragma_key}: {str(e)}"
                self.log(logging.ERROR, error_msg)
                raise ConnectionError(error_msg)

    def _apply_pragmas(self) -> None:
        """Apply all pragma settings to the connection"""
        for pragma_key, pragma_value in self.config.pragmas.items():
            pragma_statement = f"PRAGMA {pragma_key} = {pragma_value}"
            self.log(logging.DEBUG, f"Executing pragma: {pragma_statement}")

            try:
                self._connection.execute(pragma_statement)
            except sqlite3.Error as e:
                # Log the error but continue with other pragmas
                self.log(logging.WARNING, f"Failed to execute pragma {pragma_statement}: {str(e)}")

    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def connect(self) -> None:
        """Establish a connection to the SQLite database."""
        try:
            self.log(logging.INFO, f"Connecting to SQLite database: {self.config.database}")
            self._connection = sqlite3.connect(
                self.config.database,
                detect_types=self.config.detect_types,
                isolation_level=None,  # Use manual transaction management
                uri=self.config.uri,
                timeout=self.config.timeout
            )

            # Apply pragma settings
            self._apply_pragmas()

            self._connection.row_factory = sqlite3.Row
            self._connection.text_factory = str
            self.log(logging.INFO, "Connected to SQLite database successfully")
        except sqlite3.Error as e:
            self.log(logging.ERROR, f"Failed to connect to SQLite database: {str(e)}")
            raise ConnectionError(f"Failed to connect: {str(e)}")

    def disconnect(self) -> None:
        """Close the connection to the SQLite database.

        This method is idempotent - it can be safely called multiple times
        and will not raise an exception if the connection is already closed.
        """
        try:
            if self._connection:
                self.log(logging.INFO, "Disconnecting from SQLite database")

                # Check for active transaction and roll it back if needed
                if self.transaction_manager.is_active:
                    self.log(logging.WARNING, "Active transaction detected during disconnect, rolling back")
                    self.transaction_manager.rollback()

                # Close the connection
                self._connection.close()
                self._connection = None
                self._cursor = None
                self._transaction_manager = None
                self.log(logging.INFO, "Disconnected from SQLite database")

                # Handle file deletion if enabled and not using in-memory database
                if self.config.delete_on_close and not self.config.is_memory_db():
                    try:
                        import os
                        import time
                        self.log(logging.INFO, f"Deleting database files: {self.config.database}")

                        # Define retry delete function
                        def retry_delete(file_path, max_retries=5, retry_delay=0.1):
                            for attempt in range(max_retries):
                                try:
                                    if os.path.exists(file_path):
                                        os.remove(file_path)
                                        return True
                                    return True  # File doesn't exist, consider deletion successful
                                except OSError as e:
                                    if attempt < max_retries - 1:  # If not the last attempt
                                        self.log(logging.DEBUG,
                                                 f"Failed to delete file {file_path}, retrying: {str(e)}")
                                        time.sleep(retry_delay)  # Wait for a while before retrying
                                    else:
                                        self.log(logging.WARNING,
                                                 f"Failed to delete file {file_path}, maximum retry attempts reached: {str(e)}")
                                        return False
                            return False

                        # Delete main database file
                        main_db_deleted = retry_delete(self.config.database)

                        # Delete WAL and SHM files
                        wal_file = f"{self.config.database}-wal"
                        shm_file = f"{self.config.database}-shm"
                        wal_deleted = retry_delete(wal_file)
                        shm_deleted = retry_delete(shm_file)

                        # Record deletion results
                        if main_db_deleted and wal_deleted and shm_deleted:
                            self.log(logging.INFO, "Database files deleted successfully")
                        else:
                            self.log(logging.WARNING,
                                     "Some database files could not be deleted after multiple attempts")
                    except Exception as e:
                        self.log(logging.ERROR, f"Failed to delete database files: {str(e)}")
                        raise ConnectionError(f"Failed to delete database files: {str(e)}")
            else:
                # Connection is already closed or was never opened
                self.log(logging.DEBUG, "Disconnect called on already closed connection")
        except sqlite3.Error as e:
            self.log(logging.ERROR, f"Error during disconnect: {str(e)}")
            raise ConnectionError(f"Failed to disconnect: {str(e)}")

    def ping(self, reconnect: bool = True) -> bool:
        """Test the database connection and optionally reconnect.

        Args:
            reconnect: Whether to attempt reconnection if the connection is lost

        Returns:
            bool: True if connection is alive, False otherwise
        """
        if not self._connection:
            self.log(logging.DEBUG, "No active connection during ping")
            if reconnect:
                try:
                    self.log(logging.INFO, "Reconnecting during ping")
                    self.connect()
                    return True
                except ConnectionError as e:
                    self.log(logging.WARNING, f"Reconnection failed during ping: {str(e)}")
                    return False
            return False

        try:
            self.log(logging.DEBUG, "Testing connection with SELECT 1")
            self._connection.execute("SELECT 1")
            return True
        except sqlite3.Error as e:
            self.log(logging.WARNING, f"Ping failed: {str(e)}")
            if reconnect:
                try:
                    self.log(logging.INFO, "Reconnecting after failed ping")
                    self.connect()
                    return True
                except ConnectionError as e:
                    self.log(logging.WARNING, f"Reconnection failed after ping: {str(e)}")
                    return False
            return False

    @property



    def _is_select_statement(self, stmt_type: str) -> bool:
        """
        Check if statement is a SELECT-like query.

        SQLite includes pragmas as read operations.

        Args:
            stmt_type: Statement type

        Returns:
            bool: True if statement is a read-only query
        """
        return stmt_type in ("SELECT", "EXPLAIN", "PRAGMA", "ANALYZE")

    def _check_returning_compatibility(self, returning_clause: Optional['ReturningClause']) -> None:
        """
        Check compatibility issues with RETURNING clause in SQLite.

        SQLite with Python < 3.10 has known issues with RETURNING where
        affected_rows is always reported as 0.

        Args:
            returning_clause: ReturningClause object to check compatibility for

        Raises:
            ReturningNotSupportedError: If compatibility issues found
        """
        # Check SQLite version support
        version = sqlite3.sqlite_version_info
        if version < (3, 35, 0):
            error_msg = (
                f"RETURNING clause requires SQLite 3.35.0+. Current version: {sqlite3.sqlite_version}. "
            )
            self.log(logging.WARNING, error_msg)
            raise ReturningNotSupportedError(error_msg)

        # Check Python version compatibility
        if sys.version_info < (3, 10):
            error_msg = (
                "RETURNING clause has known issues in Python < 3.10 with SQLite: "
                "affected_rows always reports 0 regardless of actual rows affected."
            )
            self.log(logging.WARNING, error_msg)
            raise ReturningNotSupportedError(error_msg)

    def _get_cursor(self):
        """
        Get or create cursor for SQLite.

        Returns:
            sqlite3.Cursor: SQLite cursor with row factory
        """
        if self._cursor:
            return self._cursor

        # Create cursor with SQLite Row factory for dict-like access
        cursor = self._connection.cursor()
        return cursor

    def _handle_auto_commit_if_needed(self) -> None:
        """
        Handle auto-commit for SQLite.

        SQLite requires explicit commit when using isolation_level=None.
        """
        if not self.in_transaction and self._connection:
            self._connection.commit()
            self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")



    def _handle_error(self, error: Exception) -> None:
        """Handle SQLite-specific errors and convert to appropriate exceptions"""
        error_msg = str(error)

        if isinstance(error, sqlite3.Error):
            if isinstance(error, sqlite3.OperationalError):
                if "database is locked" in error_msg:
                    self.log(logging.ERROR, f"Database lock error: {error_msg}")
                    raise OperationalError("Database is locked")
                elif "no such table" in error_msg:
                    self.log(logging.ERROR, f"Table not found: {error_msg}")
                    raise QueryError(f"Table not found: {error_msg}")
                self.log(logging.ERROR, f"SQLite operational error: {error_msg}")
                raise OperationalError(error_msg)
            elif isinstance(error, sqlite3.IntegrityError):
                if "UNIQUE constraint failed" in error_msg:
                    self.log(logging.ERROR, f"Unique constraint violation: {error_msg}")
                    raise IntegrityError(f"Unique constraint violation: {error_msg}")
                elif "FOREIGN KEY constraint failed" in error_msg:
                    self.log(logging.ERROR, f"Foreign key constraint violation: {error_msg}")
                    raise IntegrityError(f"Foreign key constraint violation: {error_msg}")
                self.log(logging.ERROR, f"SQLite integrity error: {error_msg}")
                raise IntegrityError(error_msg)
            elif "database is locked" in error_msg:
                self.log(logging.ERROR, f"Database deadlock: {error_msg}")
                raise DeadlockError(error_msg)
            elif isinstance(error, ProgrammingError):
                self.log(logging.ERROR, f"SQLite programming error: {error_msg}")
                raise DatabaseError(error_msg)

                # Log unknown SQLite errors
            self.log(logging.ERROR, f"Unhandled SQLite error: {error_msg}")

            # Log and re-raise other errors
            self.log(logging.ERROR, f"Unhandled error: {error_msg}")
            raise error
        raise error

    def executescript(self, sql_script: str) -> None:
        """
        Execute a multi-statement SQL script.

        This is a convenience method for SQLite to run scripts from files,
        which may contain multiple statements (e.g., CREATE TABLE, INSERT).
        The underlying driver's `executescript` method is used.

        Note: This method does not return a QueryResult and is intended for
        DDL or batch DML operations, not for queries that return rows.

        Args:
            sql_script: A string containing one or more SQL statements separated
                        by semicolons.
        """
        self.log(logging.INFO, "Executing SQL script.")
        start_time = time.perf_counter()
        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._cursor or self._connection.cursor()
            cursor.executescript(sql_script)
            duration = time.perf_counter() - start_time
            self.log(logging.INFO, f"SQL script executed successfully, duration={duration:.3f}s")
            
            self._handle_auto_commit_if_needed()

        except Exception as e:
            self.log(logging.ERROR, f"Error executing SQL script: {str(e)}")
            self._handle_error(e)

    def execute_many(
            self,
            sql: str,
            params_list: List[Tuple]
    ) -> Optional[QueryResult]:
        """
        Execute batch operations with the same SQL statement and multiple parameter sets.

        This method executes the same SQL statement multiple times with different parameter sets.
        It is more efficient than executing individual statements and is ideal for bulk inserts
        or updates.

        IMPORTANT: SQLite's executemany only supports a single SQL statement at a time.
        Do NOT use statements with semicolons, as SQLite cannot execute multiple statements
        in a single call.

        The `params_list` contains sequences of parameters. Each parameter sequence
        is expected to contain values that are already database-compatible (e.g., Python `str`, `int`, `float`, `bytes`, `None`).
        Type adaptation for complex Python types (e.g., `datetime`, `UUID`, `Decimal`)
        should be performed *before* passing the `params_list` to this method, typically
        by using `prepare_parameters` from `TypeAdaptionMixin` for each parameter set.

        Parameters are passed directly to the database driver's `executemany`
        method without any further type adaptation. It is the caller's
        responsibility to ensure `params_list` contains database-compatible types.

        Args:
            sql: SQL statement (must be a single statement without semicolons)
            params_list: List of parameter tuples, one for each execution

        Returns:
            QueryResult: Execution results
        """
        self.log(logging.INFO, f"Executing batch operation: {sql} with {len(params_list)} parameter sets")
        start_time = time.perf_counter()
        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._cursor or self._connection.cursor()

            # Parameters are assumed to be pre-converted by the caller using `prepare_parameters`
            cursor.executemany(sql, params_list)
            duration = time.perf_counter() - start_time

            self.log(logging.INFO,
                     f"Batch operation completed, affected {cursor.rowcount} rows, duration={duration:.3f}s")
            
            self._handle_auto_commit_if_needed()

            return QueryResult(
                affected_rows=cursor.rowcount,
                duration=duration
            )
        except Exception as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            self._handle_error(e)
            return None

    def _handle_auto_commit(self) -> None:
        """Handle auto commit based on SQLite connection and transaction state.

        This method will commit the current connection if:
        1. The connection exists and is open
        2. There is no active transaction managed by transaction_manager

        It's used by insert/update/delete operations to ensure changes are
        persisted immediately when auto_commit=True is specified.
        """
        try:
            # Check if connection exists
            if not self._connection:
                return

            # Check if we're not in an active transaction
            if not self._transaction_manager or not self._transaction_manager.is_active:
                # For SQLite, we always need to commit explicitly since we set isolation_level=None
                # in connect() which disables autocommit
                self._connection.commit()
                self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            # Just log the error but don't raise - this is a convenience feature
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    @property
    def transaction_manager(self) -> SQLiteTransactionManager:
        """Get the transaction manager"""
        if not self._transaction_manager:
            if not self._connection:
                self.log(logging.DEBUG, "Initializing connection for transaction manager")
                self.connect()
            self.log(logging.DEBUG, "Creating new transaction manager")
            self._transaction_manager = SQLiteTransactionManager(self._connection, self.logger)
        return self._transaction_manager

    def insert(self, options: InsertOptions) -> QueryResult:
        """
        Insert a record with special handling for RETURNING clause behavior across Python versions.

        In some Python versions (e.g., 3.8) with RETURNING clauses, cursor.rowcount may return 0
        even when the operation is successful. This method ensures consistent behavior by
        checking if data was returned when affected_rows is 0, and adjusting accordingly.
        """
        # Call the parent implementation
        result = super().insert(options)

        # Special handling for RETURNING clause: if affected_rows is 0 but we have returned data,
        # this indicates the operation was successful despite cursor.rowcount behavior
        if (result.affected_rows == 0 and
            options.returning_columns is not None and
            options.returning_columns and
            result.data is not None and
            len(result.data) > 0):
            # Adjust affected_rows to reflect the successful operation
            result.affected_rows = len(result.data)

        return result

    def update(self, options: UpdateOptions) -> QueryResult:
        """
        Update records with special handling for RETURNING clause behavior across Python versions.

        In some Python versions (e.g., 3.8) with RETURNING clauses, cursor.rowcount may return 0
        even when the operation is successful. This method ensures consistent behavior by
        checking if data was returned when affected_rows is 0, and adjusting accordingly.
        """
        # Call the parent implementation
        result = super().update(options)

        # Special handling for RETURNING clause: if affected_rows is 0 but we have returned data,
        # this indicates the operation was successful despite cursor.rowcount behavior
        if (result.affected_rows == 0 and
            options.returning_columns is not None and
            options.returning_columns and
            result.data is not None and
            len(result.data) > 0):
            # Adjust affected_rows to reflect the successful operation
            result.affected_rows = len(result.data)

        return result

    def delete(self, options: DeleteOptions) -> QueryResult:
        """
        Delete records with special handling for RETURNING clause behavior across Python versions.

        In some Python versions (e.g., 3.8) with RETURNING clauses, cursor.rowcount may return 0
        even when the operation is successful. This method ensures consistent behavior by
        checking if data was returned when affected_rows is 0, and adjusting accordingly.
        """
        # Call the parent implementation
        result = super().delete(options)

        # Special handling for RETURNING clause: if affected_rows is 0 but we have returned data,
        # this indicates the operation was successful despite cursor.rowcount behavior
        if (result.affected_rows == 0 and
            options.returning_columns is not None and
            options.returning_columns and
            result.data is not None and
            len(result.data) > 0):
            # Adjust affected_rows to reflect the successful operation
            result.affected_rows = len(result.data)

        return result

    def get_server_version(self) -> tuple:
        """Get SQLite version

        For SQLite, the version is determined once and cached permanently
        since SQLite version is tied to the library itself, not a server.

        Returns:
            tuple: SQLite version as (major, minor, patch)
        """
        # Return cached version if available (class-level cache)
        if not hasattr(SQLiteBackend, '_sqlite_version_cache'):
            try:
                if not self._connection:
                    self.connect()

                cursor = self._connection.cursor()
                cursor.execute("SELECT sqlite_version()")
                version_str = cursor.fetchone()[0]
                cursor.close()

                # Parse version string (e.g. "3.39.4" into (3, 39, 4))
                version_parts = version_str.split('.')
                major = int(version_parts[0])
                minor = int(version_parts[1]) if len(version_parts) > 1 else 0
                patch = int(version_parts[2]) if len(version_parts) > 2 else 0

                # Cache at class level since SQLite version is consistent
                SQLiteBackend._sqlite_version_cache = (major, minor, patch)
                self.log(logging.INFO, f"Detected SQLite version: {major}.{minor}.{patch}")

            except Exception as e:
                # Log the error but don't fail - return a reasonable default
                if hasattr(self, 'logger'):
                    self.logger.warning(f"Failed to determine SQLite version: {str(e)}")
                # Default to a relatively recent version
                SQLiteBackend._sqlite_version_cache = (3, 35, 0)
                self.log(logging.WARNING,
                         f"Failed to determine SQLite version, defaulting to 3.35.0: {str(e)}")

        return SQLiteBackend._sqlite_version_cache

    def format_json_operation(self, column: Union[str, Any], path: Optional[str] = None,
                              operation: str = "extract", value: Any = None,
                              alias: Optional[str] = None) -> str:
        """Format JSON operation according to database dialect.

        Delegates to the dialect's json_operation_handler for database-specific formatting.

        Args:
            column: JSON column name or expression
            path: JSON path
            operation: Operation type (extract, contains, exists, etc.)
            value: Value for operations that need it (contains, insert, etc.)
            alias: Optional alias for the result

        Returns:
            str: Database-specific JSON operation SQL

        Raises:
            JsonOperationNotSupportedError: If JSON operations not supported
        """
        if not hasattr(self.dialect, 'json_operation_handler'):
            raise JsonOperationNotSupportedError(
                f"JSON operations not supported by {self.dialect.__class__.__name__}"
            )

        return self.dialect.json_operation_handler.format_json_operation(
            column=column,
            path=path,
            operation=operation,
            value=value,
            alias=alias
        )