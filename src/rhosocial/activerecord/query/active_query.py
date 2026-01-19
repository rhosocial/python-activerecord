# src/rhosocial/activerecord/query/active_query.py
"""ActiveQuery implementation."""

import logging
from typing import List, Optional, Type

from .aggregate import AggregateQueryMixin, AsyncAggregateQueryMixin
from .base import BaseQueryMixin
from .join import JoinQueryMixin
from .range import RangeQueryMixin
from .relational import RelationalQueryMixin
from .async_join import AsyncJoinQueryMixin
from .set_operation import SetOperationQuery
from ..backend.expression import (
    WildcardExpression,
    TableExpression,
    statements,
    LimitOffsetClause,
    bases
)
from ..interface.model import IActiveRecord
from ..interface.query import IQuery, IActiveQuery, IAsyncActiveQuery, ThreadSafeDict


class ActiveQuery(
    AggregateQueryMixin,
    BaseQueryMixin,
    JoinQueryMixin,
    RelationalQueryMixin,
    RangeQueryMixin,
    IActiveQuery
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

    When constructing queries that include wildcards (SELECT *), the system
    automatically uses WildcardExpression instead of Literal("*") to avoid
    treating the wildcard as a parameter value. This ensures correct SQL generation.
    """

    def __init__(self, model_class: Type[IActiveRecord]):
        """Initialize ActiveQuery with a model class.

        Args:
            model_class: The model class that this query targets
        """
        self.model_class = model_class

        # Initialize attributes from BaseQueryMixin
        self.where_clause = None
        self.order_by_clause = None
        self.join_clauses = []
        self.select_columns = None
        self.limit_offset_clause = None
        self.group_by_having_clause = None
        self._adapt_params = True
        self._explain_enabled = False
        self._explain_options = {}

        # Initialize attributes from JoinQueryMixin
        self.join_clause = None

        # Initialize attributes from RelationalQueryMixin
        self._eager_loads = ThreadSafeDict()

    def backend(self):
        """Get the backend for this query."""
        # Always return the backend from the model class to avoid duplication
        return self.model_class.backend()

    def all(self) -> List[IActiveRecord]:
        """Execute query and return all matching records as model instances.

        This method executes the query and returns a list of model instances
        representing all matching records. The returned list will be empty if
        no records match the query conditions.

        Note: Calling .explain() before .all() has no effect. To get execution plans,
        use .explain() with .aggregate() instead: User.query().explain().aggregate()

        Returns:
            List[IActiveRecord]: List of model instances (empty if no matches)

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
        rows = self.backend().fetch_all(sql, params, column_adapters=column_adapters)

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
            Optional[IActiveRecord]: Single model instance or None

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
        backend = self.backend()
        dialect = backend.dialect

        # Create a temporary QueryExpression with LIMIT 1
        from_clause = TableExpression(dialect, self.model_class.table_name())

        # Create a temporary limit_offset_clause with LIMIT 1
        temp_limit_offset = LimitOffsetClause(dialect, limit=1)

        # Use the temporary limit_offset instead of the original one
        query_expr = statements.QueryExpression(
            dialect,
            select=self.select_columns or [WildcardExpression(dialect)],  # Default to SELECT *
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
        row = self.backend().fetch_one(sql, params, column_adapters=column_adapters)

        if not row:
            return None

        # Convert database column names back to Python field names before creating model instance
        field_data = self.model_class._map_columns_to_fields(row)
        record = self.model_class.create_from_database(field_data)

        return record


    def to_sql(self) -> 'bases.SQLQueryAndParams':
        """Generate the SQL query string and parameters for ActiveQuery.

        This method overrides the base implementation to use the model's table name
        instead of a placeholder.

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        # Get dialect from backend
        dialect = self.backend().dialect

        # Use the model's actual table name
        from_clause = TableExpression(dialect, self.model_class.table_name())

        # Create QueryExpression with all components
        query_expr = statements.QueryExpression(
            dialect,
            select=self.select_columns or [WildcardExpression(dialect)],  # Default to SELECT *
            from_=self.join_clause if self.join_clause else from_clause,
            where=self.where_clause,
            group_by_having=self.group_by_having_clause,
            order_by=self.order_by_clause,
            limit_offset=self.limit_offset_clause
        )

        # Generate SQL using the QueryExpression
        return query_expr.to_sql()

    def union(self, other: 'IQuery') -> 'SetOperationQuery':
        """Perform a UNION operation with another query.

        Args:
            other: Another query object (IQuery)

        Returns:
            A new SetOperationQuery instance representing the UNION
        """
        from .set_operation import SetOperationQuery
        return SetOperationQuery(self, other, "UNION")

    def intersect(self, other: 'IQuery') -> 'SetOperationQuery':
        """Perform an INTERSECT operation with another query.

        Args:
            other: Another query object (IQuery)

        Returns:
            A new SetOperationQuery instance representing the INTERSECT
        """
        from .set_operation import SetOperationQuery
        return SetOperationQuery(self, other, "INTERSECT")

    def except_(self, other: 'IQuery') -> 'SetOperationQuery':
        """Perform an EXCEPT operation with another query.

        Args:
            other: Another query object (IQuery)

        Returns:
            A new SetOperationQuery instance representing the EXCEPT
        """
        from .set_operation import SetOperationQuery
        return SetOperationQuery(self, other, "EXCEPT")

    def _log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log query-related messages using model's logger."""
        if self.model_class:
            if "offset" not in kwargs:
                kwargs["offset"] = 1
            self.model_class.log(level, msg, *args, **kwargs)


class AsyncActiveQuery(
    AsyncAggregateQueryMixin,
    BaseQueryMixin,
    AsyncJoinQueryMixin,
    RelationalQueryMixin,  # Use the same RelationalQueryMixin as sync version
    RangeQueryMixin,
    IAsyncActiveQuery
):
    """AsyncActiveQuery implementation for model-based queries.

    This class supports two types of aggregation:
    1. Simple aggregation: Functions like count/avg/min/max/sum that return scalar values when
       used at the end of a method chain
    2. Complex aggregation: Queries using .aggregate() method for more complex aggregations

    For selective column retrieval, it's generally recommended to retrieve all columns
    to maintain object consistency with the database state. Selective column retrieval
    may result in incomplete model instances.

    Important differences from AsyncCTEQuery:
    - Requires a model_class parameter in __init__ as AsyncActiveQuery operates on specific model instances
    - Results are model instances by default
    - Supports relationship queries with model instantiation and association management

    When constructing queries that include wildcards (SELECT *), the system
    automatically uses WildcardExpression instead of Literal("*") to avoid
    treating the wildcard as a parameter value. This ensures correct SQL generation.
    """

    def __init__(self, model_class: Type[IActiveRecord]):
        """Initialize AsyncActiveQuery with a model class.

        Args:
            model_class: The model class that this query targets
        """
        self.model_class = model_class

        # Initialize attributes from BaseQueryMixin
        self.where_clause = None
        self.order_by_clause = None
        self.join_clauses = []
        self.select_columns = None
        self.limit_offset_clause = None
        self.group_by_having_clause = None
        self._adapt_params = True
        self._explain_enabled = False
        self._explain_options = {}

        # Initialize attributes from JoinQueryMixin
        self.join_clause = None

        # Initialize attributes from RelationalQueryMixin
        self._eager_loads = ThreadSafeDict()

    def backend(self):
        """Get the backend for this query."""
        # Always return the backend from the model class to avoid duplication
        return self.model_class.backend()

    async def all(self) -> List[IActiveRecord]:
        """Execute query asynchronously and return all matching records as model instances.

        This method executes the query and returns a list of model instances
        representing all matching records. The returned list will be empty if
        no records match the query conditions.

        Note: Calling .explain() before .all() has no effect. To get execution plans,
        use .explain() with .aggregate() instead: User.query().explain().aggregate()

        Returns:
            List[IActiveRecord]: List of model instances (empty if no matches)

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            users = await User.query().where(User.c.status == 'active').all()
            users = await User.query().select(User.c.id, User.c.name).where(User.c.status == 'active').all()

            2. Using raw SQL string with parameters (use with caution)
            # Warning: When using raw SQL strings, you must ensure the query is safe from SQL injection
            users = await User.query().where('status = ?', ('active',)).all()
            users = await User.query().select('id', 'name').where('status = ?', ('active',)).all()
        """
        # Get SQL and parameters
        sql, params = self.to_sql()

        self._log(logging.INFO, f"Executing async query: {sql}, parameters: {params}")

        # Step 1: Get column adapters for processing output (DB -> Python).
        # This map specifies how database results should be converted back to Python objects.
        column_adapters = self.model_class.get_column_adapters()
        self._log(logging.DEBUG, f"Column adapters map: {column_adapters}")

        # Step 2: Fetch all records, passing the column adapters to the backend.
        rows = await self.backend().fetch_all(sql, params, column_adapters=column_adapters)

        # Convert database column names back to Python field names before creating model instances
        field_data_rows = [self.model_class._map_columns_to_fields(row) for row in rows]
        records = [self.model_class.create_from_database(field_data) for field_data in field_data_rows]

        return records

    async def one(self) -> Optional[IActiveRecord]:
        """Execute query asynchronously and return the first matching record as a model instance.

        This method executes the query with a LIMIT 1 clause and returns either:
        - A single model instance if a matching record is found
        - None if no matching records exist

        Note: Calling .explain() before .one() has no effect. To get execution plans,
        use .limit(1).explain() with .aggregate() instead: User.query().limit(1).explain().aggregate()

        Returns:
            Optional[IActiveRecord]: Single model instance or None

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            user = await User.query().where(User.c.email == email).one()

            2. Handle potential None result
            if (user := await User.query().where(User.c.email == email).one()):
                print(f"Found user: {user.name}")
            else:
                print("User not found")

            3. Using raw SQL string with parameters (use with caution)
            # Warning: When using raw SQL strings, you must ensure the query is safe from SQL injection
            user = await User.query().where('email = ?', (email,)).one()
        """
        # Get backend instance and dialect
        backend = self.backend()
        dialect = backend.dialect

        # Create a temporary QueryExpression with LIMIT 1
        from_clause = TableExpression(dialect, self.model_class.table_name())

        # Create a temporary limit_offset_clause with LIMIT 1
        temp_limit_offset = LimitOffsetClause(dialect, limit=1)

        # Use the temporary limit_offset instead of the original one
        query_expr = statements.QueryExpression(
            dialect,
            select=self.select_columns or [WildcardExpression(dialect)],  # Default to SELECT *
            from_=from_clause,
            where=self.where_clause,
            group_by_having=self.group_by_having_clause,
            order_by=self.order_by_clause,
            limit_offset=temp_limit_offset  # Use temporary limit
        )

        # Generate SQL using the temporary QueryExpression
        sql, params = query_expr.to_sql()

        self._log(logging.INFO, f"Executing async query: {sql}, parameters: {params}")

        # Step 1: Get column adapters for processing output (DB -> Python).
        # This map specifies how database results should be converted back to Python objects.
        column_adapters = self.model_class.get_column_adapters()
        self._log(logging.DEBUG, f"Column adapters map: {column_adapters}")

        # Step 2: Fetch a single record, passing the column adapters to the backend.
        row = await self.backend().fetch_one(sql, params, column_adapters=column_adapters)

        if not row:
            return None

        # Convert database column names back to Python field names before creating model instance
        field_data = self.model_class._map_columns_to_fields(row)
        record = self.model_class.create_from_database(field_data)

        return record

    def to_sql(self) -> 'bases.SQLQueryAndParams':
        """Generate the SQL query string and parameters for AsyncActiveQuery.

        This method overrides the base implementation to use the model's table name
        instead of a placeholder.

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        # Get dialect from backend
        dialect = self.backend().dialect

        # Use the model's actual table name
        from_clause = TableExpression(dialect, self.model_class.table_name())

        # Create QueryExpression with all components
        query_expr = statements.QueryExpression(
            dialect,
            select=self.select_columns or [WildcardExpression(dialect)],  # Default to SELECT *
            from_=self.join_clause if self.join_clause else from_clause,
            where=self.where_clause,
            group_by_having=self.group_by_having_clause,
            order_by=self.order_by_clause,
            limit_offset=self.limit_offset_clause
        )

        # Generate SQL using the QueryExpression
        return query_expr.to_sql()

    def union(self, other: 'IQuery') -> 'SetOperationQuery':
        """Perform a UNION operation with another query.

        Args:
            other: Another query object (IQuery)

        Returns:
            A new SetOperationQuery instance representing the UNION
        """
        from .set_operation import SetOperationQuery
        return SetOperationQuery(self, other, "UNION")

    def intersect(self, other: 'IQuery') -> 'SetOperationQuery':
        """Perform an INTERSECT operation with another query.

        Args:
            other: Another query object (IQuery)

        Returns:
            A new SetOperationQuery instance representing the INTERSECT
        """
        from .set_operation import SetOperationQuery
        return SetOperationQuery(self, other, "INTERSECT")

    def except_(self, other: 'IQuery') -> 'SetOperationQuery':
        """Perform an EXCEPT operation with another query.

        Args:
            other: Another query object (IQuery)

        Returns:
            A new SetOperationQuery instance representing the EXCEPT
        """
        from .set_operation import SetOperationQuery
        return SetOperationQuery(self, other, "EXCEPT")

    def _log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log query-related messages using model's logger."""
        if self.model_class:
            if "offset" not in kwargs:
                kwargs["offset"] = 1
            self.model_class.log(level, msg, *args, **kwargs)
