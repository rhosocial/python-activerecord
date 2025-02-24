"""Range-based query methods implementation."""
import logging
from typing import Union, List, Any, Tuple
from ..interface import ModelT, IQuery


class RangeQueryMixin(IQuery[ModelT]):
    """Query methods for range-based conditions.

    Implements:
    - IN/NOT IN
    - BETWEEN/NOT BETWEEN
    - LIKE/NOT LIKE
    - IS NULL/IS NOT NULL
    """

    def in_list(self, column: str, values: Union[List[Any], Tuple[Any, ...]],
                empty_result: bool = True) -> 'IQuery[ModelT]':
        """Execute IN query on specified column.

        Args:
            column: Column name
            values: List or tuple of values
            empty_result: Behavior when value list is empty:
                         True - Return empty result set
                         False - Ignore this condition

        Returns:
            Current query instance

        Examples:
            # Simple IN query
            User.query().in_list('id', [1, 2, 3])

            # Handle empty list
            ids = []
            User.query().in_list('id', ids, empty_result=True)  # Returns empty set
            User.query().in_list('id', ids, empty_result=False) # Ignores condition

            # Combined with other conditions
            User.query()\\
                .where('status = ?', (1,))\\
                .in_list('type', ['admin', 'staff'])\\
                .order_by('created_at DESC')
        """
        if not values:
            self._log(logging.DEBUG,
                     f"Empty IN list for column {column}",
                     extra={'empty_result': empty_result})
            if empty_result:
                return self.where('1 = 0')
            return self

        if isinstance(values, list):
            values = tuple(values)

        placeholders = ','.join('?' * len(values))
        condition = f"{column} IN ({placeholders})"
        self._log(logging.DEBUG,
                  f"Added IN condition for column {column}",
                  extra={
                      'values_count': len(values),
                      'values': values[:5]  # Log first 5 values for debugging
                  })
        return self.where(condition, values)

    def not_in(self, column: str, values: Union[List[Any], Tuple[Any, ...]],
               empty_result: bool = False) -> 'IQuery[ModelT]':
        """Execute NOT IN query on specified column.

        Args:
            column: Column name
            values: List or tuple of values
            empty_result: Behavior when value list is empty:
                         True - Return empty result set
                         False - Ignore this condition (default)

        Returns:
            Current query instance

        Examples:
            # Simple NOT IN query
            User.query().not_in('id', [1, 2, 3])

            # Handle empty list
            excluded_ids = []
            User.query().not_in('id', excluded_ids) # Ignores condition by default

            # Combined with other conditions
            User.query()\\
                .where('status = ?', (1,))\\
                .not_in('type', ['banned', 'deleted'])
        """
        if not values:
            self._log(logging.DEBUG,
                      f"Empty NOT IN list for column {column}",
                      extra={'empty_result': empty_result})
            if empty_result:
                return self.where('1 = 0')
            return self

        if isinstance(values, list):
            values = tuple(values)

        placeholders = ','.join('?' * len(values))
        condition = f"{column} NOT IN ({placeholders})"
        self._log(logging.DEBUG,
                  f"Added NOT IN condition for column {column}",
                  extra={
                      'values_count': len(values),
                      'values': values[:5]  # Log first 5 values for debugging
                  })
        return self.where(condition, values)

    def between(self, column: str, start: Any, end: Any) -> 'IQuery[ModelT]':
        """Execute BETWEEN query."""
        condition = f"{column} BETWEEN ? AND ?"
        params = (start, end)
        self._log(logging.DEBUG,
                  f"Added BETWEEN condition for column {column}",
                  extra={'start': start, 'end': end})
        return self.where(condition, params)

    def not_between(self, column: str, start: Any, end: Any) -> 'IQuery[ModelT]':
        """Execute NOT BETWEEN query."""
        condition = f"{column} NOT BETWEEN ? AND ?"
        params = (start, end)
        self._log(logging.DEBUG,
                  f"Added NOT BETWEEN condition for column {column}",
                  extra={'start': start, 'end': end})
        return self.where(condition, params)

    def like(self, column: str, pattern: str) -> 'IQuery[ModelT]':
        """Execute LIKE query."""
        condition = f"{column} LIKE ?"
        params = (pattern,)
        self._log(logging.DEBUG,
                  f"Added LIKE condition for column {column}",
                  extra={'pattern': pattern})
        return self.where(condition, params)

    def not_like(self, column: str, pattern: str) -> 'IQuery[ModelT]':
        """Execute NOT LIKE query."""
        condition = f"{column} NOT LIKE ?"
        params = (pattern,)
        self._log(logging.DEBUG,
                  f"Added NOT LIKE condition for column {column}",
                  extra={'pattern': pattern})
        return self.where(condition, params)

    def is_null(self, column: str) -> 'IQuery[ModelT]':
        """Execute IS NULL query."""
        condition = f"{column} IS NULL"
        self._log(logging.DEBUG, f"Added IS NULL condition for column {column}")
        return self.where(condition)

    def is_not_null(self, column: str) -> 'IQuery[ModelT]':
        """Execute IS NOT NULL query."""
        condition = f"{column} IS NOT NULL"
        self._log(logging.DEBUG, f"Added IS NOT NULL condition for column {column}")
        return self.where(condition)