# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_expressions/order_expressions.py
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

from rhosocial.activerecord.backend.expression import (  # noqa: E402
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.core import Literal  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnDefinition,
)
from rhosocial.activerecord.backend.expression.types import (  # noqa: E402
    IntegerType,
    TextType,
)


def _column(name: str, type_name: str):
    """Build a ColumnDefinition from a compact 'name TYPE [PRIMARY KEY]' spec."""
    data_type = IntegerType() if type_name == "INTEGER" else TextType()
    constraints = []
    if "PRIMARY KEY" in type_name:
        constraints.append(ColumnConstraint(constraint_type=ColumnConstraintType.PRIMARY_KEY))
    return ColumnDefinition(name=name, data_type=data_type, constraints=constraints)


tables = [
    ("orders", [("id", "INTEGER PRIMARY KEY"), ("status", TextType()), ("user_id", IntegerType())]),
    ("inventory", [("id", "INTEGER PRIMARY KEY"), ("order_id", IntegerType()), ("available", IntegerType())]),
    ("notifications", [("id", "INTEGER PRIMARY KEY"), ("user_id", IntegerType()), ("type", TextType())]),
    (
        "payments",
        [("id", "INTEGER PRIMARY KEY"), ("order_id", IntegerType()), ("status", TextType()), ("transaction_id", TextType())],
    ),
    ("order_records", [("id", "INTEGER PRIMARY KEY"), ("order_id", IntegerType()), ("created_at", TextType())]),
]

for table_name, columns in tables:
    create = CreateTableExpression(
        dialect=dialect,
        table=table_name,
        columns=[_column(name, type_name) for name, type_name in columns],
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
            columns=[name for name, _ in tables[[t for t, _ in tables].index(table)][1]],
            source=ValuesSource(dialect, [[Literal(dialect, v) for v in row]]),
        )
        sql, params = insert.to_sql()
        backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.expression import Column, Literal, QueryExpression, TableExpression  # noqa: E402


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
from rhosocial.activerecord.backend.options import ExecutionOptions  # noqa: E402
from rhosocial.activerecord.backend.schema import StatementType  # noqa: E402

if __name__ == "__main__":
    query = get_order(dialect, order_id=1)
    sql, params = query.to_sql()
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = backend.execute(sql, params, options=options)
    print(f"Execution result: {result.data}\n")

    # ============================================================
    # SECTION: Teardown (necessary for execution, reference only)
    # ============================================================
    backend.disconnect()
