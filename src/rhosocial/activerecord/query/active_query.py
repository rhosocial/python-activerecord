# src/rhosocial/activerecord/query/active_query.py
"""ActiveQuery implementation."""

from typing import List, Union, Tuple, Any, Optional, Set, Dict
from .base import BaseQueryMixin
from .instance import InstanceQueryMixin
from .aggregate import AggregateQueryMixin
from .join import JoinQueryMixin
from .range import RangeQueryMixin
from .relational import RelationalQueryMixin


class ActiveQuery(
    AggregateQueryMixin,
    InstanceQueryMixin,
    JoinQueryMixin,
    RelationalQueryMixin,
    RangeQueryMixin,
):
    """ActiveQuery implementation for model-based queries.

    This class supports two types of aggregation:
    1. Simple aggregation: Functions like count/avg/min/max/sum that return scalar values when
       used at the end of a method chain
    2. Complex aggregation: Queries using .aggregate() method for more complex aggregations

    For selective column retrieval, it's generally recommended to retrieve all columns
    to maintain object consistency with the database state. Selective column retrieval
    may result in incomplete model instances. The best practice is to use select() in
    conjunction with to_dict() for retrieving partial data as dictionaries rather than
    model instances, which avoids object state inconsistency issues.

    Important differences from CTEQuery:
    - Requires a model_class parameter in __init__ as ActiveQuery operates on specific model instances
    - Results are model instances by default (unless to_dict() is used)
    - Supports relationship queries with model instantiation and association management

    InstanceQueryMixin is included as the highest priority mixin, providing
    model instance functionality and overriding all/one methods to return model instances.
    """

    def __init__(self, model_class: type):
        # Call the parent class __init__ to initialize all inherited attributes
        super().__init__(model_class)