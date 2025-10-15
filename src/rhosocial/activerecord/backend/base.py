# src/rhosocial/activerecord/backend/base.py
import inspect
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional, Tuple, List, Union

from .capabilities import DatabaseCapabilities
from .config import ConnectionConfig
from .dialect import SQLDialectBase, SQLExpressionBase, SQLBuilder, \
    ReturningOptions
from .errors import ReturningNotSupportedError
from .transaction import TransactionManager
from .type_converters import TypeRegistry
from .typing import QueryResult, DatabaseType

# Type hints
ColumnTypes = Dict[str, Union[DatabaseType, str, Any]]


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
        self._transaction_manager = None
        self._cursor = None
        self._server_version_cache = None
        self._capabilities = None

    @property
    def capabilities(self) -> DatabaseCapabilities:
        """Get database capabilities.
        
        This property provides access to the database's capability descriptor,
        which declares what features this backend supports. The capabilities
        are used by tests and application code to determine what features
        can be safely used with this backend.
        
        The capability system enables:
        1. Fine-grained feature detection based on database version
        2. Test skipping for unsupported features
        3. Adaptive behavior in application code based on available features
        
        Returns:
            DatabaseCapabilities: Capabilities of this backend
        """
        if self._capabilities is None:
            self._capabilities = self._initialize_capabilities()
        return self._capabilities
    
    @abstractmethod
    def _initialize_capabilities(self) -> DatabaseCapabilities:
        """Initialize database capabilities.
        
        This abstract method must be implemented by each backend to declare
        its specific capabilities based on database version and other factors.
        
        Each backend should:
        1. Create a DatabaseCapabilities instance
        2. Check database version and other factors
        3. Add supported capabilities to the instance
        4. Return the fully populated capabilities object
        
        The capabilities system allows tests and application code to check
        for feature support before using features, preventing runtime errors
        on databases that don't support certain features.
        
        Returns:
            DatabaseCapabilities: Backend capabilities
        """
        self._capabilities = None

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
    def type_registry(self) -> TypeRegistry:
        """Get the type registry from the dialect"""
        return self.dialect.type_registry

    def register_converter(self, converter: Any, names: Optional[List[str]] = None,
                           types: Optional[List[Any]] = None) -> None:
        """
        Register a type converter with this backend's dialect.

        Args:
            converter: Type converter to register
            names: Optional list of type names this converter handles
            types: Optional list of DatabaseType enum values this converter handles
        """
        self.dialect.register_converter(converter, names, types)

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

    def execute(
            self,
            sql: str,
            params: Optional[Tuple] = None,
            returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
            column_types: Optional[ColumnTypes] = None) -> Optional[QueryResult]:
        """
        Execute SQL statement with enhanced RETURNING clause support.

        This is a template method that implements the common flow for all databases,
        with specific parts delegated to hook methods that can be overridden by
        concrete database implementations.

        Args:
            sql: SQL statement to execute
            params: Query parameters
            returning: Controls RETURNING clause behavior
            column_types: Column type mapping for result type conversion

        Returns:
            QueryResult: Query result

        Raises:
            ReturningNotSupportedError: If RETURNING requested but not supported
            ConnectionError: Database connection error
            QueryError: SQL syntax error
            DatabaseError: Other database errors
        """
        import time
        start_time = time.perf_counter()

        # Log query with parameters
        self.log(logging.DEBUG, f"Executing SQL: {sql}, parameters: {params}")

        try:
            # Ensure active connection
            if not self._connection:
                self.log(logging.DEBUG, "No active connection, establishing new connection")
                self.connect()

            # Parse statement type from SQL (SELECT, INSERT, etc.)
            stmt_type = self._get_statement_type(sql)
            is_select = self._is_select_statement(stmt_type)
            is_dml = self._is_dml_statement(stmt_type)

            # Process returning parameter into ReturningOptions
            returning_options = self._process_returning_options(returning)

            # Determine if RETURNING clause is needed
            need_returning = bool(returning_options) and is_dml

            # Handle RETURNING clause for DML statements if needed
            if need_returning:
                # Check compatibility and format RETURNING clause
                sql = self._prepare_returning_clause(sql, returning_options, stmt_type)

            # Get or create cursor
            cursor = self._get_cursor()

            # Process SQL and parameters through dialect
            final_sql, final_params = self._prepare_sql_and_params(sql, params)

            # Execute the query
            cursor = self._execute_query(cursor, final_sql, final_params)

            # Handle result set for SELECT or RETURNING
            data = self._process_result_set(cursor, is_select, need_returning, column_types)

            # Calculate duration
            duration = time.perf_counter() - start_time

            # Log completion and metrics
            self._log_query_completion(stmt_type, cursor, data, duration)

            # Build result object
            result = self._build_query_result(cursor, data, duration)

            # Handle auto-commit if needed
            self._handle_auto_commit_if_needed()

            return result

        except Exception as e:
            self.log(logging.ERROR, f"Error executing query: {str(e)}")
            # Database-specific error handling
            return self._handle_execution_error(e)

    # Hook methods that can be overridden by concrete database implementations

    def _get_statement_type(self, sql: str) -> str:
        """
        Get the SQL statement type (SELECT, INSERT, etc.)

        Args:
            sql: SQL statement

        Returns:
            str: Statement type in uppercase
        """
        # Handle empty SQL
        sql_stripped = sql.strip()
        if not sql_stripped:
            return ""

        # Extract first word as statement type
        parts = sql_stripped.split(None, 1)
        return parts[0].upper()

    def _is_select_statement(self, stmt_type: str) -> bool:
        """
        Check if statement is a SELECT query or similar read-only operation.

        Args:
            stmt_type: Statement type from _get_statement_type

        Returns:
            bool: True if statement is a read-only query
        """
        return stmt_type in ("SELECT", "EXPLAIN", "SHOW", "DESCRIBE", "DESC")

    def _is_dml_statement(self, stmt_type: str) -> bool:
        """
        Check if statement is a DML operation (INSERT, UPDATE, DELETE).

        Args:
            stmt_type: Statement type from _get_statement_type

        Returns:
            bool: True if statement is a DML operation
        """
        return stmt_type in ("INSERT", "UPDATE", "DELETE")

    def _process_returning_options(self,
                                   returning: Optional[Union[bool, List[str], ReturningOptions]]) -> ReturningOptions:
        """
        Process returning parameter into ReturningOptions object.

        Args:
            returning: Controls RETURNING clause behavior:
                - None: No RETURNING clause
                - bool: Simple RETURNING * if True
                - List[str]: Return specific columns
                - ReturningOptions: Full control over RETURNING

        Returns:
            ReturningOptions: Processed options

        Raises:
            ValueError: If returning parameter is not supported type
        """
        if returning is None:
            # No RETURNING clause
            return ReturningOptions(enabled=False)
        elif isinstance(returning, bool):
            # Legacy boolean returning
            return ReturningOptions.from_legacy(returning)
        elif isinstance(returning, list):
            # List of column names
            return ReturningOptions.columns_only(returning)
        elif isinstance(returning, ReturningOptions):
            # Already a ReturningOptions object
            return returning
        else:
            # Invalid type
            raise ValueError(f"Unsupported returning type: {type(returning)}")

    def _prepare_returning_clause(self, sql: str, options: ReturningOptions, stmt_type: str) -> str:
        """
        Check compatibility and format RETURNING clause.

        Args:
            sql: SQL statement
            options: RETURNING options
            stmt_type: Statement type from _get_statement_type

        Returns:
            str: SQL statement with RETURNING clause if applicable

        Raises:
            ReturningNotSupportedError: If RETURNING not supported and not forced
        """
        # Get returning handler from dialect
        handler = self.dialect.returning_handler

        # Check if RETURNING is supported by this database
        if not handler.is_supported and not options.force:
            error_msg = (
                f"RETURNING clause not supported by this database. "
                f"Use force=True to attempt anyway if you understand the limitations."
            )
            self.log(logging.WARNING, error_msg)
            raise ReturningNotSupportedError(error_msg)

        # Database-specific compatibility checks (to be overridden)
        self._check_returning_compatibility(options)

        # Format RETURNING clause
        if options.has_column_specification():
            # Format advanced RETURNING clause with columns, expressions, aliases
            returning_clause = handler.format_advanced_clause(
                options.columns,
                options.expressions,
                options.aliases,
                options.dialect_options
            )
        else:
            # Use simple RETURNING *
            returning_clause = handler.format_clause(None)

        # Append RETURNING clause to SQL
        sql += " " + returning_clause
        self.log(logging.DEBUG, f"Added RETURNING clause: {sql}")

        return sql

    def _check_returning_compatibility(self, options: ReturningOptions) -> None:
        """
        Perform database-specific compatibility checks for RETURNING clause.

        To be overridden by specific database implementations.

        Args:
            options: RETURNING options

        Raises:
            ReturningNotSupportedError: If compatibility issues found and not forced
        """
        # Base implementation does nothing
        pass

    def _get_cursor(self):
        """
        Get or create a cursor for query execution.

        Returns:
            A database cursor object
        """
        return self._cursor or self._connection.cursor()

    def _prepare_sql_and_params(self, sql: str, params: Optional[Tuple]) -> Tuple[str, Optional[Tuple]]:
        """
        Process SQL and parameters for execution.

        Args:
            sql: SQL statement
            params: Query parameters

        Returns:
            Tuple[str, Optional[Tuple]]: (Final SQL, Processed parameters)
        """
        if params:
            return self.build_sql(sql, params)
        return sql, params

    def _execute_query(self, cursor, sql: str, params: Optional[Tuple]):
        """
        Execute the query with prepared SQL and parameters.

        Args:
            cursor: Database cursor
            sql: Prepared SQL statement
            params: Processed parameters

        Returns:
            The cursor with executed query

        Raises:
            DatabaseError: If query execution fails
        """
        # Convert parameters if needed
        if params:
            processed_params = tuple(
                self.dialect.to_database(value, None)
                for value in params
            )
            cursor.execute(sql, processed_params)
        else:
            cursor.execute(sql)

        return cursor

    def _process_result_set(self, cursor, is_select: bool, need_returning: bool, column_types: Optional[ColumnTypes]) -> \
            Optional[List[Dict]]:
        """
        Process query result set with type conversion.

        Args:
            cursor: Database cursor with executed query
            is_select: Whether this is a SELECT query
            need_returning: Whether RETURNING clause was used
            column_types: Column type mapping for conversion

        Returns:
            Optional[List[Dict]]: Processed result rows or None
        """
        if not (is_select or need_returning):
            return None

        try:
            # Fetch all rows
            rows = cursor.fetchall()
            self.log(logging.DEBUG, f"Fetched {len(rows)} rows")

            # Convert to dictionaries if needed
            if not rows:
                return []

            # Apply type conversions if specified
            if column_types:
                self.log(logging.DEBUG, "Applying type conversions")
                result = []

                # Handle different cursor row formats
                if hasattr(rows[0], 'items'):  # Dict-like rows
                    for row in rows:
                        converted_row = {}
                        for key, value in row.items():
                            type_spec = column_types.get(key)
                            if type_spec is None:
                                # No conversion specified
                                converted_row[key] = value
                            elif isinstance(type_spec, DatabaseType):
                                # Using DatabaseType enum for conversion
                                converted_row[key] = self.dialect.from_database(value, type_spec)
                            elif isinstance(type_spec, str):
                                # Using type name string
                                converter = self.dialect.type_registry.find_converter_by_name(type_spec)
                                if converter:
                                    converted_row[key] = converter.from_database(value, type_spec)
                                else:
                                    converted_row[key] = value
                            else:
                                # Assume it's a converter instance or similar
                                try:
                                    # Try to use the converter directly
                                    converted_row[key] = type_spec.from_database(value, None)
                                except (AttributeError, TypeError):
                                    # If it's not a converter, use it as a type hint
                                    converted_row[key] = self.dialect.from_database(value, type_spec)
                        result.append(converted_row)
                else:  # Tuple-like rows
                    column_names = [desc[0] for desc in cursor.description]
                    for row in rows:
                        converted_row = {}
                        for i, value in enumerate(row):
                            key = column_names[i]
                            type_spec = column_types.get(key)
                            if type_spec is None:
                                # No conversion specified
                                converted_row[key] = value
                            elif isinstance(type_spec, DatabaseType):
                                # Using DatabaseType enum for conversion
                                converted_row[key] = self.dialect.from_database(value, type_spec)
                            elif isinstance(type_spec, str):
                                # Using type name string
                                converter = self.dialect.type_registry.find_converter_by_name(type_spec)
                                if converter:
                                    converted_row[key] = converter.from_database(value, type_spec)
                                else:
                                    converted_row[key] = value
                            else:
                                # Assume it's a converter instance or similar
                                try:
                                    # Try to use the converter directly
                                    converted_row[key] = type_spec.from_database(value, None)
                                except (AttributeError, TypeError):
                                    # If it's not a converter, use it as a type hint
                                    converted_row[key] = self.dialect.from_database(value, type_spec)
                        result.append(converted_row)

                return result
            else:
                # No type conversion needed
                if hasattr(rows[0], 'items'):  # Dict-like rows
                    return [dict(row) for row in rows]
                else:  # Tuple-like rows
                    column_names = [desc[0] for desc in cursor.description]
                    return [dict(zip(column_names, row)) for row in rows]
        except Exception as e:
            self.log(logging.ERROR, f"Error processing result set: {str(e)}")
            raise

    def _log_query_completion(self, stmt_type: str, cursor, data: Optional[List[Dict]], duration: float) -> None:
        """
        Log query completion metrics.

        Args:
            stmt_type: Statement type
            cursor: Database cursor
            data: Result data if available
            duration: Query execution duration
        """
        if stmt_type in ("INSERT", "UPDATE", "DELETE"):
            rowcount = getattr(cursor, 'rowcount', 0)
            lastrowid = getattr(cursor, 'lastrowid', None)
            self.log(logging.INFO,
                     f"{stmt_type} affected {rowcount} rows, "
                     f"last_insert_id={lastrowid}, duration={duration:.3f}s")
        elif stmt_type in ("SELECT", "EXPLAIN", "SHOW", "DESCRIBE", "DESC"):
            row_count = len(data) if data is not None else 0
            self.log(logging.INFO, f"{stmt_type} returned {row_count} rows, duration={duration:.3f}s")

    def _build_query_result(self, cursor, data: Optional[List[Dict]], duration: float) -> QueryResult:
        """
        Build QueryResult object from execution results.

        Args:
            cursor: Database cursor
            data: Processed result data
            duration: Query execution duration

        Returns:
            QueryResult: Query result object
        """
        return QueryResult(
            data=data,
            affected_rows=getattr(cursor, 'rowcount', 0),
            last_insert_id=getattr(cursor, 'lastrowid', None),
            duration=duration
        )

    def _handle_auto_commit_if_needed(self) -> None:
        """
        Handle auto-commit if not in transaction.

        To be overridden by specific database implementations.
        """
        if not self.in_transaction:
            self._handle_auto_commit()

    def _handle_execution_error(self, error: Exception):
        """
        Handle database-specific errors during query execution.

        Args:
            error: Exception raised during execution

        Raises:
            Appropriate database exception based on error type
        """
        # Call the existing error handler
        self._handle_error(error)

    def execute_many(
            self,
            sql: str,
            params_list: List[Tuple]
    ) -> Optional[QueryResult]:
        """Execute batch operations for the same SQL statement with multiple parameter sets.

        This method is designed for efficiently executing the same SQL statement multiple times
        with different parameter sets. It is NOT meant for executing multiple different SQL statements
        in a single call (no statements with semicolons).

        For example, this is correct usage:
            execute_many("INSERT INTO table VALUES (?, ?)", [(1, "a"), (2, "b"), (3, "c")])

        This is incorrect usage:
            execute_many("CREATE TABLE x; INSERT INTO x VALUES (?)", [(1,), (2,)])

        Note: This method is optional and may not be implemented by all database backends.
        The default implementation falls back to executing statements one by one.

        Args:
            sql: SQL statement to execute repeatedly (must be a single statement)
            params_list: List of parameter tuples, one for each execution

        Returns:
            QueryResult: Execution results including affected rows and duration
        """
        self.log(logging.INFO,
                 f"execute_many: Executing statements individually (backend doesn't support batch operations)")
        import time
        start_time = time.perf_counter()
        affected_rows = 0

        for params in params_list:
            result = self.execute(sql, params)
            if result:
                affected_rows += result.affected_rows

        duration = time.perf_counter() - start_time
        return QueryResult(affected_rows=affected_rows, duration=duration)

    def fetch_one(self,
                  sql: str,
                  params: Optional[Tuple] = None,
                  column_types: Optional[ColumnTypes] = None) -> Optional[Dict]:
        """
        Fetch single record.

        Args:
            sql: SQL statement
            params: SQL parameters
            column_types: Column type mapping for result type conversion

        Returns:
            Optional[Dict]: Query result or None if no rows
        """
        # Use ReturningOptions.all_columns() to indicate we want result data
        result = self.execute(sql, params, ReturningOptions.all_columns(), column_types)
        return result.data[0] if result and result.data else None

    def fetch_all(self,
                  sql: str,
                  params: Optional[Tuple] = None,
                  column_types: Optional[ColumnTypes] = None) -> List[Dict]:
        """
        Fetch multiple records.

        Args:
            sql: SQL statement
            params: SQL parameters
            column_types: Column type mapping for result type conversion

        Returns:
            List[Dict]: Query result list
        """
        # Use ReturningOptions.all_columns() to indicate we want result data
        result = self.execute(sql, params, ReturningOptions.all_columns(), column_types)
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
               returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
               column_types: Optional[ColumnTypes] = None,
               auto_commit: Optional[bool] = True,
               primary_key: Optional[str] = None) -> QueryResult:
        """
        Insert record.

        Args:
            table: Table name
            data: Data to insert
            returning: Controls RETURNING clause behavior:
                - None: No RETURNING clause
                - bool: Simple RETURNING * if True
                - List[str]: Return specific columns
                - ReturningOptions: Full control over RETURNING options
            column_types: Column type mapping for result type conversion
            auto_commit: If True and not in transaction, auto commit
            primary_key: Primary key column name (optional, used by specific backends)

        Returns:
            QueryResult: Execution result
        """
        # Clean field names by stripping quotes
        cleaned_data = {
            k.strip('"').strip('`'): v
            for k, v in data.items()
        }

        # Use dialect's format_identifier to ensure correct quoting
        fields = [self.dialect.format_identifier(field) for field in cleaned_data.keys()]
        values = list(cleaned_data.values())
        placeholders = [self.dialect.get_placeholder() for _ in fields]

        sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(placeholders)})"

        # Execute query and get result
        result = self.execute(sql, tuple(values), returning, column_types)

        # Handle auto_commit if specified
        if auto_commit:
            self._handle_auto_commit_if_needed()

        # If we have returning data, ensure the column names are consistently without quotes
        if returning and result.data:
            cleaned_data = []
            for row in result.data:
                cleaned_row = {
                    k.strip('"').strip('`'): v
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
               returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
               column_types: Optional[ColumnTypes] = None,
               auto_commit: bool = True) -> QueryResult:
        """
        Update record.

        Args:
            table: Table name
            data: Data to update
            where: WHERE condition
            params: WHERE condition parameters
            returning: Controls RETURNING clause behavior:
                - None: No RETURNING clause
                - bool: Simple RETURNING * if True
                - List[str]: Return specific columns
                - ReturningOptions: Full control over RETURNING options
            column_types: Column type mapping for result type conversion
            auto_commit: If True and not in transaction, auto commit

        Returns:
            QueryResult: Execution result
        """
        # Format update statement
        set_items = [f"{self.dialect.format_identifier(k)} = {self.dialect.get_placeholder()}"
                     for k in data.keys()]
        values = list(data.values())

        sql = f"UPDATE {table} SET {', '.join(set_items)} WHERE {where}"

        # Execute query
        result = self.execute(sql, tuple(values) + params, returning, column_types)

        # Handle auto_commit if specified
        if auto_commit:
            self._handle_auto_commit_if_needed()

        return result

    def delete(self,
               table: str,
               where: str,
               params: Tuple,
               returning: Optional[Union[bool, List[str], ReturningOptions]] = None,
               column_types: Optional[ColumnTypes] = None,
               auto_commit: bool = True) -> QueryResult:
        """
        Delete record.

        Args:
            table: Table name
            where: WHERE condition
            params: WHERE condition parameters
            returning: Controls RETURNING clause behavior:
                - None: No RETURNING clause
                - bool: Simple RETURNING * if True
                - List[str]: Return specific columns
                - ReturningOptions: Full control over RETURNING options
            column_types: Column type mapping for result type conversion
            auto_commit: If True and not in transaction, auto commit

        Returns:
            QueryResult: Execution result
        """
        # Format delete statement
        sql = f"DELETE FROM {table} WHERE {where}"

        # Execute query
        result = self.execute(sql, params, returning, column_types)

        # Handle auto_commit if specified
        if auto_commit:
            self._handle_auto_commit_if_needed()

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
