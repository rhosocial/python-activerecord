from rhosocial.activerecord.backend.expression.statements import (
    ColumnPrimaryKeyConstraint,
)
from .....expression.objects import Table
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression import Column, ComparisonPredicate, Literal, QueryStatement
from rhosocial.activerecord.backend.expression.types import (  # noqa: E402
    IntegerType,
    TextType,
)
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnDefinition,
)
from rhosocial.activerecord.backend.expression import CreateTableStatement, InsertStatement, ValuesSource, ColumnConstraint
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
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

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect



def _column(name: str, type_name: str):
    """Build a ColumnDefinition from a compact 'name TYPE [PRIMARY KEY]' spec."""
    data_type = IntegerType() if type_name == "INTEGER" else TextType()
    constraints = []
    if "PRIMARY KEY" in type_name:
        constraints.append(ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect)))
    return ColumnDefinition(dialect, name=name, data_type=data_type, constraints=constraints)


tables = [
    ("orders", [("id", "INTEGER PRIMARY KEY"), ("status", "TEXT"), ("user_id", "INTEGER")]),
    ("inventory", [("id", "INTEGER PRIMARY KEY"), ("order_id", "INTEGER"), ("available", "INTEGER")]),
    ("notifications", [("id", "INTEGER PRIMARY KEY"), ("user_id", "INTEGER"), ("type", "TEXT")]),
    (
        "payments",
        [("id", "INTEGER PRIMARY KEY"), ("order_id", "INTEGER"), ("status", "TEXT"), ("transaction_id", "TEXT")],
    ),
    ("order_records", [("id", "INTEGER PRIMARY KEY"), ("order_id", "INTEGER"), ("created_at", "TEXT")]),
]

for table_name, columns in tables:
    create = CreateTableStatement(
        dialect=dialect,
        table=Table(dialect, table_name),
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
        insert = InsertStatement(
            dialect=dialect,
            into=Table(dialect, table),
            columns=[name for name, _ in tables[[t for t, _ in tables].index(table)][1]],
            source=ValuesSource(dialect, [[Literal(dialect, v) for v in row]]),
        )
        sql, params = insert.to_sql()
        backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================


def get_order(dialect, order_id: int):
    """Get order details by ID."""
    return QueryStatement(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "status"), Column(dialect, "user_id")],
        from_=NamedRelationRef(dialect, Table(dialect, "orders")),
        where=ComparisonPredicate(dialect, "=", Column(dialect, "id"), Literal(dialect, order_id)),
    )


def check_inventory(dialect, order_id: int):
    """Check available inventory for an order."""
    return QueryStatement(
        dialect,
        select=[Column(dialect, "available")],
        from_=NamedRelationRef(dialect, Table(dialect, "inventory")),
        where=ComparisonPredicate(dialect, "=", Column(dialect, "order_id"), Literal(dialect, order_id)),
    )


def reserve_inventory(dialect, order_id: int):
    """Reserve inventory for an order."""
    return QueryStatement(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "reserved")],
        from_=NamedRelationRef(dialect, Table(dialect, "inventory")),
        where=ComparisonPredicate(dialect, "=", Column(dialect, "order_id"), Literal(dialect, order_id)),
    )


def send_notification(dialect, user_id: int, type: str):
    """Send notification to a user."""
    return QueryStatement(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "notifications")),
        where=ComparisonPredicate(dialect, "=", Column(dialect, "user_id"), Literal(dialect, user_id)),
    )


def process_payment(dialect, order_id: int, amount: float):
    """Process payment for an order."""
    return QueryStatement(
        dialect,
        select=[Column(dialect, "status"), Column(dialect, "transaction_id")],
        from_=NamedRelationRef(dialect, Table(dialect, "payments")),
        where=ComparisonPredicate(dialect, "=", Column(dialect, "order_id"), Literal(dialect, order_id)),
    )


def release_inventory(dialect, order_id: int):
    """Release reserved inventory."""
    return QueryStatement(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "inventory")),
        where=ComparisonPredicate(dialect, "=", Column(dialect, "order_id"), Literal(dialect, order_id)),
    )


def create_order_record(dialect, order_id: int, user_id: int, amount: float):
    """Create an order record."""
    return QueryStatement(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "created_at")],
        from_=NamedRelationRef(dialect, Table(dialect, "order_records")),
        where=ComparisonPredicate(dialect, "=", Column(dialect, "order_id"), Literal(dialect, order_id)),
    )


def confirm_inventory(dialect, order_id: int):
    """Confirm inventory (final confirmation)."""
    return QueryStatement(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "inventory")),
        where=ComparisonPredicate(dialect, "=", Column(dialect, "order_id"), Literal(dialect, order_id)),
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
