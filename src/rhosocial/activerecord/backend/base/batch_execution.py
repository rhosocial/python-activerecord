# src/rhosocial/activerecord/backend/base/batch_execution.py
"""
Batch execution operations mixin for backend implementations.

This module provides the execute_batch_dml and execute_batch_dql methods
for both synchronous and asynchronous database operations.
"""

import copy
import logging
import time
from dataclasses import dataclass
from typing import (
    Optional,
    List,
    Dict,
    Any,
    Union,
    Type,
    Iterator,
    AsyncIterator,
    TYPE_CHECKING,
)

from ..result import QueryResult, BatchDMLResult, BatchDQLResult, BatchCommitMode
from ..type_adapter import SQLTypeAdapter
from ..expression import InsertExpression, UpdateExpression, DeleteExpression

if TYPE_CHECKING:
    from ..expression import (
        QueryExpression,
        WithQueryExpression,
        SetOperationExpression,
    )


@dataclass
class _BatchDMLBundle:
    """Internal bundle for batch DML execution.

    This class holds the compiled information needed to execute a batch
    of homogeneous DML expressions efficiently.

    Attributes:
        sql_template: Shared SQL template (without RETURNING clause).
        final_sql: Final SQL to execute (may include RETURNING clause).
        params_list: List of parameter tuples for each expression.
        expression_type: The type of DML expression (Insert/Update/Delete).
        has_returning: Whether RETURNING clause is attached.
        count: Total number of expressions in the batch.
    """

    sql_template: str
    final_sql: str
    params_list: List[tuple]
    expression_type: Type
    has_returning: bool
    count: int


# Type aliases for DML expressions
HomogeneousDMLList = Union[
    List["InsertExpression"],
    List["UpdateExpression"],
    List["DeleteExpression"],
]

# Type alias for DQL expressions
DQLExpression = Union[
    "QueryExpression",
    "WithQueryExpression",
    "SetOperationExpression",
]


