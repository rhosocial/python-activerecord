# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_expressions/order_dml.py
"""
DML named expression examples — INSERT / UPDATE / DELETE.

Each function takes 'dialect' as first parameter and returns
a BaseExpression that implements Executable.
"""

from rhosocial.activerecord.backend.expression import (
    InsertExpression,
    ValuesSource,
    UpdateExpression,
    DeleteExpression,
    Column,
    Literal,
    WhereClause,
    ReturningClause,
)


def add_order(dialect, user_id: int, status: str = "pending"):
    """Insert a new order record.

    Args:
        dialect: SQL dialect instance.
        user_id: User identifier.
        status: Order status.

    Returns:
        InsertExpression.
    """
    return InsertExpression(
        dialect,
        into="orders",
        columns=["user_id", "status"],
        source=ValuesSource(
            dialect,
            [[Literal(dialect, user_id), Literal(dialect, status)]],
        ),
    )


def add_order_bulk(dialect, user_id: int):
    """Insert multiple orders in one statement.

    Args:
        dialect: SQL dialect instance.
        user_id: User identifier.

    Returns:
        InsertExpression with multiple value rows.
    """
    return InsertExpression(
        dialect,
        into="orders",
        columns=["user_id", "status"],
        source=ValuesSource(
            dialect,
            [
                [Literal(dialect, user_id), Literal(dialect, "pending")],
                [Literal(dialect, user_id), Literal(dialect, "pending")],
            ],
        ),
    )


def update_order_status(dialect, order_id: int, new_status: str):
    """Update order status by ID.

    Args:
        dialect: SQL dialect instance.
        order_id: Order identifier.
        new_status: New status value.

    Returns:
        UpdateExpression.
    """
    return UpdateExpression(
        dialect,
        table="orders",
        assignments={"status": Literal(dialect, new_status)},
        where=WhereClause(
            dialect,
            condition=Column(dialect, "id") == Literal(dialect, order_id),
        ),
    )


def cancel_order(dialect, order_id: int):
    """Delete an order by ID.

    Args:
        dialect: SQL dialect instance.
        order_id: Order identifier.

    Returns:
        DeleteExpression.
    """
    return DeleteExpression(
        dialect,
        tables="orders",
        where=WhereClause(
            dialect,
            condition=Column(dialect, "id") == Literal(dialect, order_id),
        ),
    )


def add_payment(dialect, order_id: int, status: str = "pending"):
    """Insert a payment record (INSERT with RETURNING).

    Args:
        dialect: SQL dialect instance.
        order_id: Order identifier.
        status: Payment status.

    Returns:
        InsertExpression with RETURNING clause.
    """
    return InsertExpression(
        dialect,
        into="payments",
        columns=["order_id", "status", "transaction_id"],
        source=ValuesSource(
            dialect,
            [
                [
                    Literal(dialect, order_id),
                    Literal(dialect, status),
                    Literal(dialect, "txn_new"),
                ]
            ],
        ),
        returning=ReturningClause(
            dialect,
            expressions=[Column(dialect, "id"), Column(dialect, "transaction_id")],
        ),
    )


def archive_processed_orders(dialect, status: str = "completed"):
    """Delete orders with a given status (mass DELETE).

    Args:
        dialect: SQL dialect instance.
        status: Status to filter by.

    Returns:
        DeleteExpression.
    """
    return DeleteExpression(
        dialect,
        tables="orders",
        where=WhereClause(
            dialect,
            condition=Column(dialect, "status") == Literal(dialect, status),
        ),
    )
