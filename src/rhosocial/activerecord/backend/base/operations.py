"""
Defines mixins for high-level SQL data operations (INSERT, UPDATE, DELETE, FETCH),
implementing an Options-based pattern for clean, extensible, and type-safe APIs.
These mixins are designed to be composed into StorageBackend classes.
"""
from typing import Dict, Tuple, Type
from typing import List, Optional

from ..expression import InsertExpression, UpdateExpression, DeleteExpression, Literal
from ..expression.statements import ReturningClause, ValuesSource
from ..options import ExecutionOptions, InsertOptions, UpdateOptions, DeleteOptions
from ..result import QueryResult
from ..schema import StatementType
from ..type_adapter import SQLTypeAdapter


class SQLOperationsMixin:
    """Mixin for high-level synchronous SQL data operations (INSERT, UPDATE, DELETE, FETCH)."""

    def insert(self, options: InsertOptions) -> QueryResult:
        """
        Inserts a record into the database using encapsulated InsertOptions.

        This method generates an `InsertExpression` and executes it.
        It uses the Options pattern to keep the method signature clean and extensible.

        Args:
            options (InsertOptions): An object encapsulating all parameters for the insert operation.
        Returns:
            QueryResult: The result of the insert operation.
        """
        # Process values - they may be literals or expression objects
        processed_values = []
        for v in options.data.values():
            # Check if the value is a SQL expression that should be used directly in SQL
            if hasattr(v, 'to_sql') and hasattr(v, 'dialect'):
                # This is an expression object like FunctionCall, BinaryExpression, etc.
                processed_values.append(v)
            else:
                # This is a regular value that should be wrapped in a Literal
                processed_values.append(Literal(self.dialect, v))

        # Create a ValuesSource to use as the data source for the InsertExpression
        values_source = ValuesSource(self.dialect, [processed_values])

        # Create ReturningClause if returning_columns is specified
        returning_clause = None
        if options.returning_columns:
            from ..expression import Column as ExprColumn
            returning_expressions = [ExprColumn(self.dialect, col) for col in options.returning_columns]
            returning_clause = ReturningClause(self.dialect, returning_expressions)

        insert_expr = InsertExpression(
            dialect=self.dialect,
            into=options.table,
            source=values_source,
            columns=list(options.data.keys()),
            returning=returning_clause
        )

        sql, params = insert_expr.to_sql()

        exec_options = ExecutionOptions(
            stmt_type=StatementType.DML,  # Keep as DML since it's still a data manipulation operation
            column_adapters=options.column_adapters,
            column_mapping=options.column_mapping,
            process_result_set=bool(options.returning_columns)  # Process result set if returning columns specified
        )

        result = self.execute(sql, params, options=exec_options)

        if options.auto_commit:
            self._handle_auto_commit_if_needed()

        return result

    def update(self, options: UpdateOptions) -> QueryResult:
        """
        Updates records in the database using encapsulated UpdateOptions.

        This method generates an `UpdateExpression` and executes it.
        It expects a `SQLPredicate` for the `where` clause.

        Args:
            options (UpdateOptions): An object encapsulating all parameters for the update operation.
        Returns:
            QueryResult: The result of the update operation.
        """
        # Handle assignments - options.data may contain both literal values and expression objects
        assignments = {}

        # Process each item in the data dictionary
        for k, v in options.data.items():
            # Check if the value is a SQL expression that should be used directly in SQL
            if hasattr(v, 'to_sql') and hasattr(v, 'dialect'):
                # This is an expression object like FunctionCall, BinaryExpression, etc.
                assignments[k] = v
            else:
                # This is a regular value that should be wrapped in a Literal
                assignments[k] = Literal(self.dialect, v)

        # Create ReturningClause if returning_columns is specified
        returning_clause = None
        if options.returning_columns:
            from ..expression import Column as ExprColumn
            returning_expressions = [ExprColumn(self.dialect, col) for col in options.returning_columns]
            returning_clause = ReturningClause(self.dialect, returning_expressions)

        update_expr = UpdateExpression(
            dialect=self.dialect,
            table=options.table,
            assignments=assignments,
            where=options.where,
            returning=returning_clause
        )

        sql, params = update_expr.to_sql()

        exec_options = ExecutionOptions(
            stmt_type=StatementType.DML,  # Keep as DML since it's still a data manipulation operation
            column_adapters=options.column_adapters,
            column_mapping=options.column_mapping,
            process_result_set=bool(options.returning_columns)  # Process result set if returning columns specified
        )

        result = self.execute(sql, params, options=exec_options)

        if options.auto_commit:
            self._handle_auto_commit_if_needed()

        return result

    def delete(self, options: DeleteOptions) -> QueryResult:
        """
        Deletes records from the database using encapsulated DeleteOptions.

        This method generates a `DeleteExpression` and executes it.
        It expects a `SQLPredicate` for the `where` clause.

        Args:
            options (DeleteOptions): An object encapsulating all parameters for the delete operation.
        Returns:
            QueryResult: The result of the delete operation.
        """
        # Create ReturningClause if returning_columns is specified
        returning_clause = None
        if options.returning_columns:
            from ..expression import Column as ExprColumn
            returning_expressions = [ExprColumn(self.dialect, col) for col in options.returning_columns]
            returning_clause = ReturningClause(self.dialect, returning_expressions)

        delete_expr = DeleteExpression(
            dialect=self.dialect,
            table=options.table,
            where=options.where,
            returning=returning_clause
        )

        sql, params = delete_expr.to_sql()

        exec_options = ExecutionOptions(
            stmt_type=StatementType.DML,  # Keep as DML since it's still a data manipulation operation
            column_adapters=options.column_adapters,
            column_mapping=options.column_mapping,
            process_result_set=bool(options.returning_columns)  # Process result set if returning columns specified
        )

        result = self.execute(sql, params, options=exec_options)

        if options.auto_commit:
            self._handle_auto_commit_if_needed()

        return result

    def fetch_one(self, sql: str, params: Optional[Tuple] = None,
                  column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None,
                  column_mapping: Optional[Dict[str, str]] = None) -> Optional[Dict]:
        """
        Fetches a single record from the database.

        Args:
            sql (str): The SQL query string.
            params (Optional[Tuple]): Parameters for the SQL query.
            column_adapters (Optional[Dict]): Type adapters for processing result columns.
            column_mapping (Optional[Dict]): Mapping for renaming result columns.

        Returns:
            Optional[Dict]: A dictionary representing the fetched record, or None if no record found.
        """
        exec_options = ExecutionOptions(
            stmt_type=StatementType.DQL,
            column_adapters=column_adapters,
            column_mapping=column_mapping
        )
        result = self.execute(sql, params, options=exec_options)
        return result.data[0] if result and result.data else None

    def fetch_all(self, sql: str, params: Optional[Tuple] = None,
                  column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None,
                  column_mapping: Optional[Dict[str, str]] = None) -> List[Dict]:
        """
        Fetches all matching records from the database.

        Args:
            sql (str): The SQL query string.
            params (Optional[Tuple]): Parameters for the SQL query.
            column_adapters (Optional[Dict]): Type adapters for processing result columns.
            column_mapping (Optional[Dict]): Mapping for renaming result columns.

        Returns:
            List[Dict]: A list of dictionaries, each representing a fetched record.
        """
        exec_options = ExecutionOptions(
            stmt_type=StatementType.DQL,
            column_adapters=column_adapters,
            column_mapping=column_mapping
        )
        result = self.execute(sql, params, options=exec_options)
        return result.data or []


