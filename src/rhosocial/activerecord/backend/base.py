import inspect
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional, Tuple, List

from src.rhosocial.activerecord.backend.transaction import TransactionManager
from .dialect import TypeMapper, ValueMapper, DatabaseType, SQLDialectBase, SQLExpressionBase, SQLBuilder
from .typing import ConnectionConfig, QueryResult

# Type hints
ColumnTypes = Dict[str, DatabaseType]
ValueConverter = Dict[str, callable]

class StorageBackend(ABC):
    """Initialize storage backend

    Args:
        **kwargs: Configuration parameters including:
            - connection_config: ConnectionConfig instance
            - logger: Optional logger instance
    """
    _dialect: SQLDialectBase

    def __init__(self, **kwargs) -> None:
        """Initialize storage backend

        Args:
            **kwargs: Configuration parameters including:
                - connection_config: ConnectionConfig instance
                - logger: Optional logger instance
        """
        # Initialize logger
        self._logger: Optional[logging.Logger] = kwargs.get('logger', logging.getLogger('storage'))

        if "connection_config" not in kwargs or kwargs["connection_config"] is None:
            self.config = ConnectionConfig(**kwargs)
        else:
            self.config = kwargs["connection_config"]
        self._connection = None
        self._transaction_level = 0
        self._cursor = None
        self._server_version_cache = None

    @property
    def logger(self) -> logging.Logger:
        """Get current logger instance"""
        return self._logger

    @logger.setter
    def logger(self, logger: Optional[logging.Logger]) -> None:
        """Set logger instance

        Args:
            logger: Logger instance or None to use default
        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise ValueError("logger must be an instance of logging.Logger")
        self._logger = logger or logging.getLogger('storage')

    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log message using current logger

        Args:
            level: Log level (e.g. logging.INFO)
            msg: Log message
            *args: Format string arguments
            **kwargs: Additional logging arguments
        """
        # Calculate stack level
        current_frame = inspect.currentframe().f_back
        stack_level = 1  # Include log_info itself
        while current_frame:
            if current_frame.f_globals['__name__'] != 'storage':
                break
            current_frame = current_frame.f_back
            stack_level += 1
        if current_frame:
            stack_level += 1  # Pointed to the frame of the user code.
        self.logger.log(level, msg, *args, stacklevel=stack_level, **kwargs)

    @property
    @abstractmethod
    def dialect(self) -> SQLDialectBase:
        """Get SQL dialect"""
        pass

    def create_expression(self, expression: str) -> SQLExpressionBase:
        """Create SQL expression

        Args:
            expression: Expression string

        Returns:
            SQLExpressionBase: Expression object
        """
        return self.dialect.create_expression(expression)

    def build_sql(self, sql: str, params: Optional[Tuple] = None) -> Tuple[str, Tuple]:
        """Build SQL and parameters

        Args:
            sql: Raw SQL
            params: SQL parameters

        Returns:
            Tuple[str, Tuple]: (Processed SQL, Processed parameters)
        """
        builder = SQLBuilder(self.dialect)
        return builder.build(sql, params)

    @property
    def type_mapper(self) -> TypeMapper:
        return self._dialect.type_mapper

    @property
    def value_mapper(self) -> ValueMapper:
        return self._dialect.value_mapper

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection"""
        pass

    @abstractmethod
    def ping(self, reconnect: bool = True) -> bool:
        """Check if connection is valid"""
        pass

    @abstractmethod
    def _handle_error(self, error: Exception) -> None:
        """Handle database errors"""
        pass

    @property
    def connection(self) -> Any:
        """Get current connection"""
        if self._connection is None:
            self.connect()
        return self._connection

    @abstractmethod
    def execute(self,
                sql: str,
                params: Optional[Tuple] = None,
                returning: bool = False,
                column_types: Optional[ColumnTypes] = None,
                returning_columns: Optional[List[str]] = None,
                force_returning: bool = False) -> Optional[QueryResult]:
        """Execute SQL statement with optional RETURNING clause

        Note on SQLite RETURNING support:
        When using SQLite backend with Python <3.10, RETURNING clause has known issues:
        - affected_rows always returns 0
        - last_insert_id may be unreliable
        These limitations only affect SQLite and can be overridden using force_returning=True.

        Args:
            sql: SQL statement
            params: SQL parameters
            returning: Whether to return result set
                - For SELECT: True to fetch results
                - For DML: True to use RETURNING clause
            column_types: Column type mapping for result type conversion
                Example: {"created_at": DatabaseType.DATETIME}
            returning_columns: Specific columns to return. None means all columns.
                Only used when returning=True for DML statements.
            force_returning: If True, allows RETURNING clause in SQLite with Python <3.10
                despite known limitations. Has no effect with other database backends.

        Returns:
            QueryResult: Query result containing:
                - data: Result set if SELECT or RETURNING used
                - affected_rows: Number of affected rows
                - last_insert_id: Last inserted row ID
                - duration: Query execution time

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported by backend
                or Python version (SQLite with Python <3.10)
            ConnectionError: Database connection error
            QueryError: SQL syntax error
            DatabaseError: Other database errors
        """
        pass

    def fetch_one(self,
                  sql: str,
                  params: Optional[Tuple] = None,
                  column_types: Optional[ColumnTypes] = None) -> Optional[Dict]:
        """Fetch single record

        Args:
            sql: SQL statement
            params: SQL parameters
            column_types: Column type mapping for result type conversion

        Returns:
            Optional[Dict]: Query result
        """
        result = self.execute(sql, params, returning=True, column_types=column_types)
        return result.data[0] if result.data else None

    def fetch_all(self,
                  sql: str,
                  params: Optional[Tuple] = None,
                  column_types: Optional[ColumnTypes] = None) -> List[Dict]:
        """Fetch multiple records

        Args:
            sql: SQL statement
            params: SQL parameters
            column_types: Column type mapping for result type conversion

        Returns:
            List[Dict]: Query result list
        """
        result = self.execute(sql, params, returning=True, column_types=column_types)
        return result.data or []

    def _handle_auto_commit(self) -> None:
        """Handle auto commit based on connection and transaction state.

        This is a base implementation that does nothing. Subclasses should
        override this method with database-specific implementation.
        """
        pass  # Base implementation does nothing

    def insert(self,
               table: str,
               data: Dict,
               returning: bool = False,
               column_types: Optional[ColumnTypes] = None,
               returning_columns: Optional[List[str]] = None,
               force_returning: bool = False,
               auto_commit: bool = True) -> QueryResult:
        """Insert record

        Note on RETURNING support:
        When using SQLite backend with Python <3.10, RETURNING clause has known issues:
        - affected_rows always returns 0
        - last_insert_id may be unreliable
        Use force_returning=True to override this limitation if you understand the consequences.
        This limitation is specific to SQLite backend and does not affect other backends.

        Args:
            table: Table name
            data: Data to insert
            returning: Whether to return result set
            column_types: Column type mapping for result type conversion
            returning_columns: Specific columns to return in RETURNING clause. None means all columns.
            force_returning: If True, allows RETURNING clause in SQLite with Python <3.10
                despite known limitations. Has no effect with other database backends.
            auto_commit: If True and autocommit is disabled and not in active transaction,
                         automatically commit after operation. Default is True.

        Returns:
            QueryResult: Execution result

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported by backend
                or Python version (SQLite with Python <3.10)
        """
        # Clean field names by stripping quotes
        cleaned_data = {
            k.strip('"'): v
            for k, v in data.items()
        }

        fields = [f'"{field}"' for field in cleaned_data.keys()]  # Add quotes properly
        values = [self.value_mapper.to_database(v, column_types.get(k.strip('"')) if column_types else None)
                  for k, v in data.items()]
        placeholders = [self.dialect.get_placeholder() for _ in fields]

        sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(placeholders)})"

        # Clean returning columns by stripping quotes if specified
        if returning_columns:
            returning_columns = [col.strip('"') for col in returning_columns]

        # Execute query and get result
        result = self.execute(sql, tuple(values), returning, column_types, returning_columns, force_returning)

        # Handle auto_commit if specified - this will be overridden by subclasses
        # with specific implementations
        if auto_commit:
            self._handle_auto_commit()

        # If we have returning data, ensure the column names are consistently without quotes
        if returning and result.data:
            cleaned_data = []
            for row in result.data:
                cleaned_row = {
                    k.strip('"'): v
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
               returning: bool = False,
               column_types: Optional[ColumnTypes] = None,
               returning_columns: Optional[List[str]] = None,
               force_returning: bool = False,
               auto_commit: bool = True) -> QueryResult:
        """Update record

        Note on RETURNING support:
        When using SQLite backend with Python <3.10, RETURNING clause has known issues:
        - affected_rows always returns 0
        - last_insert_id may be unreliable
        Use force_returning=True to override this limitation if you understand the consequences.
        This limitation is specific to SQLite backend and does not affect other backends.

        Args:
            table: Table name
            data: Data to update
            where: WHERE condition
            params: WHERE condition parameters
            returning: Whether to return result set
            column_types: Column type mapping for result type conversion
            returning_columns: Specific columns to return in RETURNING clause. None means all columns.
            force_returning: If True, allows RETURNING clause in SQLite with Python <3.10
                despite known limitations. Has no effect with other database backends.
            auto_commit: If True and autocommit is disabled and not in active transaction,
                         automatically commit after operation. Default is True.

        Returns:
            QueryResult: Execution result

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported by backend
                or Python version (SQLite with Python <3.10)
        """
        set_items = [f"{k} = {self.dialect.get_placeholder()}" for k in data.keys()]
        values = [self.value_mapper.to_database(v, column_types.get(k) if column_types else None)
                  for k, v in data.items()]

        sql = f"UPDATE {table} SET {', '.join(set_items)} WHERE {where}"

        result = self.execute(sql, tuple(values) + params, returning, column_types, returning_columns, force_returning)

        # Handle auto_commit if specified - this will be overridden by subclasses
        # with specific implementations
        if auto_commit:
            self._handle_auto_commit()

        return result

    def delete(self,
               table: str,
               where: str,
               params: Tuple,
               returning: bool = False,
               column_types: Optional[ColumnTypes] = None,
               returning_columns: Optional[List[str]] = None,
               force_returning: bool = False,
               auto_commit: bool = True) -> QueryResult:
        """Delete record

        Note on RETURNING support:
        When using SQLite backend with Python <3.10, RETURNING clause has known issues:
        - affected_rows always returns 0
        - last_insert_id may be unreliable
        Use force_returning=True to override this limitation if you understand the consequences.
        This limitation is specific to SQLite backend and does not affect other backends.

        Args:
            table: Table name
            where: WHERE condition
            params: WHERE condition parameters
            returning: Whether to return result set
            column_types: Column type mapping for result type conversion
            returning_columns: Specific columns to return in RETURNING clause. None means all columns.
            force_returning: If True, allows RETURNING clause in SQLite with Python <3.10
                despite known limitations. Has no effect with other database backends.
            auto_commit: If True and autocommit is disabled and not in active transaction,
                         automatically commit after operation. Default is True.

        Returns:
            QueryResult: Execution result

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported by backend
                or Python version (SQLite with Python <3.10)
        """
        sql = f"DELETE FROM {table} WHERE {where}"

        result = self.execute(sql, params, returning, column_types, returning_columns, force_returning)

        # Handle auto_commit if specified
        if auto_commit:
            self._handle_auto_commit()

        return result

    def begin_transaction(self) -> None:
        """Begin transaction - fully delegate to transaction manager"""
        self.log(logging.INFO, "Beginning transaction")
        self.transaction_manager.begin()

    def commit_transaction(self) -> None:
        """Commit transaction - fully delegate to transaction manager"""
        self.log(logging.INFO, "Committing transaction")
        self.transaction_manager.commit()

    def rollback_transaction(self) -> None:
        """Rollback transaction - fully delegate to transaction manager"""
        self.log(logging.INFO, "Rolling back transaction")
        self.transaction_manager.rollback()

    @property
    def in_transaction(self) -> bool:
        """Check if in transaction - delegate to transaction manager"""
        is_active = self.transaction_manager.is_active if self._transaction_manager else False
        self.log(logging.DEBUG, f"Checking transaction status: {is_active}")
        return is_active

    @property
    def transaction_manager(self) -> 'TransactionManager':
        """Get the transaction manager"""
        pass

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Transaction context manager"""
        with self.transaction_manager.transaction() as t:
            yield t

    def __enter__(self):
        if not self._connection:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __del__(self):
        """Ensure resource cleanup on destruction"""
        self.disconnect()

    @property
    def supports_returning(self) -> bool:
        """Whether RETURNING clause is supported"""
        return False  # Default to not supported, specific backends can override

    @abstractmethod
    def get_server_version(self) -> tuple:
        """Get database server version

        Returns:
            tuple: Server version as (major, minor, patch)
        """
        pass