# src/rhosocial/activerecord/query/cte_query.py
"""CTEQuery implementation."""

from typing import List, Union, Tuple, Any, Optional

from .base import BaseQueryMixin
from .join import JoinQueryMixin
from .range import RangeQueryMixin
from ..interface import ICTEQuery
from ..backend.base import StorageBackend


class CTEQuery(
    BaseQueryMixin,
    JoinQueryMixin,
    RangeQueryMixin,
    ICTEQuery,
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
    _ctes: List[Any]
    _main_query: Optional[Any]
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
                 query: Union[str, 'IQuery', 'ActiveQuery', 'CTEQuery'],
                 columns: Optional[List[str]] = None,
                 materialized: Optional[bool] = None):
        pass

    def recursive(self, enabled: bool = True):
        pass

    def to_sql(self) -> Tuple[str, tuple]:
        """Generate SQL for this CTE query using WithQueryExpression.

        Note: Unlike BaseQueryMixin.to_sql(), this method constructs a complete WITH query
        using CTE expressions. The SQL generation follows the pattern:
        WITH [RECURSIVE] cte1 AS (query1), cte2 AS (query2), ...
        SELECT ... FROM ...

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        pass
    # endregion