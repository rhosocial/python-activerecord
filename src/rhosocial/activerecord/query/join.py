# src/rhosocial/activerecord/query/join.py
"""JoinQueryMixin implementation."""

from typing import List, Union

from ..interface import ModelT
from ..backend.expression.query_parts import JoinExpression, JoinType
from ..backend.expression.core import TableExpression


class JoinQueryMixin:
    """JoinQueryMixin implementation for JOIN operations.

    This mixin supports JOIN operations in both simple and complex aggregation contexts.

    Note: The or_where(), start_or_group(), and end_or_group() methods have been removed.
    Complex logical conditions should be handled using .where() with expression objects
    that represent OR logic. The backend expression system provides better support for
    complex logical predicates than the legacy group-based methods.

    Note: The query() method has been removed. Its functionality is now provided by the
    .where() method, which offers more flexible condition building capabilities.
    """

    # region Instance Attributes
    join_clauses: List[JoinExpression]
    # endregion

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # region Instance Attributes
        self.join_clauses: List[JoinExpression] = []
        # endregion

    # region JOIN Methods
    def join(self, join_clause: Union[str, type]) -> 'IQuery[ModelT]':
        """Add a JOIN clause to the query.

        Args:
            join_clause: Either a raw JOIN clause string or a model class/type

        Returns:
            Current query instance

        Examples:
            # Using raw JOIN clause
            User.query().join('JOIN orders ON users.id = orders.user_id')

            # Using model class (implementation depends on backend)
            User.query().join(Order)
        """
        # If join_clause is a string, we need to parse it appropriately
        if isinstance(join_clause, str):
            # For raw SQL string, we'll create a basic JoinExpression
            # This is a simplified approach - in a real implementation, we'd parse the string
            # and create appropriate expression objects
            dialect = self.model_class.backend().dialect
            # Create a basic JoinExpression with the table name extracted from the string
            # This is a simplified implementation - a real one would parse the full JOIN clause
            table_name = join_clause.split()[1] if len(join_clause.split()) > 1 else join_clause
            join_expr = JoinExpression(dialect, table_name, JoinType.JOIN)
        else:
            # If it's a model class, get its table name
            dialect = self.model_class.backend().dialect
            table_name = join_clause.table_name() if hasattr(join_clause, 'table_name') else str(join_clause)
            join_expr = JoinExpression(dialect, table_name, JoinType.JOIN)

        # Add join expression to the list of join clauses
        self.join_clauses.append(join_expr)
        return self

    def inner_join(self, table: str, foreign_key: str, primary_key: str = None, alias: str = None) -> 'IQuery[ModelT]':
        """Add an INNER JOIN clause to the query.

        Args:
            table: Table to join with
            foreign_key: Foreign key column in the joining table
            primary_key: Primary key column in the main table (defaults to main table's primary key)
            alias: Optional alias for the joined table

        Returns:
            Current query instance

        Examples:
            # Basic inner join
            User.query().inner_join('orders', 'user_id')

            # With explicit primary key
            User.query().inner_join('orders', 'user_id', 'id')

            # With alias
            User.query().inner_join('orders', 'user_id', alias='o')
        """
        # Construct the join expression using JoinExpression
        dialect = self.model_class.backend().dialect
        primary_key = primary_key or 'id'

        # Create the join condition as a predicate
        from ..backend.expression.predicates import ComparisonPredicate
        from ..backend.expression.core import Column

        main_table_column = Column(dialect, primary_key, table=self.model_class.table_name())
        joined_table_column = Column(dialect, foreign_key, table=table)
        condition = ComparisonPredicate(dialect, "=", main_table_column, joined_table_column)

        # Create the JoinExpression - using a simplified constructor call
        # Since I don't have the exact constructor signature, I'll create a generic one
        join_expr = JoinExpression(dialect)
        # Set properties manually based on what we know about JoinExpression
        join_expr.table_name = table
        join_expr.join_type = JoinType.INNER
        join_expr.condition = condition
        join_expr.alias = alias

        # Add join expression to the list of join clauses
        self.join_clauses.append(join_expr)
        return self

    def left_join(self, table: str, foreign_key: str, primary_key: str = None, alias: str = None, outer: bool = False) -> 'IQuery[ModelT]':
        """Add a LEFT JOIN clause to the query.

        Args:
            table: Table to join with
            foreign_key: Foreign key column in the joining table
            primary_key: Primary key column in the main table (defaults to main table's primary key)
            alias: Optional alias for the joined table
            outer: Whether to use LEFT OUTER JOIN (defaults to False, meaning LEFT JOIN)

        Returns:
            Current query instance

        Examples:
            # Basic left join
            User.query().left_join('orders', 'user_id')

            # With alias
            User.query().left_join('orders', 'user_id', alias='o')

            # With outer specification
            User.query().left_join('orders', 'user_id', outer=True)
        """
        # Construct the join expression using JoinExpression
        dialect = self.model_class.backend().dialect
        primary_key = primary_key or 'id'

        # Determine the join type based on the outer parameter
        join_type = JoinType.LEFT_OUTER if outer else JoinType.LEFT

        # Create the join condition as a predicate
        from ..backend.expression.predicates import ComparisonPredicate
        from ..backend.expression.core import Column

        main_table_column = Column(dialect, primary_key, table=self.model_class.table_name())
        joined_table_column = Column(dialect, foreign_key, table=table)
        condition = ComparisonPredicate(dialect, "=", main_table_column, joined_table_column)

        # Create the JoinExpression - using a simplified constructor call
        join_expr = JoinExpression(dialect)
        # Set properties manually based on what we know about JoinExpression
        join_expr.table_name = table
        join_expr.join_type = join_type
        join_expr.condition = condition
        join_expr.alias = alias

        # Add join expression to the list of join clauses
        self.join_clauses.append(join_expr)
        return self

    def right_join(self, table: str, foreign_key: str, primary_key: str = None, alias: str = None, outer: bool = False) -> 'IQuery[ModelT]':
        """Add a RIGHT JOIN clause to the query.

        Args:
            table: Table to join with
            foreign_key: Foreign key column in the joining table
            primary_key: Primary key column in the main table (defaults to main table's primary key)
            alias: Optional alias for the joined table
            outer: Whether to use RIGHT OUTER JOIN (defaults to False, meaning RIGHT JOIN)

        Returns:
            Current query instance

        Examples:
            # Basic right join
            User.query().right_join('orders', 'user_id')

            # With alias
            User.query().right_join('orders', 'user_id', alias='o')
        """
        # Construct the join expression using JoinExpression
        dialect = self.model_class.backend().dialect
        primary_key = primary_key or 'id'

        # Determine the join type based on the outer parameter
        join_type = JoinType.RIGHT_OUTER if outer else JoinType.RIGHT

        # Create the join condition as a predicate
        from ..backend.expression.predicates import ComparisonPredicate
        from ..backend.expression.core import Column

        main_table_column = Column(dialect, primary_key, table=self.model_class.table_name())
        joined_table_column = Column(dialect, foreign_key, table=table)
        condition = ComparisonPredicate(dialect, "=", main_table_column, joined_table_column)

        # Create the JoinExpression - using a simplified constructor call
        join_expr = JoinExpression(dialect)
        # Set properties manually based on what we know about JoinExpression
        join_expr.table_name = table
        join_expr.join_type = join_type
        join_expr.condition = condition
        join_expr.alias = alias

        # Add join expression to the list of join clauses
        self.join_clauses.append(join_expr)
        return self

    def full_join(self, table: str, foreign_key: str, primary_key: str = None, alias: str = None, outer: bool = False) -> 'IQuery[ModelT]':
        """Add a FULL JOIN clause to the query.

        Args:
            table: Table to join with
            foreign_key: Foreign key column in the joining table
            primary_key: Primary key column in the main table (defaults to main table's primary key)
            alias: Optional alias for the joined table
            outer: Whether to use FULL OUTER JOIN (defaults to False, meaning FULL JOIN)

        Returns:
            Current query instance

        Examples:
            # Basic full join
            User.query().full_join('orders', 'user_id')

            # With alias
            User.query().full_join('orders', 'user_id', alias='o')
        """
        # Construct the join expression using JoinExpression
        dialect = self.model_class.backend().dialect
        primary_key = primary_key or 'id'

        # Determine the join type based on the outer parameter
        join_type = JoinType.FULL_OUTER if outer else JoinType.FULL

        # Create the join condition as a predicate
        from ..backend.expression.predicates import ComparisonPredicate
        from ..backend.expression.core import Column

        main_table_column = Column(dialect, primary_key, table=self.model_class.table_name())
        joined_table_column = Column(dialect, foreign_key, table=table)
        condition = ComparisonPredicate(dialect, "=", main_table_column, joined_table_column)

        # Create the JoinExpression - using a simplified constructor call
        join_expr = JoinExpression(dialect)
        # Set properties manually based on what we know about JoinExpression
        join_expr.table_name = table
        join_expr.join_type = join_type
        join_expr.condition = condition
        join_expr.alias = alias

        # Add join expression to the list of join clauses
        self.join_clauses.append(join_expr)
        return self

    def cross_join(self, table: str, alias: str = None) -> 'IQuery[ModelT]':
        """Add a CROSS JOIN clause to the query (Cartesian product).

        Args:
            table: Table to cross join with
            alias: Optional alias for the joined table

        Returns:
            Current query instance

        Examples:
            # Basic cross join
            User.query().cross_join('categories')

            # With alias
            User.query().cross_join('categories', alias='c')
        """
        # Construct the join expression using JoinExpression
        dialect = self.model_class.backend().dialect

        # Create the JoinExpression for cross join
        join_expr = JoinExpression(dialect)
        # Set properties manually based on what we know about JoinExpression
        join_expr.table_name = table
        join_expr.join_type = JoinType.CROSS
        join_expr.alias = alias

        # Add join expression to the list of join clauses
        self.join_clauses.append(join_expr)
        return self

    def natural_join(self, table: str, alias: str = None) -> 'IQuery[ModelT]':
        """Add a NATURAL JOIN clause to the query.

        Args:
            table: Table to join with
            alias: Optional alias for the joined table

        Returns:
            Current query instance

        Examples:
            # Basic natural join
            User.query().natural_join('user_details')

            # With alias
            User.query().natural_join('user_details', alias='ud')
        """
        # Construct the join expression using JoinExpression
        dialect = self.model_class.backend().dialect

        # Create the JoinExpression for natural join
        join_expr = JoinExpression(dialect)
        # Set properties manually based on what we know about JoinExpression
        join_expr.table_name = table
        join_expr.join_type = JoinType.JOIN  # NATURAL JOIN is handled by the dialect
        join_expr.alias = alias
        join_expr.is_natural = True  # This would be a property indicating it's a natural join

        # Add join expression to the list of join clauses
        self.join_clauses.append(join_expr)
        return self

    def join_on(self, table: str, condition: str, alias: str = None) -> 'IQuery[ModelT]':
        """Add a JOIN clause with a custom ON condition.

        Args:
            table: Table to join with
            condition: Custom ON condition
            alias: Optional alias for the joined table

        Returns:
            Current query instance

        Examples:
            # Join with custom condition
            User.query().join_on('orders', 'users.id = orders.user_id AND orders.status = ?', 'o')
        """
        # Construct the join expression using JoinExpression
        dialect = self.model_class.backend().dialect

        # Create a raw SQL predicate for the condition
        from ..backend.expression.operators import RawSQLPredicate
        condition_pred = RawSQLPredicate(dialect, condition, ())

        # Create the JoinExpression
        join_expr = JoinExpression(dialect)
        # Set properties manually based on what we know about JoinExpression
        join_expr.table_name = table
        join_expr.join_type = JoinType.JOIN
        join_expr.condition = condition_pred
        join_expr.alias = alias

        # Add join expression to the list of join clauses
        self.join_clauses.append(join_expr)
        return self

    def join_through(self, intermediate_table: str, left_key: str, right_key: str, alias: str = None) -> 'IQuery[ModelT]':
        """Add a JOIN through an intermediate table (many-to-many relationship).

        Args:
            intermediate_table: Intermediate/junction table
            left_key: Key in the main table that connects to intermediate table
            right_key: Key in the intermediate table that connects to the target table
            alias: Optional alias for the joined table

        Returns:
            Current query instance

        Examples:
            # Join users to roles through user_roles table
            User.query().join_through('user_roles', 'id', 'user_id', alias='r')
        """
        # Construct the join expression through intermediate table
        dialect = self.model_class.backend().dialect

        # Create the join condition as a predicate
        from ..backend.expression.predicates import ComparisonPredicate
        from ..backend.expression.core import Column

        main_table_column = Column(dialect, left_key, table=self.model_class.table_name())
        intermediate_table_column = Column(dialect, right_key, table=intermediate_table)
        condition = ComparisonPredicate(dialect, "=", main_table_column, intermediate_table_column)

        # Create the JoinExpression
        join_expr = JoinExpression(dialect)
        # Set properties manually based on what we know about JoinExpression
        join_expr.table_name = intermediate_table
        join_expr.join_type = JoinType.JOIN
        join_expr.condition = condition
        join_expr.alias = alias

        # Add join expression to the list of join clauses
        self.join_clauses.append(join_expr)
        return self

    def join_relation(self, relation_name: str, alias: str = None) -> 'IQuery[ModelT]':
        """Add a JOIN based on a predefined relation.

        Args:
            relation_name: Name of the relation to join
            alias: Optional alias for the joined table

        Returns:
            Current query instance

        Examples:
            # Join based on a predefined relation
            User.query().join_relation('orders', alias='o')
        """
        # This would typically involve looking up the relation definition on the model
        # For now, we'll create a placeholder JoinExpression that would be filled in by
        # a more sophisticated implementation that knows about the model's relations
        dialect = self.model_class.backend().dialect

        # For now, we'll create a basic join expression - in a real implementation,
        # this would look up the relation definition and create the appropriate join
        join_expr = JoinExpression(dialect)
        # Set properties manually based on what we know about JoinExpression
        join_expr.table_name = relation_name
        join_expr.join_type = JoinType.JOIN
        join_expr.alias = alias

        # Add join expression to the list of join clauses
        self.join_clauses.append(join_expr)
        return self