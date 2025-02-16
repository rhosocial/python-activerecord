"""ActiveQuery implementation combining all query mixins."""
from .relational import RelationalQueryMixin
from .aggregate import AggregateQueryMixin
from .range import RangeQueryMixin
from .base import BaseQueryMixin


class ActiveQuery(
    RelationalQueryMixin,
    AggregateQueryMixin,
    RangeQueryMixin,
    # BaseQueryMixin
):
    """Complete ActiveQuery implementation.

    Combines all functionality:
    - Basic query operations (BaseQueryMixin)
    - Aggregate queries (AggregateQueryMixin)
    - Range-based queries (RangeQueryMixin)
    - Relational queries (RelationalQueryMixin)
    """
    pass