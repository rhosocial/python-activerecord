import time
import sqlite3
from sqlite3 import ProgrammingError
from typing import Optional, Tuple, List

from .dialect import SQLiteTypeMapper, SQLiteValueMapper, SQLiteDialect
from .transaction import SQLiteTransactionManager
from ...base import StorageBackend, ColumnTypes
from ...errors import ConnectionError, IntegrityError, OperationalError, QueryError, DeadlockError, DatabaseError
from ...expression import SQLDialectBase
from ...typing import QueryResult


class SQLiteBackend(StorageBackend):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cursor = None
        self._isolation_level = kwargs.get("isolation_level", None)
        self._type_mapper = SQLiteTypeMapper()
        self._value_mapper = SQLiteValueMapper(self.config)
        self._transaction_manager = None
        self._dialect = SQLiteDialect()

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
            column_types: Optional[ColumnTypes] = None
    ) -> QueryResult:
        """Execute SQL and return results

        Args:
            sql: SQL statement
            params: Query parameters
            returning: Whether to return result set
            column_types: Column type mapping {column_name: DatabaseType} for result type conversion
                Example: {"created_at": DatabaseType.DATETIME, "settings": DatabaseType.JSON}

        Returns:
            QueryResult: Query results
        """
        start_time = time.perf_counter()
        try:
            if not self._connection:
                self.connect()

            # Use existing cursor or create new one
            cursor = self._cursor or self._connection.cursor()

            # Process SQL and parameters using dialect
            final_sql, final_params = self.build_sql(sql, params)

            # Convert parameters
            if final_params:
                processed_params = tuple(
                    self._value_mapper.to_database(value, None)
                    for value in final_params
                )
                cursor.execute(final_sql, processed_params)
            else:
                cursor.execute(final_sql)

            if returning:
                # Get raw data
                rows = cursor.fetchall()

                # Convert types if mapping provided
                if column_types:
                    data = []
                    for row in rows:
                        converted_row = {}
                        for key, value in dict(row).items():
                            # Use specified type for conversion, keep original if not specified
                            db_type = column_types.get(key)
                            converted_row[key] = (
                                self._value_mapper.from_database(value, db_type)
                                if db_type is not None
                                else value
                            )
                        data.append(converted_row)
                else:
                    # Return raw data if no type mapping
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
    ) -> QueryResult:
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
                        self._value_mapper.to_database(value, None)
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