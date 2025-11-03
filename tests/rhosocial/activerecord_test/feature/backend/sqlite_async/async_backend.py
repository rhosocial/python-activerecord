# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/async_backend.py
"""
Async SQLite Backend Implementation for Testing

This module provides an async implementation of SQLite backend for testing purposes only.
It demonstrates that the async backend abstraction is workable, but is NOT intended for
production use or distribution to end users.

Uses aiosqlite library for async SQLite operations.
"""
from sqlite3 import ProgrammingError

import aiosqlite
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, Union

from rhosocial.activerecord.backend import DatabaseCapabilities, ALL_SET_OPERATIONS
from rhosocial.activerecord.backend.base import AsyncStorageBackend
from rhosocial.activerecord.backend.capabilities import JoinCapability, TransactionCapability, BulkOperationCapability, \
    ConstraintCapability, DateTimeFunctionCapability, AggregateFunctionCapability, CTECapability, JSONCapability, \
    ALL_WINDOW_FUNCTIONS, ALL_RETURNING_FEATURES, MathematicalFunctionCapability, StringFunctionCapability
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.dialect import ReturningOptions
from rhosocial.activerecord.backend.errors import (
    ConnectionError,
    DatabaseError,
    IntegrityError,
    OperationalError,
    QueryError,
    ReturningNotSupportedError,
    TransactionError, DeadlockError,
)
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.transaction import IsolationLevel


