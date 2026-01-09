# src/rhosocial/activerecord/query/aggregate.py
"""AggregateQueryMixin implementation for aggregation operations."""
import logging
from typing import List, Union, Any, Optional, Dict

from .base import BaseQueryMixin
from ..backend.expression import (
    functions,
    statements,
    BaseExpression,
    Literal,
    TableExpression
)


class AggregateQueryMixin(BaseQueryMixin):
    """Query mixin for aggregation operations that access the database.

    This mixin provides methods for SQL aggregations like COUNT, SUM, AVG, etc.
    These methods execute queries and access the database synchronously.

    Supports two types of aggregation:
    1. Simple aggregation: Functions like count/avg/min/max/sum that return scalar values when
       used at the end of a method chain
    2. Complex aggregation: Queries using .aggregate() method for more complex aggregations

    For selective column retrieval in aggregation queries, it's generally recommended to use
    specific aggregation functions rather than general column selection to maintain
    aggregation query consistency. The best practice is to use aggregation functions
    directly in aggregation contexts rather than mixing with general select() operations.
    """

    def count(self, column: Union[str, BaseExpression] = "*", is_distinct: bool = False, alias: Optional[str] = None) -> int:
        """Simple aggregation function that returns a scalar count value when used at the end of a method chain.

        Args:
            column: Column to count, defaults to "*" for COUNT(*). Can be a string column name or BaseExpression.
            is_distinct: Whether to count distinct values
            alias: Optional alias (ignored when returning scalar)

        Returns:
            Scalar count value

        Note: Calling .explain() before .count() has no effect. To get execution plans for aggregation queries,
        use .select() with .explain() and .aggregate() instead:
        User.query().select(functions.count(User.c.id).as_('total')).explain().aggregate()

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            total_users = User.query().count()
            active_users = User.query().where(User.c.status == 'active').count()
            unique_emails = User.query().count(User.c.email, is_distinct=True)

            2. Using raw column names (use with caution)
            # Warning: When using raw column names as strings, ensure they match your database schema
            total_users = User.query().count('*')
            unique_emails = User.query().count('email', is_distinct=True)
        """
        backend = self.model_class.backend()
        dialect = backend.backend

        # Use the factory function from functions.py to create the aggregation expression
        agg_expr = functions.count(dialect, column, is_distinct=is_distinct, alias=alias)

        # Store original select_columns to restore later
        original_select_columns = self.select_columns

        # Set the aggregation expression as the only selected column
        self.select_columns = [agg_expr]

        # Execute the query and return the scalar result
        result = self.all()

        # Restore original select_columns
        self.select_columns = original_select_columns

        if result and len(result) > 0:
            # Get the aggregated value from the result dictionary
            # The key will be the alias if provided, otherwise a default name
            key = alias if alias else "agg_0"
            return result[0].get(key, 0)
        return 0  # Default to 0 if no results

    def sum_(self, column: Union[str, BaseExpression], is_distinct: bool = False, alias: Optional[str] = None) -> float:
        """Simple aggregation function that returns a scalar sum value when used at the end of a method chain.

        Args:
            column: Column to sum. Can be a string column name or BaseExpression.
            is_distinct: Whether to sum distinct values
            alias: Optional alias (ignored when returning scalar)

        Returns:
            Scalar sum value

        Note: Calling .explain() before .sum_() has no effect. To get execution plans for aggregation queries,
        use .select() with .explain() and .aggregate() instead:
        User.query().select(functions.sum_(User.c.amount).as_('total')).explain().aggregate()

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            total_amount = Order.query().sum_(Order.c.amount)
            total_discount = Order.query().where(Order.c.status == 'active').sum_(Order.c.discount)
            unique_total = Order.query().sum_(Order.c.amount, is_distinct=True)

            2. Using raw column names (use with caution)
            # Warning: When using raw column names as strings, ensure they match your database schema
            total_amount = Order.query().sum_('amount')
            total_discount = Order.query().where('status = ?', ('active',)).sum_('discount')
            unique_total = Order.query().sum_('amount', is_distinct=True)
        """
        backend = self.model_class.backend()
        dialect = backend.backend

        # Use the factory function from functions.py to create the aggregation expression
        agg_expr = functions.sum_(dialect, column, is_distinct=is_distinct, alias=alias)

        # Store original select_columns to restore later
        original_select_columns = self.select_columns

        # Set the aggregation expression as the only selected column
        self.select_columns = [agg_expr]

        # Execute the query and return the scalar result
        result = self.all()

        # Restore original select_columns
        self.select_columns = original_select_columns

        if result and len(result) > 0:
            # Get the aggregated value from the result dictionary
            # The key will be the alias if provided, otherwise a default name
            key = alias if alias else "agg_0"
            return result[0].get(key, 0.0)
        return 0.0  # Default to 0.0 if no results

    def avg(self, column: Union[str, BaseExpression], is_distinct: bool = False, alias: Optional[str] = None) -> float:
        """Simple aggregation function that returns a scalar average value when used at the end of a method chain.

        Args:
            column: Column to average. Can be a string column name or BaseExpression.
            is_distinct: Whether to average distinct values
            alias: Optional alias (ignored when returning scalar)

        Returns:
            Scalar average value

        Note: Calling .explain() before .avg() has no effect. To get execution plans for aggregation queries,
        use .select() with .explain() and .aggregate() instead:
        User.query().select(functions.avg(User.c.age).as_('average_age')).explain().aggregate()

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            avg_score = Student.query().avg(Student.c.score)
            avg_salary = Employee.query().where(Employee.c.department == 'IT').avg(Employee.c.salary)
            unique_avg = Student.query().avg(Student.c.score, is_distinct=True)

            2. Using raw column names (use with caution)
            # Warning: When using raw column names as strings, ensure they match your database schema
            avg_score = Student.query().avg('score')
            avg_salary = Employee.query().where('department = ?', ('IT',)).avg('salary')
            unique_avg = Student.query().avg('score', is_distinct=True)
        """
        backend = self.model_class.backend()
        dialect = backend.backend

        # Use the factory function from functions.py to create the aggregation expression
        agg_expr = functions.avg(dialect, column, is_distinct=is_distinct, alias=alias)

        # Store original select_columns to restore later
        original_select_columns = self.select_columns

        # Set the aggregation expression as the only selected column
        self.select_columns = [agg_expr]

        # Execute the query and return the scalar result
        result = self.all()

        # Restore original select_columns
        self.select_columns = original_select_columns

        if result and len(result) > 0:
            # Get the aggregated value from the result dictionary
            # The key will be the alias if provided, otherwise a default name
            key = alias if alias else "agg_0"
            return result[0].get(key, 0.0)
        return 0.0  # Default to 0.0 if no results

    def min_(self, column: Union[str, BaseExpression], alias: Optional[str] = None) -> Any:
        """Simple aggregation function that returns a scalar minimum value when used at the end of a method chain.

        Args:
            column: Column to find minimum of. Can be a string column name or BaseExpression.
            alias: Optional alias (ignored when returning scalar)

        Returns:
            Scalar minimum value

        Note: Calling .explain() before .min_() has no effect. To get execution plans for aggregation queries,
        use .select() with .explain() and .aggregate() instead:
        User.query().select(functions.min_(User.c.age).as_('min_age')).explain().aggregate()

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            min_price = Product.query().min_(Product.c.price)
            min_age = User.query().where(User.c.status == 'active').min_(User.c.age)

            2. Using raw column names (use with caution)
            # Warning: When using raw column names as strings, ensure they match your database schema
            min_price = Product.query().min_('price')
            min_age = User.query().where('status = ?', ('active',)).min_('age')
        """
        backend = self.model_class.backend()
        dialect = backend.backend

        # Use the factory function from functions.py to create the aggregation expression
        agg_expr = functions.min_(dialect, column, alias=alias)

        # Store original select_columns to restore later
        original_select_columns = self.select_columns

        # Set the aggregation expression as the only selected column
        self.select_columns = [agg_expr]

        # Execute the query and return the scalar result
        result = self.all()

        # Restore original select_columns
        self.select_columns = original_select_columns

        if result and len(result) > 0:
            # Get the aggregated value from the result dictionary
            # The key will be the alias if provided, otherwise a default name
            key = alias if alias else "agg_0"
            return result[0].get(key)
        return None  # Return None if no results

    def max_(self, column: Union[str, BaseExpression], alias: Optional[str] = None) -> Any:
        """Simple aggregation function that returns a scalar maximum value when used at the end of a method chain.

        Args:
            column: Column to find maximum of. Can be a string column name or BaseExpression.
            alias: Optional alias (ignored when returning scalar)

        Returns:
            Scalar maximum value

        Note: Calling .explain() before .max_() has no effect. To get execution plans for aggregation queries,
        use .select() with .explain() and .aggregate() instead:
        User.query().select(functions.max_(User.c.age).as_('max_age')).explain().aggregate()

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            max_price = Product.query().max_(Product.c.price)
            max_age = User.query().where(User.c.status == 'active').max_(User.c.age)

            2. Using raw column names (use with caution)
            # Warning: When using raw column names as strings, ensure they match your database schema
            max_price = Product.query().max_('price')
            max_age = User.query().where('status = ?', ('active',)).max_('age')
        """
        backend = self.model_class.backend()
        dialect = backend.backend

        # Use the factory function from functions.py to create the aggregation expression
        agg_expr = functions.max_(dialect, column, alias=alias)

        # Store original select_columns to restore later
        original_select_columns = self.select_columns

        # Set the aggregation expression as the only selected column
        self.select_columns = [agg_expr]

        # Execute the query and return the scalar result
        result = self.all()

        # Restore original select_columns
        self.select_columns = original_select_columns

        if result and len(result) > 0:
            # Get the aggregated value from the result dictionary
            # The key will be the alias if provided, otherwise a default name
            key = alias if alias else "agg_0"
            return result[0].get(key)
        return None  # Return None if no results

    def aggregate(self) -> List[Dict[str, Any]]:
        """Execute aggregate query with all configured expressions and groupings.

        Executes the query with all configured expressions and groupings.
        Inherits WHERE conditions, ORDER BY, and LIMIT/OFFSET from base query.

        Returns a list of result dictionaries. The list may contain a single item
        or multiple items depending on the query definition (GROUP BY, etc.).

        If explain() has been called on the query, this method will return
        the execution plan instead of the actual results.

        Returns:
            List[Dict[str, Any]]: Results as a list of dictionaries
            Union[str, List[Dict]]: Execution plan if explain is enabled

        Examples:
            1. With grouping (returns multiple rows)
            result = User.query()\\
                .group_by('department')\\
                .select(functions.count(User.c.id).as_('total'))\\
                .aggregate()

            2. Scalar aggregate (returns a single row in a list)
            result = User.query()\\
                .select(functions.count(User.c.id).as_('total'))\\
                .aggregate()
            total = result[0]['total'] if result else 0

            3. Multiple aggregations
            result = User.query()\\
                .group_by('status')\\
                .select(
                    functions.count(User.c.id).as_('count'),
                    functions.avg(User.c.age).as_('average_age')
                )\\
                .aggregate()

            4. With explain enabled
            plan = User.query()\\
                .group_by('department')\\
                .select(functions.count(User.c.id).as_('total'))\\
                .explain()\\
                .aggregate()
        """
        # Handle explain if enabled
        if self._explain_enabled:
            # Get backend instance and dialect
            backend = self.model_class.backend()
            dialect = backend.backend

            # Create the underlying query expression
            from_clause = TableExpression(dialect, self.model_class.table_name())

            query_expr = statements.QueryExpression(
                dialect,
                select=self.select_columns or [Literal(dialect, "*")],  # Default to SELECT *
                from_=from_clause,
                where=self.where_clause,
                group_by_having=self.group_by_having_clause,
                order_by=self.order_by_clause,
                limit_offset=self.limit_offset_clause
            )

            # Create ExplainExpression with the query and options
            explain_options = statements.ExplainOptions(**self._explain_options)
            explain_expr = statements.ExplainExpression(dialect, query_expr, explain_options)

            # Generate SQL for the EXPLAIN statement
            explain_sql, explain_params = explain_expr.to_sql()

            self._log(logging.INFO, f"Executing EXPLAIN aggregate query: {explain_sql}")

            # Execute the EXPLAIN query using the backend
            result = backend.execute_query(explain_sql, explain_params)

            return result

        # Get SQL and parameters using the existing to_sql method
        sql, params = self.to_sql()
        self._log(logging.INFO, f"Executing aggregate query: {sql}")

        # Execute the aggregate query
        backend = self.model_class.backend()
        result = backend.fetch_all(sql, params)

        # Always return a list, even if empty
        return result

    def exists(self) -> bool:
        """Check if any matching records exist.

        This method executes a query to check if any records match the query conditions.
        It's more efficient than fetching all records when only existence matters.

        Note: Calling .explain() before .exists() has no effect. To get execution plans for existence queries,
        use .select() with .explain() and .aggregate() instead:
        User.query().select(functions.count(User.c.id).as_('total')).explain().aggregate()

        Returns:
            bool: True if at least one record matches, False otherwise

        Examples:
            1. Using ActiveRecord field proxy (recommended)
            if User.query().where(User.c.email == email).exists():
                print("User exists")
            else:
                print("User does not exist")

            2. Check with complex conditions
            has_active_admins = User.query()\\
                .where(User.c.role == 'admin')\\
                .where(User.c.status == 'active')\\
                .exists()

            3. Using raw SQL string with parameters (use with caution)
            # Warning: When using raw SQL strings, you must ensure the query is safe from SQL injection
            if User.query().where('email = ?', (email,)).exists():
                print("User exists")
            else:
                print("User does not exist")
        """
        # Use count to check existence - this is more reliable than LIMIT 1
        return self.count() > 0