# tests/rhosocial/activerecord_test/feature/backend/named_expression/example_queries.py
"""
Example named queries for testing.

Sample query definitions for the named-procedure tests, which call named
queries. Each function takes the dialect it was resolved against and returns a
:class:`~rhosocial.activerecord.backend.expression.statements.dql.QueryStatement`.
"""

from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.statements.dql import (
    LimitOffsetClause,
    QueryStatement,
)


def _column(dialect, name: str) -> Column:
    """A projection: a bare column reference."""
    return Column(dialect, name)


def _equals(dialect, column: str, value) -> ComparisonPredicate:
    """``<column> = <literal>``."""
    return ComparisonPredicate(
        dialect,
        "=",
        Column(dialect, column),
        Literal(dialect, value),
    )


def get_all_users(dialect, limit: int = 100):
    """Get all users with optional limit."""
    return QueryStatement(
        dialect,
        select=[_column(dialect, n) for n in ("id", "name", "email")],
        from_="users",
        limit_offset=LimitOffsetClause(dialect, limit=limit),
    )


def get_active_orders(dialect, status: str = "active"):
    """Get orders by status."""
    return QueryStatement(
        dialect,
        select=[
            _column(dialect, n)
            for n in ("id", "user_id", "total", "status", "created_at")
        ],
        from_="orders",
        where=_equals(dialect, "status", status),
    )


def get_monthly_summary(dialect, month: str):
    """Get monthly summary data."""
    return QueryStatement(
        dialect,
        select=[
            _column(dialect, n)
            for n in ("id", "user_id", "total", "status")
        ],
        from_="orders",
        where=_equals(dialect, "month", month),
    )


def create_order_record(dialect, user_id: int, total: float, month: str):
    """Select the order record a caller is about to create.

    The name predates the expression layer and is kept for the named-query
    fixture it identifies; the query itself is a projection over ``orders``.
    """
    return QueryStatement(
        dialect,
        select=[_column(dialect, "id")],
        from_="orders",
        where=ComparisonPredicate(
            dialect,
            "AND",
            ComparisonPredicate(
                dialect,
                "=",
                Column(dialect, "user_id"),
                Literal(dialect, user_id),
            ),
            ComparisonPredicate(
                dialect,
                "=",
                Column(dialect, "total"),
                Literal(dialect, total),
            ),
        ),
    )


def get_user_summary(dialect, user_id: int):
    """Get summary for a specific user."""
    return QueryStatement(
        dialect,
        select=[_column(dialect, n) for n in ("id", "name", "email")],
        from_="users",
        where=_equals(dialect, "id", user_id),
    )
