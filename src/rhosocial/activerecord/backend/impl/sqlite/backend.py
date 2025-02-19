import sqlite3
import sys
import time
from sqlite3 import ProgrammingError
from typing import Optional, Tuple, List

from .dialect import SQLiteDialect, SQLDialectBase
from .transaction import SQLiteTransactionManager
from ...base import StorageBackend, ColumnTypes
from ...errors import ConnectionError, IntegrityError, OperationalError, QueryError, DeadlockError, DatabaseError, \
    ReturningNotSupportedError
from ...typing import QueryResult


class SQLiteBackend(StorageBackend):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cursor = None
        self._isolation_level = kwargs.get("isolation_level", None)
        self._transaction_manager = None
        self._dialect = SQLiteDialect(self.config)

    @property
    def dialect(self) -> SQLDialectBase:
        return self._dialect

    def connect(self) -> None:
        """Establish a connection to the SQLite database."""
        try:
            self._connection = sqlite3.connect(
                self.config.database,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                isolation_level=None  # Use manual transaction management
            )
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA synchronous = FULL")
            self._connection.execute("PRAGMA wal_autocheckpoint = 1000")
            self._connection.row_factory = sqlite3.Row
            self._connection.text_factory = str
        except sqlite3.Error as e:
            raise ConnectionError(f"Failed to connect: {str(e)}")

    def disconnect(self) -> None:
        """Close the connection to the SQLite database."""
        if self._connection:
            try:
                if self.transaction_manager.is_active:
                    self.transaction_manager.rollback()
                self._connection.close()
                self._connection = None
                self._cursor = None
                self._transaction_manager = None
            except sqlite3.Error as e:
                raise ConnectionError(f"Failed to disconnect: {str(e)}")

    def ping(self, reconnect: bool = True) -> bool:
        """Test the database connection and optionally reconnect.

        Args:
            reconnect: Whether to attempt reconnection if the connection is lost

        Returns:
            bool: True if connection is alive, False otherwise
        """
        if not self._connection:
            if reconnect:
                self.connect()
                return True
            return False

        try:
            self._connection.execute("SELECT 1")
            return True
        except sqlite3.Error:
            if reconnect:
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

        try:
            # Ensure active connection
            if not self._connection:
                self.connect()

            # Parse statement type from SQL
            stmt_type = sql.strip().split(None, 1)[0].upper()
            is_select = stmt_type == "SELECT"
            is_dml = stmt_type in ("INSERT", "UPDATE", "DELETE")
            need_returning = returning and not is_select

            # Version compatibility check for RETURNING in DML statements
            if need_returning and is_dml:
                py_version = sys.version_info[:2]
                if py_version < (3, 10) and not force_returning:
                    raise ReturningNotSupportedError(
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
                elif py_version < (3, 10) and force_returning:
                    import warnings
                    warnings.warn(
                        f"Executing {stmt_type} with RETURNING clause in Python {py_version[0]}.{py_version[1]}. "
                        f"Be aware that:\n"
                        f"- affected_rows will always be 0\n"
                        f"- last_insert_id may be unreliable",
                        RuntimeWarning
                    )

            # Add RETURNING clause for DML statements if needed
            if need_returning:
                handler = self.dialect.returning_handler
                if not handler.is_supported:
                    raise ReturningNotSupportedError(
                        f"RETURNING clause not supported by current SQLite version {sqlite3.sqlite_version}"
                    )
                # Format and append RETURNING clause
                sql += " " + handler.format_clause(returning_columns)

            # Get or create cursor
            cursor = self._cursor or self._connection.cursor()

            # Process SQL and parameters through dialect
            final_sql, final_params = self.build_sql(sql, params)

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
                # Apply type conversions if specified
                if column_types:
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

            # Build and return result
            return QueryResult(
                data=data,
                affected_rows=cursor.rowcount,
                last_insert_id=cursor.lastrowid,
                duration=time.perf_counter() - start_time
            )

        except sqlite3.Error as e:
            self._handle_error(e)
        except Exception as e:
            # Re-raise non-database errors
            if not isinstance(e, DatabaseError):
                raise
            self._handle_error(e)

    def _handle_error(self, error: Exception) -> None:
        """Handle SQLite-specific errors and convert to appropriate exceptions."""
        if isinstance(error, sqlite3.Error):
            if isinstance(error, sqlite3.OperationalError):
                if "database is locked" in str(error):
                    raise OperationalError("Database is locked")
                elif "no such table" in str(error):
                    raise QueryError(f"Table not found: {str(error)}")
                raise OperationalError(str(error))
            elif isinstance(error, sqlite3.IntegrityError):
                if "UNIQUE constraint failed" in str(error):
                    raise IntegrityError(f"Unique constraint violation: {str(error)}")
                elif "FOREIGN KEY constraint failed" in str(error):
                    raise IntegrityError(f"Foreign key constraint violation: {str(error)}")
                raise IntegrityError(str(error))
            elif "database is locked" in str(error):
                raise DeadlockError(str(error))
            elif isinstance(error, ProgrammingError):
                raise DatabaseError(str(error))
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
        start_time = time.perf_counter()
        try:
            if not self._connection:
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

            return QueryResult(
                affected_rows=cursor.rowcount,
                duration=time.perf_counter() - start_time
            )
        except Exception as e:
            self._handle_error(e)

    def begin_transaction(self) -> None:
        """Start a transaction"""
        self.transaction_manager.begin()

    def commit_transaction(self) -> None:
        """Commit the current transaction"""
        self.transaction_manager.commit()

    def rollback_transaction(self) -> None:
        """Rollback the current transaction"""
        self.transaction_manager.rollback()

    @property
    def in_transaction(self) -> bool:
        """Check if currently in a transaction"""
        return self.transaction_manager.is_active

    @property
    def transaction_manager(self) -> SQLiteTransactionManager:
        """Get the transaction manager"""
        if not self._transaction_manager:
            if not self._connection:
                self.connect()
            self._transaction_manager = SQLiteTransactionManager(self._connection)
        return self._transaction_manager

    @property
    def supports_returning(self) -> bool:
        """Check if SQLite version supports RETURNING clause"""
        return tuple(map(int, sqlite3.sqlite_version.split('.'))) >= (3, 35, 0)

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

            except Exception as e:
                # Log the error but don't fail - return a reasonable default
                if hasattr(self, 'logger'):
                    self.logger.warning(f"Failed to determine SQLite version: {str(e)}")
                # Default to a relatively recent version
                SQLiteBackend._sqlite_version_cache = (3, 35, 0)

        return SQLiteBackend._sqlite_version_cache