# src/rhosocial/activerecord/query/active_query.py
"""ActiveQuery implementation."""

from typing import List, Optional, Union, Type
import logging

from .aggregate import AggregateQueryMixin
from .join import JoinQueryMixin
from .range import RangeQueryMixin
from .relational import RelationalQueryMixin
from .set_operation import SetOperationQuery
from .base import BaseQueryMixin
from ..interface import IActiveQuery
from ..backend.expression import (
    BaseExpression,
    Literal,
    TableExpression,
    statements,
    WhereClause,
    OrderByClause,
    LimitOffsetClause,
    GroupByHavingClause
)
from ..interface.model import IActiveRecord
from ..backend.base import StorageBackend


class ActiveQuery(
    AggregateQueryMixin,
    BaseQueryMixin,
    JoinQueryMixin,
    RelationalQueryMixin,
    RangeQueryMixin,
    IActiveQuery,
):
    """ActiveQuery implementation for model-based queries.

    This class supports two types of aggregation:
    1. Simple aggregation: Functions like count/avg/min/max/sum that return scalar values when
       used at the end of a method chain
    2. Complex aggregation: Queries using .aggregate() method for more complex aggregations

    For selective column retrieval, it's generally recommended to retrieve all columns
    to maintain object consistency with the database state. Selective column retrieval
    may result in incomplete model instances.

    Important differences from CTEQuery:
    - Requires a model_class parameter in __init__ as ActiveQuery operates on specific model instances
    - Results are model instances by default
    - Supports relationship queries with model instantiation and association management
    """

    model_class: Type[IActiveRecord]
    _backend: 'StorageBackend'
    # Query clause attributes
    where_clause: Optional['WhereClause']
    order_by_clause: Optional['OrderByClause']
    join_clauses: List[Union[str, type]]
    select_columns: Optional[List[BaseExpression]]
    limit_offset_clause: Optional['LimitOffsetClause']
    group_by_having_clause: Optional['GroupByHavingClause']
    _adapt_params: bool
    _explain_enabled: bool
    _explain_options: dict

    def __init__(self, model_class: Type[IActiveRecord]):
        # Initialize BaseQueryMixin with backend
        super().__init__(model_class.backend())
        self.model_class = model_class
        self._backend = model_class.backend()

    @property
    def backend(self):
        """Get the backend for this query."""
        return self.model_class.backend()

    def all(self) -> List[IActiveRecord]:
        """Execute query and return all matching records as model instances.

        This method executes the query and returns a list of model instances
        representing all matching records. The returned list will be empty if
        no records match the query conditions.

        Note: Calling .explain() before .all() has no effect. To get execution plans,
        use .explain() with .aggregate() instead: User.query().explain().aggregate()

        Returns:
            List[ModelT]: List of model instances (empty if no matches)

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            users = User.query().where(User.c.status == 'active').all()
            users = User.query().select(User.c.id, User.c.name).where(User.c.status == 'active').all()

            2. Using raw SQL string with parameters (use with caution)
            # Warning: When using raw SQL strings, you must ensure the query is safe from SQL injection
            users = User.query().where('status = ?', ('active',)).all()
            users = User.query().select('id', 'name').where('status = ?', ('active',)).all()
        """
        # Get SQL and parameters
        sql, params = self.to_sql()

        self._log(logging.INFO, f"Executing query: {sql}, parameters: {params}")

        # Step 1: Get column adapters for processing output (DB -> Python).
        # This map specifies how database results should be converted back to Python objects.
        column_adapters = self.model_class.get_column_adapters()
        self._log(logging.DEBUG, f"Column adapters map: {column_adapters}")

        # Step 2: Fetch all records, passing the column adapters to the backend.
        rows = self.model_class.backend().fetch_all(sql, params, column_adapters=column_adapters)

        # Convert database column names back to Python field names before creating model instances
        field_data_rows = [self.model_class._map_columns_to_fields(row) for row in rows]
        records = [self.model_class.create_from_database(field_data) for field_data in field_data_rows]

        return records

    def one(self) -> Optional[IActiveRecord]:
        """Execute query and return the first matching record as a model instance.

        This method executes the query with a LIMIT 1 clause and returns either:
        - A single model instance if a matching record is found
        - None if no matching records exist

        Note: Calling .explain() before .one() has no effect. To get execution plans,
        use .limit(1).explain() with .aggregate() instead: User.query().limit(1).explain().aggregate()

        Returns:
            Optional[ModelT]: Single model instance or None

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            user = User.query().where(User.c.email == email).one()

            2. Handle potential None result
            if (user := User.query().where(User.c.email == email).one()):
                print(f"Found user: {user.name}")
            else:
                print("User not found")

            3. Using raw SQL string with parameters (use with caution)
            # Warning: When using raw SQL strings, you must ensure the query is safe from SQL injection
            user = User.query().where('email = ?', (email,)).one()
        """
        # Get backend instance and dialect
        backend = self.model_class.backend()
        dialect = backend.dialect

        # Create a temporary QueryExpression with LIMIT 1
        from_clause = TableExpression(dialect, self.model_class.table_name())

        # Create a temporary limit_offset_clause with LIMIT 1
        temp_limit_offset = LimitOffsetClause(dialect, limit=1)

        # Use the temporary limit_offset instead of the original one
        query_expr = statements.QueryExpression(
            dialect,
            select=self.select_columns or [Literal(dialect, "*")],  # Default to SELECT *
            from_=from_clause,
            where=self.where_clause,
            group_by_having=self.group_by_having_clause,
            order_by=self.order_by_clause,
            limit_offset=temp_limit_offset  # Use temporary limit
        )

        # Generate SQL using the temporary QueryExpression
        sql, params = query_expr.to_sql()

        self._log(logging.INFO, f"Executing query: {sql}, parameters: {params}")

        # Step 1: Get column adapters for processing output (DB -> Python).
        # This map specifies how database results should be converted back to Python objects.
        column_adapters = self.model_class.get_column_adapters()
        self._log(logging.DEBUG, f"Column adapters map: {column_adapters}")

        # Step 2: Fetch a single record, passing the column adapters to the backend.
        row = self.model_class.backend().fetch_one(sql, params, column_adapters=column_adapters)

        if not row:
            return None

        # Convert database column names back to Python field names before creating model instance
        field_data = self.model_class._map_columns_to_fields(row)
        record = self.model_class.create_from_database(field_data)

        return record

    def _log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log query-related messages using model's logger."""
        if self.model_class:
            if "offset" not in kwargs:
                kwargs["offset"] = 1
            self.model_class.log(level, msg, *args, **kwargs)