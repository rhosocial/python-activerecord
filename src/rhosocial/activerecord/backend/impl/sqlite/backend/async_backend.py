# src/rhosocial/activerecord/backend/impl/sqlite/backend/async_backend.py
"""
Async SQLite Backend Implementation

This module provides an async implementation of SQLite backend.
Uses aiosqlite library for async SQLite operations.
"""

import logging
import sqlite3
import time
from typing import Any, List, Optional, Tuple, Union

import aiosqlite

from .common import SQLiteBackendMixin, SQLiteConcurrencyMixin, DEFAULT_PRAGMAS
from ..config import SQLiteConnectionConfig
from ..dialect import SQLiteDialect
from ..async_transaction import AsyncSQLiteTransactionManager
from rhosocial.activerecord.backend.base import AsyncStorageBackend
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.errors import ConnectionError
from rhosocial.activerecord.backend.explain import AsyncExplainBackendMixin
from rhosocial.activerecord.backend.introspection.backend_mixin import IntrospectorBackendMixin
from rhosocial.activerecord.backend.options import InsertOptions, UpdateOptions, DeleteOptions
from rhosocial.activerecord.backend.result import QueryResult
from ..explain import (
    SQLiteExplainRow,
    SQLiteExplainQueryPlanRow,
    SQLiteExplainResult,
    SQLiteExplainQueryPlanResult,
)


