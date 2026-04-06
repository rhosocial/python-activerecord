# tests/rhosocial/activerecord_test/feature/connection/test_active_record_context_awareness.py
"""Test ActiveRecord context awareness with connection pool."""

from typing import Optional

import pytest

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.connection.pool import (
    BackendPool,
    AsyncBackendPool,
    PoolConfig,
    get_current_backend,
    get_current_async_backend,
    get_current_transaction_backend,
    get_current_async_transaction_backend,
)


def execute_sql(backend, sql: str, params=None):
    """Helper to execute SQL with proper options."""
    options = ExecutionOptions(stmt_type=StatementType.DDL if 'CREATE' in sql.upper() else StatementType.DML)
    return backend.execute(sql, params or (), options=options)


async def async_execute_sql(backend, sql: str, params=None):
    """Helper to execute SQL asynchronously with proper options."""
    options = ExecutionOptions(stmt_type=StatementType.DDL if 'CREATE' in sql.upper() else StatementType.DML)
    return await backend.execute(sql, params or (), options=options)


# Sync Test Model (named to avoid pytest collection warning)
class ContextTestUser(IntegerPKMixin, ActiveRecord):
    """Test User model for context awareness tests."""
    __table_name__ = "ctx_test_users"

    id: Optional[int] = None
    name: str
    email: str


# Async Test Model
class AsyncContextTestUser(IntegerPKMixin, AsyncActiveRecord):
    """Test Async User model for context awareness tests."""
    __table_name__ = "async_ctx_test_users"

    id: Optional[int] = None
    name: str
    email: str


class TestSyncActiveRecordContextAwareness:
    """Test synchronous ActiveRecord context awareness."""

    def test_backend_returns_class_backend_without_context(self):
        """Test that backend() returns class backend when no context is set."""
        ContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

        # Without any context, should return class backend
        backend = ContextTestUser.backend()
        assert backend is ContextTestUser.__backend__

    def test_backend_returns_context_backend_in_connection(self):
        """Test that backend() returns context backend in connection context."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

        try:
            ContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

            with pool.context():
                with pool.connection() as conn_backend:
                    # Should return connection backend, not class backend
                    model_backend = ContextTestUser.backend()
                    assert model_backend is conn_backend
                    assert model_backend is not ContextTestUser.__backend__
        finally:
            pool.close()

    def test_backend_returns_context_backend_in_transaction(self):
        """Test that backend() returns context backend in transaction context."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

        try:
            ContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

            with pool.context():
                with pool.transaction() as tx_backend:
                    # Should return transaction backend
                    model_backend = ContextTestUser.backend()
                    assert model_backend is tx_backend

                    # Verify it's the same as context functions
                    assert get_current_backend() is tx_backend
                    assert get_current_transaction_backend() is tx_backend
        finally:
            pool.close()

    def test_crud_in_transaction_context(self):
        """Test CRUD operations work in transaction context."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

        try:
            ContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

            # Create test table
            with pool.connection() as backend:
                execute_sql(backend, """
                    CREATE TABLE ctx_test_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL
                    )
                """)

            with pool.transaction() as backend:
                # Insert
                execute_sql(backend, "INSERT INTO ctx_test_users (name, email) VALUES (?, ?)", ("Alice", "alice@test.com"))
                execute_sql(backend, "INSERT INTO ctx_test_users (name, email) VALUES (?, ?)", ("Bob", "bob@test.com"))

            # Verify committed
            with pool.connection() as backend:
                result = backend.fetch_all("SELECT * FROM ctx_test_users")
                assert len(result) == 2
        finally:
            pool.close()

    def test_transaction_rollback_on_error(self):
        """Test that transaction rolls back on error."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

        try:
            ContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

            # Create test table
            with pool.connection() as backend:
                execute_sql(backend, """
                    CREATE TABLE ctx_test_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL
                    )
                """)

            # Insert initial data
            with pool.transaction() as backend:
                execute_sql(backend, "INSERT INTO ctx_test_users (name, email) VALUES (?, ?)", ("Alice", "alice@test.com"))

            # Attempt to insert but fail
            try:
                with pool.transaction() as backend:
                    execute_sql(backend, "INSERT INTO ctx_test_users (name, email) VALUES (?, ?)", ("Bob", "bob@test.com"))
                    raise ValueError("Simulated error")
            except ValueError:
                pass

            # Verify rollback
            with pool.connection() as backend:
                result = backend.fetch_all("SELECT * FROM ctx_test_users")
                assert len(result) == 1  # Only Alice, Bob was rolled back
        finally:
            pool.close()

    def test_nested_connection_contexts_reuse(self):
        """Test that nested connection contexts reuse the same backend."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

        try:
            ContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

            with pool.connection() as outer_conn:
                outer_backend = ContextTestUser.backend()
                assert outer_backend is outer_conn

                with pool.connection() as inner_conn:
                    inner_backend = ContextTestUser.backend()
                    # Should reuse the same connection
                    assert inner_backend is outer_backend
                    assert inner_conn is outer_conn
        finally:
            pool.close()

    def test_active_query_backend_context_awareness(self):
        """Test that ActiveQuery.backend() is context aware."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

        try:
            ContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

            with pool.connection() as conn_backend:
                query = ContextTestUser.query()
                query_backend = query.backend()
                assert query_backend is conn_backend
        finally:
            pool.close()


