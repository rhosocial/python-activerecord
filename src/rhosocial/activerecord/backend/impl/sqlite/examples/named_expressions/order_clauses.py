# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_expressions/order_clauses.py
"""
Clause named expression examples — WHERE / JOIN / GROUP BY / ORDER BY / LIMIT.

Each function takes 'dialect' as first parameter and returns
a BaseExpression that demonstrates a specific SQL clause.

These are building-block examples that show how individual clauses
compose into complete queries.
"""
from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    Column,
    Literal,
    FunctionCall,
    TableExpression,
    WhereClause,
    JoinExpression,
    GroupByHavingClause,
    OrderByClause,
    LimitOffsetClause,
    SelectModifier,
)


def where_example(dialect, status: str = "active"):
    """SELECT with WHERE filter.

    Demonstrates the WhereClause building block.

    Args:
        dialect: SQL dialect instance.
        status: Status value to filter by.

    Returns:
        QueryExpression with WHERE clause.
    """
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "status")],
        from_=TableExpression(dialect, "orders"),
        where=WhereClause(
            dialect,
            condition=Column(dialect, "status") == Literal(dialect, status),
        ),
    )


def join_example(dialect, user_id: int = 1):
    """SELECT with JOIN.

    Demonstrates JoinExpression and JoinType building blocks.

    Args:
        dialect: SQL dialect instance.
        user_id: User identifier.

    Returns:
        QueryExpression with JOIN.
    """
    return QueryExpression(
        dialect,
        select=[
            Column(dialect, "o.id"),
            Column(dialect, "o.status"),
            Column(dialect, "u.name"),
        ],
        from_=JoinExpression(
            dialect,
            left_table=TableExpression(dialect, "orders", alias="o"),
            right_table=TableExpression(dialect, "users", alias="u"),
            join_type="INNER JOIN",
            condition=Column(dialect, "o.user_id") == Column(dialect, "u.id"),
        ),
        where=WhereClause(
            dialect,
            condition=Column(dialect, "u.id") == Literal(dialect, user_id),
        ),
    )


def group_by_example(dialect, min_total: float = 100.0):
    """SELECT with GROUP BY and HAVING.

    Demonstrates GroupByHavingClause building block.

    Args:
        dialect: SQL dialect instance.
        min_total: Minimum total for HAVING filter.

    Returns:
        QueryExpression with GROUP BY / HAVING.
    """
    return QueryExpression(
        dialect,
        select=[
            Column(dialect, "status"),
            FunctionCall(dialect, "COUNT", Column(dialect, "id")).as_("cnt"),
        ],
        from_=TableExpression(dialect, "orders"),
        group_by_having=GroupByHavingClause(
            dialect,
            group_by=[Column(dialect, "status")],
        ),
    )


def order_by_example(dialect, limit: int = 10):
    """SELECT with ORDER BY and LIMIT.

    Demonstrates OrderByClause and LimitOffsetClause.

    Args:
        dialect: SQL dialect instance.
        limit: Maximum number of rows.

    Returns:
        QueryExpression with ORDER BY and LIMIT.
    """
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "status"), Column(dialect, "amount")],
        from_=TableExpression(dialect, "orders"),
        order_by=OrderByClause(
            dialect,
            expressions=[(Column(dialect, "amount"), "DESC")],
        ),
        limit_offset=LimitOffsetClause(
            dialect,
            limit=limit,
        ),
    )


def distinct_example(dialect):
    """SELECT DISTINCT.

    Demonstrates the SelectModifier building block.

    Args:
        dialect: SQL dialect instance.

    Returns:
        QueryExpression with DISTINCT modifier.
    """
    return QueryExpression(
        dialect,
        select=[Column(dialect, "status")],
        from_=TableExpression(dialect, "orders"),
        select_modifier=SelectModifier.DISTINCT,
    )


def compound_example(dialect, user_id: int = 1, status: str = "pending"):
    """Combined clauses — WHERE + JOIN + ORDER BY + LIMIT.

    Demonstrates how multiple clauses compose together.

    Args:
        dialect: SQL dialect instance.
        user_id: User identifier.
        status: Status filter.

    Returns:
        QueryExpression with multiple clauses.
    """
    return QueryExpression(
        dialect,
        select=[
            Column(dialect, "o.id"),
            Column(dialect, "o.status"),
            Column(dialect, "o.amount"),
            Column(dialect, "u.name"),
        ],
        from_=JoinExpression(
            dialect,
            left_table=TableExpression(dialect, "orders", alias="o"),
            right_table=TableExpression(dialect, "users", alias="u"),
            join_type="INNER JOIN",
            condition=Column(dialect, "o.user_id") == Column(dialect, "u.id"),
        ),
        where=WhereClause(
            dialect,
            condition=(
                (Column(dialect, "o.user_id") == Literal(dialect, user_id))
                & (Column(dialect, "o.status") == Literal(dialect, status))
            ),
        ),
        order_by=OrderByClause(
            dialect,
            expressions=[(Column(dialect, "o.id"), "DESC")],
        ),
        limit_offset=LimitOffsetClause(
            dialect,
            limit=5,
        ),
    )