class AsyncSQLOperationsMixin:
    """Mixin for high-level asynchronous SQL data operations (INSERT, UPDATE, DELETE, FETCH)."""

    async def insert(self, options: InsertOptions) -> QueryResult:
        """
        Inserts a record asynchronously into the database using encapsulated InsertOptions.

        Args:
            options (InsertOptions): An object encapsulating all parameters for the insert operation.
        Returns:
            QueryResult: The result of the insert operation.
        """
        # Process values - they may be literals or expression objects
        processed_values = []
        for v in options.data.values():
            # Check if the value is a SQL expression that should be used directly in SQL
            if hasattr(v, 'to_sql') and hasattr(v, 'dialect'):
                # This is an expression object like FunctionCall, BinaryExpression, etc.
                processed_values.append(v)
            else:
                # This is a regular value that should be wrapped in a Literal
                processed_values.append(Literal(self.dialect, v))

        # Create a ValuesSource to use as the data source for the InsertExpression
        values_source = ValuesSource(self.dialect, [processed_values])

        # Create ReturningClause if returning_columns is specified
        returning_clause = None
        if options.returning_columns:
            from ..expression import Column as ExprColumn
            returning_expressions = [ExprColumn(self.dialect, col) for col in options.returning_columns]
            returning_clause = ReturningClause(self.dialect, returning_expressions)

        insert_expr = InsertExpression(
            dialect=self.dialect,
            into=options.table,
            source=values_source,
            columns=list(options.data.keys()),
            returning=returning_clause
        )

        sql, params = insert_expr.to_sql()

        exec_options = ExecutionOptions(
            stmt_type=StatementType.DML,  # Keep as DML since it's still a data manipulation operation
            column_adapters=options.column_adapters,
            column_mapping=options.column_mapping,
            process_result_set=bool(options.returning_columns)  # Process result set if returning columns specified
        )

        result = await self.execute(sql, params, options=exec_options)

        if options.auto_commit:
            await self._handle_auto_commit_if_needed()

        return result

    async def update(self, options: UpdateOptions) -> QueryResult:
        """
        Updates records asynchronously in the database using encapsulated UpdateOptions.

        Args:
            options (UpdateOptions): An object encapsulating all parameters for the update operation.
        Returns:
            QueryResult: The result of the update operation.
        """
        # Handle assignments - options.data may contain both literal values and expression objects
        assignments = {}

        # Process each item in the data dictionary
        for k, v in options.data.items():
            # Check if the value is a SQL expression that should be used directly in SQL
            if hasattr(v, 'to_sql') and hasattr(v, 'dialect'):
                # This is an expression object like FunctionCall, BinaryExpression, etc.
                assignments[k] = v
            else:
                # This is a regular value that should be wrapped in a Literal
                assignments[k] = Literal(self.dialect, v)

        # Create ReturningClause if returning_columns is specified
        returning_clause = None
        if options.returning_columns:
            from ..expression import Column as ExprColumn
            returning_expressions = [ExprColumn(self.dialect, col) for col in options.returning_columns]
            returning_clause = ReturningClause(self.dialect, returning_expressions)

        update_expr = UpdateExpression(
            dialect=self.dialect,
            table=options.table,
            assignments=assignments,
            where=options.where,
            returning=returning_clause
        )

        sql, params = update_expr.to_sql()

        exec_options = ExecutionOptions(
            stmt_type=StatementType.DML,  # Keep as DML since it's still a data manipulation operation
            column_adapters=options.column_adapters,
            column_mapping=options.column_mapping,
            process_result_set=bool(options.returning_columns)  # Process result set if returning columns specified
        )

        result = await self.execute(sql, params, options=exec_options)

        if options.auto_commit:
            await self._handle_auto_commit_if_needed()

        return result

    async def delete(self, options: DeleteOptions) -> QueryResult:
        """
        Deletes records asynchronously from the database using encapsulated DeleteOptions.

        Args:
            options (DeleteOptions): An object encapsulating all parameters for the delete operation.
        Returns:
            QueryResult: The result of the delete operation.
        """
        # Create ReturningClause if returning_columns is specified
        returning_clause = None
        if options.returning_columns:
            from ..expression import Column as ExprColumn
            returning_expressions = [ExprColumn(self.dialect, col) for col in options.returning_columns]
            returning_clause = ReturningClause(self.dialect, returning_expressions)

        delete_expr = DeleteExpression(
            dialect=self.dialect,
            table=options.table,
            where=options.where,
            returning=returning_clause
        )

        sql, params = delete_expr.to_sql()

        exec_options = ExecutionOptions(
            stmt_type=StatementType.DML,  # Keep as DML since it's still a data manipulation operation
            column_adapters=options.column_adapters,
            column_mapping=options.column_mapping,
            process_result_set=bool(options.returning_columns)  # Process result set if returning columns specified
        )

        result = await self.execute(sql, params, options=exec_options)

        if options.auto_commit:
            await self._handle_auto_commit_if_needed()

        return result

    async def fetch_one(self, sql: str, params: Optional[Tuple] = None,
                        column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None,
                        column_mapping: Optional[Dict[str, str]] = None) -> Optional[Dict]:
        """
        Fetches a single record from the database asynchronously.

        Args:
            sql (str): The SQL query string.
            params (Optional[Tuple]): Parameters for the SQL query.
            column_adapters (Optional[Dict]): Type adapters for processing result columns.
            column_mapping (Optional[Dict]): Mapping for renaming result columns.

        Returns:
            Optional[Dict]: A dictionary representing the fetched record, or None if no record found.
        """
        exec_options = ExecutionOptions(
            stmt_type=StatementType.DQL,
            column_adapters=column_adapters,
            column_mapping=column_mapping
        )
        result = await self.execute(sql, params, options=exec_options)
        return result.data[0] if result and result.data else None

    async def fetch_all(self, sql: str, params: Optional[Tuple] = None,
                        column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None,
                        column_mapping: Optional[Dict[str, str]] = None) -> List[Dict]:
        """
        Fetches all matching records from the database asynchronously.

        Args:
            sql (str): The SQL query string.
            params (Optional[Tuple]): Parameters for the SQL query.
            column_adapters (Optional[Dict]): Type adapters for processing result columns.
            column_mapping (Optional[Dict]): Mapping for renaming result columns.

        Returns:
            List[Dict]: A list of dictionaries, each representing a fetched record.
        """
        exec_options = ExecutionOptions(
            stmt_type=StatementType.DQL,
            column_adapters=column_adapters,
            column_mapping=column_mapping
        )
        result = await self.execute(sql, params, options=exec_options)
        return result.data or []
