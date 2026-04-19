# tests/rhosocial/activerecord_test/feature/backend/named_query/example_async_procedures.py
"""
Async example procedures for testing.

This module contains sample async procedure definitions for testing
the named procedure functionality with async execution.
"""
import types
from rhosocial.activerecord.backend.named_query.procedure import (
    AsyncProcedure,
    AsyncProcedureContext,
)


class AsyncSimpleHelloProcedure(AsyncProcedure):
    """An async simple procedure that logs a greeting."""

    name: str = "World"

    async def run(self, ctx: AsyncProcedureContext) -> None:
        await ctx.log(f"Hello, {self.name}!")


class AsyncConditionalProcedure(AsyncProcedure):
    """An async procedure with conditional logic based on query results."""

    threshold: int = 10

    async def run(self, ctx: AsyncProcedureContext) -> None:
        mock_data = [
            {"id": 1, "value": 5},
            {"id": 2, "value": 15},
            {"id": 3, "value": 25},
        ]
        await ctx.bind("test_data", mock_data)

        total = sum(row["value"] async for row in ctx.rows("test_data"))
        if total >= self.threshold:
            await ctx.log(f"Total {total} meets threshold {self.threshold}")
        else:
            await ctx.log(f"Total {total} below threshold {self.threshold}")


class AsyncMultiStepProcedure(AsyncProcedure):
    """An async procedure with multiple execution steps."""

    month: str
    limit: int = 100

    async def run(self, ctx: AsyncProcedureContext) -> None:
        await ctx.log(f"Step 1: Starting procedure for month {self.month}")

        await ctx.bind("users", [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ])

        user_count = sum(1 async for _ in ctx.rows("users"))
        await ctx.log(f"Step 2: Found {user_count} users")

        async for user in ctx.rows("users"):
            await ctx.log(f"Processing user: {user['name']}")

        await ctx.log("Step 3: Procedure completed")


class AsyncAbortProcedure(AsyncProcedure):
    """An async procedure that tests abort functionality."""

    should_abort: bool = False

    async def run(self, ctx: AsyncProcedureContext) -> None:
        await ctx.log("Starting abort test procedure")

        if self.should_abort:
            await ctx.abort("example_async_procedures.AsyncAbortProcedure", "Test abort triggered")

        await ctx.log("This should not be reached")


class AsyncDataAggregationProcedure(AsyncProcedure):
    """An async procedure that aggregates data from multiple queries."""

    async def run(self, ctx: AsyncProcedureContext) -> None:
        await ctx.bind("sales", [
            {"product": "A", "amount": 100},
            {"product": "B", "amount": 200},
            {"product": "C", "amount": 150},
        ])

        await ctx.bind("returns", [
            {"product": "A", "amount": 10},
            {"product": "C", "amount": 20},
        ])

        total_sales = sum(row["amount"] async for row in ctx.rows("sales"))
        total_returns = sum(row["amount"] async for row in ctx.rows("returns"))

        await ctx.bind("summary", {
            "total_sales": total_sales,
            "total_returns": total_returns,
            "net": total_sales - total_returns,
        })

        await ctx.log(f"Sales: {total_sales}, Returns: {total_returns}, Net: {total_sales - total_returns}")


def get_async_procedures_module():
    """Return a module-like object containing all async procedures."""
    module = types.ModuleType("example_async_procedures")
    module.AsyncSimpleHelloProcedure = AsyncSimpleHelloProcedure
    module.AsyncConditionalProcedure = AsyncConditionalProcedure
    module.AsyncMultiStepProcedure = AsyncMultiStepProcedure
    module.AsyncAbortProcedure = AsyncAbortProcedure
    module.AsyncDataAggregationProcedure = AsyncDataAggregationProcedure
    return module