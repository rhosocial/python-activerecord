# src/rhosocial/activerecord/query/base.py
"""BaseQueryMixin implementation."""

from typing import List, Tuple, Optional, Union, Set, Dict, Any, overload
from ..interface import ModelT, IQuery
from ..backend.expression.bases import BaseExpression, SQLPredicate
from ..backend.expression.core import Column, Literal
from ..backend.expression.literals import Identifier
from ..backend.expression.predicates import ComparisonPredicate
from ..backend.expression.operators import RawSQLPredicate
from ..backend.expression.query_parts import WhereClause, GroupByHavingClause, OrderByClause, LimitOffsetClause


class BaseQueryMixin(IQuery[ModelT]):
    """BaseQueryMixin implementation for basic and aggregate query operations.

    This class unifies the functionality previously split between BaseQueryMixin and AggregateQueryMixin.
    It supports two types of aggregation:
    1. Simple aggregation: Functions like count/avg/min/max/sum that return scalar values when
       used at the end of a method chain
    2. Complex aggregation: Queries using .aggregate() method for more complex aggregations
    For aggregation states, to_dict() calls are ineffective.

    The select() method accepts both column names (strings) and expression objects,
    effectively replacing the need for a separate select_expr() method.

    For complex logical conditions, use .where() with expression objects that represent
    OR logic. The backend expression system provides better support for complex logical
    predicates than the legacy group-based methods (or_where, start_or_group, end_or_group).

    The query() method has been removed as its functionality is fully covered by the
    more flexible .where() method.
    """

    # region Instance Attributes
    model_class: type
    _backend: Any
    # Query clause attributes
    where_clause: Optional[WhereClause]
    order_clauses: List[str]
    join_clauses: List[Union[str, type]]
    select_columns: Optional[List[str]]
    limit_count: Optional[int]
    offset_count: Optional[int]
    _adapt_params: bool
    _explain_enabled: bool
    _explain_options: dict
    _group_columns: List[str]
    _having_conditions: List[Tuple[str, Tuple]]
    _expressions: List[Any]
    _window_definitions: Dict[str, Dict]
    _grouping_sets: Optional[Any]
    # endregion

    def __init__(self, model_class: type):
        pass

    # region Basic Query Methods
    @overload
    def where(self, condition: str, params: Optional[Union[tuple, List[Any]]] = None) -> 'BaseQueryMixin[ModelT]':
        """Add AND condition to the query using a SQL placeholder string.

        Args:
            condition: A SQL placeholder string with parameters (e.g., "name = ? AND age > ?")
            params: Query parameters for the placeholders

        Returns:
            Query instance for method chaining
        """
        ...

    @overload
    def where(self, condition: SQLPredicate, params: None = None) -> 'BaseQueryMixin[ModelT]':
        """Add AND condition to the query using a predicate expression.

        Args:
            condition: A predicate expression (e.g., User.c.age > 25, which is a SQLPredicate instance)
            params: Should be None when using predicate expressions

        Returns:
            Query instance for method chaining
        """
        ...

    def where(self, condition, params=None):
        """Add AND condition to the query.

        This method maintains the AND logic design principle - each call to where()
        adds an additional condition connected with AND to the existing conditions.
        For complex OR logic, use expression objects with the where() method.

        Args:
            condition: Condition can be either:
                      1. A SQL placeholder string with parameters (e.g., "name = ? AND age > ?")
                      2. A predicate expression (e.g., User.c.age > 25, which is a SQLPredicate instance)
            params: Query parameters for placeholder strings (not used with expression objects)

        Returns:
            Query instance for method chaining
        """
        # Get backend instance from model class, then get dialect
        backend = self.model_class.backend()
        dialect = backend.dialect

        # Convert string condition to SQLPredicate
        if isinstance(condition, str):
            # Use the new RawSQLPredicate class to handle raw SQL string conditions
            predicate = RawSQLPredicate(dialect, condition, tuple(params) if params else ())
        elif isinstance(condition, SQLPredicate):
            # Already a SQLPredicate, use directly
            predicate = condition
        else:
            raise TypeError(f"Condition must be str or SQLPredicate, got {type(condition)}")

        # If there's already a where_clause, connect new condition with existing conditions using AND
        if self.where_clause:
            # Get existing condition and create new AND condition
            combined_condition = self.where_clause.condition & predicate
            self.where_clause = WhereClause(dialect, condition=combined_condition)
        else:
            # Create new WhereClause
            self.where_clause = WhereClause(dialect, condition=predicate)

        return self


    def select(self, *columns: Union[str, BaseExpression, Column], append: bool = False):
        """Select specific columns or expressions to retrieve from the query.

        For ActiveRecord queries, it's generally recommended to retrieve all columns
        to maintain object consistency with the database state. Selective column
        retrieval may result in incomplete model instances.

        The best practice is to use this method in conjunction with to_dict() for
        retrieving partial data as dictionaries rather than model instances, which
        avoids object state inconsistency issues.

        This method accepts both column names (strings) and expression objects,
        effectively replacing the need for a separate select_expr() method.

        Args:
            *columns: Variable number of column names (str) or expression objects (BaseExpression, Column) to select
            append: If True, append columns to existing selection.
                   If False (default), replace existing selection.

        Returns:
            IQuery: Query instance for method chaining
        """
        pass

    def order_by(self, *clauses: Union[str, BaseExpression, Tuple[Union[BaseExpression, str], str]]):
        """Add ORDER BY clauses to the query.

        Args:
            *clauses: Variable number of ordering specifications. Each can be:
                     1. A column name as string (e.g., "name")
                     2. An expression object (e.g., User.c.name, which is a BaseExpression instance)
                     3. A tuple of (expression, direction) where direction is "ASC" or "DESC"
        """
        pass

    def limit(self, count: Union[int, BaseExpression]):
        """Add LIMIT clause to restrict the number of rows returned.

        Args:
            count: Maximum number of rows to return, can be an integer or expression

        Returns:
            Query instance for method chaining
        """
        pass

    def offset(self, count: Union[int, BaseExpression]):
        """Add OFFSET clause to skip a specified number of rows.

        Args:
            count: Number of rows to skip, can be an integer or expression

        Returns:
            Query instance for method chaining
        """
        pass
    # endregion


    # region Aggregate Methods
    def group_by(self, *columns: Union[str, BaseExpression]):
        """Add GROUP BY columns for complex aggregations.

        Args:
            *columns: Variable number of column names (str) or expression objects (BaseExpression) to group by

        Returns:
            Query instance for method chaining
        """
        pass

    @overload
    def having(self, condition: str, params: Optional[Union[tuple, List[Any]]] = None) -> 'BaseQueryMixin[ModelT]':
        """Add HAVING condition using a SQL placeholder string for complex aggregations.

        Args:
            condition: A SQL placeholder string with parameters (e.g., "COUNT(*) > ?")
            params: Query parameters for the placeholders

        Returns:
            Query instance for method chaining
        """
        ...

    @overload
    def having(self, condition: SQLPredicate, params: None = None) -> 'BaseQueryMixin[ModelT]':
        """Add HAVING condition using a predicate expression for complex aggregations.

        Args:
            condition: A predicate expression (e.g., FunctionCall("COUNT", Column("*")) > 5, which is a SQLPredicate instance)
            params: Should be None when using predicate expressions

        Returns:
            Query instance for method chaining
        """
        ...

    def having(self, condition, params=None):
        """Add HAVING condition for complex aggregations.

        Args:
            condition: HAVING condition can be either:
                      1. A SQL placeholder string with parameters (e.g., "COUNT(*) > ?")
                      2. A predicate expression (e.g., FunctionCall("COUNT", Column("*")) > 5, which is a SQLPredicate instance)
            params: Query parameters for placeholder strings (not used with expression objects)

        Returns:
            Query instance for method chaining
        """
        pass

    def count(self, column: str = "*", alias: Optional[str] = None, distinct: bool = False):
        """Simple aggregation function that returns a scalar count value when used at the end of a method chain."""
        pass

    def sum(self, column: str, alias: Optional[str] = None):
        """Simple aggregation function that returns a scalar sum value when used at the end of a method chain."""
        pass

    def avg(self, column: str, alias: Optional[str] = None):
        """Simple aggregation function that returns a scalar average value when used at the end of a method chain."""
        pass

    def min(self, column: str, alias: Optional[str] = None):
        """Simple aggregation function that returns a scalar minimum value when used at the end of a method chain."""
        pass

    def max(self, column: str, alias: Optional[str] = None):
        """Simple aggregation function that returns a scalar maximum value when used at the end of a method chain."""
        pass

    def aggregate(self):
        """Complex aggregation method that returns a list of dictionaries representing aggregated results."""
        pass
    # endregion


    # region Core Methods
    def to_sql(self) -> Tuple[str, tuple]:
        pass

    def all(self) -> List[ModelT]:
        pass

    def one(self) -> Optional[ModelT]:
        pass

    def exists(self) -> bool:
        pass

    def explain(self, **kwargs):
        pass

    def adapt_params(self, adapt: bool = True):
        pass
    # endregion