# src/rhosocial/activerecord/backend/base/execution.py
"""
Execution operations mixin for backend implementations.

This mixin provides the core execute methods for both synchronous and asynchronous
database operations. It handles the complete execution pipeline including parameter
preparation, SQL preparation, query execution, and result processing.
"""
import logging
import time
from typing import Optional, Tuple, List, Union, Dict

from ..options import ExecutionOptions
from ..result import QueryResult
from ..schema import StatementType


class ExecutionMixin:
    """
    Mixin for the core synchronous execute method.

    This mixin provides the primary execution method for synchronous database operations.
    It implements the complete execution pipeline including:
    1. Connection management
    2. Parameter type adaptation
    3. SQL and parameter preparation
    4. Query execution
    5. Result set processing
    6. Transaction management
    7. Error handling

    The execute method follows the principle of centralized parameter type conversion,
    where all parameter adaptation happens in this single location to ensure consistent
    behavior across all database operations.
    """
    def execute(self, sql: str, params: Optional[Tuple] = None, *, options: ExecutionOptions) -> QueryResult:
        """
        Execute a SQL statement synchronously with comprehensive parameter and result processing.

        This method implements the complete execution pipeline for synchronous database
        operations. It handles connection management, parameter type adaptation, SQL
        preparation, query execution, and result processing in a single cohesive flow.

        The method follows the principle of centralized parameter type conversion,
        performing all parameter adaptations in this single location to ensure consistent
        behavior across all database operations. This avoids scattered type conversion
        logic that could lead to inconsistent behavior.

        Args:
            sql: The SQL statement to execute
            params: Optional tuple of parameter values to bind to the SQL statement
            options: ExecutionOptions object containing all execution parameters including:
                    - stmt_type: Type of SQL statement (DQL, DML, DDL, etc.)
                    - process_result_set: Whether to process result sets (defaults to DQL behavior)
                    - column_adapters: Type adapters for processing result columns
                    - column_mapping: Column name to field name mapping for results

        Returns:
            QueryResult object containing execution results including affected rows,
            duration, and optionally result data if process_result_set is True

        Raises:
            DatabaseError: If the query execution fails
            ConnectionError: If there are connection-related issues
        """
        start_time = time.perf_counter()
        self.log(logging.DEBUG, f"Executing SQL: {sql}, parameters: {params}")
        try:
            if not self._connection: self.connect()
            stmt_type = options.stmt_type
            # Determine if result set should be processed based on statement type and process_result_set flag
            # If process_result_set is explicitly set, use that; otherwise, default to DQL behavior
            if options.process_result_set is not None:
                is_select = options.process_result_set
            else:
                is_select = (options.stmt_type == StatementType.DQL)
            cursor = self._get_cursor()

            # Prepare parameters for database compatibility
            # This is the centralized location for parameter type conversion following the design principle
            prepared_params = params
            if params:
                # Get default adapter suggestions from backend
                all_suggestions = self.get_default_adapter_suggestions()

                # Build param_adapters for prepare_parameters for sequence parameters
                param_adapters = []
                for param_value in params:
                    py_type = type(param_value)
                    suggestion = all_suggestions.get(py_type)

                    if suggestion:
                        param_adapters.append(suggestion)
                    else:
                        # If no specific adapter is found, append None (no conversion)
                        param_adapters.append(None)

                # Prepare the parameters using the backend's prepare_parameters method
                # This performs the actual type conversion from Python types to database-compatible types
                prepared_params = self.prepare_parameters(params, param_adapters)

            final_sql, final_params = self._prepare_sql_and_params(sql, prepared_params)
            cursor = self._execute_query(cursor, final_sql, final_params)
            data = self._process_result_set(cursor, is_select, options.column_adapters, options.column_mapping)
            duration = time.perf_counter() - start_time
            self._log_query_completion(stmt_type, cursor, data, duration)
            result = self._build_query_result(cursor, data, duration)
            self._handle_auto_commit_if_needed()
            return result
        except Exception as e:
            self.log(logging.ERROR, f"Error executing query: {str(e)}")
            return self._handle_execution_error(e)
    def execute_many(self, sql: str, params_list: List[Tuple]) -> Optional[QueryResult]:
        """
        Execute a SQL statement multiple times with different parameter sets (batch operation).

        This method performs a batch execution of the same SQL statement with multiple
        parameter sets. It's optimized for bulk operations like inserting multiple records
        or updating multiple rows with different values. Unlike the single execute method,
        this method does not perform individual parameter type conversion since it assumes
        the parameters are already in database-compatible format.

        Args:
            sql: The SQL statement to execute multiple times
            params_list: List of parameter tuples, each containing values for one execution

        Returns:
            QueryResult object containing total affected rows and execution duration,
            or None if an error occurred

        Note:
            This method expects all parameters in params_list to be already database-compatible.
            It does not perform individual type conversion for each parameter set.
            The caller is responsible for ensuring parameters are properly formatted.
        """
        self.log(logging.INFO, f"Executing batch operation: {sql} with {len(params_list)} parameter sets")
        start_time = time.perf_counter()
        try:
            if not self._connection: self.connect()
            cursor = self._get_cursor()
            final_sql, _ = self._prepare_sql_and_params(sql, None)
            cursor.executemany(final_sql, params_list)
            duration = time.perf_counter() - start_time
            self._handle_auto_commit_if_needed()
            return QueryResult(affected_rows=cursor.rowcount, duration=duration)
        except Exception as e:
            self.log(logging.ERROR, f"Error in batch operation: {str(e)}")
            return self._handle_execution_error(e)

