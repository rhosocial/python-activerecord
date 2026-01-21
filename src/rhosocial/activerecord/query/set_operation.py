# src/rhosocial/activerecord/query/set_operation.py
"""SetOperationQuery implementation for building UNION, INTERSECT, and EXCEPT queries."""

from typing import Union, List, Dict, Any

from ..backend.expression import SetOperationExpression, bases
from ..interface import IQuery, IAsyncQuery, ISetOperationQuery, IAsyncSetOperationQuery


class SetOperationQuery(ISetOperationQuery):
    """SetOperationQuery implementation for UNION, INTERSECT, and EXCEPT queries.

    This class allows combining results from multiple queries using set operations.
    It does not support query building methods like WHERE, SELECT, etc.
    It only supports chaining other SetOperationQuery instances.

    This class can be instantiated directly for set operations, or created
    indirectly through union(), intersect(), except_() methods on ActiveQuery
    or CTEQuery instances.
    """

    def __init__(self, left: Union[ISetOperationQuery, IQuery],
                 right: Union[ISetOperationQuery, IQuery],
                 operation: str):
        self.left = left
        self.right = right
        self.operation = operation

        # Get backends first to check their types
        left_backend = left.backend()
        right_backend = right.backend()

        # Check that both operands use synchronous backends (not async backends)
        from ..backend.base import AsyncStorageBackend
        if isinstance(left_backend, AsyncStorageBackend):
            raise TypeError(f"SetOperationQuery does not support async backends. Left operand uses {type(left_backend).__name__}")
        if isinstance(right_backend, AsyncStorageBackend):
            raise TypeError(f"SetOperationQuery does not support async backends. Right operand uses {type(right_backend).__name__}")

        # Check backend consistency between left and right operands
        left_dialect = left_backend.dialect
        right_dialect = right_backend.dialect
        if type(left_dialect) is not type(right_dialect):
            raise ValueError(f"Different dialect types for left ({type(left_dialect)}) and right ({type(right_dialect)}) operands")

        # Use SetOperationExpression to represent the set operation
        self._set_op_expr = SetOperationExpression(
            left_dialect,  # Use left's dialect as the main dialect
            left=self._convert_to_base_expression(left),
            right=self._convert_to_base_expression(right),
            operation=operation
        )

        # Initialize explain-related attributes
        self._explain_enabled = False
        self._explain_options = {}

        # Call parent constructor with the left's backend since it's validated to be the same as right's
        super().__init__(left_backend)

    def _convert_to_base_expression(self, query: IQuery) -> bases.BaseExpression:
        """Convert a query object to a BaseExpression suitable for expression system.

        Since SetOperationExpression belongs to the expression system, it should only accept
        BaseExpression objects, not high-level IQuery objects.
        """
        # If the query is a SetOperationQuery (which inherits from IQuery), get its underlying expression
        if isinstance(query, SetOperationQuery):
            return query._set_op_expr
        # If the query implements IQuery (including ActiveQuery), convert it to a RawSQLExpression to avoid extra parentheses
        elif isinstance(query, IQuery):
            from ..backend.expression.operators import RawSQLExpression
            # Convert the IQuery to SQL first, then create a RawSQLExpression
            sql, params = query.to_sql()
            return RawSQLExpression(query.backend().dialect, sql, params)
        else:
            # Fallback: This case might indicate a design issue or missing functionality
            # in how different query types are handled
            raise TypeError(f"Query type {type(query)} is not supported in set operations")

    def to_sql(self) -> 'bases.SQLQueryAndParams':
        """Convert the set operation query to SQL and parameters."""
        # Use the SetOperationExpression's to_sql method
        return self._set_op_expr.to_sql()

    def union(self, other: 'IQuery') -> 'SetOperationQuery':
        """Perform a UNION operation with another query."""
        return SetOperationQuery(self, other, "UNION")

    def intersect(self, other: 'IQuery') -> 'SetOperationQuery':
        """Perform an INTERSECT operation with another query."""
        return SetOperationQuery(self, other, "INTERSECT")

    def except_(self, other: 'IQuery') -> 'SetOperationQuery':
        """Perform an EXCEPT operation with another query."""
        return SetOperationQuery(self, other, "EXCEPT")

    def aggregate(self) -> List[Dict[str, Any]]:
        """Execute the set operation query and return results as a list of dictionaries.

        This method executes the set operation (UNION, INTERSECT, EXCEPT) and returns
        the results as a list of dictionaries, where each dictionary represents a row
        with column names as keys. This is particularly useful for set operations
        or when you need raw data instead of model instances.

        If explain() has been called on the query, this method will return
        the execution plan instead of the actual results.

        Note: For queries that could normally return ActiveRecord instances (like with .one() or .all()),
        you can use .aggregate() to get raw dictionary results instead of model instances.
        This is useful when you want to avoid model instantiation overhead or when dealing
        with custom SELECT expressions that don't map directly to model fields.

        Examples:
            1. With set operations (returns multiple rows)
            result = query1.union(query2).aggregate()
            # Returns [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]

            2. With complex set operations
            result = query1.intersect(query2).aggregate()
            # Returns [{'id': 1, 'name': 'Alice'}]

            3. With explain enabled
            plan = query1.union(query2).explain().aggregate()
        """
        # Handle explain if enabled
        if self._explain_enabled:
            # Get backend instance and dialect
            backend = self.backend()
            dialect = backend.dialect

            # Create the underlying set operation expression
            from ..backend.expression.statements import ExplainExpression, ExplainOptions

            # Create ExplainExpression with the set operation expression and options
            explain_options = ExplainOptions(**self._explain_options)
            explain_expr = ExplainExpression(dialect, self._set_op_expr, explain_options)

            # Generate SQL for the EXPLAIN statement
            explain_sql, explain_params = explain_expr.to_sql()

            # Execute the EXPLAIN query using the backend
            result = backend.fetch_all(explain_sql, explain_params)

            return result

        # Get SQL and parameters using the existing to_sql method
        sql, params = self.to_sql()

        # Execute the aggregate query
        backend = self.backend()
        result = backend.fetch_all(sql, params)

        # Always return a list, even if empty
        return result

    def backend(self) -> 'StorageBackend':
        """Get the backend for this query."""
        # Return the backend of the left operand, as it's used for the SetOperationExpression
        return self.left.backend()


