# src/rhosocial/activerecord/query/range.py
"""RangeQueryMixin implementation."""

from typing import List, Union, Tuple, Any
from ..interface import ModelT, IQuery


class RangeQueryMixin(IQuery[ModelT]):
    """RangeQueryMixin implementation for range-based operations.

    This mixin supports range operations in both simple and complex aggregation contexts.

    Note: The or_where(), start_or_group(), and end_or_group() methods have been removed.
    Complex logical conditions should be handled using .where() with expression objects
    that represent OR logic. The backend expression system provides better support for
    complex logical predicates than the legacy group-based methods.

    Note: The query() method has been removed. Its functionality is now provided by the
    .where() method, which offers more flexible condition building capabilities.
    """

    # region Range Methods
    def in_list(self, column: str, values: Union[List[Any], Tuple[Any, ...]], empty_result: bool = True) -> 'IQuery[ModelT]':
        pass

    def not_in(self, column: str, values: Union[List[Any], Tuple[Any, ...]], empty_result: bool = False) -> 'IQuery[ModelT]':
        pass

    def between(self, column: str, start: Any, end: Any) -> 'IQuery[ModelT]':
        pass

    def not_between(self, column: str, start: Any, end: Any) -> 'IQuery[ModelT]':
        pass

    def like(self, column: str, pattern: str) -> 'IQuery[ModelT]':
        pass

    def not_like(self, column: str, pattern: str) -> 'IQuery[ModelT]':
        pass

    def ilike(self, column: str, pattern: str) -> 'IQuery[ModelT]':
        pass

    def not_ilike(self, column: str, pattern: str) -> 'IQuery[ModelT]':
        pass

    def is_null(self, column: str) -> 'IQuery[ModelT]':
        pass

    def is_not_null(self, column: str) -> 'IQuery[ModelT]':
        pass

    def greater_than(self, column: str, value: Any) -> 'IQuery[ModelT]':
        pass

    def greater_than_or_equal(self, column: str, value: Any) -> 'IQuery[ModelT]':
        pass

    def less_than(self, column: str, value: Any) -> 'IQuery[ModelT]':
        pass

    def less_than_or_equal(self, column: str, value: Any) -> 'IQuery[ModelT]':
        pass
    # endregion