class TestAsyncActiveRecordContextAwareness:
    """Test asynchronous ActiveRecord context awareness."""

    @pytest.mark.asyncio
    async def test_backend_returns_class_backend_without_context(self):
        """Test that backend() returns class backend when no context is set."""
        await AsyncContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), AsyncSQLiteBackend)

        # Without any context, should return class backend
        backend = AsyncContextTestUser.backend()
        assert backend is AsyncContextTestUser.__backend__

        # Cleanup: disconnect the backend to avoid hanging on teardown
        await AsyncContextTestUser.__backend__.disconnect()
        AsyncContextTestUser.__backend__ = None

    @pytest.mark.asyncio
    async def test_backend_returns_context_backend_in_connection(self):
        """Test that backend() returns context backend in async connection context."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = AsyncBackendPool(config)

        try:
            await AsyncContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), AsyncSQLiteBackend)

            async with pool.context():
                async with pool.connection() as conn_backend:
                    # Should return connection backend, not class backend
                    model_backend = AsyncContextTestUser.backend()
                    assert model_backend is conn_backend
                    assert model_backend is not AsyncContextTestUser.__backend__
        finally:
            await pool.close()
            # Cleanup
            if AsyncContextTestUser.__backend__:
                await AsyncContextTestUser.__backend__.disconnect()
                AsyncContextTestUser.__backend__ = None

    @pytest.mark.asyncio
    async def test_backend_returns_context_backend_in_transaction(self):
        """Test that backend() returns context backend in async transaction context."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = AsyncBackendPool(config)

        try:
            await AsyncContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), AsyncSQLiteBackend)

            async with pool.context():
                async with pool.transaction() as tx_backend:
                    # Should return transaction backend
                    model_backend = AsyncContextTestUser.backend()
                    assert model_backend is tx_backend

                    # Verify it's the same as context functions
                    assert get_current_async_backend() is tx_backend
                    assert get_current_async_transaction_backend() is tx_backend
        finally:
            await pool.close()
            # Cleanup
            if AsyncContextTestUser.__backend__:
                await AsyncContextTestUser.__backend__.disconnect()
                AsyncContextTestUser.__backend__ = None

    @pytest.mark.asyncio
    async def test_crud_in_transaction_context(self):
        """Test CRUD operations work in async transaction context."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = AsyncBackendPool(config)

        try:
            await AsyncContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), AsyncSQLiteBackend)

            # Create test table
            async with pool.connection() as backend:
                await async_execute_sql(backend, """
                    CREATE TABLE async_ctx_test_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL
                    )
                """)

            async with pool.transaction() as backend:
                # Insert
                await async_execute_sql(backend, "INSERT INTO async_ctx_test_users (name, email) VALUES (?, ?)", ("Alice", "alice@test.com"))
                await async_execute_sql(backend, "INSERT INTO async_ctx_test_users (name, email) VALUES (?, ?)", ("Bob", "bob@test.com"))

            # Verify committed
            async with pool.connection() as backend:
                result = await backend.fetch_all("SELECT * FROM async_ctx_test_users")
                assert len(result) == 2
        finally:
            await pool.close()
            # Cleanup
            if AsyncContextTestUser.__backend__:
                await AsyncContextTestUser.__backend__.disconnect()
                AsyncContextTestUser.__backend__ = None

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self):
        """Test that async transaction rolls back on error."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = AsyncBackendPool(config)

        try:
            await AsyncContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), AsyncSQLiteBackend)

            # Create test table
            async with pool.connection() as backend:
                await async_execute_sql(backend, """
                    CREATE TABLE async_ctx_test_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL
                    )
                """)

            # Insert initial data
            async with pool.transaction() as backend:
                await async_execute_sql(backend, "INSERT INTO async_ctx_test_users (name, email) VALUES (?, ?)", ("Alice", "alice@test.com"))

            # Attempt to insert but fail
            try:
                async with pool.transaction() as backend:
                    await async_execute_sql(backend, "INSERT INTO async_ctx_test_users (name, email) VALUES (?, ?)", ("Bob", "bob@test.com"))
                    raise ValueError("Simulated error")
            except ValueError:
                pass

            # Verify rollback
            async with pool.connection() as backend:
                result = await backend.fetch_all("SELECT * FROM async_ctx_test_users")
                assert len(result) == 1  # Only Alice, Bob was rolled back
        finally:
            await pool.close()
            # Cleanup
            if AsyncContextTestUser.__backend__:
                await AsyncContextTestUser.__backend__.disconnect()
                AsyncContextTestUser.__backend__ = None

    @pytest.mark.asyncio
    async def test_nested_connection_contexts_reuse(self):
        """Test that nested async connection contexts reuse the same backend."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = AsyncBackendPool(config)

        try:
            await AsyncContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), AsyncSQLiteBackend)

            async with pool.connection() as outer_conn:
                outer_backend = AsyncContextTestUser.backend()
                assert outer_backend is outer_conn

                async with pool.connection() as inner_conn:
                    inner_backend = AsyncContextTestUser.backend()
                    # Should reuse the same connection
                    assert inner_backend is outer_backend
                    assert inner_conn is outer_conn
        finally:
            await pool.close()
            # Cleanup
            if AsyncContextTestUser.__backend__:
                await AsyncContextTestUser.__backend__.disconnect()
                AsyncContextTestUser.__backend__ = None

    @pytest.mark.asyncio
    async def test_active_query_backend_context_awareness(self):
        """Test that AsyncActiveQuery.backend() is context aware."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = AsyncBackendPool(config)

        try:
            await AsyncContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), AsyncSQLiteBackend)

            async with pool.connection() as conn_backend:
                query = AsyncContextTestUser.query()
                query_backend = query.backend()
                assert query_backend is conn_backend
        finally:
            await pool.close()
            # Cleanup
            if AsyncContextTestUser.__backend__:
                await AsyncContextTestUser.__backend__.disconnect()
                AsyncContextTestUser.__backend__ = None


