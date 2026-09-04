# tests/rhosocial/activerecord_test/feature/backend/backend/test_backend_context_async.py
"""Async twin of test_backend_context.py for AsyncSQLiteBackend.context()."""

import asyncio
import os
import tempfile

import pytest

from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


class TestAsyncSyncBackendContext:
    """Async equivalents for synchronous backend context() tests."""

    @pytest.mark.asyncio
    async def test_context_basic_usage(self):
        """Test 1: Basic context usage - connect, execute, disconnect."""
        backend = AsyncSQLiteBackend(database=":memory:")

        async with backend.context() as ctx:
            result = await ctx.execute("SELECT 1")
            assert result is not None

        assert backend._connection is None

    @pytest.mark.asyncio
    async def test_context_with_parameters(self):
        """Test 2: Context with query parameters."""
        backend = AsyncSQLiteBackend(database=":memory:")

        async with backend.context() as ctx:
            await ctx.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
            options = ExecutionOptions(stmt_type=StatementType.DML)
            result = await ctx.execute("INSERT INTO test (name) VALUES (?)", ["Alice"], options=options)
            assert result.affected_rows == 1
            dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = await ctx.execute("SELECT * FROM test WHERE name = ?", ["Alice"], options=dql_options)
            assert result.data[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_context_multiple_enter_exit(self):
        """Test 3: Multiple enter/exit cycles."""
        backend = AsyncSQLiteBackend(database=":memory:")

        async with backend.context() as ctx:
            result1 = await ctx.execute("SELECT 1")
            assert result1 is not None
        assert backend._connection is None

        async with backend.context() as ctx:
            result2 = await ctx.execute("SELECT 2")
            assert result2 is not None
        assert backend._connection is None

    @pytest.mark.asyncio
    async def test_context_exception_handling(self):
        """Test 4: Context properly disconnects on exception."""
        backend = AsyncSQLiteBackend(database=":memory:")

        with pytest.raises(ValueError):
            async with backend.context() as ctx:
                await ctx.execute("SELECT 1")
                raise ValueError("Test exception")

        assert backend._connection is None

    @pytest.mark.asyncio
    async def test_context_no_exception_when_already_connected(self):
        """Test 5: Context works when backend already has connection."""
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()

        try:
            async with backend.context() as ctx:
                result = await ctx.execute("SELECT 1")
                assert result is not None
        finally:
            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_context_with_ddl_statements(self):
        """Test 6: Context with DDL statements."""
        backend = AsyncSQLiteBackend(database=":memory:")

        async with backend.context() as ctx:
            await ctx.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)
            await ctx.execute("""
                CREATE TABLE posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = await ctx.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
                                       options=dql_options)
            table_names = [row["name"] for row in result.data]
            assert "users" in table_names
            assert "posts" in table_names

    @pytest.mark.asyncio
    async def test_context_transaction_auto_commit(self):
        """Test 7: Context with transaction (auto-commit mode)."""
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            backend = AsyncSQLiteBackend(database=db_path)

            async with backend.context() as ctx:
                await ctx.execute("CREATE TABLE test_tx (id INTEGER PRIMARY KEY, value TEXT)")
                options = ExecutionOptions(stmt_type=StatementType.DML)
                await ctx.execute("INSERT INTO test_tx (value) VALUES ('test1')", options=options)
                await ctx.execute("INSERT INTO test_tx (value) VALUES ('test2')", options=options)

            async with backend.context() as ctx:
                dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
                result = await ctx.execute("SELECT COUNT(*) as cnt FROM test_tx", options=dql_options)
                assert result.data[0]["cnt"] == 2
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_context_repr_during_context(self):
        """Test 8: Backend repr works during context."""
        backend = AsyncSQLiteBackend(database=":memory:")

        async with backend.context():
            repr_str = repr(backend)
            assert "AsyncSQLiteBackend" in repr_str
            assert backend._connection is not None

    @pytest.mark.asyncio
    async def test_context_with_multiple_statements(self):
        """Test 9: Context with multiple SQL statements."""
        backend = AsyncSQLiteBackend(database=":memory:")
        dml_options = ExecutionOptions(stmt_type=StatementType.DML)
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        async with backend.context() as ctx:
            await ctx.execute("CREATE TABLE t (id INTEGER)")
            await ctx.execute("INSERT INTO t VALUES (1)", options=dml_options)
            await ctx.execute("INSERT INTO t VALUES (2)", options=dml_options)
            await ctx.execute("INSERT INTO t VALUES (3)", options=dml_options)
            result = await ctx.execute("SELECT * FROM t ORDER BY id", options=dql_options)
            assert len(result.data) == 3

    @pytest.mark.asyncio
    async def test_context_empty_database(self):
        """Test 10: Context with empty database."""
        backend = AsyncSQLiteBackend(database=":memory:")

        async with backend.context() as ctx:
            dql_options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = await ctx.execute("SELECT name FROM sqlite_master WHERE type='table'", options=dql_options)
            assert result.data == []


class TestAsyncSyncBackendContextConcurrency:
    """Async task-based equivalents for the concurrency context() tests."""

    @pytest.mark.asyncio
    async def test_context_in_multiple_threads(self):
        """Test 11: Multiple tasks using context simultaneously."""
        errors = []
        results = []
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        async def worker(worker_id):
            try:
                backend = AsyncSQLiteBackend(database=":memory:")
                async with backend.context() as ctx:
                    result = await ctx.execute("SELECT ? as worker_id", [worker_id], options=dql_options)
                    results.append((worker_id, result.data[0]["worker_id"]))
                assert backend._connection is None
            except Exception as e:
                errors.append((worker_id, str(e)))

        await asyncio.gather(*(worker(i) for i in range(10)))

        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10
        assert sorted([r[1] for r in results]) == list(range(10))

    @pytest.mark.asyncio
    async def test_context_thread_isolation(self):
        """Test 12: Each task's connection is isolated."""
        connections_seen = []
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        async def worker(worker_id):
            backend = AsyncSQLiteBackend(database=":memory:")
            async with backend.context() as ctx:
                conn_id = id(ctx._connection)
                connections_seen.append(conn_id)
                result = await ctx.execute("SELECT ? as wid", [worker_id], options=dql_options)
                assert result.data[0]["wid"] == worker_id

        await asyncio.gather(*(worker(i) for i in range(5)))

        assert len(connections_seen) == 5

    @pytest.mark.asyncio
    async def test_context_no_cross_thread_contamination(self):
        """Test 13: No contamination between tasks."""
        results = {}
        dml_options = ExecutionOptions(stmt_type=StatementType.DML)
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        async def worker(worker_id, expected_value):
            backend = AsyncSQLiteBackend(database=":memory:")
            async with backend.context() as ctx:
                await ctx.execute("CREATE TABLE test_contamination (id INTEGER, value TEXT)")
                await ctx.execute("INSERT INTO test_contamination VALUES (?, ?)", [worker_id, expected_value],
                                  options=dml_options)
                result = await ctx.execute("SELECT value FROM test_contamination WHERE id = ?", [worker_id],
                                           options=dql_options)
                actual_value = result.data[0]["value"]
                results[worker_id] = actual_value
                assert actual_value == expected_value

        await asyncio.gather(*(worker(i, f"value_{i}") for i in range(5)))

        assert len(results) == 5
        for i in range(5):
            assert results[i] == f"value_{i}"


class TestAsyncAsyncBackendContext:
    """Async twin of the async context() tests in the sync file."""

    @pytest.mark.asyncio
    async def test_async_context_basic_usage(self):
        """Test 14: Basic async context usage."""
        backend = AsyncSQLiteBackend(database=":memory:")

        async with backend.context() as ctx:
            result = await ctx.execute("SELECT 1")
            assert result is not None

        assert backend._connection is None

    @pytest.mark.asyncio
    async def test_async_context_with_parameters(self):
        """Test 15: Async context with query parameters."""
        backend = AsyncSQLiteBackend(database=":memory:")

        async with backend.context() as ctx:
            await ctx.execute("CREATE TABLE test_async (id INTEGER PRIMARY KEY, name TEXT)")
            options = ExecutionOptions(stmt_type=StatementType.DML)
            result = await ctx.execute("INSERT INTO test_async (name) VALUES (?)", ["Bob"], options=options)
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


class TestAsyncBackendContextComparison:
    """Async twins comparing context() with __aenter__/__aexit__."""

    @pytest.mark.asyncio
    async def test_context_vs_enter_exit_basic(self):
        """Test 18: Compare context() with __aenter__/__aexit__ - basic."""
        dql_options = ExecutionOptions(stmt_type=StatementType.DQL)

        backend1 = AsyncSQLiteBackend(database=":memory:")
        await backend1.__aenter__()
        result1 = await backend1.execute("SELECT 1", options=dql_options)
        await backend1.__aexit__(None, None, None)

        backend2 = AsyncSQLiteBackend(database=":memory:")
        async with backend2.context() as ctx:
            result2 = await ctx.execute("SELECT 1", options=dql_options)

        assert result1 is not None
        assert result2 is not None

    @pytest.mark.asyncio
    async def test_context_vs_enter_exit_exception(self):
        """Test 19: Compare behavior on exception."""
        from rhosocial.activerecord.backend.errors import OperationalError

        backend1 = AsyncSQLiteBackend(database=":memory:")
        await backend1.__aenter__()
        try:
            await backend1.execute("SELECT invalid")
        except OperationalError:
            pass
        finally:
            await backend1.__aexit__(None, None, None)

        backend2 = AsyncSQLiteBackend(database=":memory:")
        with pytest.raises(OperationalError):
            async with backend2.context() as ctx:
                await ctx.execute("SELECT invalid")

        assert backend1._connection is None
        assert backend2._connection is None

    @pytest.mark.asyncio
    async def test_context_explicit_lifecycle(self):
        """Test 20: context() provides explicit lifecycle control."""
        backend = AsyncSQLiteBackend(database=":memory:")

        assert backend._connection is None

        async with backend.context() as ctx:
            assert backend._connection is not None
            assert ctx is backend

        assert backend._connection is None
