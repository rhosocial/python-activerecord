# src/rhosocial/activerecord/query/active_query.py
"""ActiveQuery implementation combining all query mixins."""
from .cte import CTEQueryMixin
from .join import JoinQueryMixin
from .range import RangeQueryMixin
from .relational import RelationalQueryMixin


class ActiveQuery(
    CTEQueryMixin,
    JoinQueryMixin,
    RelationalQueryMixin,
    # AggregateQueryMixin,
    RangeQueryMixin,
):
    """Complete ActiveQuery implementation.

    Combines all functionality:
    - Common Table Expressions (CTEQueryMixin)
    - Basic query operations (BaseQueryMixin via inheritance chain)
    - Aggregate queries (AggregateQueryMixin via CTEQueryMixin)
    - Join operations (JoinQueryMixin)
    - Range-based queries (RangeQueryMixin)
    - Relational queries (RelationalQueryMixin)

    Inheritance hierarchy:
    - BaseQueryMixin
      └── AggregateQueryMixin
          └── CTEQueryMixin

    Note on CTE operations:
    - All CTE operations are handled by CTEQueryMixin
    - Use with_cte() to define CTEs
    - Use from_cte() to query from a CTE
    - Both simple and recursive CTEs are supported

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

        # CTE example
        query = User.query()\\
            .with_cte(
                "active_users",
                "SELECT * FROM users WHERE status = 'active'"
            )\\
            .from_cte("active_users")\\
            .order_by("created_at DESC")
    """
    pass
