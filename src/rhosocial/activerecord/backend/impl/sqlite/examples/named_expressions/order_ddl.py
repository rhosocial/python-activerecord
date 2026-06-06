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
    AlterTableExpression,
    AddColumn,
    TableExpression,
)


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
            ColumnDefinition(dialect, "id", "INTEGER PRIMARY KEY"),
            ColumnDefinition(dialect, "user_id", "INTEGER NOT NULL"),
            ColumnDefinition(dialect, "status", "TEXT DEFAULT 'pending'"),
            ColumnDefinition(dialect, "amount", "REAL DEFAULT 0.0"),
            ColumnDefinition(dialect, "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
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
            ColumnDefinition(dialect, "id", "INTEGER PRIMARY KEY"),
            ColumnDefinition(dialect, "order_id", "INTEGER NOT NULL"),
            ColumnDefinition(dialect, "available", "INTEGER DEFAULT 0"),
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
                column=ColumnDefinition(dialect, "amount", "REAL DEFAULT 0.0"),
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
