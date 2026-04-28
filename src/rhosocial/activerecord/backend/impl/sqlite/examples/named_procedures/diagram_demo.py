# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_procedures/diagram_demo.py
"""
Demo script: Generate static and instance diagrams for order processing workflow.

Usage:
    cd src/rhosocial/activerecord/backend/impl/sqlite/examples/named_procedures
    PYTHONPATH=../../../../..:. python3 diagram_demo.py

Or:
    python -m rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.diagram_demo
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.named_query import (
    ProcedureRunner,
    TransactionMode,
)

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect

from rhosocial.activerecord.backend.expression import (
    CreateTableExpression,
    InsertExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition

# Create tables
tables = [
    ("orders", ["id INTEGER PRIMARY KEY", "user_id INTEGER", "status TEXT", "amount REAL"]),
    ("inventory", ["id INTEGER PRIMARY KEY", "order_id INTEGER", "available INTEGER", "reserved INTEGER"]),
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
sample_data = [
    ("orders", ["id", "user_id", "status", "amount"], [(1, 100, "pending", 99.99)]),
    ("inventory", ["id", "order_id", "available", "reserved"], [(1, 1, 10, 0)]),
    ("payments", ["id", "order_id", "status", "transaction_id"], [(1, 1, "success", "TXN123")]),
]
for table, cols, rows in sample_data:
    for row in rows:
        insert = InsertExpression(
            dialect=dialect,
            into=table,
            columns=cols,
            source=ValuesSource(dialect, [[Literal(dialect, v) for v in row]]),
        )
        sql, params = insert.to_sql()
        backend.execute(sql, params)


# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
from rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow import (
    OrderProcessingProcedure,
)


def main():
    print("=" * 60)
    print("Order Processing Workflow - Static Diagram Demo")
    print("=" * 60)
    print()

    # Static flowchart
    print("【Flowchart Static Diagram】")
    print("-" * 40)
    flowchart = OrderProcessingProcedure.static_diagram("flowchart")
    print(flowchart)
    print()

    # Static sequence diagram
    print("【Sequence Static Diagram】")
    print("-" * 40)
    sequence = OrderProcessingProcedure.static_diagram("sequence")
    print(sequence)
    print()

    # Instance diagram
    print("=" * 60)
    print("Order Processing Workflow - Instance Diagram Demo")
    print("=" * 60)
    print()

    def execute_query(sql, params, stmt_type=None):
        class MockResult:
            def __init__(self, data, affected_rows):
                self.data = data
                self.affected_rows = affected_rows

        conn = backend.connection
        try:
            cursor = conn.execute(sql, params)
            if sql.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                data = [dict(zip(columns, row)) for row in rows] if columns else []
                return MockResult(data, len(data))
            else:
                conn.commit()
                return MockResult([], cursor.rowcount)
        except Exception as e:
            conn.rollback()
            return MockResult([], 0)

    runner = ProcedureRunner(
        "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure"
    ).load()

    result = runner.run(
        backend,
        user_params={"order_id": 1, "user_id": 100, "amount": 99.99},
        transaction_mode=TransactionMode.AUTO,
    )

    print(f"Execution result: success={result.success}, aborted={result.aborted}")
    if result.aborted:
        print(f"Abort reason: {result.abort_reason}")
    print()

    # Instance flowchart
    print("【Flowchart Instance Diagram】")
    print("-" * 40)
    instance_flowchart = result.diagram("flowchart", procedure_name="OrderProcessingProcedure")
    print(instance_flowchart)
    print()

    # Instance sequence diagram
    print("【Sequence Instance Diagram】")
    print("-" * 40)
    instance_sequence = result.diagram("sequence", procedure_name="OrderProcessingProcedure")
    print(instance_sequence)
    print()

    print("=" * 60)
    print("Notes:")
    print("- Instance diagram shows execution status (green=success, red=failure)")
    print("- Shows execution time for each step (milliseconds)")
    print("- Unexecuted steps shown in gray")
    print("- END node shows total steps and total time")
    print("=" * 60)


if __name__ == "__main__":
    main()

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()