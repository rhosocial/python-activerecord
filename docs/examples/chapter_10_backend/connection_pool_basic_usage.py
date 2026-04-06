#!/usr/bin/env python3
"""
Example: Basic Connection Pool Usage

This example demonstrates the fundamental usage patterns for connection pools,
including manual acquire/release, context managers, and transactions.

Run with: python basic_usage.py
"""

import tempfile
import os

from rhosocial.activerecord.connection.pool import PoolConfig, BackendPool
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


def main():
    print("=" * 60)
    print("Connection Pool - Basic Usage Examples")
    print("=" * 60)

    # Use a temporary file database so all connections share the same data
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    db_path = temp_db.name

    try:
        # Create connection pool
        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(database=db_path)
        )
        pool = BackendPool(config)

        print(f"\nPool created: {pool}")
        print(f"Initial stats: {pool.get_stats()}")

        # -----------------------------------------------------------
        # Example 1: Manual acquire/release
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 1: Manual acquire/release")
        print("-" * 40)

        backend = pool.acquire()
        try:
            # Create a test table
            options = ExecutionOptions(stmt_type=StatementType.DDL)
            backend.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)", [], options=options)

            options = ExecutionOptions(stmt_type=StatementType.DML)
            backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",), options=options)
            backend.execute("INSERT INTO users (name) VALUES (?)", ("Bob",), options=options)

            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = backend.execute("SELECT COUNT(*) FROM users", [], options=options)
            print(f"User count: {result.data[0]['COUNT(*)']}")
        finally:
            pool.release(backend)

        print(f"After release: {pool.get_stats()}")

        # -----------------------------------------------------------
        # Example 2: Connection context manager
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 2: Connection context manager")
        print("-" * 40)

        with pool.connection() as backend:
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = backend.execute("SELECT * FROM users", [], options=options)
            print(f"Users: {[row for row in result.data]}")

        print(f"Connection automatically released")

        # -----------------------------------------------------------
        # Example 3: Transaction context manager
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 3: Transaction context manager")
        print("-" * 40)

        # Successful transaction
        try:
            with pool.transaction() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DML)
                backend.execute("INSERT INTO users (name) VALUES (?)", ("Charlie",), options=options)
                print("Inserted Charlie - will be committed")
                # Auto commit on success
        except Exception as e:
            print(f"Transaction failed: {e}")

        # Verify insert
        with pool.connection() as backend:
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = backend.execute("SELECT name FROM users ORDER BY id", [], options=options)
            print(f"All users after commit: {[row['name'] for row in result.data]}")

        # Failed transaction (rollback)
        print("\nSimulating transaction failure:")
        try:
            with pool.transaction() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DML)
                backend.execute("INSERT INTO users (name) VALUES (?)", ("David",), options=options)
                print("Inserted David - but will be rolled back")
                raise ValueError("Simulated error")
        except ValueError:
            print("Transaction rolled back due to error")

        # Verify rollback
        with pool.connection() as backend:
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = backend.execute("SELECT name FROM users ORDER BY id", [], options=options)
            print(f"Users after rollback (David not present): {[row['name'] for row in result.data]}")

        # -----------------------------------------------------------
        # Example 4: Statistics and monitoring
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 4: Statistics and monitoring")
        print("-" * 40)

        stats = pool.get_stats()
        print(f"Total connections created: {stats.total_created}")
        print(f"Total acquired: {stats.total_acquired}")
        print(f"Total released: {stats.total_released}")
        print(f"Current available: {stats.current_available}")
        print(f"Current in use: {stats.current_in_use}")
        print(f"Utilization rate: {stats.utilization_rate:.1%}")

        health = pool.health_check()
        print(f"\nHealth check:")
        print(f"  Healthy: {health['healthy']}")
        print(f"  Closed: {health['closed']}")
        print(f"  Stats: {health['stats']}")

        # -----------------------------------------------------------
        # Cleanup
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Cleanup")
        print("-" * 40)

        pool.close()
        print(f"Pool closed: {pool.is_closed}")

        print("\n" + "=" * 60)
        print("All examples completed!")
        print("=" * 60)

    finally:
        # Clean up temporary database file
        try:
            os.unlink(db_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