class TestSyncAsyncIsolation:
    """Test that sync and async contexts are properly isolated."""

    def test_sync_backend_in_async_context_returns_none(self):
        """Test that get_current_backend() returns None without any context."""
        assert get_current_backend() is None

    @pytest.mark.asyncio
    async def test_async_backend_in_sync_context_returns_none(self):
        """Test that get_current_async_backend() returns None without any context."""
        assert get_current_async_backend() is None


class TestCTEQueryContextAwareness:
    """Test CTEQuery context awareness."""

    def test_cte_query_backend_context_awareness(self):
        """Test that CTEQuery.backend() is context aware."""
        from rhosocial.activerecord.query import CTEQuery

        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

        try:
            with pool.connection() as conn_backend:
                # Create CTEQuery with any backend
                original_backend = SQLiteBackend(database=":memory:")
                cte = CTEQuery(original_backend)

                # Should return context backend, not original
                cte_backend = cte.backend()
                assert cte_backend is conn_backend
                assert cte_backend is not original_backend
        finally:
            pool.close()

    def test_cte_query_fallback_without_context(self):
        """Test that CTEQuery falls back to constructor backend without context."""
        from rhosocial.activerecord.query import CTEQuery

        backend = SQLiteBackend(database=":memory:")
        cte = CTEQuery(backend)
        cte_backend = cte.backend()
        assert cte_backend is backend


class TestSetOperationQueryContextAwareness:
    """Test SetOperationQuery context awareness."""

    def test_set_operation_query_backend_context_awareness(self):
        """Test that SetOperationQuery.backend() is context aware."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

        try:
            ContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

            with pool.connection() as conn_backend:
                q1 = ContextTestUser.query()
                q2 = ContextTestUser.query()

                union_query = q1.union(q2)
                union_backend = union_query.backend()
                assert union_backend is conn_backend
        finally:
            pool.close()

    def test_set_operation_query_fallback_without_context(self):
        """Test that SetOperationQuery falls back to left backend without context."""
        ContextTestUser.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

        q1 = ContextTestUser.query()
        q2 = ContextTestUser.query()

        union_query = q1.union(q2)
        union_backend = union_query.backend()
        # Should return the left query's backend (which is the class backend)
        assert union_backend is ContextTestUser.__backend__
