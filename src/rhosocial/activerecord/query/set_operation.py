# src/rhosocial/activerecord/query/set_operation.py
"""SetOperationQuery implementation for building UNION, INTERSECT, and EXCEPT queries."""

from typing import Union

from ..backend.expression import BaseExpression, SetOperationExpression
from ..interface import IQuery, ISetOperationQuery


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

        # Check backend consistency between left and right operands
        left_dialect = left.backend.dialect
        right_dialect = right.backend.dialect
        if left_dialect is not right_dialect:
            raise ValueError(f"Different backends for left ({type(left_dialect)}) and right ({type(right_dialect)}) operands")

        # Use SetOperationExpression to represent the set operation
        self._set_op_expr = SetOperationExpression(
            left_dialect,  # Use left's dialect as the main dialect
            left=self._get_query_expression(left),
            right=self._get_query_expression(right),
            operation=operation
        )

        # Call parent constructor with the left's backend since it's validated to be the same as right's
        super().__init__(left.backend)

    def _get_query_expression(self, query: Union[ISetOperationQuery, IQuery]) -> BaseExpression:
        """Convert a query object to a BaseExpression."""
        # If the query is a SetOperationQuery, use its _set_op_expr
        if isinstance(query, SetOperationQuery):
            return query._set_op_expr
        # Otherwise, assume it's an IQuery instance that can be converted to a BaseExpression
        # This is a simplified approach, a more robust solution might be needed
        # depending on how IQuery instances are expected to be converted to SQL expressions
        elif isinstance(query, IQuery):
            # If the query is an IQuery instance, it should have a to_sql method
            # For now, we'll assume it's a valid expression that can be used directly
            # This is a placeholder - actual implementation depends on IQuery's structure
            return query
        else:
            # Fallback: This case might indicate a design issue or missing functionality
            # in how different query types are handled
            raise TypeError(f"Query type {type(query)} is not supported in set operations")

    def to_sql(self):
        """Convert the set operation query to SQL and parameters."""
        # Use the SetOperationExpression's to_sql method
        return self._set_op_expr.to_sql()

    def union(self, other: Union[ISetOperationQuery, IQuery]) -> 'SetOperationQuery':
        """Perform a UNION operation with another query."""
        return SetOperationQuery(self, other, "UNION")

    def intersect(self, other: Union[ISetOperationQuery, IQuery]) -> 'SetOperationQuery':
        """Perform an INTERSECT operation with another query."""
        return SetOperationQuery(self, other, "INTERSECT")

    def except_(self, other: Union[ISetOperationQuery, IQuery]) -> 'SetOperationQuery':
        """Perform an EXCEPT operation with another query."""
        return SetOperationQuery(self, other, "EXCEPT")

    @property
    def backend(self):
        """Get the backend for this query."""
        # Return the backend of the left operand, as it's used for the SetOperationExpression
        return self.left.backend