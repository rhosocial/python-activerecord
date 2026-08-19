# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_expressions/order_ddl.py
"""
DDL named expression examples — CREATE / ALTER / DROP.

Each function takes 'dialect' as first parameter and returns
a BaseExpression that implements Executable.
"""

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    DropTableExpression,
    CreateIndexExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    AlterTableExpression,
    AddColumn,
    TableExpression,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, RealType, TextType


def _pk_column(name: str):
    """Integer PRIMARY KEY column definition."""
    return ColumnDefinition(
        name=name,
        data_type=IntegerType(),
        constraints=[
            ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY),
        ],
    )


def _integer_column(name: str, default: int = None, not_null: bool = False):
    """Integer column definition with optional DEFAULT / NOT NULL."""
    constraints = []
    if not_null:
        constraints.append(ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL))
    if default is not None:
        constraints.append(
            ColumnConstraint(constraint_type=ColumnConstraintType.DEFAULT, default_value=default)
        )
    return ColumnDefinition(name=name, data_type=IntegerType(), constraints=constraints)


def _text_column(name: str, default: str = None, not_null: bool = False):
    """Text column definition with optional DEFAULT / NOT NULL."""
    constraints = []
    if not_null:
        constraints.append(ColumnConstraint(constraint_type=ColumnConstraintType.NOT_NULL))
    if default is not None:
        constraints.append(
            ColumnConstraint(constraint_type=ColumnConstraintType.DEFAULT, default_value=default)
        )
    return ColumnDefinition(name=name, data_type=TextType(), constraints=constraints)


def _real_column(name: str, default: float = None):
    """REAL column definition with optional DEFAULT."""
    constraints = []
    if default is not None:
        constraints.append(
            ColumnConstraint(constraint_type=ColumnConstraintType.DEFAULT, default_value=default)
        )
    return ColumnDefinition(name=name, data_type=RealType(), constraints=constraints)


def create_orders_table(dialect):
    """Create the orders table.

    Args:
        dialect: SQL dialect instance.

    Returns:
        CreateTableExpression.
    """
    return CreateTableExpression(
        dialect,
        table="orders",
        columns=[
            _pk_column("id"),
            _integer_column("user_id", not_null=True),
            _text_column("status", default="pending"),
            _real_column("amount", default=0.0),
            _text_column("created_at", default="CURRENT_TIMESTAMP"),
        ],
        if_not_exists=True,
    )


def create_inventory_table(dialect):
    """Create the inventory table.

    Args:
        dialect: SQL dialect instance.

    Returns:
        CreateTableExpression.
    """
    return CreateTableExpression(
        dialect,
        table="inventory",
        columns=[
            _pk_column("id"),
            _integer_column("order_id", not_null=True),
            _integer_column("available", default=0),
        ],
        if_not_exists=True,
    )


def add_amount_column(dialect):
    """Add amount column to an existing table (ALTER TABLE ADD COLUMN).

    Args:
        dialect: SQL dialect instance.

    Returns:
        AlterTableExpression.
    """
    return AlterTableExpression(
        dialect,
        table_name="orders",
        actions=[
            AddColumn(
                dialect,
                column=_real_column("amount", default=0.0),
            ),
        ],
    )


def add_orders_status_index(dialect):
    """Create an index on orders.status.

    Args:
        dialect: SQL dialect instance.

    Returns:
        CreateIndexExpression.
    """
    return CreateIndexExpression(
        dialect,
        index_name="idx_orders_status",
        table_name="orders",
        columns=["status"],
        if_not_exists=True,
    )


def drop_old_orders_table(dialect):
    """Drop the legacy temp_orders table.

    Args:
        dialect: SQL dialect instance.

    Returns:
        DropTableExpression.
    """
    return DropTableExpression(
        dialect,
        table=TableExpression(dialect, "temp_orders"),
        if_exists=True,
    )
