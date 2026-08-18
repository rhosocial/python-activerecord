# tests/rhosocial/activerecord_test/feature/backend/cli/named_series/queries.py
"""Named query fixtures (named-expression building blocks).

Each function receives a *dialect* and returns an expression object.
Importing this module performs no I/O.  The tables (users, posts) are
created by named_migrations.migrations (run via the CLI).
"""

from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    FunctionCall,
    QueryExpression,
    TableExpression,
    InsertExpression,
    ValuesSource,
    OrderByClause,
)


def list_users(dialect):
    """List all users (id, name, email)."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name"), Column(dialect, "email")],
        from_=TableExpression(dialect, "users"),
        order_by=OrderByClause(dialect, expressions=[Column(dialect, "id")]),
    )


def user_by_id(dialect, user_id: int):
    """Fetch a single user by id."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name"), Column(dialect, "email")],
        from_=TableExpression(dialect, "users"),
        where=Column(dialect, "id") == Literal(dialect, user_id),
    )


def list_posts(dialect):
    """List all posts (id, title, user_id)."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "title"), Column(dialect, "user_id")],
        from_=TableExpression(dialect, "posts"),
        order_by=OrderByClause(dialect, expressions=[Column(dialect, "id")]),
    )


def posts_by_user(dialect, user_id: int):
    """List posts for a specific user."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "title")],
        from_=TableExpression(dialect, "posts"),
        where=Column(dialect, "user_id") == Literal(dialect, user_id),
    )


def count_posts(dialect):
    """Count posts, aliased as total."""
    return QueryExpression(
        dialect,
        select=[FunctionCall(dialect, "COUNT", Column(dialect, "id")).as_("total")],
        from_=TableExpression(dialect, "posts"),
    )


def insert_user(dialect, name: str, email: str):
    """Insert a user row; returns id/name for verification."""
    return InsertExpression(
        dialect,
        into="users",
        columns=["name", "email"],
        source=ValuesSource(dialect, [[Literal(dialect, name), Literal(dialect, email)]]),
    )


def insert_post(dialect, title: str, user_id: int):
    """Insert a post row; returns id/title for verification."""
    return InsertExpression(
        dialect,
        into="posts",
        columns=["title", "user_id"],
        source=ValuesSource(dialect, [[Literal(dialect, title), Literal(dialect, user_id)]]),
    )
