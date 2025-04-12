"""ActiveQuery implementation combining all query mixins."""
from .aggregate import AggregateQueryMixin
from .join import JoinQueryMixin
from .range import RangeQueryMixin
from .relational import RelationalQueryMixin


class ActiveQuery(
    JoinQueryMixin,
    RelationalQueryMixin,
    AggregateQueryMixin,
    RangeQueryMixin,
):
    """Complete ActiveQuery implementation.

    Combines all functionality:
    - Basic query operations (BaseQueryMixin)
    - Aggregate queries (AggregateQueryMixin)
    - Range-based queries (RangeQueryMixin)
    - Relational queries (RelationalQueryMixin)

    Usage notes:
    - For simple queries on a single table, use .all() or .one() to retrieve model instances
    - For JOIN queries that return columns not in the model schema, use .to_dict(direct_dict=True).all()
      to bypass model validation
    - For aggregate queries, use .aggregate() to retrieve results as dictionaries

    Examples:
        # Simple query returning model instances
        users = User.query().where('status = ?', ('active',)).all()

        # JOIN query returning raw dictionaries (bypassing model validation)
        results = User.query()\\
            .join('JOIN orders ON users.id = orders.user_id')\\
            .select('users.id', 'users.name', 'orders.total')\\
            .to_dict(direct_dict=True)\\
            .all()

        # Aggregate query
        stats = User.query()\\
            .group_by('status')\\
            .count('id', 'user_count')\\
            .aggregate()
    """
    pass