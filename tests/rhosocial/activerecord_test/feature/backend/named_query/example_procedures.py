# tests/rhosocial/activerecord_test/feature/backend/named_query/example_procedures.py
"""
Example procedures for testing.

This module contains sample procedure definitions for testing
the named procedure functionality.
"""
import types
from rhosocial.activerecord.backend.named_query.procedure import (
    Procedure,
    ProcedureContext,
)


class SimpleHelloProcedure(Procedure):
    """A simple procedure that just logs a greeting."""

    name: str = "World"

    def run(self, ctx: ProcedureContext) -> None:
        ctx.log(f"Hello, {self.name}!")


class ConditionalProcedure(Procedure):
    """A procedure with conditional logic based on query results."""

    threshold: int = 10

    def run(self, ctx: ProcedureContext) -> None:
        mock_data = [
            {"id": 1, "value": 5},
            {"id": 2, "value": 15},
            {"id": 3, "value": 25},
        ]
        ctx.bind("test_data", mock_data)

        total = sum(row["value"] for row in ctx.rows("test_data"))
        if total >= self.threshold:
            ctx.log(f"Total {total} meets threshold {self.threshold}")
        else:
            ctx.log(f"Total {total} below threshold {self.threshold}")


class MultiStepProcedure(Procedure):
    """A procedure with multiple execution steps."""

    month: str
    limit: int = 100

    def run(self, ctx: ProcedureContext) -> None:
        ctx.log(f"Step 1: Starting procedure for month {self.month}")

        ctx.bind("users", [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ])

        ctx.log(f"Step 2: Found {len(list(ctx.rows('users'))} users")

        for user in ctx.rows("users"):
            ctx.log(f"Processing user: {user['name']}")

        ctx.log("Step 3: Procedure completed")


class AbortProcedure(Procedure):
    """A procedure that tests abort functionality."""

    should_abort: bool = False

    def run(self, ctx: ProcedureContext) -> None:
        ctx.log("Starting abort test procedure")

        if self.should_abort:
            ctx.abort("Test abort triggered")

        ctx.log("This should not be reached")


class DataAggregationProcedure(Procedure):
    """Procedure that aggregates data from multiple queries."""

    def run(self, ctx: ProcedureContext) -> None:
        ctx.bind("sales", [
            {"product": "A", "amount": 100},
            {"product": "B", "amount": 200},
            {"product": "C", "amount": 150},
        ])

        ctx.bind("returns", [
            {"product": "A", "amount": 10},
            {"product": "C", "amount": 20},
        ])

        total_sales = sum(row["amount"] for row in ctx.rows("sales"))
        total_returns = sum(row["amount"] for row in ctx.rows("returns"))

        ctx.bind("summary", {
            "total_sales": total_sales,
            "total_returns": total_returns,
            "net": total_sales - total_returns,
        })

        ctx.log(f"Sales: {total_sales}, Returns: {total_returns}, Net: {total_sales - total_returns}")


def get_procedures_module():
    """Return a module-like object containing all procedures."""
    module = types.ModuleType("example_procedures")
    module.SimpleHelloProcedure = SimpleHelloProcedure
    module.ConditionalProcedure = ConditionalProcedure
    module.MultiStepProcedure = MultiStepProcedure
    module.AbortProcedure = AbortProcedure
    module.DataAggregationProcedure = DataAggregationProcedure
    return module