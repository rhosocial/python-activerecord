# src/rhosocial/activerecord/query/set_operation.py
"""SetOperationQuery implementation for building UNION, INTERSECT, and EXCEPT queries."""

from typing import Union

from ..backend.expression import BaseExpression, SetOperationExpression, bases
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
        left_dialect = left.backend().dialect
        right_dialect = right.backend().dialect
        if left_dialect is not right_dialect:
            raise ValueError(f"Different backends for left ({type(left_dialect)}) and right ({type(right_dialect)}) operands")

        # Use SetOperationExpression to represent the set operation
        self._set_op_expr = SetOperationExpression(
            left_dialect,  # Use left's dialect as the main dialect
            left=self._convert_to_base_expression(left),
            right=self._convert_to_base_expression(right),
            operation=operation
        )

        # Call parent constructor with the left's backend since it's validated to be the same as right's
        super().__init__(left.backend)

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

    def backend(self):
        """Get the backend for this query."""
        # Return the backend of the left operand, as it's used for the SetOperationExpression
        return self.left.backend