class AsyncSetOperationQuery(IAsyncSetOperationQuery):
    """AsyncSetOperationQuery implementation for asynchronous UNION, INTERSECT, and EXCEPT queries.

    This class allows combining results from multiple async queries using set operations.
    It does not support query building methods like WHERE, SELECT, etc.
    It only supports chaining other AsyncSetOperationQuery instances.

    This class can be instantiated directly for async set operations, or created
    indirectly through union(), intersect(), except_() methods on AsyncActiveQuery
    or AsyncCTEQuery instances.
    """

    def __init__(self, left: Union['IAsyncSetOperationQuery', 'IAsyncQuery'],
                 right: Union['IAsyncSetOperationQuery', 'IAsyncQuery'],
                 operation: str):
        self.left = left
        self.right = right
        self.operation = operation

        # Get backends first to check their types
        left_backend = left.backend()
        right_backend = right.backend()

        # Check that both operands use async backends (not sync backends)
        from ..backend.base import AsyncStorageBackend, StorageBackend
        if not isinstance(left_backend, AsyncStorageBackend):
            raise TypeError(f"AsyncSetOperationQuery requires async backends. Left operand uses {type(left_backend).__name__}")
        if not isinstance(right_backend, AsyncStorageBackend):
            raise TypeError(f"AsyncSetOperationQuery requires async backends. Right operand uses {type(right_backend).__name__}")

        # Check backend consistency between left and right operands
        left_dialect = left_backend.dialect
        right_dialect = right_backend.dialect
        if type(left_dialect) is not type(right_dialect):
            raise ValueError(f"Different dialect types for left ({type(left_dialect)}) and right ({type(right_dialect)}) operands")

        # Use SetOperationExpression to represent the set operation
        self._set_op_expr = SetOperationExpression(
            left_dialect,  # Use left's dialect as the main dialect
            left=self._convert_to_base_expression(left),
            right=self._convert_to_base_expression(right),
            operation=operation
        )

        # Initialize explain-related attributes
        self._explain_enabled = False
        self._explain_options = {}

        # Call parent constructor with the left's backend since it's validated to be the same as right's
        super().__init__(left_backend)

    def _convert_to_base_expression(self, query: IAsyncQuery) -> bases.BaseExpression:
        """Convert an async query object to a BaseExpression suitable for expression system.

        Since SetOperationExpression belongs to the expression system, it should only accept
        BaseExpression objects, not high-level IAsyncQuery objects.
        """
        # If the query is an AsyncSetOperationQuery (which inherits from IAsyncQuery), get its underlying expression
        if isinstance(query, AsyncSetOperationQuery):
            return query._set_op_expr
        # If the query implements IAsyncQuery (including AsyncActiveQuery), convert it to a RawSQLExpression to avoid extra parentheses
        elif isinstance(query, IAsyncQuery):
            from ..backend.expression.operators import RawSQLExpression
            # Convert the IAsyncQuery to SQL first, then create a RawSQLExpression
            sql, params = query.to_sql()
            return RawSQLExpression(query.backend().dialect, sql, params)
        else:
            # Fallback: This case might indicate a design issue or missing functionality
            # in how different query types are handled
            raise TypeError(f"Query type {type(query)} is not supported in async set operations")

    def to_sql(self) -> 'bases.SQLQueryAndParams':
        """Convert the async set operation query to SQL and parameters."""
        # Use the SetOperationExpression's to_sql method
        return self._set_op_expr.to_sql()

    def union(self, other: 'IAsyncQuery') -> 'AsyncSetOperationQuery':
        """Perform a UNION operation with another async query."""
        return AsyncSetOperationQuery(self, other, "UNION")

    def intersect(self, other: 'IAsyncQuery') -> 'AsyncSetOperationQuery':
        """Perform an INTERSECT operation with another async query."""
        return AsyncSetOperationQuery(self, other, "INTERSECT")

    def except_(self, other: 'IAsyncQuery') -> 'AsyncSetOperationQuery':
        """Perform an EXCEPT operation with another async query."""
        return AsyncSetOperationQuery(self, other, "EXCEPT")

    async def aggregate(self) -> List[Dict[str, Any]]:
        """Execute the async set operation query and return results as a list of dictionaries.

        This method executes the async set operation (UNION, INTERSECT, EXCEPT) and returns
        the results as a list of dictionaries, where each dictionary represents a row
        with column names as keys. This is particularly useful for set operations
        or when you need raw data instead of model instances.

        If explain() has been called on the query, this method will return
        the execution plan instead of the actual results.

        Note: For queries that could normally return ActiveRecord instances (like with .one() or .all()),
        you can use .aggregate() to get raw dictionary results instead of model instances.
        This is useful when you want to avoid model instantiation overhead or when dealing
        with custom SELECT expressions that don't map directly to model fields.

        Examples:
            1. With set operations (returns multiple rows)
            result = await query1.union(query2).aggregate()
            # Returns [{'id': 1, 'name': 'Alice'}, {'id': 2, 'name': 'Bob'}]

            2. With complex set operations
            result = await query1.intersect(query2).aggregate()
            # Returns [{'id': 1, 'name': 'Alice'}]

            3. With explain enabled
            plan = await query1.union(query2).explain().aggregate()
        """
        # Handle explain if enabled
        if self._explain_enabled:
            # Get backend instance and dialect
            backend = self.backend()
            dialect = backend.dialect

            # Create the underlying set operation expression
            from ..backend.expression.statements import ExplainExpression, ExplainOptions

            # Create ExplainExpression with the set operation expression and options
            explain_options = ExplainOptions(**self._explain_options)
            explain_expr = ExplainExpression(dialect, self._set_op_expr, explain_options)

            # Generate SQL for the EXPLAIN statement
            explain_sql, explain_params = explain_expr.to_sql()

            # Execute the EXPLAIN query using the async backend
            result = await backend.fetch_all(explain_sql, explain_params)

            return result

        # Get SQL and parameters using the existing to_sql method
        sql, params = self.to_sql()

        # Execute the aggregate query
        backend = self.backend()
        result = await backend.fetch_all(sql, params)

        # Always return a list, even if empty
        return result

    def backend(self) -> 'StorageBackend':
        """Get the backend for this query."""
        # Return the backend of the left operand, as it's used for the SetOperationExpression
        return self.left.backend()