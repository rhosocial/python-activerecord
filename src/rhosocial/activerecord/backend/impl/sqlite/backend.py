import logging
import re
import sqlite3
import sys
import time
from sqlite3 import ProgrammingError
from typing import Optional, Tuple, List, Any, Dict, Union

from .dialect import SQLiteDialect, SQLDialectBase
from .transaction import SQLiteTransactionManager
from ...dialect import ReturningOptions
from ...base import StorageBackend, ColumnTypes
from ...errors import ConnectionError, IntegrityError, OperationalError, QueryError, DeadlockError, DatabaseError, \
    ReturningNotSupportedError, JsonOperationNotSupportedError
from ...typing import QueryResult


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
        self._isolation_level = kwargs.get("isolation_level", None)
        self._transaction_manager = None
        self._dialect = SQLiteDialect(self.config)
        self._delete_on_close = kwargs.get("delete_on_close", False)

        # Extract custom pragmas from options
        self._pragmas = self._get_pragma_settings(kwargs)

    @property
    def pragmas(self) -> Dict[str, str]:
        """Get current pragma settings

        Returns:
            Dict[str, str]: Current pragma settings
        """
        return self._pragmas.copy()

    def set_pragma(self, pragma_key: str, pragma_value: Any) -> None:
        """Set a pragma parameter at runtime

        Args:
            pragma_key: Pragma parameter name
            pragma_value: Pragma parameter value

        Raises:
            ConnectionError: If pragma cannot be set
        """
        pragma_value_str = str(pragma_value)
        self._pragmas[pragma_key] = pragma_value_str

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

    def _get_pragma_settings(self, kwargs: Dict[str, Any]) -> Dict[str, str]:
        """Extract and merge pragma settings from options

        Args:
            kwargs: Configuration parameters

        Returns:
            Dict[str, str]: Merged pragma settings with defaults
        """
        pragmas = self.DEFAULT_PRAGMAS.copy()
        custom_pragmas = {}

        # Check for pragmas in options dictionary
        if "pragmas" in kwargs:
            custom_pragmas = kwargs["pragmas"]
        elif hasattr(self.config, "pragmas") and self.config.pragmas:  # 添加这一行
            custom_pragmas = self.config.pragmas  # 添加这一行
        elif "options" in kwargs and "pragmas" in kwargs["options"]:
            custom_pragmas = kwargs["options"]["pragmas"]
        elif hasattr(self.config, "options") and "pragmas" in self.config.options:
            custom_pragmas = self.config.options["pragmas"]

        # Override defaults with custom settings
        if custom_pragmas:
            for pragma_key, pragma_value in custom_pragmas.items():
                pragmas[pragma_key] = str(pragma_value)

        return pragmas

    def _apply_pragmas(self) -> None:
        """Apply all pragma settings to the connection"""
        for pragma_key, pragma_value in self._pragmas.items():
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
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                isolation_level=None,  # Use manual transaction management
                uri=self.config.options['uri'] if 'uri' in self.config.options else False
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
        """Close the connection to the SQLite database."""
        if self._connection:
            try:
                self.log(logging.INFO, "Disconnecting from SQLite database")
                if self.transaction_manager.is_active:
                    self.log(logging.WARNING, "Active transaction detected during disconnect, rolling back")
                    self.transaction_manager.rollback()
                self._connection.close()
                self._connection = None
                self._cursor = None
                self._transaction_manager = None
                self.log(logging.INFO, "Disconnected from SQLite database")

                # Handle file deletion if enabled and not using in-memory database
                if self._delete_on_close and self.config.database != ":memory:":
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
                                        self.log(logging.DEBUG, f"Failed to delete file {file_path}, retrying: {str(e)}")
                                        time.sleep(retry_delay)  # Wait for a while before retrying
                                    else:
                                        self.log(logging.WARNING, f"Failed to delete file {file_path}, maximum retry attempts reached: {str(e)}")
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
                            self.log(logging.WARNING, "Some database files could not be deleted after multiple attempts")
                    except Exception as e:
                        self.log(logging.ERROR, f"Failed to delete database files: {str(e)}")
                        raise ConnectionError(f"Failed to delete database files: {str(e)}")
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
                self.log(logging.INFO, "Reconnecting during ping")
                self.connect()
                return True
            return False

        try:
            self.log(logging.DEBUG, "Testing connection with SELECT 1")
            self._connection.execute("SELECT 1")
            return True
        except sqlite3.Error as e:
            self.log(logging.WARNING, f"Ping failed: {str(e)}")
            if reconnect:
                self.log(logging.INFO, "Reconnecting after failed ping")
                self.connect()
                return True
            return False

    @property
    def is_sqlite(self) -> bool:
        """Flag to identify SQLite backend for compatibility checks"""
        return True

    def _get_statement_type(self, sql: str) -> str:
        """
        Parse the SQL statement type from the query.

        SQLite supports pragmas which start with 'PRAGMA'.

        Args:
            sql: SQL statement

        Returns:
            str: Statement type in uppercase
        """
        # Strip comments and whitespace for better detection
        clean_sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE).strip()

        # Check for PRAGMA statements
        if clean_sql.upper().startswith('PRAGMA'):
            return 'PRAGMA'

        # Default to base implementation
        return super()._get_statement_type(clean_sql)

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

    def _check_returning_compatibility(self, options: ReturningOptions) -> None:
        """
        Check compatibility issues with RETURNING clause in SQLite.

        SQLite with Python < 3.10 has known issues with RETURNING where
        affected_rows is always reported as 0.

        Args:
            options: RETURNING options

        Raises:
            ReturningNotSupportedError: If compatibility issues found and not forced
        """
        # Check SQLite version support
        version = sqlite3.sqlite_version_info
        if version < (3, 35, 0) and not options.force:
            error_msg = (
                f"RETURNING clause requires SQLite 3.35.0+. Current version: {sqlite3.sqlite_version}. "
                f"Use force=True to attempt anyway if your SQLite binary supports it."
            )
            self.log(logging.WARNING, error_msg)
            raise ReturningNotSupportedError(error_msg)

        # Check Python version compatibility
        if sys.version_info < (3, 10) and not options.force:
            error_msg = (
                "RETURNING clause has known issues in Python < 3.10 with SQLite: "
                "affected_rows always reports 0 regardless of actual rows affected. "
                "Use force=True to use anyway if you understand these limitations."
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

    def _execute_query(self, cursor, sql: str, params: Optional[Tuple]):
        """
        Execute query in SQLite.

        Args:
            cursor: SQLite cursor
            sql: SQL statement
            params: Query parameters

        Returns:
            sqlite3.Cursor: Cursor with executed query
        """
        # Execute with parameters if provided
        if params:
            processed_params = tuple(
                self.dialect.value_mapper.to_database(value, None)
                for value in params
            )
            cursor.execute(sql, processed_params)
        else:
            cursor.execute(sql)

        return cursor

    def _process_result_set(self, cursor, is_select: bool, need_returning: bool, column_types: Optional[ColumnTypes]) -> \
    Optional[List[Dict]]:
        """
        Process query result set for SQLite.

        SQLite returns Row objects which can be accessed like dictionaries.

        Args:
            cursor: SQLite cursor with executed query
            is_select: Whether this is a SELECT query
            need_returning: Whether RETURNING clause was used
            column_types: Column type mapping for conversion

        Returns:
            Optional[List[Dict]]: Processed result rows or None
        """
        if not (is_select or need_returning):
            return None

        # Fetch all rows
        rows = cursor.fetchall()
        self.log(logging.DEBUG, f"Fetched {len(rows)} rows")

        if not rows:
            return []

        # Apply type conversions if specified
        if column_types:
            self.log(logging.DEBUG, "Applying type conversions")
            data = []
            for row in rows:
                # Convert sqlite3.Row to dict and apply type conversions
                converted_row = {}
                for key in row.keys():
                    value = row[key]
                    db_type = column_types.get(key)
                    if db_type is not None:
                        converted_row[key] = self.dialect.value_mapper.from_database(value, db_type)
                    else:
                        converted_row[key] = value
                data.append(converted_row)
            return data
        else:
            # Convert sqlite3.Row objects to regular dictionaries
            return [dict(row) for row in rows]

    def _handle_auto_commit_if_needed(self) -> None:
        """
        Handle auto-commit for SQLite.

        SQLite requires explicit commit when using isolation_level=None.
        """
        if not self.in_transaction and self._connection:
            self._connection.commit()
            self.log(logging.DEBUG, "Auto-committed operation (not in active transaction)")

    def _handle_execution_error(self, error: Exception):
        """
        Handle SQLite-specific errors during execution.

        Args:
            error: Exception raised during execution

        Raises:
            Appropriate database exception based on error type
        """
        if isinstance(error, sqlite3.Error):
            error_msg = str(error)

            if isinstance(error, sqlite3.OperationalError):
                if "database is locked" in error_msg:
                    self.log(logging.ERROR, f"Database lock error: {error_msg}")
                    raise OperationalError("Database is locked")
                elif "no such table" in error_msg:
                    self.log(logging.ERROR, f"Table not found: {error_msg}")
                    raise QueryError(f"Table not found: {error_msg}")

            elif isinstance(error, sqlite3.IntegrityError):
                if "UNIQUE constraint failed" in error_msg:
                    self.log(logging.ERROR, f"Unique constraint violation: {error_msg}")
                    raise IntegrityError(f"Unique constraint violation: {error_msg}")
                elif "FOREIGN KEY constraint failed" in error_msg:
                    self.log(logging.ERROR, f"Foreign key constraint violation: {error_msg}")
                    raise IntegrityError(f"Foreign key constraint violation: {error_msg}")

        # Call parent handler for common error processing
        super()._handle_execution_error(error)

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

    def execute_many(
            self,
            sql: str,
            params_list: List[Tuple]
    ) -> Optional[QueryResult]:
        """Execute batch operations

        Args:
            sql: SQL statement
            params_list: List of parameter tuples

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

            # Convert all parameters
            converted_params = []
            for params in params_list:
                if params:
                    converted = tuple(
                        self.value_mapper.to_database(value, None)
                        for value in params
                    )
                    converted_params.append(converted)

            cursor.executemany(sql, converted_params)
            duration = time.perf_counter() - start_time

            self.log(logging.INFO,
                     f"Batch operation completed, affected {cursor.rowcount} rows, duration={duration:.3f}s")

            return QueryResult(
                affected_rows=cursor.rowcount,
                duration=duration
            )
        except Exception as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            self._handle_error(e)

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

    @property
    def supports_returning(self) -> bool:
        """Check if SQLite version supports RETURNING clause"""
        supported = tuple(map(int, sqlite3.sqlite_version.split('.'))) >= (3, 35, 0)
        self.log(logging.DEBUG, f"RETURNING clause support: {supported}")
        return supported

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