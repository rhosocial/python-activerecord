# src/rhosocial/activerecord/backend/base/execution.py
import logging
import time
from typing import Optional, Tuple, List, Union, Dict
from ..options import ExecutionOptions
from ..result import QueryResult
from ..schema import StatementType

class ExecutionMixin:
    """Mixin for the core synchronous execute method."""
    def execute(self, sql: str, params: Optional[Tuple] = None, *, options: ExecutionOptions) -> QueryResult:
        start_time = time.perf_counter()
        self.log(logging.DEBUG, f"Executing SQL: {sql}, parameters: {params}")
        try:
            if not self._connection: self.connect()
            stmt_type, is_select, is_dml = options.stmt_type, (options.stmt_type == StatementType.DQL), (options.stmt_type == StatementType.DML)
            returning_options = self._process_returning_options(options.returning)
            need_returning = bool(returning_options) and is_dml
            if need_returning: sql = self._prepare_returning_clause(sql, returning_options, stmt_type)
            cursor = self._get_cursor()
            final_sql, final_params = self._prepare_sql_and_params(sql, params)
            cursor = self._execute_query(cursor, final_sql, final_params)
            data = self._process_result_set(cursor, is_select, need_returning, options.column_adapters, options.column_mapping)
            duration = time.perf_counter() - start_time
            self._log_query_completion(stmt_type, cursor, data, duration)
            result = self._build_query_result(cursor, data, duration)
            self._handle_auto_commit_if_needed()
            return result
        except Exception as e:
            self.log(logging.ERROR, f"Error executing query: {str(e)}")
            return self._handle_execution_error(e)
    def execute_many(self, sql: str, params_list: List[Tuple]) -> Optional[QueryResult]:
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
    """Mixin for the core asynchronous execute method."""
    async def execute(self, sql: str, params: Optional[Tuple] = None, *, options: ExecutionOptions) -> QueryResult:
        start_time = time.perf_counter()
        self.log(logging.DEBUG, f"Executing SQL: {sql}, parameters: {params}")
        try:
            if not self._connection: await self.connect()
            stmt_type, is_select, is_dml = options.stmt_type, (options.stmt_type == StatementType.DQL), (options.stmt_type == StatementType.DML)
            returning_options = self._process_returning_options(options.returning)
            need_returning = bool(returning_options) and is_dml
            if need_returning: sql = self._prepare_returning_clause(sql, returning_options, stmt_type)
            cursor = await self._get_cursor()
            final_sql, final_params = self._prepare_sql_and_params(sql, params)
            cursor = await self._execute_query(cursor, final_sql, final_params)
            data = await self._process_result_set(cursor, is_select, need_returning, options.column_adapters, options.column_mapping)
            duration = time.perf_counter() - start_time
            self._log_query_completion(stmt_type, cursor, data, duration)
            result = self._build_query_result(cursor, data, duration)
            await self._handle_auto_commit_if_needed()
            return result
        except Exception as e:
            self.log(logging.ERROR, f"Error executing query: {str(e)}")
            return await self._handle_execution_error(e)
    async def execute_many(self, sql: str, params_list: List[Union[Tuple, Dict]]) -> Optional[QueryResult]:
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