class AsyncTransactionManager:
    """Async transaction manager for SQLite"""

    def __init__(self, connection: aiosqlite.Connection, logger: Optional[logging.Logger] = None):
        self._connection = connection
        self._transaction_level = 0
        self._savepoint_count = 0
        self._active_savepoints: List[str] = []
        self._isolation_level = IsolationLevel.SERIALIZABLE
        self._logger = logger or logging.getLogger('transaction')

    @property
    def is_active(self) -> bool:
        """Check if transaction is active"""
        return self._transaction_level > 0

    @property
    def logger(self) -> logging.Logger:
        """Get logger"""
        return self._logger

    @logger.setter
    def logger(self, logger: Optional[logging.Logger]):
        """Set logger"""
        if logger is None:
            self._logger = logging.getLogger('transaction')
        elif not isinstance(logger, logging.Logger):
            raise ValueError("Logger must be a logging.Logger instance")
        else:
            self._logger = logger

    def log(self, level: int, message: str, *args, **kwargs):
        """Log message"""
        self._logger.log(level, message, *args, **kwargs)

    @property
    def isolation_level(self) -> IsolationLevel:
        """Get isolation level"""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: IsolationLevel):
        """Set isolation level"""
        self.log(logging.DEBUG, f"Setting isolation level to {level}")

        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise TransactionError("Cannot change isolation level during active transaction")

        if level not in [IsolationLevel.SERIALIZABLE, IsolationLevel.READ_UNCOMMITTED]:
            self.log(logging.ERROR, f"Unsupported isolation level: {level}")
            raise TransactionError(f"Unsupported isolation level: {level}")

        self._isolation_level = level

    async def begin(self):
        """Begin transaction"""
        self.log(logging.DEBUG, f"Beginning transaction (level {self._transaction_level})")

        try:
            if self._transaction_level == 0:
                # Begin outermost transaction
                if self._isolation_level == IsolationLevel.SERIALIZABLE:
                    await self._connection.execute("BEGIN IMMEDIATE")
                    await self._connection.execute("PRAGMA read_uncommitted = 0")
                else:
                    await self._connection.execute("BEGIN DEFERRED")
                    await self._connection.execute("PRAGMA read_uncommitted = 1")

                self.log(logging.INFO, f"Starting new transaction with isolation level {self._isolation_level}")
            else:
                # Begin nested transaction using savepoint
                savepoint_name = f"LEVEL{self._transaction_level}"
                await self._connection.execute(f"SAVEPOINT {savepoint_name}")
                self._active_savepoints.append(savepoint_name)
                self.log(logging.INFO, f"Creating savepoint {savepoint_name} for nested transaction")

            self._transaction_level += 1
        except Exception as e:
            self.log(logging.ERROR, f"Failed to begin transaction: {e}")
            raise TransactionError(f"Failed to begin transaction: {e}")

    async def commit(self):
        """Commit transaction"""
        if not self.is_active:
            self.log(logging.ERROR, "No active transaction to commit")
            raise TransactionError("No active transaction to commit")

        self.log(logging.DEBUG, f"Committing transaction (level {self._transaction_level})")

        try:
            if self._transaction_level == 1:
                # Commit outermost transaction
                await self._connection.commit()
                self.log(logging.INFO, "Committing outermost transaction")
            else:
                # Release nested transaction savepoint
                savepoint_name = self._active_savepoints.pop()
                await self._connection.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                self.log(logging.INFO, f"Releasing savepoint {savepoint_name} for nested transaction")

            self._transaction_level -= 1
        except Exception as e:
            self.log(logging.ERROR, f"Failed to commit transaction: {e}")
            raise TransactionError(f"Failed to commit transaction: {e}")

    async def rollback(self):
        """Rollback transaction"""
        if not self.is_active:
            self.log(logging.ERROR, "No active transaction to rollback")
            raise TransactionError("No active transaction to rollback")

        self.log(logging.DEBUG, f"Rolling back transaction (level {self._transaction_level})")

        try:
            if self._transaction_level == 1:
                # Rollback outermost transaction
                await self._connection.rollback()
                self.log(logging.INFO, "Rolling back outermost transaction")
            else:
                # Rollback to nested transaction savepoint
                savepoint_name = self._active_savepoints.pop()
                await self._connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                self.log(logging.INFO, f"Rolling back to savepoint {savepoint_name} for nested transaction")

            self._transaction_level -= 1
        except Exception as e:
            self.log(logging.ERROR, f"Failed to rollback transaction: {e}")
            raise TransactionError(f"Failed to rollback transaction: {e}")

    def savepoint(self, name: Optional[str] = None) -> str:
        """Create savepoint (sync method for compatibility)"""
        raise NotImplementedError("Use async version: async_savepoint")

    async def async_savepoint(self, name: Optional[str] = None) -> str:
        """Create savepoint"""
        if not self.is_active:
            self.log(logging.ERROR, "Cannot create savepoint: no active transaction")
            raise TransactionError("Cannot create savepoint: no active transaction")

        if name is None:
            self._savepoint_count += 1
            name = f"SP_{self._savepoint_count}"

        self.log(logging.DEBUG, f"Creating savepoint (name: {name})")

        try:
            await self._connection.execute(f"SAVEPOINT {name}")
            self._active_savepoints.append(name)
            self.log(logging.INFO, f"Creating savepoint: {name}")
            return name
        except Exception as e:
            self.log(logging.ERROR, f"Failed to create savepoint {name}: {e}")
            raise TransactionError(f"Failed to create savepoint {name}: {e}")

    async def release(self, name: str):
        """Release savepoint"""
        if name not in self._active_savepoints:
            self.log(logging.ERROR, f"Invalid savepoint name: {name}")
            raise TransactionError(f"Invalid savepoint name: {name}")

        self.log(logging.DEBUG, f"Releasing savepoint: {name}")

        try:
            await self._connection.execute(f"RELEASE SAVEPOINT {name}")
            self._active_savepoints.remove(name)
            self.log(logging.INFO, f"Releasing savepoint: {name}")
        except Exception as e:
            self.log(logging.ERROR, f"Failed to release savepoint {name}: {e}")
            raise TransactionError(f"Failed to release savepoint {name}: {e}")

    async def rollback_to(self, name: str):
        """Rollback to savepoint"""
        if name not in self._active_savepoints:
            self.log(logging.ERROR, f"Invalid savepoint name: {name}")
            raise TransactionError(f"Invalid savepoint name: {name}")

        self.log(logging.DEBUG, f"Rolling back to savepoint: {name}")

        try:
            await self._connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
            self.log(logging.INFO, f"Rolling back to savepoint: {name}")
        except Exception as e:
            self.log(logging.ERROR, f"Failed to rollback to savepoint {name}: {e}")
            raise TransactionError(f"Failed to rollback to savepoint {name}: {e}")

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported"""
        return True


class AsyncSQLiteBackend(AsyncStorageBackend):
    """Async SQLite backend implementation for testing"""

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
            ConstraintCapability.CHECK,
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

    async def _handle_error(self, error: Exception) -> None:
        error_msg = str(error)

        if isinstance(error, sqlite3.Error):
            if isinstance(error, sqlite3.OperationalError):
                if "database is locked" in error_msg:
                    self.log(logging.ERROR, f"Database lock error: {error_msg}")
                    raise OperationalError("Database is locked") from error
                elif "no such table" in error_msg:
                    self.log(logging.ERROR, f"Table not found: {error_msg}")
                    raise QueryError(f"Table not found: {error_msg}") from error
                self.log(logging.ERROR, f"SQLite operational error: {error_msg}")
                raise OperationalError(error_msg) from error
            elif isinstance(error, sqlite3.IntegrityError):
                if "UNIQUE constraint failed" in error_msg:
                    self.log(logging.ERROR, f"Unique constraint violation: {error_msg}")
                    raise IntegrityError(f"Unique constraint violation: {error_msg}") from error
                elif "FOREIGN KEY constraint failed" in error_msg:
                    self.log(logging.ERROR, f"Foreign key constraint violation: {error_msg}")
                    raise IntegrityError(f"Foreign key constraint violation: {error_msg}") from error
                self.log(logging.ERROR, f"SQLite integrity error: {error_msg}")
                raise IntegrityError(error_msg) from error
            elif "database is locked" in error_msg:  # This is also in OperationalError, but can appear elsewhere
                self.log(logging.ERROR, f"Database deadlock: {error_msg}")
                raise DeadlockError(error_msg) from error
            elif isinstance(error, ProgrammingError):
                self.log(logging.ERROR, f"SQLite programming error: {error_msg}")
                raise DatabaseError(error_msg) from error
            else:
                # Log unknown SQLite errors
                self.log(logging.ERROR, f"Unhandled SQLite error: {error_msg}")
                raise DatabaseError(f"Unhandled SQLite error: {error_msg}") from error
        else:
            # Log and re-raise other errors
            self.log(logging.ERROR, f"Unhandled non-SQLite error: {error_msg}")
            raise error

    _sqlite_version_cache: Optional[Tuple[int, int, int]] = None

    def __init__(
            self,
            connection_config: Optional[Union[ConnectionConfig, SQLiteConnectionConfig]] = None,
            database: Optional[str] = None,
            **kwargs
    ):
        # Handle backwards compatibility with direct database parameter
        if connection_config is None and database is not None:
            connection_config = SQLiteConnectionConfig(database=database, **kwargs)
        elif connection_config is None:
            raise ValueError("Either connection_config or database must be provided")

        # Ensure it's a SQLiteConnectionConfig
        if not isinstance(connection_config, SQLiteConnectionConfig):
            # Convert generic ConnectionConfig to SQLiteConnectionConfig
            connection_config = SQLiteConnectionConfig(
                database=connection_config.database,
                **{k: v for k, v in connection_config.__dict__.items() if k != 'database'}
            )

        super().__init__(connection_config=connection_config)
        self._connection: Optional[aiosqlite.Connection] = None
        self._cursor: Optional[aiosqlite.Cursor] = None
        self._transaction_manager: Optional[AsyncTransactionManager] = None
        self._dialect = SQLiteDialect(connection_config)

    @property
    def dialect(self) -> SQLiteDialect:
        """Get SQL dialect"""
        return self._dialect

    @property
    def pragmas(self) -> Dict[str, str]:
        """Get pragma settings"""
        return self.config.pragmas.copy()

    @property
    def is_sqlite(self) -> bool:
        """Check if this is SQLite backend"""
        return True

    @property
    def supports_returning(self) -> bool:
        """Check if RETURNING clause is supported"""
        version = self.get_server_version()
        return version >= (3, 35, 0)

    @property
    def transaction_manager(self) -> AsyncTransactionManager:
        """Get transaction manager"""
        if self._transaction_manager is None:
            if self._connection is None:
                raise ConnectionError("Not connected to database")
            self._transaction_manager = AsyncTransactionManager(self._connection, self.logger)
        return self._transaction_manager

    async def connect(self) -> None:
        """Connect to database"""
        try:
            self._connection = await aiosqlite.connect(
                self.config.database,
                timeout=self.config.timeout,
                detect_types=self.config.detect_types,
                isolation_level=None,  # Manual transaction control
                uri=self.config.uri
            )

            # Enable dict row factory
            self._connection.row_factory = aiosqlite.Row

            # Apply pragmas
            await self._apply_pragmas()

            self.logger.info(f"Connected to SQLite database: {self.config.database}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {e}")

    async def disconnect(self) -> None:
        """Disconnect from database"""
        try:
            if self._connection is not None:
                await self._connection.close()
                self._connection = None
                self._cursor = None
                self._transaction_manager = None

            # Delete database files if configured
            if self.config.delete_on_close:
                await self._delete_database_files()
        except Exception as e:
            if self.config.delete_on_close:
                raise ConnectionError(f"Failed to delete database files: {e}")
            # Don't raise for disconnect errors, just log
            self.logger.warning(f"Error during disconnect: {e}")

    async def _delete_database_files(self):
        """Delete database files"""
        import aiofiles.os
        files_to_delete = [
            self.config.database,
            f"{self.config.database}-wal",
            f"{self.config.database}-shm"
        ]

        for filepath in files_to_delete:
            if await aiofiles.os.path.exists(filepath):
                max_retries = 5
                for attempt in range(max_retries):
                    try:
                        await aiofiles.os.remove(filepath)
                        break
                    except OSError as e:
                        if attempt < max_retries - 1:
                            await self._async_sleep(0.1)
                        else:
                            self.logger.warning(f"Failed to delete {filepath}: {e}")

    async def _async_sleep(self, seconds: float):
        """Async sleep"""
        import asyncio
        await asyncio.sleep(seconds)

    async def _apply_pragmas(self):
        """Apply PRAGMA settings"""
        for pragma_key, pragma_value in self.config.pragmas.items():
            pragma_statement = f"PRAGMA {pragma_key} = {pragma_value}"
            self.log(logging.DEBUG, f"Executing pragma: {pragma_statement}")

            try:
                await self._connection.execute(pragma_statement)
            except sqlite3.Error as e:
                # Log the error but continue with other pragmas
                self.log(logging.WARNING, f"Failed to execute pragma {pragma_statement}: {str(e)}")

    def set_pragma(self, key: str, value: str):
        """Set pragma (will be applied on next connect if not connected)"""
        pragmas = self.config.get_pragmas()
        pragmas[key] = str(value)

        if self._connection is not None:
            try:
                # Use sync execute since this is a sync method
                import asyncio
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self._connection.execute(f"PRAGMA {key} = {value}"))
            except Exception as e:
                raise ConnectionError(f"Failed to set pragma {key}: {e}")

    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connection is not None

    async def ping(self, reconnect: bool = True) -> bool:
        """Test connection"""
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

    def get_server_version(self) -> Tuple[int, int, int]:
        """Get SQLite version"""
        if AsyncSQLiteBackend._sqlite_version_cache is not None:
            return AsyncSQLiteBackend._sqlite_version_cache

        try:
            # Use sqlite3.sqlite_version since it's the same for all connections
            version_str = sqlite3.sqlite_version
            parts = version_str.split('.')
            version = tuple(int(p) for p in parts[:3])

            # Pad with zeros if needed
            while len(version) < 3:
                version = version + (0,)

            AsyncSQLiteBackend._sqlite_version_cache = version
            return version
        except Exception:
            # Default version if error
            return 3, 35, 0



    def _convert_params(self, params: Union[Dict[str, Any], Tuple, List]) -> Union[Tuple, List]:
        """Convert parameters for SQLite"""
        if isinstance(params, dict):
            # Convert dict to tuple (SQLite doesn't support named params well)
            return tuple(params.values())
        return params

    def _should_use_returning(self, returning: Union[bool, List[str], ReturningOptions, None]) -> bool:
        """Check if RETURNING should be used"""
        if returning is None or returning is False:
            return False
        if returning is True:
            return True
        if isinstance(returning, list):
            return True
        if isinstance(returning, ReturningOptions):
            return returning.enabled
        return False

    def _check_returning_compatibility(self, options: ReturningOptions):
        """Check RETURNING compatibility"""
        version = self.get_server_version()

        if not options.force:
            if version < (3, 35, 0):
                raise ReturningNotSupportedError(
                    f"RETURNING clause requires SQLite 3.35.0+, current version: {'.'.join(map(str, version))}"
                )

            import sys
            if sys.version_info < (3, 10):
                raise ReturningNotSupportedError(
                    "RETURNING clause has known issues in Python < 3.10. Use force=True to bypass."
                )

    def _add_returning_clause(
            self,
            sql: str,
            returning: Union[bool, List[str], ReturningOptions]
    ) -> str:
        """Add RETURNING clause to SQL"""
        if isinstance(returning, ReturningOptions):
            if returning.columns:
                # Validate column names
                for col in returning.columns:
                    self._validate_column_name(col)
                columns_str = ", ".join(returning.columns)
            else:
                columns_str = "*"
        elif isinstance(returning, list):
            for col in returning:
                self._validate_column_name(col)
            columns_str = ", ".join(returning)
        else:
            columns_str = "*"

        return f"{sql.rstrip(';')} RETURNING {columns_str}"

    def _validate_column_name(self, name: str):
        """Validate column name for SQL injection"""
        # Remove quotes if present
        clean_name = name.strip('"\'`')

        # Check for dangerous patterns
        dangerous = [';', '--', 'DROP', 'DELETE', 'INSERT', 'UPDATE', 'UNION', 'SELECT']
        for pattern in dangerous:
            if pattern in clean_name.upper():
                raise ValueError(f"Invalid column name: {name}")

    async def _handle_auto_commit(self):
        """Handle auto-commit"""
        if self._transaction_manager is None or not self._transaction_manager.is_active:
            try:
                await self._connection.commit()
            except Exception as e:
                self.logger.warning(f"Auto-commit failed: {e}")