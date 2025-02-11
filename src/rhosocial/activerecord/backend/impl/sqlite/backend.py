import sqlite3
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
            returning_columns: Optional[List[str]] = None) -> Optional[QueryResult]:
        """Execute SQL and return results

        Args:
            sql: SQL statement
            params: Query parameters
            returning: Whether statement has or needs RETURNING clause
                - For SELECT statements, should be True to fetch results
                - For INSERT/UPDATE/DELETE, indicates if RETURNING clause needed
            column_types: Column type mapping for result type conversion
                Example: {"created_at": DatabaseType.DATETIME, "settings": DatabaseType.JSON}
            returning_columns: Specific columns in RETURNING clause. None means all columns.
                Only used when returning=True for INSERT/UPDATE/DELETE statements.
                Ignored for SELECT statements.

        Returns:
            QueryResult: Query results with following fields:
                - data: Result set if SELECT or RETURNING used, otherwise None
                - affected_rows: Number of affected rows
                - last_insert_id: Last inserted row ID (if applicable)
                - duration: Query execution time in seconds

        Raises:
            ConnectionError: Database connection error
            QueryError: SQL syntax error
            TypeConversionError: Type conversion error
            ReturningNotSupportedError: RETURNING clause not supported
            DatabaseError: Other database errors
        """
        start_time = time.perf_counter()

        try:
            # Ensure connection
            if not self._connection:
                self.connect()

            # Determine statement type based on first word
            stmt_type = sql.strip().split(None, 1)[0].upper()
            is_select = stmt_type == "SELECT"
            need_returning = returning and not is_select

            # Process RETURNING clause if needed (non-SELECT only)
            if need_returning:
                handler = self.dialect.returning_handler
                if not handler.is_supported:
                    raise ReturningNotSupportedError(
                        f"RETURNING clause not supported by SQLite {sqlite3.sqlite_version}"
                    )
                sql += " " + handler.format_clause(returning_columns)

            # Use existing cursor or create new one
            cursor = self._cursor or self._connection.cursor()

            # Build final SQL and process parameters using dialect
            final_sql, final_params = self.build_sql(sql, params)

            # Convert parameters
            if final_params:
                processed_params = tuple(
                    self.dialect.value_mapper.to_database(value, None)
                    for value in final_params
                )
                cursor.execute(final_sql, processed_params)
            else:
                cursor.execute(final_sql)

            # Fetch results if SELECT or RETURNING used
            if returning:
                rows = cursor.fetchall()
                # Convert types if mapping provided
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
                    data = [dict(row) for row in rows]
            else:
                data = None

            return QueryResult(
                data=data,
                affected_rows=cursor.rowcount,
                last_insert_id=cursor.lastrowid,
                duration=time.perf_counter() - start_time
            )

        except Exception as e:
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