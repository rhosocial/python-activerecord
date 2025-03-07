import logging
import sqlite3
import sys
import time
from sqlite3 import ProgrammingError
from typing import Optional, Tuple, List, Any, Dict

from .dialect import SQLiteDialect, SQLDialectBase
from .transaction import SQLiteTransactionManager
from ...base import StorageBackend, ColumnTypes
from ...errors import ConnectionError, IntegrityError, OperationalError, QueryError, DeadlockError, DatabaseError, \
    ReturningNotSupportedError
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
                        self.log(logging.INFO, f"Deleting database files: {self.config.database}")
                        # Delete main database file
                        if os.path.exists(self.config.database):
                            os.remove(self.config.database)

                        # Delete WAL and SHM files if they exist
                        wal_file = f"{self.config.database}-wal"
                        shm_file = f"{self.config.database}-shm"
                        if os.path.exists(wal_file):
                            os.remove(wal_file)
                        if os.path.exists(shm_file):
                            os.remove(shm_file)
                        self.log(logging.INFO, "Database files deleted successfully")
                    except OSError as e:
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

    def execute(
            self,
            sql: str,
            params: Optional[Tuple] = None,
            returning: bool = False,
            column_types: Optional[ColumnTypes] = None,
            returning_columns: Optional[List[str]] = None,
            force_returning: bool = False) -> Optional[QueryResult]:
        """Execute SQL statement and return results

        Due to SQLite and Python version differences, RETURNING clause behavior varies:
        - Python 3.10+: Full support for RETURNING clause in INSERT/UPDATE/DELETE
        - Python 3.9 and earlier: RETURNING clause has known issues where affected_rows
          always returns 0, regardless of actual rows affected

        To ensure data consistency and prevent silent failures:
        - SELECT statements work normally in all Python versions when returning=True
        - For INSERT/UPDATE/DELETE in Python 3.9 and earlier:
          - If returning=True and force_returning=False (default), raises ReturningNotSupportedError
          - If returning=True and force_returning=True, executes with warning that affected_rows will be 0
          - Users should either:
            1. Upgrade to Python 3.10+ for full RETURNING support
            2. Set returning=False to execute without RETURNING
            3. Set force_returning=True to execute with known limitations

        Args:
            sql: SQL statement to execute
            params: Query parameters tuple for parameterized queries
            returning: Controls result fetching behavior:
                - For SELECT: True to fetch results (default), False to skip fetching
                - For INSERT/UPDATE/DELETE: True to use RETURNING clause (fully supported in Python 3.10+)
            column_types: Column type mapping for automated type conversion
                Example: {"created_at": DatabaseType.DATETIME, "settings": DatabaseType.JSON}
            returning_columns: Columns to include in RETURNING clause
                - None: Return all columns (*)
                - List[str]: Return specific columns
                - Only used when returning=True for DML statements
                - Ignored for SELECT statements
            force_returning: If True, allows RETURNING clause in Python <3.10 with known issues:
                - affected_rows will always be 0
                - last_insert_id may be unreliable
                - Only use if you understand and can handle these limitations

        Returns:
            QueryResult with fields:
                - data: List[Dict] for SELECT/RETURNING results, None otherwise
                - affected_rows: Number of rows affected (always 0 if force_returning=True in Python <3.10)
                - last_insert_id: Last inserted row ID for INSERT statements
                - duration: Query execution time in seconds

        Raises:
            ConnectionError: Database connection failed or was lost
            QueryError: Invalid SQL syntax or statement execution failed
            TypeConversionError: Failed to convert data types
            ReturningNotSupportedError:
                - RETURNING clause used in Python <3.10 for DML statements without force_returning=True
                - RETURNING clause not supported by SQLite version
            DatabaseError: Other database-related errors
        """
        start_time = time.perf_counter()

        # Log query start
        self.log(logging.DEBUG, f"Executing SQL: {sql}, parameters: {params}")

        try:
            # Ensure active connection
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            # Parse statement type from SQL
            stmt_type = sql.strip().split(None, 1)[0].upper()
            is_select = stmt_type in ("SELECT", "EXPLAIN")
            is_dml = stmt_type in ("INSERT", "UPDATE", "DELETE")
            need_returning = returning and is_dml

            # Add RETURNING clause for DML statements if needed
            if need_returning:
                # First check if SQLite version supports RETURNING clause
                handler = self.dialect.returning_handler
                if not handler.is_supported:
                    error_msg = f"RETURNING clause not supported by current SQLite version {sqlite3.sqlite_version}"
                    self.log(logging.WARNING, error_msg)
                    raise ReturningNotSupportedError(error_msg)

                # Then check Python version compatibility
                py_version = sys.version_info[:2]
                if py_version < (3, 10) and not force_returning:
                    error_msg = (
                        f"RETURNING clause not supported in Python <3.10 for {stmt_type} statements. "
                        f"Current Python version {py_version[0]}.{py_version[1]} has known SQLite "
                        f"adapter issues where affected_rows is always 0 with RETURNING clause.\n"
                        f"You have three options:\n"
                        f"1. Upgrade to Python 3.10 or higher for full RETURNING support\n"
                        f"2. Set returning=False to execute without RETURNING clause\n"
                        f"3. Set force_returning=True to execute with RETURNING clause, but note:\n"
                        f"   - affected_rows will always be 0\n"
                        f"   - last_insert_id may be unreliable\n"
                        f"   Only use force_returning if you understand these limitations"
                    )
                    self.log(logging.WARNING,
                             f"RETURNING clause not supported in Python {py_version[0]}.{py_version[1]} "
                             f"for {stmt_type} statements")
                    raise ReturningNotSupportedError(error_msg)
                elif py_version < (3, 10) and force_returning:
                    self.log(logging.WARNING,
                             f"Force executing {stmt_type} with RETURNING clause in "
                             f"Python {py_version[0]}.{py_version[1]}. affected_rows will be 0")
                    import warnings
                    warnings.warn(
                        f"Executing {stmt_type} with RETURNING clause in Python {py_version[0]}.{py_version[1]}. "
                        f"Be aware that:\n"
                        f"- affected_rows will always be 0\n"
                        f"- last_insert_id may be unreliable",
                        RuntimeWarning
                    )

                # Format and append RETURNING clause
                sql += " " + handler.format_clause(returning_columns)

            # Get or create cursor
            cursor = self._cursor or self._connection.cursor()

            # Process SQL and parameters through dialect
            final_sql, final_params = self.build_sql(sql, params)
            self.log(logging.DEBUG, f"Processed SQL: {final_sql}, parameters: {params}")

            # Execute query with type conversion for parameters
            if final_params:
                processed_params = tuple(
                    self.dialect.value_mapper.to_database(value, None)
                    for value in final_params
                )
                cursor.execute(final_sql, processed_params)
            else:
                cursor.execute(final_sql)

            # Handle result set for SELECT or RETURNING
            data = None
            if returning:
                rows = cursor.fetchall()
                self.log(logging.DEBUG, f"Fetched {len(rows)} rows")
                # Apply type conversions if specified
                if column_types:
                    self.log(logging.DEBUG, "Applying type conversions")
                    data = []
                    for row in rows:
                        converted_row = {}
                        for key, value in dict(row).items():
                            db_type = column_types.get(key)
                            converted_row[key] = (
                                self.dialect.value_mapper.from_database(value, db_type)
                                if db_type is not None
                                else value
                            )
                        data.append(converted_row)
                else:
                    # Return raw dictionaries if no type conversion needed
                    data = [dict(row) for row in rows]

            duration = time.perf_counter() - start_time

            # Log completion and metrics
            if is_dml:
                self.log(logging.INFO,
                         f"{stmt_type} affected {cursor.rowcount} rows, "
                         f"last_insert_id={cursor.lastrowid}, duration={duration:.3f}s")
            elif is_select:
                row_count = len(data) if data is not None else 0
                self.log(logging.INFO,
                         f"SELECT returned {row_count} rows, duration={duration:.3f}s")

            # Build and return result
            return QueryResult(
                data=data,
                affected_rows=cursor.rowcount,
                last_insert_id=cursor.lastrowid,
                duration=duration
            )

        except sqlite3.Error as e:
            self.log(logging.ERROR, f"SQLite error executing query: {str(e)}")
            self._handle_error(e)
        except Exception as e:
            # Re-raise non-database errors
            if not isinstance(e, DatabaseError):
                self.log(logging.ERROR, f"Non-database error executing query: {str(e)}")
                raise
            self.log(logging.ERROR, f"Database error executing query: {str(e)}")
            self._handle_error(e)

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