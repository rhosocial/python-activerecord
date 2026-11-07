# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_expressions/order_dml.py
"""
DML named expression examples — INSERT / UPDATE / DELETE.

Each function takes 'dialect' as first parameter and returns
a BaseExpression that implements Executable.
"""

from rhosocial.activerecord.backend.expression import (
    InsertStatement,
    ValuesSource,
    UpdateStatement,
    DeleteStatement,
    Column,
    ComparisonPredicate,
    Literal,
    WhereClause,
    ReturningClause,
)
from .....expression.objects import Table


#: The status a new order carries in the demo schema when the caller names
#: none.
#:
#: The order examples run against one fixture table whose first row is a
#: pending order, and three of the write and clause examples default to it.
#: Writing ``"pending"`` down three times would be three places that have to
#: stay in step: change one and the others would insert or filter on a status
#: the fixture does not hold, which is a silent mismatch rather than an error.
#: Per ``.claude/rules/constants.md`` a value read from more than one
#: function, where the readings must agree, takes a module-level constant and
#: a test that pins it -- see
#: ``tests/rhosocial/activerecord_test/feature/rules/test_shared_defaults.py``.
DEFAULT_ORDER_STATUS: str = "pending"


def add_order(dialect, user_id: int, status: str = DEFAULT_ORDER_STATUS):
    """Insert a new order record.

    Args:
        dialect: SQL dialect instance.
        user_id: User identifier.
        status: Order status.

    Returns:
        InsertStatement.
    """
    return InsertStatement(
        dialect,
        into=Table(dialect, 'orders'),
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
        InsertStatement with multiple value rows.
    """
    return InsertStatement(
        dialect,
        into=Table(dialect, 'orders'),
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
        UpdateStatement.
    """
    return UpdateStatement(
        dialect,
        table=Table(dialect, 'orders'),
        assignments={"status": Literal(dialect, new_status)},
        where=WhereClause(
            dialect,
            condition=ComparisonPredicate(dialect, "=", Column(dialect, "id"), Literal(dialect, order_id)),
        ),
    )


def cancel_order(dialect, order_id: int):
    """Delete an order by ID.

    Args:
        dialect: SQL dialect instance.
        order_id: Order identifier.

    Returns:
        DeleteStatement.
    """
    return DeleteStatement(
        dialect,
        tables=Table(dialect, 'orders'),
        where=WhereClause(
            dialect,
            condition=ComparisonPredicate(dialect, "=", Column(dialect, "id"), Literal(dialect, order_id)),
        ),
    )


def add_payment(dialect, order_id: int, status: str = DEFAULT_ORDER_STATUS):
    """Insert a payment record (INSERT with RETURNING).

    Args:
        dialect: SQL dialect instance.
        order_id: Order identifier.
        status: Payment status.

    Returns:
        InsertStatement with RETURNING clause.
    """
    return InsertStatement(
        dialect,
        into=Table(dialect, 'payments'),
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
        DeleteStatement.
    """
    return DeleteStatement(
        dialect,
        tables=Table(dialect, 'orders'),
        where=WhereClause(
            dialect,
            condition=ComparisonPredicate(dialect, "=", Column(dialect, "status"), Literal(dialect, status)),
        ),
    )
