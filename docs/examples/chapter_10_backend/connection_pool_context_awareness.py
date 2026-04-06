#!/usr/bin/env python3
"""
Example: Connection Pool Context Awareness

This example demonstrates how context awareness works with connection pools,
allowing classes to sense the current pool, connection, and transaction.

Run with: python context_awareness.py
"""

import tempfile
import os

from rhosocial.activerecord.connection.pool import (
    PoolConfig,
    BackendPool,
    get_current_pool,
    get_current_transaction_backend,
    get_current_connection_backend,
    get_current_backend,
)
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


class UserRepository:
    """Repository that uses context-aware database operations."""

    def find_by_id(self, user_id: int):
        """Find user by ID using the current context backend."""
        backend = get_current_backend()
        if backend is None:
            raise RuntimeError("No connection in current context")

        options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = backend.execute(
            "SELECT * FROM users WHERE id = ?",
            [user_id],
            options=options
        )
        return result.data[0] if result.data else None

    def create(self, name: str, email: str) -> int:
        """Create a new user."""
        backend = get_current_backend()
        if backend is None:
            raise RuntimeError("No connection in current context")

        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            [name, email],
            options=options
        )

        # Get the last insert ID
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = backend.execute("SELECT last_insert_rowid() as id", [], options=options)
        return result.data[0]['id']

    def count(self) -> int:
        """Count all users."""
        backend = get_current_backend()
        if backend is None:
            raise RuntimeError("No connection in current context")

        options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = backend.execute("SELECT COUNT(*) as count FROM users", [], options=options)
        return result.data[0]['count']


class OrderRepository:
    """Repository for orders that uses context-aware operations."""

    def create(self, user_id: int, amount: float) -> int:
        """Create a new order."""
        backend = get_current_backend()
        if backend is None:
            raise RuntimeError("No connection in current context")

        options = ExecutionOptions(stmt_type=StatementType.DML)
        backend.execute(
            "INSERT INTO orders (user_id, amount) VALUES (?, ?)",
            [user_id, amount],
            options=options
        )

        options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = backend.execute("SELECT last_insert_rowid() as id", [], options=options)
        return result.data[0]['id']

    def find_by_user(self, user_id: int):
        """Find all orders for a user."""
        backend = get_current_backend()
        if backend is None:
            raise RuntimeError("No connection in current context")

        options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = backend.execute(
            "SELECT * FROM orders WHERE user_id = ?",
            [user_id],
            options=options
        )
        return result.data


class OrderService:
    """Service that orchestrates user and order operations."""

    def __init__(self):
        self.user_repo = UserRepository()
        self.order_repo = OrderRepository()

    def create_user_with_order(self, name: str, email: str, amount: float):
        """
        Create a user and their first order in a single transaction.
        Uses context-aware repositories.
        """
        # Verify we're in a transaction context
        tx_backend = get_current_transaction_backend()
        if tx_backend is None:
            raise RuntimeError("Must be called within transaction context")

        print(f"  Creating user '{name}' with email '{email}'...")
        user_id = self.user_repo.create(name, email)
        print(f"  User created with ID: {user_id}")

        print(f"  Creating order for user {user_id} with amount ${amount}...")
        order_id = self.order_repo.create(user_id, amount)
        print(f"  Order created with ID: {order_id}")

        return user_id, order_id

    def get_user_orders(self, user_id: int):
        """Get all orders for a user."""
        user = self.user_repo.find_by_id(user_id)
        orders = self.order_repo.find_by_user(user_id)
        return user, orders


def print_context_state(label: str):
    """Helper to print current context state."""
    pool = get_current_pool()
    tx_backend = get_current_transaction_backend()
    conn_backend = get_current_connection_backend()
    current_backend = get_current_backend()

    print(f"\n{label}:")
    print(f"  Pool: {pool is not None}")
    print(f"  Transaction Backend: {tx_backend is not None}")
    print(f"  Connection Backend: {conn_backend is not None}")
    print(f"  Current Backend: {current_backend is not None}")


