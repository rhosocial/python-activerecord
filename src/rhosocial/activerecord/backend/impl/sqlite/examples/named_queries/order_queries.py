# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_queries/order_queries.py
"""
Order-related named query examples.

This file demonstrates how to define named queries (Named Query) for encapsulating
reusable SQL query logic. Named queries are backend features, independent of
ActiveRecord models.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
)

tables = [
    ("orders", ["id INTEGER PRIMARY KEY", "status TEXT", "user_id INTEGER"]),
    ("inventory", ["id INTEGER PRIMARY KEY", "order_id INTEGER", "available INTEGER"]),
    ("notifications", ["id INTEGER PRIMARY KEY", "user_id INTEGER", "type TEXT"]),
    ("payments", ["id INTEGER PRIMARY KEY", "order_id INTEGER", "status TEXT", "transaction_id TEXT"]),
    ("order_records", ["id INTEGER PRIMARY KEY", "order_id INTEGER", "created_at TEXT"]),
]

for table_name, columns in tables:
    create = CreateTableExpression(
        dialect=dialect,
        table_name=table_name,
        columns=[ColumnDefinition(c.split()[0], c.split()[1]) for c in columns],
        if_not_exists=True,
    )
    sql, params = create.to_sql()
    backend.execute(sql, params)

# Insert sample data
for table, data in [
    ("orders", [(1, "pending", 100)]),
    ("inventory", [(1, 1, 10)]),
]:
    for row in data:
        insert = InsertExpression(
            dialect=dialect,
            into=table,
            columns=[c.split()[0] for c in tables[[t for t, _ in tables].index(table)][1]],
            source=ValuesSource(dialect, [[Literal(dialect, v) for v in row]]),
        )
        sql, params = insert.to_sql()
        backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import Column, Literal, QueryExpression, TableExpression


def get_order(dialect, order_id: int):
    """Get order details by ID."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "status"), Column(dialect, "user_id")],
        from_=TableExpression(dialect, "orders"),
        where=Column(dialect, "id") == Literal(dialect, order_id),
    )


def check_inventory(dialect, order_id: int):
    """Check available inventory for an order."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "available")],
        from_=TableExpression(dialect, "inventory"),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
    )


def reserve_inventory(dialect, order_id: int):
    """Reserve inventory for an order."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "reserved")],
        from_=TableExpression(dialect, "inventory"),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
    )


def send_notification(dialect, user_id: int, type: str):
    """Send notification to a user."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id")],
        from_=TableExpression(dialect, "notifications"),
        where=Column(dialect, "user_id") == Literal(dialect, user_id),
    )


def process_payment(dialect, order_id: int, amount: float):
    """Process payment for an order."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "status"), Column(dialect, "transaction_id")],
        from_=TableExpression(dialect, "payments"),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
    )


def release_inventory(dialect, order_id: int):
    """Release reserved inventory."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id")],
        from_=TableExpression(dialect, "inventory"),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
    )


def create_order_record(dialect, order_id: int, user_id: int, amount: float):
    """Create an order record."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "created_at")],
        from_=TableExpression(dialect, "order_records"),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
    )


def confirm_inventory(dialect, order_id: int):
    """Confirm inventory (final confirmation)."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "id")],
        from_=TableExpression(dialect, "inventory"),
        where=Column(dialect, "order_id") == Literal(dialect, order_id),
    )


# Demo: Generate SQL for a named query
if __name__ == "__main__":
    print("=== Named Query Examples ===\n")

    query = get_order(dialect, order_id=1)
    sql, params = query.to_sql()
    print(f"get_order SQL: {sql}")
    print(f"Params: {params}\n")

    query = check_inventory(dialect, order_id=1)
    sql, params = query.to_sql()
    print(f"check_inventory SQL: {sql}")
    print(f"Params: {params}\n")

    query = reserve_inventory(dialect, order_id=1)
    sql, params = query.to_sql()
    print(f"reserve_inventory SQL: {sql}")
    print(f"Params: {params}\n")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

query = get_order(dialect, order_id=1)
sql, params = query.to_sql()
options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"Execution result: {result.data}\n")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()