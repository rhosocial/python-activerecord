#!/usr/bin/env python3
"""
Example: Async Connection Pool Usage

This example demonstrates asynchronous connection pool usage with full
context awareness support.

Run with: python async_usage.py
"""

import asyncio
import tempfile
import os

from rhosocial.activerecord.connection.pool import (
    PoolConfig,
    AsyncBackendPool,
    get_current_async_pool,
    get_current_transaction_backend,
    get_current_connection_backend,
    get_current_backend,
)
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


async def print_context_state(label: str):
    """Helper to print current context state."""
    pool = get_current_async_pool()
    tx_backend = get_current_transaction_backend()
    conn_backend = get_current_connection_backend()
    current_backend = get_current_backend()

    print(f"\n{label}:")
    print(f"  Async Pool: {pool is not None}")
    print(f"  Transaction Backend: {tx_backend is not None}")
    print(f"  Connection Backend: {conn_backend is not None}")
    print(f"  Current Backend: {current_backend is not None}")


async def worker(pool: AsyncBackendPool, worker_id: int):
    """Simulate a worker that uses the pool."""
    async with pool.connection() as backend:
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = await backend.execute(
            "SELECT * FROM items WHERE worker_id = ?",
            [worker_id],
            options=options
        )
        print(f"Worker {worker_id}: found {len(result.data)} items")
        await asyncio.sleep(0.1)  # Simulate work
        return worker_id, len(result.data)


class AsyncItemRepository:
    """Async repository that uses context-aware operations."""

    async def create(self, name: str, worker_id: int) -> int:
        """Create a new item."""
        backend = get_current_backend()
        if backend is None:
            raise RuntimeError("No connection in current context")

        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute(
            "INSERT INTO items (name, worker_id) VALUES (?, ?)",
            [name, worker_id],
            options=options
        )

        options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = await backend.execute("SELECT last_insert_rowid() as id", [], options=options)
        return result.data[0]['id']

    async def count(self) -> int:
        """Count all items."""
        backend = get_current_backend()
        if backend is None:
            raise RuntimeError("No connection in current context")

        options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = await backend.execute("SELECT COUNT(*) as count FROM items", [], options=options)
        return result.data[0]['count']


async def main():
    print("=" * 60)
    print("Async Connection Pool - Usage Examples")
    print("=" * 60)

    # Use a temporary file database so all connections share the same data
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    db_path = temp_db.name

    try:
        # Create async connection pool
        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=db_path)
        )
        pool = AsyncBackendPool(config)

        print(f"\nPool created: {pool}")

        # Create table
        async with pool.connection() as backend:
            options = ExecutionOptions(stmt_type=StatementType.DDL)
            await backend.execute("""
                CREATE TABLE items (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    worker_id INTEGER
                )
            """, [], options=options)

        # -----------------------------------------------------------
        # Example 1: Basic async connection context
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 1: Basic Async Connection Context")
        print("-" * 40)

        async with pool.connection() as backend:
            options = ExecutionOptions(stmt_type=StatementType.DML)
            await backend.execute("INSERT INTO items (name, worker_id) VALUES (?, ?)", ["Item1", 1], options=options)
            await backend.execute("INSERT INTO items (name, worker_id) VALUES (?, ?)", ["Item2", 2], options=options)

            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = await backend.execute("SELECT COUNT(*) as count FROM items", [], options=options)
            print(f"Items count: {result.data[0]['count']}")

        # -----------------------------------------------------------
        # Example 2: Async pool context
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 2: Async Pool Context")
        print("-" * 40)

        await print_context_state("Outside pool context")

        async with pool.context():
            await print_context_state("Inside async pool context")
            assert get_current_async_pool() is pool
            print("\nAsync pool is accessible!")

        await print_context_state("Outside pool context again")

        # -----------------------------------------------------------
        # Example 3: Async transaction context
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 3: Async Transaction Context")
        print("-" * 40)

        async with pool.context():
            async with pool.transaction() as backend:
                await print_context_state("In async transaction context")

                # Both transaction and connection are set
                tx = get_current_transaction_backend()
                conn = get_current_connection_backend()
                assert tx is backend
                assert conn is backend

                # Use repository
                repo = AsyncItemRepository()
                item_id = await repo.create("Item3", 3)
                print(f"\nCreated item with ID: {item_id}")

                # Count using repository
                count = await repo.count()
                print(f"Total items: {count}")

        # -----------------------------------------------------------
        # Example 4: Concurrent operations
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 4: Concurrent Operations")
        print("-" * 40)

        # Insert more items for concurrent access test
        async with pool.connection() as backend:
            options = ExecutionOptions(stmt_type=StatementType.DML)
            for i in range(3, 11):
                await backend.execute("INSERT INTO items (name, worker_id) VALUES (?, ?)", [f"Item{i}", i % 3 + 1], options=options)

        print("Running 5 concurrent workers...")
        tasks = [worker(pool, i) for i in range(1, 6)]
        results = await asyncio.gather(*tasks)
        print(f"Results: {results}")

        # -----------------------------------------------------------
        # Example 5: Nested async contexts
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 5: Nested Async Contexts")
        print("-" * 40)

        async with pool.connection() as outer_conn:
            outer_id = id(outer_conn)
            print(f"Outer connection ID: {outer_id}")

            async with pool.connection() as inner_conn:
                inner_id = id(inner_conn)
                print(f"Inner connection ID: {inner_id}")

                if outer_id == inner_id:
                    print("\nSame connection reused in async context!")
                else:
                    print("\nDifferent connections - unexpected!")

        # -----------------------------------------------------------
        # Example 6: Async transaction with rollback
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 6: Async Transaction with Rollback")
        print("-" * 40)

        async with pool.context():
            # Get count before
            async with pool.connection() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DQL)
                result = await backend.execute("SELECT COUNT(*) as count FROM items", [], options=options)
                count_before = result.data[0]['count']
                print(f"Items before: {count_before}")

            # Failed transaction
            try:
                async with pool.transaction() as backend:
                    repo = AsyncItemRepository()
                    await repo.create("TempItem", 99)
                    print("Created temp item...")

                    # Count in transaction
                    count_in_tx = await repo.count()
                    print(f"Items in transaction: {count_in_tx}")

                    raise ValueError("Simulated async error")
            except ValueError as e:
                print(f"Error: {e}")
                print("Transaction rolled back!")

            # Verify rollback
            async with pool.connection() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DQL)
                result = await backend.execute("SELECT COUNT(*) as count FROM items", [], options=options)
                count_after = result.data[0]['count']
                print(f"Items after rollback: {count_after}")

                if count_before == count_after:
                    print("Rollback verified - count unchanged!")
                else:
                    print("ERROR - count changed, rollback failed!")

        # -----------------------------------------------------------
        # Example 7: Statistics
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 7: Pool Statistics")
        print("-" * 40)

        stats = pool.get_stats()
        print(f"Total created: {stats.total_created}")
        print(f"Total acquired: {stats.total_acquired}")
        print(f"Total released: {stats.total_released}")
        print(f"Current available: {stats.current_available}")
        print(f"Current in use: {stats.current_in_use}")

        health = await pool.health_check()
        print(f"\nHealth check:")
        print(f"  Healthy: {health['healthy']}")
        print(f"  Utilization: {health['utilization']:.1%}")

        # -----------------------------------------------------------
        # Cleanup
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Cleanup")
        print("-" * 40)

        await pool.close()
        print("Pool closed")

        print("\n" + "=" * 60)
        print("All async examples completed!")
        print("=" * 60)

    finally:
        # Clean up temporary database file
        try:
            os.unlink(db_path)
        except OSError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