class AsyncSQLiteBackend(
    AsyncExplainBackendMixin,
    IntrospectorBackendMixin,
    SQLiteBackendMixin,
    SQLiteConcurrencyMixin,
    AsyncStorageBackend,
):
    """Async SQLite backend implementation."""

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
        self._connection: Optional[aiosqlite.Connection] = None
        self._cursor: Optional[aiosqlite.Cursor] = None
        self._transaction_manager: Optional[AsyncSQLiteTransactionManager] = None
        self._dialect = SQLiteDialect()

        self._register_sqlite_adapters()

    @property
    def dialect(self) -> SQLiteDialect:
        """Get SQL dialect."""
        return self._dialect


    def _parse_explain_result(self, raw_rows, sql, duration):
        """Return a SQLite-specific typed EXPLAIN result (shared with sync backend)."""
        if "QUERY PLAN" in sql.upper():
            rows = [SQLiteExplainQueryPlanRow(**r) for r in raw_rows]
            return SQLiteExplainQueryPlanResult(
                raw_rows=raw_rows, sql=sql, duration=duration, rows=rows
            )
        rows = [SQLiteExplainRow(**r) for r in raw_rows]
        return SQLiteExplainResult(
            raw_rows=raw_rows, sql=sql, duration=duration, rows=rows
        )

    def _create_introspector(self):
        from ..introspection import AsyncSQLiteIntrospector
        from rhosocial.activerecord.backend.introspection.executor import (
            AsyncIntrospectorExecutor,
        )
        return AsyncSQLiteIntrospector(self, AsyncIntrospectorExecutor(self))

    async def set_pragma(self, pragma_key: str, pragma_value: Any) -> None:
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
                await backend.set_pragma('journal_mode', 'WAL')
                await backend.set_pragma('foreign_keys', 'ON')

                # Dangerous: Accepting user input directly
                # await backend.set_pragma(user_input_key, user_input_value)  # NEVER do this!
        """
        pragma_value_str = str(pragma_value)
        self.config.pragmas[pragma_key] = pragma_value_str

        if self._connection:
            pragma_statement = f"PRAGMA {pragma_key} = {pragma_value_str}"
            self.log(logging.DEBUG, f"Setting pragma: {pragma_statement}")
            try:
                await self._connection.execute(pragma_statement)
            except sqlite3.Error as e:
                error_msg = f"Failed to set pragma {pragma_key}: {str(e)}"
                self.log(logging.ERROR, error_msg)
                raise ConnectionError(error_msg) from e

    async def _apply_pragmas(self) -> None:
        """Apply PRAGMA settings."""
        for pragma_key, pragma_value in self.config.pragmas.items():
            pragma_statement = f"PRAGMA {pragma_key} = {pragma_value}"
            self.log(logging.DEBUG, f"Executing pragma: {pragma_statement}")
            try:
                await self._connection.execute(pragma_statement)
            except sqlite3.Error as e:
                self.log(logging.WARNING, f"Failed to execute pragma {pragma_statement}: {str(e)}")

    async def connect(self) -> None:
        """Establish a connection to the SQLite database asynchronously."""
        try:
            self._connection = await aiosqlite.connect(
                self.config.database,
                timeout=self.config.timeout,
                detect_types=self.config.detect_types,
                isolation_level=None,
                uri=self.config.uri,
            )
            self._connection.row_factory = aiosqlite.Row
            await self._apply_pragmas()
            self.logger.info(f"Connected to SQLite database: {self.config.database}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {e}") from e

    async def disconnect(self) -> None:
        """Close the connection to the SQLite database asynchronously."""
        try:
            if self._connection is not None:
                if self._transaction_manager is not None and self._transaction_manager.is_active:
                    self.logger.warning("Active transaction detected during disconnect, rolling back")
                    await self._transaction_manager.rollback()
                await self._connection.close()
                self._connection = None
                self._cursor = None
                self._transaction_manager = None

            if self.config.delete_on_close and not self.config.is_memory_db():
                await self._delete_database_files()
            self.logger.info("Disconnected from SQLite database")
        except Exception as e:
            self.logger.warning(f"Error during disconnect: {e}")

    async def _delete_database_files(self) -> None:
        """Delete database files when delete_on_close is enabled.

        Uses aiofiles.os for async file operations with retry logic.
        """
        import asyncio
        import aiofiles.os

        files_to_delete = [self.config.database, f"{self.config.database}-wal", f"{self.config.database}-shm"]

        for filepath in files_to_delete:
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    if await aiofiles.os.path.exists(filepath):
                        await aiofiles.os.remove(filepath)
                    break
                except OSError as e:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(0.1)
                    else:
                        self.logger.warning(f"Failed to delete {filepath}: {e}")

    async def ping(self, reconnect: bool = True) -> bool:
        """Test the database connection and optionally reconnect asynchronously."""
        try:
            if self._connection is None:
                if reconnect:
                    await self.connect()
                    return True
                return False

            await self._connection.execute("SELECT 1")
            return True
        except Exception:
            if reconnect:
                try:
                    await self.connect()
                    return True
                except Exception:
                    return False
            return False

    async def _get_cursor(self):
        """Get database cursor for async operations."""
        if not self._connection:
            await self.connect()
        return await self._connection.cursor()

    async def _handle_auto_commit_if_needed(self):
        """Handle auto-commit if needed."""
        if not self.in_transaction:
            try:
                await self._connection.commit()
            except Exception as e:
                self.logger.warning(f"Auto-commit failed: {e}")

    async def _handle_error(self, error: Exception) -> None:
        """Handle SQLite-specific errors and convert to appropriate exceptions."""
        self._handle_sqlite_error(error)

    async def executescript(self, sql_script: str) -> None:
        """Execute a multi-statement SQL script asynchronously."""
        self.log(logging.INFO, "Executing SQL script asynchronously.")
        start_time = time.perf_counter()
        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                await self.connect()

            await self._connection.executescript(sql_script)
            duration = time.perf_counter() - start_time
            self.log(logging.INFO, f"Async SQL script executed successfully, duration={duration:.3f}s")
            await self._handle_auto_commit()

        except Exception as e:
            self.log(logging.ERROR, f"Error executing async SQL script: {str(e)}")
            await self._handle_error(e)

    async def execute_many(self, sql: str, params_list: List[Tuple]) -> Optional[QueryResult]:
        """Execute batch operations with the same SQL statement and multiple parameter sets.

        Args:
            sql: The SQL statement to execute.
            params_list: List of parameter tuples for each execution.

        Returns:
            QueryResult with affected_rows and duration, or None on error.
        """
        self.log(logging.INFO, f"Executing batch operation: {sql} with {len(params_list)} parameter sets")
        start_time = time.perf_counter()
        try:
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                await self.connect()

            cursor = await self._connection.cursor()
            await cursor.executemany(sql, params_list)
            duration = time.perf_counter() - start_time

            self.log(
                logging.INFO, f"Batch operation completed, affected {cursor.rowcount} rows, duration={duration:.3f}s"
            )
            await self._handle_auto_commit_if_needed()

            return QueryResult(affected_rows=cursor.rowcount, duration=duration)
        except Exception as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            await self._handle_error(e)
            return None

    async def _handle_auto_commit(self):
        """Handle auto-commit."""
        if self._transaction_manager is None or not self._transaction_manager.is_active:
            try:
                await self._connection.commit()
            except Exception as e:
                self.logger.warning(f"Auto-commit failed: {e}")

    @property
    def transaction_manager(self) -> AsyncSQLiteTransactionManager:
        """Get transaction manager."""
        if self._transaction_manager is None:
            if self._connection is None:
                raise ConnectionError("Not connected to database")
            self._transaction_manager = AsyncSQLiteTransactionManager(self, self.logger)
        return self._transaction_manager

    async def insert(self, options: InsertOptions) -> QueryResult:
        """Insert a record with special handling for RETURNING clause.

        Args:
            options: Insert options containing data and returning columns.

        Returns:
            QueryResult with proper affected_rows for RETURNING clause.
        """
        result = await super().insert(options)
        if (
            result.affected_rows == 0
            and options.returning_columns is not None
            and options.returning_columns
            and result.data is not None
            and len(result.data) > 0
        ):
            result.affected_rows = len(result.data)
        return result

    async def update(self, options: UpdateOptions) -> QueryResult:
        """Update records with special handling for RETURNING clause.

        Args:
            options: Update options containing data and returning columns.

        Returns:
            QueryResult with proper affected_rows for RETURNING clause.
        """
        result = await super().update(options)
        if (
            result.affected_rows == 0
            and options.returning_columns is not None
            and options.returning_columns
            and result.data is not None
            and len(result.data) > 0
        ):
            result.affected_rows = len(result.data)
        return result

    async def delete(self, options: DeleteOptions) -> QueryResult:
        """Delete records with special handling for RETURNING clause.

        Args:
            options: Delete options containing returning columns.

        Returns:
            QueryResult with proper affected_rows for RETURNING clause.
        """
        result = await super().delete(options)
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

        Uses the aiosqlite module's version info, which doesn't require a connection.
        Falls back to querying the database only if the module version is unavailable.

        Returns:
            Tuple of (major, minor, patch) version numbers.
        """
        if AsyncSQLiteBackend._sqlite_version_cache is not None:
            return AsyncSQLiteBackend._sqlite_version_cache

        try:
            version_str = aiosqlite.sqlite_version
            parts = version_str.split(".")
            version = tuple(int(p) for p in parts[:3])

            while len(version) < 3:
                version = version + (0,)

            AsyncSQLiteBackend._sqlite_version_cache = version
            self.log(logging.INFO, f"Detected SQLite version: {version[0]}.{version[1]}.{version[2]}")
            return version
        except Exception as e:
            error_msg = f"Failed to determine SQLite version: {str(e)}"
            if hasattr(self, "logger"):
                self.logger.error(error_msg)
            from rhosocial.activerecord.backend.errors import OperationalError

            raise OperationalError(error_msg) from e

    async def introspect_and_adapt(self) -> None:
        """Introspect backend and adapt backend instance to actual server capabilities.

        This method ensures a connection exists (if not already cached), queries
        the actual SQLite version, and updates the backend's internal state.

        Note: SQLite version is cached at class level for efficiency. If the version
        is already cached, a new connection is only needed for extension detection
        on SQLite < 3.38.0.
        """
        # Ensure connection exists for version detection or extension checks
        if not self._connection:
            await self.connect()

        # Get the actual SQLite version and update the dialect
        version = self.get_server_version()
        self._dialect.version = version
        self.log(logging.INFO, f"Adapted dialect version to SQLite {version[0]}.{version[1]}.{version[2]}")

        # Detect math functions availability at runtime
        math_available = await self._detect_math_functions()
        self._dialect.set_runtime_param("math_functions_available", math_available)
        status = "available" if math_available else "unavailable"
        self.log(logging.INFO, f"Math functions runtime detection: {status}")

        # Detect json1 extension availability at runtime
        json1_available = await self._detect_json1_extension()
        self._dialect.set_runtime_param("json1_available", json1_available)
        status = "available" if json1_available else "unavailable"
        self.log(logging.INFO, f"JSON1 extension runtime detection: {status}")

        # Detect virtual table extensions availability via compile options
        compile_options = await self.get_compile_options()
        self._dialect.set_runtime_param("compile_options", compile_options)

    async def _detect_math_functions(self) -> bool:
        """Detect if math functions are available at runtime.

        Returns False if no connection is established.
        """
        if self._connection is None:
            return False
        try:
            cursor = await self._connection.cursor()
            await cursor.execute("SELECT SQRT(4)")
            await cursor.close()
            return True
        except Exception:
            return False

    async def _detect_json1_extension(self) -> bool:
        """Detect if json1 extension is available at runtime.

        Returns False if no connection is established.
        """
        if self._connection is None:
            return False
        try:
            cursor = await self._connection.cursor()
            await cursor.execute("SELECT json('{}')")
            await cursor.close()
            return True
        except Exception:
            return False

    async def get_compile_options(self) -> Dict[str, str]:
        """Get SQLite compile options from PRAGMA compile_options.

        Returns:
            Dictionary mapping option names to their values (empty string if no value)
        """
        if self._connection is None:
            return {}
        options: Dict[str, str] = {}
        try:
            cursor = await self._connection.cursor()
            await cursor.execute("PRAGMA compile_options")
            rows = await cursor.fetchall()
            for row in rows:
                opt_name = row[0]
                if "=" in opt_name:
                    key, value = opt_name.split("=", 1)
                    options[key] = value
                else:
                    options[opt_name] = ""
            await cursor.close()
        except Exception:
            pass
        return options

    async def has_compile_option(self, option_name: str) -> bool:
        """Check if a compile option is enabled.

        Args:
            option_name: Name of the compile option (e.g., "ENABLE_MATH_FUNCTIONS")

        Returns:
            True if the option is enabled
        """
        options = await self.get_compile_options()
        return option_name in options

    async def _detect_json1_extension(self) -> bool:
        """Detect if json1 extension is available at runtime.

        Returns False if no connection is established.
        """
        if self._connection is None:
            return False
        try:
            cursor = await self._connection.cursor()
            await cursor.execute("SELECT json('{}')")
            await cursor.close()
            return True
        except Exception:
            return False
