# src/rhosocial/activerecord/query/cte_query.py
"""CTEQuery implementation."""

from typing import List, Union, Tuple, Optional

from .base import BaseQueryMixin
from .join import JoinQueryMixin
from .range import RangeQueryMixin
from .set_operation import SetOperationQuery
from ..backend.base import StorageBackend
from ..backend.expression import (
    statements,
    Literal,
    TableExpression,
    query_sources,
    bases
)
from ..backend.expression.query_sources import CTEExpression
from ..interface import ICTEQuery, ISetOperationQuery, IQuery


class CTEQuery(
    BaseQueryMixin,
    JoinQueryMixin,
    RangeQueryMixin,
    ICTEQuery,
    ISetOperationQuery,
):
    """CTEQuery implementation for Common Table Expression queries.

    This class supports two types of aggregation:
    1. Simple aggregation: Functions like count/avg/min/max/sum that return scalar values when
       used at the end of a method chain
    2. Complex aggregation: Queries using .aggregate() method for more complex aggregations

    CTEQuery results are always returned as dictionaries since CTEs are temporary result sets,
    not model instances. This makes it ideal for complex analytical queries and reporting.

    Important differences from ActiveQuery:
    - Does not require a model_class parameter in __init__ as CTEs are temporary result sets, not tied to specific model schemas
    - to_sql() method has different implementation logic compared to BaseQueryMixin, specifically handling WITH clause construction
    - Results are always dictionaries, no model instantiation occurs

    """

    # region Instance Attributes
    _ctes: List[CTEExpression]
    _main_query: Optional[Union[str, 'IQuery', 'ActiveQuery', 'CTEQuery']]
    _recursive: bool
    # endregion

    def __init__(self, backend: StorageBackend):
        """Initialize CTE Query.

        Args:
            backend: The storage backend to use for this query
        """
        super().__init__(backend)  # Initialize BaseQueryMixin with backend
        self._backend = backend
        self._ctes = []
        self._main_query = None
        self._recursive = False

    @property
    def backend(self):
        """Get the backend for this query."""
        return self._backend

    # region CTE Methods
    def with_cte(self, name: str,
                 query: Union[str, 'bases.SQLQueryAndParams', 'IQuery'],
                 columns: Optional[List[str]] = None,
                 materialized: Optional[bool] = None):
        """Add a Common Table Expression (CTE) to this query.

        Args:
            name: Name of the CTE
            query: The query that defines the CTE, can be a string, IQuery, ActiveQuery, or CTEQuery
            columns: Optional list of column names for the CTE
            materialized: Whether the CTE should be materialized (for databases that support it)

        Returns:
            self for method chaining
        """
        # Get dialect from backend
        dialect = self.backend.dialect

        # Convert the query to an appropriate expression
        if isinstance(query, str):
            # If query is a string, we'll need to handle it differently
            # For now, we'll create a RawSQLExpression
            from ..backend.expression.operators import RawSQLExpression
            query_expr = RawSQLExpression(dialect, query)
        elif bases.is_sql_query_and_params(query):
            # If query is a SQLQueryAndParams (str, tuple), create a RawSQLExpression with parameters
            from ..backend.expression.operators import RawSQLExpression
            sql_string, params = query
            # If params is None, use an empty tuple
            params = params if params is not None else ()
            query_expr = RawSQLExpression(dialect, sql_string, params)
        elif isinstance(query, bases.BaseExpression):
            # If query is a BaseExpression, use it directly
            query_expr = query
        elif isinstance(query, IQuery):
            # If query is an IQuery, wrap it in a Subquery
            from ..backend.expression.core import Subquery
            query_expr = Subquery(dialect, query)
        else:
            # Assume it's already a BaseExpression
            query_expr = query

        # Create a CTEExpression
        cte_expr = query_sources.CTEExpression(
            dialect,
            name=name,
            query=query_expr,
            columns=columns,
            materialized=materialized
        )

        # Add to the list of CTEs
        self._ctes.append(cte_expr)

        return self

    def query(self, main_query: Union[str, 'bases.SQLQueryAndParams', 'IQuery']):
        """Set the main query that will use the defined CTEs.

        Args:
            main_query: The main query that will reference the defined CTEs

        Returns:
            self for method chaining
        """
        self._main_query = main_query
        return self

    def recursive(self, enabled: bool = True):
        """Set whether this CTE query should be recursive.

        Args:
            enabled: Whether to enable recursive mode

        Returns:
            self for method chaining
        """
        self._recursive = enabled
        return self

    def to_sql(self) -> 'bases.SQLQueryAndParams':
        """Generate SQL for this CTE query using WithQueryExpression.

        Note: Unlike BaseQueryMixin.to_sql(), this method constructs a complete WITH query
        using CTE expressions. The SQL generation follows the pattern:
        WITH [RECURSIVE] cte1 AS (query1), cte2 AS (query2), ...
        SELECT ... FROM ...

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        # Get dialect from backend
        dialect = self.backend.dialect

        # Convert the main query to an appropriate expression
        if self._main_query is None:
            # If no main query is specified, we'll create a basic query that selects from the last CTE
            if self._ctes:
                last_cte_name = self._ctes[-1].name
                main_query_expr = statements.QueryExpression(
                    dialect,
                    select=self.select_columns or [Literal(dialect, "*")],  # Use selected columns or default to SELECT *
                    from_=TableExpression(dialect, last_cte_name),  # Reference the last CTE
                    where=self.where_clause,
                    group_by_having=self.group_by_having_clause,
                    order_by=self.order_by_clause,
                    limit_offset=self.limit_offset_clause
                )
            else:
                raise ValueError("CTEQuery must have at least one CTE defined")
        else:
            # Convert the main query to an appropriate expression
            if isinstance(self._main_query, str):
                # If main_query is a string, we'll need to handle it differently
                # For now, we'll create a RawSQLExpression wrapped in a QueryExpression
                from ..backend.expression.operators import RawSQLExpression
                main_query_expr = statements.QueryExpression(
                    dialect,
                    select=[RawSQLExpression(dialect, self._main_query)],
                    from_=TableExpression(dialect, "placeholder_main_query")
                )
            elif bases.is_sql_query_and_params(self._main_query):
                # If main_query is a SQLQueryAndParams (str, tuple), create a RawSQLExpression with parameters
                from ..backend.expression.operators import RawSQLExpression
                sql_string, params = self._main_query
                # If params is None, use an empty tuple
                params = params if params is not None else ()
                main_query_expr = statements.QueryExpression(
                    dialect,
                    select=[RawSQLExpression(dialect, sql_string, params)],
                    from_=TableExpression(dialect, "placeholder_main_query")
                )
            elif isinstance(self._main_query, bases.BaseExpression):
                # If main_query is a BaseExpression, use it directly
                main_query_expr = self._main_query
            elif isinstance(self._main_query, IQuery):
                # If main_query is an IQuery, wrap it in a Subquery
                from ..backend.expression.core import Subquery
                main_query_expr = Subquery(dialect, self._main_query)
            else:
                # For other types, assume it's already a BaseExpression
                main_query_expr = self._main_query

        # Create WithQueryExpression with the CTEs and main query
        with_query_expr = query_sources.WithQueryExpression(
            dialect,
            ctes=self._ctes,
            main_query=main_query_expr,
            recursive=self._recursive
        )
        return with_query_expr.to_sql()

    def union(self, other: Union[ISetOperationQuery, 'IQuery']) -> 'SetOperationQuery':
        """Perform a UNION operation with another query.

        Args:
            other: Another query object (either ISetOperationQuery or IQuery)

        Returns:
            A new SetOperationQuery instance representing the UNION
        """
        return SetOperationQuery(self, other, "UNION")

    def intersect(self, other: Union[ISetOperationQuery, 'IQuery']) -> 'SetOperationQuery':
        """Perform an INTERSECT operation with another query.

        Args:
            other: Another query object (either ISetOperationQuery or IQuery)

        Returns:
            A new SetOperationQuery instance representing the INTERSECT
        """
        return SetOperationQuery(self, other, "INTERSECT")

    def except_(self, other: Union[ISetOperationQuery, 'IQuery']) -> 'SetOperationQuery':
        """Perform an EXCEPT operation with another query.

        Args:
            other: Another query object (either ISetOperationQuery or IQuery)

        Returns:
            A new SetOperationQuery instance representing the EXCEPT
        """
        return SetOperationQuery(self, other, "EXCEPT")
    # endregion