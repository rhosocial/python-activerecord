# src/rhosocial/activerecord/query/join.py
"""JoinQueryMixin implementation."""

from typing import List, Union, Tuple, Any
from ..interface import ModelT, IQuery


class JoinQueryMixin(IQuery[ModelT]):
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
    join_clauses: List[Union[str, type]]
    # endregion

    # region JOIN Methods
    def join(self, join_clause: Union[str, type]) -> 'IQuery[ModelT]':
        pass

    def inner_join(self, table: str, foreign_key: str, primary_key: str = None, alias: str = None) -> 'IQuery[ModelT]':
        pass

    def left_join(self, table: str, foreign_key: str, primary_key: str = None, alias: str = None, outer: bool = False) -> 'IQuery[ModelT]':
        pass

    def right_join(self, table: str, foreign_key: str, primary_key: str = None, alias: str = None, outer: bool = False) -> 'IQuery[ModelT]':
        pass

    def full_join(self, table: str, foreign_key: str, primary_key: str = None, alias: str = None, outer: bool = False) -> 'IQuery[ModelT]':
        pass

    def cross_join(self, table: str, alias: str = None) -> 'IQuery[ModelT]':
        pass

    def natural_join(self, table: str, alias: str = None) -> 'IQuery[ModelT]':
        pass

    def join_on(self, table: str, condition: str, alias: str = None) -> 'IQuery[ModelT]':
        pass

    def join_through(self, intermediate_table: str, left_key: str, right_key: str, alias: str = None) -> 'IQuery[ModelT]':
        pass

    def join_relation(self, relation_name: str, alias: str = None) -> 'IQuery[ModelT]':
        pass