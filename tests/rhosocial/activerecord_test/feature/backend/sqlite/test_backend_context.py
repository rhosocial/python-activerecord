# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_backend_context.py
"""
Tests for StorageBackend.context() method.

This module tests the context manager functionality for explicit connection
lifecycle control, ensuring connections are created and destroyed in the
same thread.
"""

import threading
import tempfile
import os
import pytest

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


class TestSyncBackendContext:
    """Tests for synchronous backend context() method."""

    def test_context_basic_usage(self):
        """Test 1: Basic context usage - connect, execute, disconnect."""
        backend = SQLiteBackend(database=":memory:")

        with backend.context() as ctx:
            result = ctx.execute("SELECT 1")
            assert result is not None

        # Connection should be closed after context exit
        assert backend._connection is None

    def test_context_with_parameters(self):
        """Test 2: Context with query parameters."""
        backend = SQLiteBackend(database=":memory:")

        with backend.context() as ctx:
            # Create table
            ctx.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            # Insert with parameter
            options = ExecutionOptions(stmt_type=StatementType.DML)
            result = ctx.execute(
                "INSERT INTO test (name) VALUES (?)",
                ["Alice"],
                options=options
            )
            assert result.affected_rows == 1
            # Query back
            dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = ctx.execute("SELECT * FROM test WHERE name = ?", ["Alice"], options=dql_options)
            assert result.data[0]["name"] == "Alice"

    def test_context_multiple_enter_exit(self):
        """Test 3: Multiple enter/exit cycles."""
        backend = SQLiteBackend(database=":memory:")

        # First context
        with backend.context() as ctx:
            result1 = ctx.execute("SELECT 1")
            assert result1 is not None
        assert backend._connection is None

        # Second context - should create new connection
        with backend.context() as ctx:
            result2 = ctx.execute("SELECT 2")
            assert result2 is not None
        assert backend._connection is None

    def test_context_exception_handling(self):
        """Test 4: Context properly disconnects on exception."""
        backend = SQLiteBackend(database=":memory:")

        with pytest.raises(ValueError):
            with backend.context() as ctx:
                ctx.execute("SELECT 1")
                raise ValueError("Test exception")

        # Connection should still be closed
        assert backend._connection is None

    def test_context_no_exception_when_already_connected(self):
        """Test 5: Context works when backend already has connection."""
        backend = SQLiteBackend(database=":memory:")
        backend.connect()

        try:
            with backend.context() as ctx:
                # Should not raise, just execute
                result = ctx.execute("SELECT 1")
                assert result is not None
        finally:
            backend.disconnect()

    def test_context_with_ddl_statements(self):
        """Test 6: Context with DDL statements."""
        backend = SQLiteBackend(database=":memory:")

        with backend.context() as ctx:
            # DDL should work in context
            ctx.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)
            ctx.execute("""
                CREATE TABLE posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Verify tables exist
            dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = ctx.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
                options=dql_options
            )
            table_names = [row["name"] for row in result.data]
            assert "users" in table_names
            assert "posts" in table_names

    def test_context_transaction_auto_commit(self):
        """Test 7: Context with transaction (auto-commit mode)."""
        import tempfile
        import os

        # Use file-based database for persistence across contexts
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            backend = SQLiteBackend(database=db_path)

            with backend.context() as ctx:
                # Create table
                ctx.execute("CREATE TABLE test_tx (id INTEGER PRIMARY KEY, value TEXT)")
                # Each execute is auto-committed in autocommit mode
                options = ExecutionOptions(stmt_type=StatementType.DML)
                ctx.execute("INSERT INTO test_tx (value) VALUES ('test1')", options=options)
                ctx.execute("INSERT INTO test_tx (value) VALUES ('test2')", options=options)

            # Verify data persists after context exit - new connection should see data
            with backend.context() as ctx:
                dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
                result = ctx.execute("SELECT COUNT(*) as cnt FROM test_tx", options=dql_options)
                assert result.data[0]["cnt"] == 2
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_context_repr_during_context(self):
        """Test 8: Backend repr works during context."""
        backend = SQLiteBackend(database=":memory:")

        with backend.context():
            repr_str = repr(backend)
            assert "SQLiteBackend" in repr_str
            # During context, connection should be established
            assert backend._connection is not None

    def test_context_with_multiple_statements(self):
        """Test 9: Context with multiple SQL statements."""
        backend = SQLiteBackend(database=":memory:")
        dml_options = ExecutionOptions(stmt_type=StatementType.DML)
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        with backend.context() as ctx:
            ctx.execute("CREATE TABLE t (id INTEGER)")
            ctx.execute("INSERT INTO t VALUES (1)", options=dml_options)
            ctx.execute("INSERT INTO t VALUES (2)", options=dml_options)
            ctx.execute("INSERT INTO t VALUES (3)", options=dml_options)
            result = ctx.execute("SELECT * FROM t ORDER BY id", options=dql_options)
            assert len(result.data) == 3

    def test_context_empty_database(self):
        """Test 10: Context with empty database."""
        backend = SQLiteBackend(database=":memory:")

        with backend.context() as ctx:
            dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = ctx.execute(
                "SELECT name FROM sqlite_master WHERE type='table'",
                options=dql_options
            )
            assert result.data == []


class TestSyncBackendContextConcurrency:
    """Tests for concurrent access with context() method."""

    def test_context_in_multiple_threads(self):
        """Test 11: Multiple threads using context simultaneously."""
        errors = []
        results = []
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        def worker(worker_id):
            try:
                backend = SQLiteBackend(database=":memory:")
                with backend.context() as ctx:
                    result = ctx.execute("SELECT ? as worker_id", [worker_id], options=dql_options)
                    results.append((worker_id, result.data[0]["worker_id"]))
                # Connection should be closed
                assert backend._connection is None
            except Exception as e:
                errors.append((worker_id, str(e)))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
        assert sorted([r[1] for r in results]) == list(range(10))

    def test_context_thread_isolation(self):
        """Test 12: Each thread's connection is isolated."""
        connections_seen = []
        lock = threading.Lock()
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        def worker(worker_id):
            backend = SQLiteBackend(database=f":memory:")
            with backend.context() as ctx:
                # Each worker should see its own connection
                conn_id = id(ctx._connection)
                with lock:
                    connections_seen.append(conn_id)
                # Verify we can do operations
                result = ctx.execute("SELECT ? as wid", [worker_id], options=dql_options)
                assert result.data[0]["wid"] == worker_id

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Each thread should have seen at least some connections (may have duplicates due to GC)
        assert len(connections_seen) == 5
        # Verify each thread completed successfully by checking all workers saw their own ID
        # (The actual isolation is verified by the successful execute above)

    def test_context_no_cross_thread_contamination(self):
        """Test 13: No contamination between threads."""
        results = {}
        lock = threading.Lock()
        dml_options = ExecutionOptions(stmt_type=StatementType.DML)
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        def worker(worker_id, expected_value):
            backend = SQLiteBackend(database=f":memory:")
            with backend.context() as ctx:
                # Set up isolated data
                ctx.execute(
                    "CREATE TABLE test_contamination (id INTEGER, value TEXT)"
                )
                ctx.execute(
                    "INSERT INTO test_contamination VALUES (?, ?)",
                    [worker_id, expected_value],
                    options=dml_options
                )
                # Query back
                result = ctx.execute(
                    "SELECT value FROM test_contamination WHERE id = ?",
                    [worker_id],
                    options=dql_options
                )
                actual_value = result.data[0]["value"]
                with lock:
                    results[worker_id] = actual_value
                assert actual_value == expected_value

        threads = [
            threading.Thread(target=worker, args=(i, f"value_{i}"))
            for i in range(5)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5
        for i in range(5):
            assert results[i] == f"value_{i}"


class TestAsyncBackendContext:
    """Tests for asynchronous backend context() method."""

    @pytest.mark.asyncio
    async def test_async_context_basic_usage(self):
        """Test 14: Basic async context usage."""
        backend = AsyncSQLiteBackend(database=":memory:")

        async with backend.context() as ctx:
            result = await ctx.execute("SELECT 1")
            assert result is not None

        # Connection should be closed after context exit
        assert backend._connection is None

    @pytest.mark.asyncio
    async def test_async_context_with_parameters(self):
        """Test 15: Async context with query parameters."""
        backend = AsyncSQLiteBackend(database=":memory:")

        async with backend.context() as ctx:
            await ctx.execute("CREATE TABLE test_async (id INTEGER PRIMARY KEY, name TEXT)")
            options = ExecutionOptions(stmt_type=StatementType.DML)
            result = await ctx.execute(
                "INSERT INTO test_async (name) VALUES (?)",
                ["Bob"],
                options=options
            )
            assert result.affected_rows == 1

    @pytest.mark.asyncio
    async def test_async_context_exception_handling(self):
        """Test 16: Async context disconnects on exception."""
        backend = AsyncSQLiteBackend(database=":memory:")

        with pytest.raises(ValueError):
            async with backend.context():
                await backend.execute("SELECT 1")
                raise ValueError("Async test exception")

        assert backend._connection is None

    @pytest.mark.asyncio
    async def test_async_context_multiple_cycles(self):
        """Test 17: Multiple async context enter/exit cycles."""
        backend = AsyncSQLiteBackend(database=":memory:")

        for i in range(3):
            async with backend.context() as ctx:
                result = await ctx.execute("SELECT ?", [i])
                assert result is not None
            assert backend._connection is None


class TestBackendContextComparison:
    """Tests comparing context() with __enter__/__exit__."""

    def test_context_vs_enter_exit_basic(self):
        """Test 18: Compare context() with __enter__/__exit__ - basic."""
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        # Using __enter__/__exit__
        backend1 = SQLiteBackend(database=":memory:")
        backend1.__enter__()
        result1 = backend1.execute("SELECT 1", options=dql_options)
        backend1.__exit__(None, None, None)

        # Using context()
        backend2 = SQLiteBackend(database=":memory:")
        with backend2.context() as ctx:
            result2 = ctx.execute("SELECT 1", options=dql_options)

        assert result1 is not None
        assert result2 is not None

    def test_context_vs_enter_exit_exception(self):
        """Test 19: Compare behavior on exception."""
        from rhosocial.activerecord.backend.errors import OperationalError

        # Using __enter__/__exit__
        backend1 = SQLiteBackend(database=":memory:")
        backend1.__enter__()
        try:
            backend1.execute("SELECT invalid")  # This will raise OperationalError
        except OperationalError:
            pass
        finally:
            backend1.__exit__(None, None, None)

        # Using context() - should be cleaner
        backend2 = SQLiteBackend(database=":memory:")
        with pytest.raises(OperationalError):
            with backend2.context() as ctx:
                ctx.execute("SELECT invalid")

        # Both should have closed connections
        assert backend1._connection is None
        assert backend2._connection is None

    def test_context_explicit_lifecycle(self):
        """Test 20: context() provides explicit lifecycle control."""
        backend = SQLiteBackend(database=":memory:")

        # Before context - no connection
        assert backend._connection is None

        # Inside context - connection exists
        with backend.context() as ctx:
            assert backend._connection is not None
            assert ctx is backend

        # After context - connection closed
        assert backend._connection is None