def main():
    print("=" * 60)
    print("Connection Pool - Context Awareness Examples")
    print("=" * 60)

    # Use a temporary file database so all connections share the same data
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    db_path = temp_db.name

    try:
        # Setup
        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(database=db_path)
        )
        pool = BackendPool(config)

        # Create tables
        with pool.connection() as backend:
            options = ExecutionOptions(stmt_type=StatementType.DDL)
            backend.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE
                )
            """, [], options=options)
            backend.execute("""
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """, [], options=options)

        # -----------------------------------------------------------
        # Example 1: Pool context
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 1: Pool Context")
        print("-" * 40)

        print_context_state("Outside pool context")

        with pool.context():
            print_context_state("Inside pool context")
            assert get_current_pool() is pool
            print("\nPool is accessible inside context!")

        print_context_state("Outside pool context again")

        # -----------------------------------------------------------
        # Example 2: Connection context
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 2: Connection Context")
        print("-" * 40)

        with pool.context():
            print_context_state("In pool context, no connection")

            with pool.connection() as backend:
                print_context_state("In connection context")

                # Repository can use the connection via context
                user_repo = UserRepository()

                # Direct SQL for demo
                options = ExecutionOptions(stmt_type=StatementType.DML)
                backend.execute("INSERT INTO users (name, email) VALUES (?, ?)", ["Demo", "demo@example.com"], options=options)

                # Repository method
                user = user_repo.find_by_id(1)
                print(f"\nFound user via repository: {user}")

            print_context_state("After connection context")

        # -----------------------------------------------------------
        # Example 3: Transaction context
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 3: Transaction Context (Both TX and Connection)")
        print("-" * 40)

        with pool.context():
            print_context_state("In pool context")

            with pool.transaction() as backend:
                print_context_state("In transaction context")

                # Both transaction and connection are set
                tx = get_current_transaction_backend()
                conn = get_current_connection_backend()
                assert tx is backend
                assert conn is backend
                print("\nTransaction and connection are the same backend!")

                # Execute some operations
                options = ExecutionOptions(stmt_type=StatementType.DML)
                backend.execute("INSERT INTO users (name, email) VALUES (?, ?)", ["Alice", "alice@example.com"], options=options)
                print("Inserted user Alice")

            print_context_state("After transaction (committed)")

        # -----------------------------------------------------------
        # Example 4: Nested contexts (connection reuse)
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 4: Nested Contexts (Connection Reuse)")
        print("-" * 40)

        with pool.connection() as outer_conn:
            outer_id = id(outer_conn)
            print(f"Outer connection ID: {outer_id}")

            with pool.connection() as inner_conn:
                inner_id = id(inner_conn)
                print(f"Inner connection ID: {inner_id}")

                if outer_id == inner_id:
                    print("\nSame connection reused! No connection leak.")
                else:
                    print("\nDifferent connections - unexpected!")

        # -----------------------------------------------------------
        # Example 5: Service with context-aware repositories
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 5: Service with Context-Aware Repositories")
        print("-" * 40)

        service = OrderService()

        with pool.context():
            print("Creating user with order in transaction:")
            with pool.transaction():
                user_id, order_id = service.create_user_with_order(
                    name="Bob",
                    email="bob@example.com",
                    amount=99.99
                )
                print(f"\nUser ID: {user_id}, Order ID: {order_id}")
                # Auto commit

            print("\nVerifying committed data:")
            with pool.connection():
                user, orders = service.get_user_orders(user_id)
                print(f"User: {user}")
                print(f"Orders: {orders}")

        # -----------------------------------------------------------
        # Example 6: Transaction rollback on error
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Example 6: Transaction Rollback on Error")
        print("-" * 40)

        with pool.context():
            print("Attempting to create user (will fail):")
            try:
                with pool.transaction():
                    options = ExecutionOptions(stmt_type=StatementType.DML)
                    backend = get_current_backend()

                    # Insert user
                    backend.execute("INSERT INTO users (name, email) VALUES (?, ?)", ["Charlie", "charlie@example.com"], options=options)
                    print("  User inserted...")

                    # Simulate error
                    raise ValueError("Simulated error during order creation")

            except ValueError as e:
                print(f"  Error occurred: {e}")
                print("  Transaction rolled back!")

            print("\nVerifying rollback (Charlie should not exist):")
            with pool.connection():
                options = ExecutionOptions(stmt_type=StatementType.DQL)
                result = backend.execute("SELECT name FROM users WHERE name = ?", ["Charlie"], options=options)
                if result.data:
                    print("  ERROR: Charlie found - rollback failed!")
                else:
                    print("  Verified: Charlie not found - rollback successful!")

        # -----------------------------------------------------------
        # Cleanup
        # -----------------------------------------------------------
        print("\n" + "-" * 40)
        print("Cleanup")
        print("-" * 40)

        pool.close()
        print("Pool closed")

        print("\n" + "=" * 60)
        print("All context awareness examples completed!")
        print("=" * 60)

    finally:
        # Clean up temporary database file
        try:
            os.unlink(db_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
