# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_procedures/order_workflow.py
"""
Order processing workflow example - demonstrates Named Procedure flowchart capabilities.

This procedure includes:
- Conditional branching (inventory check)
- Parallel execution (inventory reservation + notification)
- Conditional rollback (payment failure)

Named Procedure is a backend feature, independent of ActiveRecord models.
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
    ColumnConstraint,
    ColumnConstraintType,
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
sample_data = [
    ("orders", ["id", "status", "user_id"], [(1, "pending", 100)]),
    ("inventory", ["id", "order_id", "available"], [(1, 1, 10)]),
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
from rhosocial.activerecord.backend.named_query import (
    Procedure,
    ProcedureContext,
    ParallelStep,
)


class OrderProcessingProcedure(Procedure):
    """Complete order processing workflow.

    Flow:
    1. Query order details
    2. Check inventory (abort if insufficient)
    3. Parallel: reserve inventory + send notification
    4. Process payment (rollback inventory on failure)
    5. Create order record
    6. Final inventory confirmation
    """

    order_id: int
    user_id: int
    amount: float = 0.0

    def run(self, ctx: ProcedureContext) -> None:
        ctx.log(f"Starting order processing: {self.order_id}", "INFO")

        ctx.execute(
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.get_order",
            params={"order_id": self.order_id},
            bind="order",
        )

        order = ctx.scalar("order", "status")
        if order is None:
            ctx.log(f"Order {self.order_id} not found", "ERROR")
            ctx.abort("OrderProcessingProcedure", f"Order {self.order_id} not found")

        ctx.log(f"Order status: {order}", "DEBUG")

        ctx.execute(
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.check_inventory",
            params={"order_id": self.order_id},
            bind="inventory",
        )

        available = ctx.scalar("inventory", "available")
        if not available or available < 1:
            ctx.log("Insufficient inventory, aborting", "WARNING")
            ctx.abort("OrderProcessingProcedure", "Insufficient inventory")

        ctx.parallel(
            ParallelStep(
                "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.reserve_inventory",
                params={"order_id": self.order_id},
                bind="reserved",
            ),
            ParallelStep(
                "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.send_notification",
                params={"user_id": self.user_id, "type": "order_started"},
            ),
            max_concurrency=2,
        )

        ctx.execute(
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.process_payment",
            params={"order_id": self.order_id, "amount": self.amount},
            bind="payment",
        )

        payment_status = ctx.scalar("payment", "status")
        if payment_status != "success":
            ctx.log(f"Payment failed: {payment_status}, rolling back inventory", "ERROR")
            ctx.execute(
                "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.release_inventory",
                params={"order_id": self.order_id},
                output=True,
            )
            ctx.abort("OrderProcessingProcedure", f"Payment failed: {payment_status}")

        ctx.execute(
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.create_order_record",
            params={
                "order_id": self.order_id,
                "user_id": self.user_id,
                "amount": self.amount,
            },
            bind="order_record",
            output=True,
        )

        ctx.execute(
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.confirm_inventory",
            params={"order_id": self.order_id},
            output=True,
        )

        ctx.log(f"Order {self.order_id} processing complete", "INFO")


# Demo: Generate static diagram
if __name__ == "__main__":
    print("=== Order Processing Procedure ===\n")
    print("Static Diagram (Flowchart):")
    print(OrderProcessingProcedure.static_diagram("flowchart"))
    print("\nStatic Diagram (Sequence):")
    print(OrderProcessingProcedure.static_diagram("sequence"))

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
from rhosocial.activerecord.backend.named_query import ProcedureRunner, TransactionMode

runner = ProcedureRunner(
    "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure"
).load()

result = runner.run(
    backend,
    user_params={"order_id": 1, "user_id": 100, "amount": 99.99},
    transaction_mode=TransactionMode.AUTO,
)

print(f"Procedure completed. Aborted: {result.aborted}")
if result.aborted:
    print(f"Abort reason: {result.abort_reason}")
for log in result.logs:
    print(f"[{log.level}] {log.message}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()