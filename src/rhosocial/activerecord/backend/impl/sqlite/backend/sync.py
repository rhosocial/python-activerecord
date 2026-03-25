# src/rhosocial/activerecord/backend/impl/sqlite/backend/sync.py
"""
SQLite-specific synchronous implementation of the StorageBackend.

This module provides the concrete implementation for interacting with SQLite databases,
handling connections, queries, transactions, and type adaptations tailored for SQLite's
specific behaviors and SQL dialect.
"""

import logging
import sqlite3
import time
from datetime import datetime
from typing import Any, List, Optional, Tuple, Union

from .common import SQLiteBackendMixin, DEFAULT_PRAGMAS
from ..config import SQLiteConnectionConfig
from ..dialect import SQLiteDialect, SQLDialectBase
from ..transaction import SQLiteTransactionManager
from ..introspection import SQLiteIntrospectionMixin
from rhosocial.activerecord.backend.base import StorageBackend
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.errors import ConnectionError
from rhosocial.activerecord.backend.options import DeleteOptions, InsertOptions, UpdateOptions
from rhosocial.activerecord.backend.result import QueryResult


class SQLiteBackend(SQLiteBackendMixin, SQLiteIntrospectionMixin, StorageBackend):
    """Synchronous SQLite backend implementation.

    Provides database introspection capabilities through SQLiteIntrospectionMixin,
    which implements the BackendIntrospectionSupport protocol.
    """

    DEFAULT_PRAGMAS = DEFAULT_PRAGMAS
    _sqlite_version_cache: Optional[Tuple[int, int, int]] = None

    def __init__(
        self,
        connection_config: Optional[Union[ConnectionConfig, SQLiteConnectionConfig]] = None,
        database: Optional[str] = None,
        **kwargs,
    ):
        if connection_config is None and database is not None:
            connection_config = SQLiteConnectionConfig(database=database, **kwargs)
        elif connection_config is None:
            raise ValueError("Either connection_config or database must be provided")

        if not isinstance(connection_config, SQLiteConnectionConfig):
            pragmas = {}
            if hasattr(connection_config, "pragmas"):
                pragmas = connection_config.pragmas
            connection_config = SQLiteConnectionConfig(
                host=getattr(connection_config, "host", None),
                port=getattr(connection_config, "port", None),
                database=connection_config.database,
                username=getattr(connection_config, "username", None),
                password=getattr(connection_config, "password", None),
                driver_type=getattr(connection_config, "driver_type", None),
                pragmas=pragmas,
                delete_on_close=getattr(connection_config, "delete_on_close", False),
                options=getattr(connection_config, "options", {}),
            )

        super().__init__(connection_config=connection_config)
        self._cursor = None
        self._dialect = SQLiteDialect()

        self._register_sqlite_adapters()

    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def set_pragma(self, pragma_key: str, pragma_value: Any) -> None:
        """Set a pragma parameter at runtime.

        Args:
            pragma_key: The pragma name to set.
            pragma_value: The value to set for the pragma.

        Raises:
            ConnectionError: If the pragma cannot be set.

        .. warning::
            **SECURITY WARNING**: This method directly concatenates the pragma key and value
            into SQL statements without parameterization. Users MUST NOT expose these parameters
            to untrusted input, as this could lead to SQL injection vulnerabilities.

            **Do NOT** accept pragma_key or pragma_value directly from user input without
            proper validation and sanitization. Use a whitelist of allowed pragma names and
            validate values against expected patterns.

            Example of safe usage:

            .. code-block:: python

                # Safe: Using hardcoded or validated values
                backend.set_pragma('journal_mode', 'WAL')
                backend.set_pragma('foreign_keys', 'ON')

                # Dangerous: Accepting user input directly
                # backend.set_pragma(user_input_key, user_input_value)  # NEVER do this!
        """
        pragma_value_str = str(pragma_value)
        self.config.pragmas[pragma_key] = pragma_value_str

        if self._connection:
            pragma_statement = f"PRAGMA {pragma_key} = {pragma_value_str}"
            self.log(logging.DEBUG, f"Setting pragma: {pragma_statement}")
            try:
                self._connection.execute(pragma_statement)
            except sqlite3.Error as e:
                error_msg = f"Failed to set pragma {pragma_key}: {str(e)}"
                self.log(logging.ERROR, error_msg)
                raise ConnectionError(error_msg) from e

    def _apply_pragmas(self) -> None:
        """Apply all pragma settings to the connection."""
        for pragma_key, pragma_value in self.config.pragmas.items():
            pragma_statement = f"PRAGMA {pragma_key} = {pragma_value}"
            self.log(logging.DEBUG, f"Executing pragma: {pragma_statement}")
            try:
                self._connection.execute(pragma_statement)
            except sqlite3.Error as e:
                self.log(logging.WARNING, f"Failed to execute pragma {pragma_statement}: {str(e)}")

    def connect(self) -> None:
        """Establish a connection to the SQLite database."""
        try:
            sqlite3.register_converter("timestamp", lambda val: datetime.fromisoformat(val.decode("utf-8")))
            self.log(logging.INFO, f"Connecting to SQLite database: {self.config.database}")
            self._connection = sqlite3.connect(
                self.config.database,
                detect_types=self.config.detect_types,
                isolation_level=None,
                uri=self.config.uri,
                timeout=self.config.timeout,
                check_same_thread=self.config.check_same_thread,
            )
            self._apply_pragmas()
            self._connection.row_factory = sqlite3.Row
            self.log(logging.INFO, "Connected to SQLite database successfully")
        except sqlite3.Error as e:
            self.log(logging.ERROR, f"Failed to connect to SQLite database: {str(e)}")
            raise ConnectionError(f"Failed to connect: {str(e)}") from e

    def disconnect(self) -> None:
        """Close the connection to the SQLite database."""
        try:
            if self._connection:
                self.log(logging.INFO, "Disconnecting from SQLite database")
                if self.transaction_manager.is_active:
                    self.log(logging.WARNING, "Active transaction detected during disconnect, rolling back")
                    self.transaction_manager.rollback()
                self._connection.close()
                self._connection = None
                self._cursor = None
                self._transaction_manager = None
                self.log(logging.INFO, "Disconnected from SQLite database")

                if self.config.delete_on_close and not self.config.is_memory_db():
                    self._delete_database_files()
            else:
                self.log(logging.DEBUG, "Disconnect called on already closed connection")
        except sqlite3.Error as e:
            self.log(logging.ERROR, f"Error during disconnect: {str(e)}")
            raise ConnectionError(f"Failed to disconnect: {str(e)}") from e

    def _delete_database_files(self) -> None:
        """Delete database files when delete_on_close is enabled."""
        import os

        self.log(logging.INFO, f"Deleting database files: {self.config.database}")

        def retry_delete(file_path: str, max_retries: int = 5, retry_delay: float = 0.1) -> bool:
            for attempt in range(max_retries):
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    return True
                except OSError as e:
                    if attempt < max_retries - 1:
                        self.log(logging.DEBUG, f"Failed to delete file {file_path}, retrying: {str(e)}")
                        time.sleep(retry_delay)
                    else:
                        self.log(
                            logging.WARNING,
                            f"Failed to delete file {file_path}, maximum retry attempts reached: {str(e)}",
                        )
                        return False
            return False

        try:
            main_db_deleted = retry_delete(self.config.database)
            wal_deleted = retry_delete(f"{self.config.database}-wal")
            shm_deleted = retry_delete(f"{self.config.database}-shm")

            if main_db_deleted and wal_deleted and shm_deleted:
                self.log(logging.INFO, "Database files deleted successfully")
            else:
                self.log(logging.WARNING, "Some database files could not be deleted after multiple attempts")
        except Exception as e:
            self.log(logging.ERROR, f"Failed to delete database files: {str(e)}")
            raise ConnectionError(f"Failed to delete database files: {str(e)}") from e

    def ping(self, reconnect: bool = True) -> bool:
        """Test the database connection and optionally reconnect."""
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

    def _get_cursor(self):
        """Get or create cursor for SQLite."""
        return self._connection.cursor()

    def _handle_auto_commit_if_needed(self) -> None:
        """Handle auto-commit for SQLite."""
        if not self.in_transaction and self._connection:
            self._connection.commit()
            self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")

    def _handle_error(self, error: Exception) -> None:
        """Handle SQLite-specific errors and convert to appropriate exceptions."""
        self._handle_sqlite_error(error)

    def executescript(self, sql_script: str) -> None:
        """Execute a multi-statement SQL script."""
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

    def execute_many(self, sql: str, params_list: List[Tuple]) -> Optional[QueryResult]:
        """Execute batch operations with the same SQL statement and multiple parameter sets."""
        self.log(logging.INFO, f"Executing batch operation: {sql} with {len(params_list)} parameter sets")
        start_time = time.perf_counter()
        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            cursor = self._cursor or self._connection.cursor()
            cursor.executemany(sql, params_list)
            duration = time.perf_counter() - start_time

            self.log(
                logging.INFO, f"Batch operation completed, affected {cursor.rowcount} rows, duration={duration:.3f}s"
            )
            self._handle_auto_commit_if_needed()

            return QueryResult(affected_rows=cursor.rowcount, duration=duration)
        except Exception as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            self._handle_error(e)
            return None

    def _handle_auto_commit(self) -> None:
        """Handle auto commit based on SQLite connection and transaction state."""
        try:
            if not self._connection:
                return
            if not self._transaction_manager or not self._transaction_manager.is_active:
                self._connection.commit()
                self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")
        except Exception as e:
            self.log(logging.WARNING, f"Failed to auto-commit: {str(e)}")

    @property
    def transaction_manager(self) -> SQLiteTransactionManager:
        """Get the transaction manager."""
        if not self._transaction_manager:
            if not self._connection:
                self.log(logging.DEBUG, "Initializing connection for transaction manager")
                self.connect()
            self.log(logging.DEBUG, "Creating new transaction manager")
            self._transaction_manager = SQLiteTransactionManager(self._connection, self.logger)
        return self._transaction_manager

    def insert(self, options: InsertOptions) -> QueryResult:
        """Insert a record with special handling for RETURNING clause."""
        result = super().insert(options)
        if (
            result.affected_rows == 0
            and options.returning_columns is not None
            and options.returning_columns
            and result.data is not None
            and len(result.data) > 0
        ):
            result.affected_rows = len(result.data)
        return result

    def update(self, options: UpdateOptions) -> QueryResult:
        """Update records with special handling for RETURNING clause."""
        result = super().update(options)
        if (
            result.affected_rows == 0
            and options.returning_columns is not None
            and options.returning_columns
            and result.data is not None
            and len(result.data) > 0
        ):
            result.affected_rows = len(result.data)
        return result

    def delete(self, options: DeleteOptions) -> QueryResult:
        """Delete records with special handling for RETURNING clause."""
        result = super().delete(options)
        if (
            result.affected_rows == 0
            and options.returning_columns is not None
            and options.returning_columns
            and result.data is not None
            and len(result.data) > 0
        ):
            result.affected_rows = len(result.data)
        return result

    def get_server_version(self) -> Tuple[int, int, int]:
        """Get SQLite version.

        Uses the sqlite3 module's version info, which doesn't require a connection.
        Falls back to querying the database only if the module version is unavailable.

        Returns:
            Tuple of (major, minor, patch) version numbers.
        """
        if SQLiteBackend._sqlite_version_cache is None:
            # Prefer module version (no connection needed)
            try:
                version_info = sqlite3.sqlite_version_info
                if version_info and len(version_info) >= 3:
                    SQLiteBackend._sqlite_version_cache = version_info[:3]
                    self.log(
                        logging.INFO, f"Detected SQLite version: {version_info[0]}.{version_info[1]}.{version_info[2]}"
                    )
                    return SQLiteBackend._sqlite_version_cache
            except Exception:
                pass

            # Fallback to query if needed (for older Python versions)
            try:
                if not self._connection:
                    self.connect()
                cursor = self._connection.cursor()
                cursor.execute("SELECT sqlite_version()")
                version_str = cursor.fetchone()[0]
                cursor.close()

                version_parts = version_str.split(".")
                major = int(version_parts[0])
                minor = int(version_parts[1]) if len(version_parts) > 1 else 0
                patch = int(version_parts[2]) if len(version_parts) > 2 else 0

                SQLiteBackend._sqlite_version_cache = (major, minor, patch)
                self.log(logging.INFO, f"Detected SQLite version (from query): {major}.{minor}.{patch}")
            except Exception as e:
                error_msg = f"Failed to determine SQLite version: {str(e)}"
                if hasattr(self, "logger"):
                    self.logger.error(error_msg)
                from rhosocial.activerecord.backend.errors import OperationalError

                raise OperationalError(error_msg) from e

        return SQLiteBackend._sqlite_version_cache

    def introspect_and_adapt(self) -> None:
        """Introspect backend and adapt backend instance to actual server capabilities.

        This method ensures a connection exists (if not already cached), queries
        the actual SQLite version, and updates the backend's internal state.

        Note: SQLite version is cached at class level for efficiency. If the version
        is already cached, a new connection is only needed for extension detection
        on SQLite < 3.38.0.
        """
        # Ensure connection exists for version detection or extension checks
        if not self._connection:
            self.connect()

        # Get the actual SQLite version and update the dialect
        version = self.get_server_version()
        self._dialect.version = version
        self.log(logging.INFO, f"Adapted dialect version to SQLite {version[0]}.{version[1]}.{version[2]}")

        # For SQLite < 3.38.0, detect json1 extension availability at runtime
        if version < (3, 38, 0):
            json1_available = self._detect_json1_extension()
            self._dialect.set_runtime_param("json1_available", json1_available)
            status = "available" if json1_available else "unavailable"
            self.log(logging.INFO, f"JSON1 extension runtime detection: {status}")

    def _detect_json1_extension(self) -> bool:
        """Detect if json1 extension is available at runtime.

        Returns False if no connection is established.
        """
        if self._connection is None:
            return False
        try:
            cursor = self._connection.cursor()
            cursor.execute("SELECT json('{}')")
            cursor.close()
            return True
        except sqlite3.Error:
            return False