class BatchExecutionMixin:
    """
    Mixin for batch DML and DQL execution methods (synchronous).

    This mixin provides batch execution capabilities for database operations,
    supporting both DML (INSERT, UPDATE, DELETE) and DQL (SELECT) statements.

    Key features:
    - Homogeneous expression validation for DML batches
    - RETURNING clause support through expression-dialect system
    - Flexible transaction management (WHOLE vs PER_BATCH commit modes)
    - Lazy iteration through generators for memory efficiency
    """

    def execute_batch_dml(
        self,
        expressions: HomogeneousDMLList,
        *,
        batch_size: int = 100,
        commit_mode: BatchCommitMode = BatchCommitMode.WHOLE,
        returning_columns: Optional[List[str]] = None,
        column_adapters: Optional[Dict] = None,
        column_mapping: Optional[Dict] = None,
    ) -> Iterator[BatchDMLResult]:
        """
        Execute a batch of homogeneous DML expressions with iteration.

        This method executes multiple DML expressions (INSERT, UPDATE, or DELETE)
        in batches, yielding results after each batch. It supports RETURNING
        clause for backends that implement it.

        Args:
            expressions: List of homogeneous DML expressions (all must be the same
                        type - all InsertExpression, all UpdateExpression, or all
                        DeleteExpression).
            batch_size: Number of expressions to process per batch. Default: 100.
            commit_mode: Transaction commit strategy:
                - WHOLE: Execute all batches in a single transaction (default).
                - PER_BATCH: Commit after each batch completes.
            returning_columns: Optional list of column names to return. If specified,
                              RETURNING clause is attached through expression cloning.
            column_adapters: Optional type adapters for processing returned columns.
            column_mapping: Optional mapping from column names to field names.

        Yields:
            BatchDMLResult: Result object for each processed batch containing:
                - results: List of QueryResult objects (when has_returning is True)
                - batch_index: Zero-based batch index
                - batch_size: Actual number of expressions in this batch
                - total_affected_rows: Total rows affected in this batch
                - duration: Execution time in seconds
                - has_returning: Whether this batch contains RETURNING data

        Raises:
            TypeError: If expressions are not homogeneous (mixed types).
            ValueError: If expressions carry their own RETURNING clause, or if
                       SQL templates are not identical across expressions.
            UnsupportedFeatureError: If returning_columns is specified but the
                                    dialect does not support RETURNING clause.
                                    This exception is naturally raised by the
                                    expression-dialect system during to_sql().

        Note:
            - For INSERT expressions, all expressions should have the same
              ValuesSource row count to ensure identical SQL templates.
            - When commit_mode is WHOLE and iteration is interrupted (break),
              the managed transaction is automatically rolled back.
            - When commit_mode is PER_BATCH, already committed batches cannot
              be rolled back.

        Example:
            >>> expressions = [
            ...     InsertExpression(dialect, into="users", source=ValuesSource(...)),
            ...     InsertExpression(dialect, into="users", source=ValuesSource(...)),
            ... ]
            >>> for result in backend.execute_batch_dml(expressions, batch_size=50):
            ...     print(f"Batch {result.batch_index}: {result.total_affected_rows} rows")
        """
        # Handle empty expressions list
        if not expressions:
            return iter([])

        # Stage 1-5: Compile and validate (includes type check, RETURNING conflict,
        # template validation, and RETURNING attachment through expression cloning)
        bundle = self._compile_and_validate_dml(expressions, returning_columns)

        # Ensure connection
        if not self._connection:
            self.connect()

        # Transaction management
        managed_tx = False
        completed = False
        try:
            # Start transaction for WHOLE mode if not already in transaction
            if commit_mode == BatchCommitMode.WHOLE and not self.in_transaction:
                self.begin_transaction()
                managed_tx = True

            # Stage 6: Batch execution
            total_count = bundle.count
            batch_index = 0

            for start_idx in range(0, total_count, batch_size):
                end_idx = min(start_idx + batch_size, total_count)
                current_batch_size = end_idx - start_idx
                batch_params = bundle.params_list[start_idx:end_idx]

                # Start PER_BATCH transaction if needed
                if commit_mode == BatchCommitMode.PER_BATCH and not self.in_transaction:
                    self.begin_transaction()
                    managed_tx = True

                start_time = time.perf_counter()

                try:
                    if bundle.has_returning:
                        # Execute with RETURNING clause - use execute path
                        results = self._execute_batch_with_returning(
                            bundle.final_sql,
                            batch_params,
                            column_adapters,
                            column_mapping,
                        )
                        total_affected = sum(r.affected_rows for r in results)
                    else:
                        # Execute without RETURNING - use executemany path
                        total_affected = self._execute_batch_fast(
                            bundle.final_sql,
                            batch_params,
                        )
                        results = []

                    duration = time.perf_counter() - start_time

                    # Create result
                    result = BatchDMLResult(
                        results=results,
                        batch_index=batch_index,
                        batch_size=current_batch_size,
                        total_affected_rows=total_affected,
                        duration=duration,
                        has_returning=bundle.has_returning,
                    )

                    # Handle PER_BATCH commit
                    if commit_mode == BatchCommitMode.PER_BATCH:
                        self.commit_transaction()
                        if end_idx < total_count:
                            self.begin_transaction()

                    batch_index += 1
                    yield result

                except Exception as e:
                    self.log(logging.ERROR, f"Error in batch execution: {str(e)}")
                    if managed_tx and self.in_transaction:
                        self.rollback_transaction()
                    raise

            # Only reached when all batches have been yielded AND consumed
            completed = True

        finally:
            if managed_tx and self.in_transaction:
                if completed:
                    self.commit_transaction()
                else:
                    self.rollback_transaction()

    def execute_batch_dql(
        self,
        expression: DQLExpression,
        *,
        page_size: int = 1000,
        column_adapters: Optional[Dict] = None,
        column_mapping: Optional[Dict] = None,
    ) -> Iterator[BatchDQLResult]:
        """
        Execute a DQL expression with lazy pagination.

        This method executes a single DQL expression (SELECT query) and
        yields results page by page using fetchmany() for memory-efficient
        processing of large result sets.

        Args:
            expression: A DQL expression (QueryExpression, WithQueryExpression,
                       or SetOperationExpression).
            page_size: Number of rows per page. Default: 1000.
            column_adapters: Optional type adapters for processing columns.
            column_mapping: Optional mapping from column names to field names.

        Yields:
            BatchDQLResult: Result object for each page containing:
                - data: List of row dictionaries for this page
                - page_index: Zero-based page index
                - page_size: Actual number of rows in this page
                - has_more: Whether there are more pages available
                - duration: Time to fetch this page in seconds

        Note:
            - The cursor remains open throughout iteration and is automatically
              closed when iteration completes or is interrupted.
            - Breaking out of the iteration early will properly close the cursor.

        Example:
            >>> query = QueryExpression(dialect, select=[...], from_="users")
            >>> for page in backend.execute_batch_dql(query, page_size=500):
            ...     print(f"Page {page.page_index}: {page.page_size} rows")
            ...     for row in page.data:
            ...         process(row)
            ...     if not page.has_more:
            ...         break
        """
        # Ensure connection
        if not self._connection:
            self.connect()

        # Compile expression to SQL
        sql, params = expression.to_sql()

        # Prepare parameters with type conversion
        prepared_params = params
        if params:
            all_suggestions = self.get_default_adapter_suggestions()
            param_adapters = []
            for param_value in params:
                py_type = type(param_value)
                suggestion = all_suggestions.get(py_type)
                param_adapters.append(suggestion if suggestion else None)
            prepared_params = self.prepare_parameters(params, param_adapters)

        final_sql, final_params = self._prepare_sql_and_params(sql, prepared_params)

        # Get appropriate cursor for DQL
        cursor = self._get_dql_cursor()

        try:
            # Execute query
            cursor.execute(final_sql, final_params)

            # Get column names from cursor description
            column_names = []
            if cursor.description:
                column_names = [desc[0] for desc in cursor.description]

            # Pagination loop
            page_index = 0
            while True:
                start_time = time.perf_counter()
                rows = cursor.fetchmany(page_size)

                if not rows:
                    break

                # Process rows
                data = []
                for row in rows:
                    if hasattr(row, "keys"):
                        # Row object with keys (e.g., sqlite3.Row)
                        row_dict = dict(row)
                    else:
                        # Tuple - map to column names
                        row_dict = dict(zip(column_names, row))

                    # Apply column adapters and mapping
                    if column_adapters or column_mapping:
                        row_dict = self._adapt_and_map_row(row_dict, column_adapters, column_mapping)

                    data.append(row_dict)

                duration = time.perf_counter() - start_time
                has_more = len(rows) == page_size

                result = BatchDQLResult(
                    data=data,
                    page_index=page_index,
                    page_size=len(rows),
                    has_more=has_more,
                    duration=duration,
                )

                page_index += 1
                yield result

                if not has_more:
                    break

        finally:
            # Always close cursor
            try:
                cursor.close()
            except Exception:
                pass

    def _compile_and_validate_dml(
        self,
        expressions: HomogeneousDMLList,
        returning_columns: Optional[List[str]] = None,
    ) -> _BatchDMLBundle:
        """
        Compile DML expressions, validate homogeneity, and attach RETURNING.

        This method performs:
        1. Type validation - ensure all expressions are the same type
        2. RETURNING conflict detection - no expression should carry its own RETURNING
        3. Template compilation and validation - all SQL templates must be identical
        4. RETURNING attachment - through expression cloning + to_sql()

        The RETURNING attachment uses the expression-dialect system:
        - Clone the first expression (shallow copy)
        - Construct a ReturningClause and attach to the clone
        - Call to_sql() on the clone to get the final SQL with RETURNING
        - If the dialect does not support RETURNING, format_returning_clause()
          will naturally raise UnsupportedFeatureError

        Args:
            expressions: List of homogeneous DML expressions.
            returning_columns: Optional list of column names for RETURNING clause.

        Returns:
            _BatchDMLBundle containing the SQL templates, parameters, and metadata.

        Raises:
            TypeError: If expressions are not homogeneous.
            ValueError: If any expression carries its own RETURNING clause,
                       or if SQL templates differ.
            UnsupportedFeatureError: If returning_columns is specified but
                                    the dialect does not support RETURNING.
        """
        # Stage 1: Type validation
        first_type = type(expressions[0])
        for i, expr in enumerate(expressions):
            if type(expr) is not first_type:
                raise TypeError(
                    f"Batch requires homogeneous expressions. "
                    f"Expected {first_type.__name__}, found {type(expr).__name__} at index {i}."
                )

        # Stage 2: RETURNING conflict detection
        for i, expr in enumerate(expressions):
            if isinstance(expr, (InsertExpression, UpdateExpression, DeleteExpression)) and expr.returning is not None:
                raise ValueError(
                    f"Expressions must not carry their own RETURNING clause. "
                    f"Use the returning_columns parameter instead. "
                    f"Found RETURNING at index {i}."
                )

        # Stage 3: Compile all expressions
        sql_templates = set()
        params_list = []

        for expr in expressions:
            sql, params = expr.to_sql()
            sql_templates.add(sql)
            params_list.append(params if params else ())

        # Stage 4: Template validation
        if len(sql_templates) > 1:
            raise ValueError(
                f"Batch execution requires identical SQL templates. Found {len(sql_templates)} distinct templates."
            )

        sql_template = sql_templates.pop()

        # Stage 5: RETURNING attachment (through expression cloning + to_sql)
        has_returning = returning_columns is not None and len(returning_columns) > 0
        final_sql = sql_template

        if has_returning:
            # Clone the first expression (shallow copy is sufficient)
            clone = copy.copy(expressions[0])

            # Import here to avoid circular dependency
            from ..expression import ReturningClause, Column

            # Construct ReturningClause with the specified columns
            dialect = expressions[0].dialect
            column_exprs = [Column(dialect, col) for col in returning_columns]
            returning_clause = ReturningClause(dialect, column_exprs)

            # Attach RETURNING to the clone
            clone.returning = returning_clause

            # Call to_sql() to get the final SQL with RETURNING
            # This will naturally raise UnsupportedFeatureError if the dialect
            # does not support RETURNING (through format_returning_clause)
            final_sql, _ = clone.to_sql()

        return _BatchDMLBundle(
            sql_template=sql_template,
            final_sql=final_sql,
            params_list=params_list,
            expression_type=first_type,
            has_returning=has_returning,
            count=len(expressions),
        )

    def _execute_batch_fast(
        self,
        sql: str,
        params_list: List[tuple],
    ) -> int:
        """
        Execute batch DML using executemany for optimal performance.

        This method is used when no RETURNING clause is needed, allowing
        the use of cursor.executemany() for efficient bulk operations.

        Args:
            sql: The SQL statement to execute.
            params_list: List of parameter tuples.

        Returns:
            Total number of affected rows.
        """
        cursor = self._get_cursor()
        cursor.executemany(sql, params_list)
        affected = cursor.rowcount
        self._handle_auto_commit_if_needed()
        return affected if affected >= 0 else 0

    def _execute_batch_with_returning(
        self,
        sql: str,
        params_list: List[tuple],
        column_adapters: Optional[Dict],
        column_mapping: Optional[Dict],
    ) -> List[QueryResult]:
        """
        Execute batch DML with RETURNING clause.

        This method executes each statement individually to capture
        RETURNING data for each row.

        Args:
            sql: The SQL statement with RETURNING clause.
            params_list: List of parameter tuples.
            column_adapters: Type adapters for returned columns.
            column_mapping: Column name to field name mapping.

        Returns:
            List of QueryResult objects, one per expression.
        """
        results = []

        for params in params_list:
            # Prepare parameters with type conversion
            prepared_params = params
            if params:
                all_suggestions = self.get_default_adapter_suggestions()
                param_adapters = []
                for param_value in params:
                    py_type = type(param_value)
                    suggestion = all_suggestions.get(py_type)
                    param_adapters.append(suggestion if suggestion else None)
                prepared_params = self.prepare_parameters(params, param_adapters)

            final_sql, final_params = self._prepare_sql_and_params(sql, prepared_params)

            # Execute and get result
            cursor = self._get_cursor()
            cursor.execute(final_sql, final_params)

            # Process result set
            data = self._process_result_set(
                cursor,
                is_select=True,
                column_adapters=column_adapters,
                column_mapping=column_mapping,
            )

            affected = cursor.rowcount if cursor.rowcount >= 0 else 0
            if data:
                affected = len(data)

            result = QueryResult(
                data=data,
                affected_rows=affected,
                duration=0.0,  # Individual duration not tracked in batch
            )
            results.append(result)

        self._handle_auto_commit_if_needed()
        return results

    def _adapt_and_map_row(
        self,
        row_dict: Dict[str, Any],
        column_adapters: Optional[Dict],
        column_mapping: Optional[Dict],
    ) -> Dict[str, Any]:
        """
        Apply type adapters and column mapping to a row.

        Args:
            row_dict: Original row dictionary.
            column_adapters: Type adapters by column name.
            column_mapping: Column name to field name mapping.

        Returns:
            Transformed row dictionary.
        """
        result = {}

        for col_name, value in row_dict.items():
            # Apply adapter if available
            if column_adapters and col_name in column_adapters:
                adapter = column_adapters[col_name]
                if adapter and isinstance(adapter, SQLTypeAdapter):
                    value = adapter.from_database(value)

            # Apply column mapping
            field_name = col_name
            if column_mapping and col_name in column_mapping:
                field_name = column_mapping[col_name]

            result[field_name] = value

        return result

    def _get_dql_cursor(self):
        """
        Get a cursor suitable for DQL operations.

        Subclasses can override this to provide specialized cursors
        (e.g., unbuffered cursors for MySQL, named cursors for PostgreSQL).

        Returns:
            A database cursor for executing DQL statements.
        """
        return self._get_cursor()


