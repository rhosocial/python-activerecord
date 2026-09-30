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
# NOTE: nothing below connects to a database at import time. The named
# expressions in this module are resolved by FQN, so the CLI imports this file
# just to answer --list or --describe -- and a module-level connection would make
# reading a docstring open a database and run DDL. main() does the setup; see the
# bottom of the file.
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    Column,
    ColumnConstraint,
    ColumnConstraintType,
    CreateTableExpression,
    InsertExpression,
    QueryExpression,
    TableExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal  # noqa: E402
from rhosocial.activerecord.backend.expression.statements import (  # noqa: E402
    ColumnDefinition,
)
from rhosocial.activerecord.backend.expression.types import (  # noqa: E402
    IntegerType,
    TextType,
)
from rhosocial.activerecord.backend.options import ExecutionOptions  # noqa: E402
from rhosocial.activerecord.backend.schema import StatementType  # noqa: E402


TABLES = [
    ("orders", [("id", "INTEGER PRIMARY KEY"), ("status", "TEXT"), ("user_id", "INTEGER")]),
    ("inventory", [("id", "INTEGER PRIMARY KEY"), ("order_id", "INTEGER"), ("available", "INTEGER")]),
    ("notifications", [("id", "INTEGER PRIMARY KEY"), ("user_id", "INTEGER"), ("type", "TEXT")]),
    (
        "payments",
        [("id", "INTEGER PRIMARY KEY"), ("order_id", "INTEGER"), ("status", "TEXT"), ("transaction_id", "TEXT")],
    ),
    ("order_records", [("id", "INTEGER PRIMARY KEY"), ("order_id", "INTEGER"), ("created_at", "TEXT")]),
]

def _column(dialect, name: str, type_name: str):
    """Build a ColumnDefinition from a compact 'name TYPE [PRIMARY KEY]' spec."""
    data_type = IntegerType(dialect) if type_name == "INTEGER" else TextType(dialect)
    constraints = []
    if "PRIMARY KEY" in type_name:
        constraints.append(ColumnConstraint(dialect, constraint_type=ColumnConstraintType.PRIMARY_KEY))
    return ColumnDefinition(dialect, name=name, data_type=data_type, constraints=constraints)


SAMPLE_ROWS = {
    "orders": [(1, "pending", 100)],
    "inventory": [(1, 1, 10)],
}


def prepare_database(backend) -> None:
    """Create the tables and insert the sample rows. Called from main() only."""
    dialect = backend.dialect
    for table_name, columns in TABLES:
        create = CreateTableExpression(
            dialect=dialect,
            table=table_name,
            columns=[_column(dialect, name, type_name) for name, type_name in columns],
            if_not_exists=True,
        )
        sql, params = create.to_sql()
        backend.execute(sql, params)

    for table, rows in SAMPLE_ROWS.items():
        names = [name for name, _ in TABLES[[t for t, _ in TABLES].index(table)][1]]
        for row in rows:
            insert = InsertExpression(
                dialect=dialect,
                into=table,
                columns=names,
                source=ValuesSource(dialect, [[Literal(dialect, v) for v in row]]),
            )
            sql, params = insert.to_sql()
            backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================


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


# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
def main() -> None:
    """Connect, prepare the sample data, then render and run a few queries."""
    # Imported here rather than at module scope: SQLiteBackend drags in the whole
    # dialect stack, and resolving this module's named expressions needs none of
    # it. Keeping it at module level made `import` cost ~3.5s for a file whose
    # exports are pure expression builders.
    from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
    from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

    config = SQLiteConnectionConfig(database=":memory:")
    backend = SQLiteBackend(config)

    # Version-gated features (RETURNING, JSON1, math functions) read the dialect
    # version, which is only known after the server has been inspected.
    backend.introspect_and_adapt()
    dialect = backend.dialect

    prepare_database(backend)

    print("=== Named Expression Examples ===\n")

    for name, kwargs in (
        ("get_order", {"order_id": 1}),
        ("check_inventory", {"order_id": 1}),
        ("reserve_inventory", {"order_id": 1}),
    ):
        query = globals()[name](dialect, **kwargs)
        sql, params = query.to_sql()
        print(f"{name} SQL: {sql}")
        print(f"Params: {params}\n")

    query = get_order(dialect, order_id=1)
    sql, params = query.to_sql()
    options = ExecutionOptions(stmt_type=StatementType.DQL)
    result = backend.execute(sql, params, options=options)
    print(f"Execution result: {result.data}\n")

    # ============================================================
    # SECTION: Teardown (necessary for execution, reference only)
    # ============================================================
    backend.disconnect()


if __name__ == "__main__":
    main()