class AsyncExecutionMixin:
    """
    Mixin for the core asynchronous execute method.

    This mixin provides the primary execution method for asynchronous database operations.
    It implements the same complete execution pipeline as the synchronous version but
    using async/await syntax for non-blocking database operations. The pipeline includes:
    1. Async connection management
    2. Parameter type adaptation
    3. SQL and parameter preparation
    4. Async query execution
    5. Async result set processing
    6. Async transaction management
    7. Async error handling

    Like its synchronous counterpart, this method centralizes parameter type conversion
    in a single location to ensure consistent behavior across all async database operations.
    """
    async def execute(self, sql: str, params: Optional[Tuple] = None, *, options: ExecutionOptions) -> QueryResult:
        """
        Execute a SQL statement asynchronously with comprehensive parameter and result processing.

        This method implements the complete execution pipeline for asynchronous database
        operations. It handles async connection management, parameter type adaptation,
        SQL preparation, async query execution, and async result processing in a single
        cohesive flow.

        The method follows the principle of centralized parameter type conversion,
        performing all parameter adaptations in this single location to ensure consistent
        behavior across all database operations, whether synchronous or asynchronous.

        Args:
            sql: The SQL statement to execute
            params: Optional tuple of parameter values to bind to the SQL statement
            options: ExecutionOptions object containing all execution parameters including:
                    - stmt_type: Type of SQL statement (DQL, DML, DDL, etc.)
                    - process_result_set: Whether to process result sets (defaults to DQL behavior)
                    - column_adapters: Type adapters for processing result columns
                    - column_mapping: Column name to field name mapping for results

        Returns:
            QueryResult object containing execution results including affected rows,
            duration, and optionally result data if process_result_set is True

        Raises:
            DatabaseError: If the query execution fails
            ConnectionError: If there are connection-related issues
        """
        start_time = time.perf_counter()
        self.log(logging.DEBUG, f"Executing SQL: {sql}, parameters: {params}")
        try:
            if not self._connection: await self.connect()
            stmt_type = options.stmt_type
            # Determine if result set should be processed based on statement type and process_result_set flag
            # If process_result_set is explicitly set, use that; otherwise, default to DQL behavior
            if options.process_result_set is not None:
                is_select = options.process_result_set
            else:
                is_select = (options.stmt_type == StatementType.DQL)
            cursor = await self._get_cursor()

            # Prepare parameters for database compatibility
            # This is the centralized location for parameter type conversion following the design principle
            prepared_params = params
            if params:
                # Get default adapter suggestions from backend
                all_suggestions = self.get_default_adapter_suggestions()

                # Build param_adapters for prepare_parameters for sequence parameters
                param_adapters = []
                for param_value in params:
                    py_type = type(param_value)
                    suggestion = all_suggestions.get(py_type)

                    if suggestion:
                        param_adapters.append(suggestion)
                    else:
                        # If no specific adapter is found, append None (no conversion)
                        param_adapters.append(None)

                # Prepare the parameters using the backend's prepare_parameters method
                # This performs the actual type conversion from Python types to database-compatible types
                prepared_params = self.prepare_parameters(params, param_adapters)

            final_sql, final_params = self._prepare_sql_and_params(sql, prepared_params)
            cursor = await self._execute_query(cursor, final_sql, final_params)
            data = await self._process_result_set(cursor, is_select, options.column_adapters, options.column_mapping)
            duration = time.perf_counter() - start_time
            self._log_query_completion(stmt_type, cursor, data, duration)
            result = self._build_query_result(cursor, data, duration)
            await self._handle_auto_commit_if_needed()
            return result
        except Exception as e:
            self.log(logging.ERROR, f"Error executing query: {str(e)}")
            return await self._handle_execution_error(e)
    async def execute_many(self, sql: str, params_list: List[Union[Tuple, Dict]]) -> Optional[QueryResult]:
        """
        Execute a SQL statement multiple times with different parameter sets asynchronously (batch operation).

        This method performs an asynchronous batch execution of the same SQL statement
        with multiple parameter sets. It's optimized for bulk operations like inserting
        multiple records or updating multiple rows with different values in a non-blocking way.

        Args:
            sql: The SQL statement to execute multiple times
            params_list: List of parameter tuples or dicts, each containing values for one execution

        Returns:
            QueryResult object containing total affected rows and execution duration,
            or None if an error occurred

        Note:
            This method expects all parameters in params_list to be already database-compatible.
            It does not perform individual type conversion for each parameter set.
            The caller is responsible for ensuring parameters are properly formatted.
        """
        self.log(logging.DEBUG, f"Executing many SQL: {sql}")
        start_time = time.perf_counter()
        try:
            if not self._connection: await self.connect()
            cursor = await self._get_cursor()
            await cursor.executemany(sql, params_list)
            await self._handle_auto_commit_if_needed()
            duration = time.perf_counter() - start_time
            return QueryResult(affected_rows=cursor.rowcount, duration=duration)
        except Exception as e:
            self.log(logging.ERROR, f"Error executing many: {str(e)}")
            return await self._handle_execution_error(e)