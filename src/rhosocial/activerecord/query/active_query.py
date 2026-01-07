# src/rhosocial/activerecord/query/active_query.py
"""ActiveQuery implementation."""

from typing import List, Union, Tuple, Any, Optional, Set, Dict
from .dict_query import DictQueryMixin
from .base import BaseQueryMixin
from .join import JoinQueryMixin
from .range import RangeQueryMixin
from .relational import RelationalQueryMixin


class ActiveQuery(
    DictQueryMixin,
    BaseQueryMixin,
    JoinQueryMixin,
    RelationalQueryMixin,
    RangeQueryMixin,
):
    """ActiveQuery implementation for model-based queries.

    This class supports two types of aggregation:
    1. Simple aggregation: Functions like count/avg/min/max/sum that return scalar values when
       used at the end of a method chain
    2. Complex aggregation: Queries using .aggregate() method for more complex aggregations
    For aggregation states, to_dict() calls are ineffective.

    For selective column retrieval, it's generally recommended to retrieve all columns
    to maintain object consistency with the database state. Selective column retrieval
    may result in incomplete model instances. The best practice is to use select() in
    conjunction with to_dict() for retrieving partial data as dictionaries rather than
    model instances, which avoids object state inconsistency issues.

    Important differences from CTEQuery:
    - Requires a model_class parameter in __init__ as ActiveQuery operates on specific model instances
    - Results are model instances by default (unless to_dict() is used)
    - Supports relationship queries with model instantiation and association management

    Note: The select_expr() method has been removed. Its functionality is now provided
    by the select() method, which accepts both column names (strings) and expression objects.

    Note: The or_where(), start_or_group(), and end_or_group() methods have been removed.
    Complex logical conditions should be handled using .where() with expression objects
    that represent OR logic. The backend expression system provides better support for
    complex logical predicates than the legacy group-based methods.

    Note: The query() method has been removed. Its functionality is now provided by the
    .where() method, which offers more flexible condition building capabilities.

    Note: DictQueryMixin is now included as the highest priority mixin, providing
    to_dict functionality and overriding all/one methods to support dictionary conversion.
    """

    def __init__(self, model_class: type):
        pass