class AsyncBatchExecutionMixin:
    """
    Mixin for batch DML and DQL execution methods (asynchronous).

    This mixin provides the async equivalents of BatchExecutionMixin methods,
    supporting non-blocking database operations with the same features.
    """

    async def execute_batch_dml(
        self,
        expressions: HomogeneousDMLList,
        *,
        batch_size: int = 100,
        commit_mode: BatchCommitMode = BatchCommitMode.WHOLE,
        returning_columns: Optional[List[str]] = None,
        column_adapters: Optional[Dict] = None,
        column_mapping: Optional[Dict] = None,
    ) -> AsyncIterator[BatchDMLResult]:
        """
        Execute a batch of homogeneous DML expressions asynchronously.

        See BatchExecutionMixin.execute_batch_dml for detailed documentation.
        This is the async version that yields AsyncIterator[BatchDMLResult].
        """
        if not expressions:
            return

        # Stage 1-5: Compile and validate
        bundle = self._compile_and_validate_dml(expressions, returning_columns)

        # Ensure connection
        if not self._connection:
            await self.connect()

        # Transaction management
        managed_tx = False
        completed = False
        try:
            if commit_mode == BatchCommitMode.WHOLE and not self.in_transaction:
                await self.begin_transaction()
                managed_tx = True

            total_count = bundle.count
            batch_index = 0

            for start_idx in range(0, total_count, batch_size):
                end_idx = min(start_idx + batch_size, total_count)
                current_batch_size = end_idx - start_idx
                batch_params = bundle.params_list[start_idx:end_idx]

                if commit_mode == BatchCommitMode.PER_BATCH and not self.in_transaction:
                    await self.begin_transaction()
                    managed_tx = True

                start_time = time.perf_counter()

                try:
                    if bundle.has_returning:
                        results = await self._execute_batch_with_returning_async(
                            bundle.final_sql,
                            batch_params,
                            column_adapters,
                            column_mapping,
                        )
                        total_affected = sum(r.affected_rows for r in results)
                    else:
                        total_affected = await self._execute_batch_fast_async(
                            bundle.final_sql,
                            batch_params,
                        )
                        results = []

                    duration = time.perf_counter() - start_time

                    result = BatchDMLResult(
                        results=results,
                        batch_index=batch_index,
                        batch_size=current_batch_size,
                        total_affected_rows=total_affected,
                        duration=duration,
                        has_returning=bundle.has_returning,
                    )

                    if commit_mode == BatchCommitMode.PER_BATCH:
                        await self.commit_transaction()
                        if end_idx < total_count:
                            await self.begin_transaction()

                    batch_index += 1
                    yield result

                except Exception as e:
                    self.log(logging.ERROR, f"Error in async batch execution: {str(e)}")
                    if managed_tx and self.in_transaction:
                        await self.rollback_transaction()
                    raise

            # Only reached when all batches have been yielded AND consumed
            completed = True

        finally:
            if managed_tx and self.in_transaction:
                if completed:
                    await self.commit_transaction()
                else:
                    await self.rollback_transaction()

    async def execute_batch_dql(
        self,
        expression: DQLExpression,
        *,
        page_size: int = 1000,
        column_adapters: Optional[Dict] = None,
        column_mapping: Optional[Dict] = None,
    ) -> AsyncIterator[BatchDQLResult]:
        """
        Execute a DQL expression with lazy pagination asynchronously.

        See BatchExecutionMixin.execute_batch_dql for detailed documentation.
        This is the async version that yields AsyncIterator[BatchDQLResult].
        """
        if not self._connection:
            await self.connect()

        sql, params = expression.to_sql()

        prepared_params = params
        if params:
            all_suggestions = self.get_default_adapter_suggestions()
            param_adapters = []
            for param_value in params:
                py_type = type(param_value)
                suggestion = all_suggestions.get(py_type)
                param_adapters.append(suggestion if suggestion else None)
            prepared_params = self.prepare_parameters(params, param_adapters)

        final_sql, final_params = self._prepare_sql_and_params(sql, prepared_params)

        cursor = await self._get_dql_cursor()

        try:
            await cursor.execute(final_sql, final_params)

            column_names = []
            if cursor.description:
                column_names = [desc[0] for desc in cursor.description]

            page_index = 0
            while True:
                start_time = time.perf_counter()
                rows = await cursor.fetchmany(page_size)

                if not rows:
                    break

                data = []
                for row in rows:
                    if hasattr(row, "keys"):
                        row_dict = dict(row)
                    else:
                        row_dict = dict(zip(column_names, row))

                    if column_adapters or column_mapping:
                        row_dict = self._adapt_and_map_row(row_dict, column_adapters, column_mapping)

                    data.append(row_dict)

                duration = time.perf_counter() - start_time
                has_more = len(rows) == page_size

                result = BatchDQLResult(
                    data=data,
                    page_index=page_index,
                    page_size=len(rows),
                    has_more=has_more,
                    duration=duration,
                )

                page_index += 1
                yield result

                if not has_more:
                    break

        finally:
            try:
                await cursor.close()
            except Exception:
                pass

    def _compile_and_validate_dml(
        self,
        expressions: HomogeneousDMLList,
        returning_columns: Optional[List[str]] = None,
    ) -> _BatchDMLBundle:
        """
        Compile DML expressions, validate homogeneity, and attach RETURNING.

        This method is shared between sync and async implementations.
        See BatchExecutionMixin._compile_and_validate_dml for details.
        """
        # Stage 1: Type validation
        first_type = type(expressions[0])
        for i, expr in enumerate(expressions):
            if type(expr) is not first_type:
                raise TypeError(
                    f"Batch requires homogeneous expressions. "
                    f"Expected {first_type.__name__}, found {type(expr).__name__} at index {i}."
                )

        # Stage 2: RETURNING conflict detection
        for i, expr in enumerate(expressions):
            if isinstance(expr, (InsertExpression, UpdateExpression, DeleteExpression)) and expr.returning is not None:
                raise ValueError(
                    f"Expressions must not carry their own RETURNING clause. "
                    f"Use the returning_columns parameter instead. "
                    f"Found RETURNING at index {i}."
                )

        # Stage 3: Compile all expressions
        sql_templates = set()
        params_list = []

        for expr in expressions:
            sql, params = expr.to_sql()
            sql_templates.add(sql)
            params_list.append(params if params else ())

        # Stage 4: Template validation
        if len(sql_templates) > 1:
            raise ValueError(
                f"Batch execution requires identical SQL templates. Found {len(sql_templates)} distinct templates."
            )

        sql_template = sql_templates.pop()

        # Stage 5: RETURNING attachment (through expression cloning + to_sql)
        has_returning = returning_columns is not None and len(returning_columns) > 0
        final_sql = sql_template

        if has_returning:
            # Clone the first expression (shallow copy is sufficient)
            clone = copy.copy(expressions[0])

            # Import here to avoid circular dependency
            from ..expression import ReturningClause, Column

            # Construct ReturningClause with the specified columns
            dialect = expressions[0].dialect
            column_exprs = [Column(dialect, col) for col in returning_columns]
            returning_clause = ReturningClause(dialect, column_exprs)

            # Attach RETURNING to the clone
            clone.returning = returning_clause

            # Call to_sql() to get the final SQL with RETURNING
            # This will naturally raise UnsupportedFeatureError if the dialect
            # does not support RETURNING
            final_sql, _ = clone.to_sql()

        return _BatchDMLBundle(
            sql_template=sql_template,
            final_sql=final_sql,
            params_list=params_list,
            expression_type=first_type,
            has_returning=has_returning,
            count=len(expressions),
        )

    async def _execute_batch_fast_async(
        self,
        sql: str,
        params_list: List[tuple],
    ) -> int:
        """Execute batch DML using async executemany."""
        cursor = await self._get_cursor()
        await cursor.executemany(sql, params_list)
        affected = cursor.rowcount
        await self._handle_auto_commit_if_needed()
        return affected if affected >= 0 else 0

    async def _execute_batch_with_returning_async(
        self,
        sql: str,
        params_list: List[tuple],
        column_adapters: Optional[Dict],
        column_mapping: Optional[Dict],
    ) -> List[QueryResult]:
        """Execute batch DML with RETURNING clause asynchronously."""
        results = []

        for params in params_list:
            prepared_params = params
            if params:
                all_suggestions = self.get_default_adapter_suggestions()
                param_adapters = []
                for param_value in params:
                    py_type = type(param_value)
                    suggestion = all_suggestions.get(py_type)
                    param_adapters.append(suggestion if suggestion else None)
                prepared_params = self.prepare_parameters(params, param_adapters)

            final_sql, final_params = self._prepare_sql_and_params(sql, prepared_params)

            cursor = await self._get_cursor()
            await cursor.execute(final_sql, final_params)

            data = await self._process_result_set(
                cursor,
                is_select=True,
                column_adapters=column_adapters,
                column_mapping=column_mapping,
            )

            affected = cursor.rowcount if cursor.rowcount >= 0 else 0
            if data:
                affected = len(data)

            result = QueryResult(
                data=data,
                affected_rows=affected,
                duration=0.0,
            )
            results.append(result)

        await self._handle_auto_commit_if_needed()
        return results

    def _adapt_and_map_row(
        self,
        row_dict: Dict[str, Any],
        column_adapters: Optional[Dict],
        column_mapping: Optional[Dict],
    ) -> Dict[str, Any]:
        """Apply adapters and mapping (shared with sync)."""
        result = {}

        for col_name, value in row_dict.items():
            if column_adapters and col_name in column_adapters:
                adapter = column_adapters[col_name]
                if adapter and isinstance(adapter, SQLTypeAdapter):
                    value = adapter.from_database(value)

            field_name = col_name
            if column_mapping and col_name in column_mapping:
                field_name = column_mapping[col_name]

            result[field_name] = value

        return result

    async def _get_dql_cursor(self):
        """Get a cursor suitable for async DQL operations."""
        return await self._get_cursor()
