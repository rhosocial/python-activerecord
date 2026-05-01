# tests/rhosocial/activerecord_test/feature/backend/named_query/example_queries.py
"""
Example named queries for testing.

This module contains sample query definitions for testing
the named procedure functionality (which calls named queries).
"""
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.statements.dql import Select


def get_all_users(dialect, limit: int = 100):
    """Get all users with optional limit."""
    return Select(
        targets=["id", "name", "email"],
        from_="users",
        limit=limit,
    )


def get_active_orders(dialect, status: str = "active"):
    """Get orders by status."""
    return Select(
        targets=["id", "user_id", "total", "status", "created_at"],
        from_="orders",
        where={"status": status},
    )


def get_monthly_summary(dialect, month: str):
    """Get monthly summary data."""
    return Select(
        targets=[
            "id",
            "user_id",
            "total",
            "status",
        ],
        from_="orders",
        where={"month": month},
    )


def create_order_record(dialect, user_id: int, total: float, month: str):
    """Insert a new order record."""
    return Select(
        targets=["id"],
        from_="orders",
        where={"user_id": user_id, "total": total, "month": month},
    )


def get_user_summary(dialect, user_id: int):
    """Get summary for a specific user."""
    return Select(
        targets=["id", "name", "email"],
        from_="users",
        where={"id": user_id},
    )