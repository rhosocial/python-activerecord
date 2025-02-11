from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional, Tuple, List

from .dialect import TypeMapper, ValueMapper, DatabaseType, SQLDialectBase, SQLExpressionBase, SQLBuilder
from .typing import ConnectionConfig, QueryResult

# Type hints
ColumnTypes = Dict[str, DatabaseType]
ValueConverter = Dict[str, callable]

class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    _dialect: SQLDialectBase

    def __init__(self, **kwargs) -> None:
        if "connection_config" not in kwargs or kwargs["connection_config"] is None:
            self.config = ConnectionConfig(**kwargs)
        else:
            self.config = kwargs["connection_config"]
        self._connection = None
        self._transaction_level = 0
        self._cursor = None

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
                returning_columns: Optional[List[str]] = None) -> Optional[QueryResult]:
        """Execute SQL statement with optional RETURNING clause

        Args:
            sql: SQL statement
            params: SQL parameters
            returning: Whether to return result set
            column_types: Column type mapping for result type conversion
            returning_columns: Specific columns to return. None means all columns.

        Returns:
            QueryResult: Query result

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported
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

    def insert(self,
               table: str,
               data: Dict,
               returning: bool = False,
               column_types: Optional[ColumnTypes] = None,
               returning_columns: Optional[List[str]] = None) -> QueryResult:
        """Insert record

        Args:
            table: Table name
            data: Data to insert
            returning: Whether to return result set
            column_types: Column type mapping for result type conversion
            returning_columns: Specific columns to return in RETURNING clause. None means all columns.

        Returns:
            QueryResult: Execution result

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported
        """
        fields = list(data.keys())
        values = [self.value_mapper.to_database(v, column_types.get(k) if column_types else None)
                 for k, v in data.items()]
        placeholders = [self.dialect.get_placeholder() for _ in fields]

        sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(placeholders)})"

        return self.execute(sql, tuple(values), returning, column_types, returning_columns)

    def update(self,
               table: str,
               data: Dict,
               where: str,
               params: Tuple,
               returning: bool = False,
               column_types: Optional[ColumnTypes] = None,
               returning_columns: Optional[List[str]] = None) -> QueryResult:
        """Update record

        Args:
            table: Table name
            data: Data to update
            where: WHERE condition
            params: WHERE condition parameters
            returning: Whether to return result set
            column_types: Column type mapping for result type conversion
            returning_columns: Specific columns to return in RETURNING clause. None means all columns.

        Returns:
            QueryResult: Execution result

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported
        """
        set_items = [f"{k} = {self.dialect.get_placeholder()}" for k in data.keys()]
        values = [self.value_mapper.to_database(v, column_types.get(k) if column_types else None)
                 for k, v in data.items()]

        sql = f"UPDATE {table} SET {', '.join(set_items)} WHERE {where}"

        return self.execute(sql, tuple(values) + params, returning, column_types, returning_columns)

    def delete(self,
               table: str,
               where: str,
               params: Tuple,
               returning: bool = False,
               column_types: Optional[ColumnTypes] = None,
               returning_columns: Optional[List[str]] = None) -> QueryResult:
        """Delete record

        Args:
            table: Table name
            where: WHERE condition
            params: WHERE condition parameters
            returning: Whether to return result set
            column_types: Column type mapping for result type conversion
            returning_columns: Specific columns to return in RETURNING clause. None means all columns.

        Returns:
            QueryResult: Execution result

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported
        """
        sql = f"DELETE FROM {table} WHERE {where}"

        return self.execute(sql, params, returning, column_types, returning_columns)

    def begin_transaction(self) -> None:
        """Begin transaction"""
        if self._transaction_level == 0:
            self.execute("BEGIN TRANSACTION")
        else:
            self.execute(f"SAVEPOINT SP_{self._transaction_level}")
        self._transaction_level += 1

    def commit_transaction(self) -> None:
        """Commit transaction"""
        if self._transaction_level > 0:
            self._transaction_level -= 1
            if self._transaction_level == 0:
                self.execute("COMMIT")
            else:
                self.execute(f"RELEASE SAVEPOINT SP_{self._transaction_level}")

    def rollback_transaction(self) -> None:
        """Rollback transaction"""
        if self._transaction_level > 0:
            if self._transaction_level == 1:
                self.execute("ROLLBACK")
                self._transaction_level = 0
            else:
                self.execute(f"ROLLBACK TO SAVEPOINT SP_{self._transaction_level - 1}")
                self._transaction_level -= 1

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Transaction context manager"""
        try:
            self.begin_transaction()
            yield
            self.commit_transaction()
        except:
            self.rollback_transaction()
            raise

    @property
    def in_transaction(self) -> bool:
        """Check if in transaction"""
        return self._transaction_level > 0

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