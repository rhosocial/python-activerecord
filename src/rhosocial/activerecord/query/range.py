# src/rhosocial/activerecord/query/range.py
"""RangeQueryMixin implementation."""

from typing import List, Union, Tuple, Any

from .base import BaseQueryMixin
from ..backend.expression import Column, BaseExpression
from ..interface import IQuery


class RangeQueryMixin(BaseQueryMixin):
    """RangeQueryMixin implementation for range-based operations.

    This mixin provides a set of convenience methods for common filtering operations.
    All methods in this mixin add conditions to the query using `AND` logic. If you
    need to combine conditions with `OR`, you should construct the predicate
    expression manually and use the `where()` method.

    For example:
    >>> User.query().where((User.c.age > 65) | (User.c.status == 'inactive'))
    """

    def _get_col_expr(self, column: Union[str, BaseExpression]) -> BaseExpression:
        """
        Convert a column name string to a Column expression, or validates a BaseExpression.

        Args:
            column: The column name as a string or a BaseExpression instance.

        Returns:
            A BaseExpression instance.

        Raises:
            TypeError: If the column is not a string or a BaseExpression.
        """
        if isinstance(column, str):
            dialect = self.backend.dialect
            return Column(dialect, column)
        elif isinstance(column, BaseExpression):
            return column
        else:
            raise TypeError(f"column must be a string or a BaseExpression, but got {type(column)}")

    # region Range Methods
    def in_list(self, column: Union[str, BaseExpression], values: Union[List[Any], Tuple[Any, ...]], empty_result: bool = True) -> 'IQuery':
        """
        Add an IN condition to the query.

        This method filters records where the specified column's value is in the given list of values.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to filter on. Can be a string (column name) or a BaseExpression.
            values: A list or tuple of values to check against.
            empty_result: If True (default) and `values` is empty, the query will return no results.
                          If False and `values` is empty, the condition is omitted.

        Returns:
            Query instance for method chaining.

        Examples:
            1. Using ActiveRecord field proxy (recommended):
            >>> User.query().in_list(User.c.status, ['active', 'pending'])

            2. Using a function expression:
            >>> from rhosocial.activerecord.backend.expression import functions
            >>> User.query().in_list(functions.lower(User.c.username), ['admin', 'guest'])

            3. Using raw column name (use with caution):
            >>> User.query().in_list('status', ['active', 'pending'])
        """
        if not values:
            if empty_result:
                # Add a condition that is always false to return no results.
                return self.where("1 = 0")
            else:
                # Don't add any condition, return self.
                return self

        col_expr = self._get_col_expr(column)
        predicate = col_expr.in_(list(values))
        return self.where(predicate)

    def not_in(self, column: Union[str, BaseExpression], values: Union[List[Any], Tuple[Any, ...]], empty_result: bool = False) -> 'IQuery':
        """
        Add a NOT IN condition to the query.

        This method filters records where the specified column's value is not in the given list of values.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to filter on. Can be a string (column name) or a BaseExpression.
            values: A list or tuple of values to check against.
            empty_result: If False (default) and `values` is empty, the query will not be filtered.
                          If True and `values` is empty, the query will return no results.

        Returns:
            Query instance for method chaining.

        Examples:
            1. Using ActiveRecord field proxy (recommended):
            >>> User.query().not_in(User.c.status, ['archived', 'deleted'])

            2. Using raw column name (use with caution):
            >>> User.query().not_in('status', ['archived', 'deleted'])
        """
        if not values:
            if empty_result:
                # Add a condition that is always false to return no results.
                return self.where("1 = 0")
            else:
                # An empty NOT IN clause should not filter anything.
                return self

        col_expr = self._get_col_expr(column)
        predicate = col_expr.not_in(list(values))
        return self.where(predicate)

    def between(self, column: Union[str, BaseExpression], start: Any, end: Any) -> 'IQuery':
        """
        Add a BETWEEN condition to the query.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to filter on. Can be a string (column name) or a BaseExpression.
            start: The start of the range (inclusive).
            end: The end of the range (inclusive).

        Returns:
            Query instance for method chaining.

        Examples:
            1. Using ActiveRecord field proxy (recommended):
            >>> User.query().between(User.c.age, 18, 30)

            2. Using raw column name (use with caution):
            >>> User.query().between('age', 18, 30)
        """
        col_expr = self._get_col_expr(column)
        predicate = col_expr.between(start, end)
        return self.where(predicate)

    def not_between(self, column: Union[str, BaseExpression], start: Any, end: Any) -> 'IQuery':
        """
        Add a NOT BETWEEN condition to the query.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to filter on. Can be a string (column name) or a BaseExpression.
            start: The start of the range.
            end: The end of the range.

        Returns:
            Query instance for method chaining.

        Examples:
            1. Using ActiveRecord field proxy (recommended):
            >>> User.query().not_between(User.c.age, 18, 30)

            2. Using raw column name (use with caution):
            >>> User.query().not_between('age', 18, 30)
        """
        col_expr = self._get_col_expr(column)
        predicate = ~(col_expr.between(start, end))
        return self.where(predicate)

    def like(self, column: Union[str, BaseExpression], pattern: str) -> 'IQuery':
        """
        Add a LIKE condition (case-sensitive) to the query.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to filter on. Can be a string (column name) or a BaseExpression.
            pattern: The SQL LIKE pattern (e.g., 'John%', '%Smith', '%Doe%').

        Returns:
            Query instance for method chaining.

        Examples:
            1. Using ActiveRecord field proxy (recommended):
            >>> User.query().like(User.c.name, 'John%')

            2. Using raw column name (use with caution):
            >>> User.query().like('name', 'John%')
        """
        col_expr = self._get_col_expr(column)
        predicate = col_expr.like(pattern)
        return self.where(predicate)

    def not_like(self, column: Union[str, BaseExpression], pattern: str) -> 'IQuery':
        """
        Add a NOT LIKE condition (case-sensitive) to the query.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to filter on. Can be a string (column name) or a BaseExpression.
            pattern: The SQL LIKE pattern.

        Returns:
            Query instance for method chaining.

        Examples:
            >>> User.query().not_like(User.c.name, 'Admin%')
        """
        col_expr = self._get_col_expr(column)
        predicate = ~(col_expr.like(pattern))
        return self.where(predicate)

    def ilike(self, column: Union[str, BaseExpression], pattern: str) -> 'IQuery':
        """
        Add an ILIKE condition (case-insensitive) to the query.

        Note:
            ILIKE is not standard SQL and may not be supported by all database backends.
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to filter on. Can be a string (column name) or a BaseExpression.
            pattern: The SQL ILIKE pattern.

        Returns:
            Query instance for method chaining.

        Examples:
            >>> User.query().ilike(User.c.name, 'john%')
        """
        col_expr = self._get_col_expr(column)
        predicate = col_expr.ilike(pattern)
        return self.where(predicate)

    def not_ilike(self, column: Union[str, BaseExpression], pattern: str) -> 'IQuery':
        """
        Add a NOT ILIKE condition (case-insensitive) to the query.

        Note:
            ILIKE is not standard SQL and may not be supported by all database backends.
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to filter on. Can be a string (column name) or a BaseExpression.
            pattern: The SQL ILIKE pattern.

        Returns:
            Query instance for method chaining.

        Examples:
            >>> User.query().not_ilike(User.c.name, 'admin%')
        """
        col_expr = self._get_col_expr(column)
        predicate = ~(col_expr.ilike(pattern))
        return self.where(predicate)

    def is_null(self, column: Union[str, BaseExpression]) -> 'IQuery':
        """
        Add an IS NULL condition to the query.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to check for NULL. Can be a string or a BaseExpression.

        Returns:
            Query instance for method chaining.

        Examples:
            >>> User.query().is_null(User.c.deleted_at)
        """
        col_expr = self._get_col_expr(column)
        predicate = col_expr.is_null()
        return self.where(predicate)

    def is_not_null(self, column: Union[str, BaseExpression]) -> 'IQuery':
        """
        Add an IS NOT NULL condition to the query.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to check for non-NULL. Can be a string or a BaseExpression.

        Returns:
            Query instance for method chaining.

        Examples:
            >>> User.query().is_not_null(User.c.updated_at)
        """
        col_expr = self._get_col_expr(column)
        predicate = col_expr.is_not_null()
        return self.where(predicate)

    def greater_than(self, column: Union[str, BaseExpression], value: Any) -> 'IQuery':
        """
        Add a "greater than" (>) condition to the query.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to compare. Can be a string or a BaseExpression.
            value: The value to compare against.

        Returns:
            Query instance for method chaining.

        Examples:
            >>> User.query().greater_than(User.c.age, 18)
        """
        col_expr = self._get_col_expr(column)
        predicate = col_expr > value
        return self.where(predicate)

    def greater_than_or_equal(self, column: Union[str, BaseExpression], value: Any) -> 'IQuery':
        """
        Add a "greater than or equal to" (>=) condition to the query.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to compare. Can be a string or a BaseExpression.
            value: The value to compare against.

        Returns:
            Query instance for method chaining.

        Examples:
            >>> User.query().greater_than_or_equal(User.c.age, 18)
        """
        col_expr = self._get_col_expr(column)
        predicate = col_expr >= value
        return self.where(predicate)

    def less_than(self, column: Union[str, BaseExpression], value: Any) -> 'IQuery':
        """
        Add a "less than" (<) condition to the query.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to compare. Can be a string or a BaseExpression.
            value: The value to compare against.

        Returns:
            Query instance for method chaining.

        Examples:
            >>> User.query().less_than(User.c.age, 65)
        """
        col_expr = self._get_col_expr(column)
        predicate = col_expr < value
        return self.where(predicate)

    def less_than_or_equal(self, column: Union[str, BaseExpression], value: Any) -> 'IQuery':
        """
        Add a "less than or equal to" (<=) condition to the query.

        Note:
            This condition is combined with existing query conditions using AND logic.
            For OR logic, you must build the predicate expression manually.

        Args:
            column: The column to compare. Can be a string or a BaseExpression.
            value: The value to compare against.

        Returns:
            Query instance for method chaining.

        Examples:
            >>> User.query().less_than_or_equal(User.c.age, 65)
        """
        col_expr = self._get_col_expr(column)
        predicate = col_expr <= value
        return self.where(predicate)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # endregion