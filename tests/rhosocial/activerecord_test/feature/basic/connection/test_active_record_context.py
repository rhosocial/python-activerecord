# tests/rhosocial/activerecord_test/feature/basic/connection/test_active_record_context.py
"""Test ActiveRecord context awareness with connection pool."""

from typing import Optional
import pytest
import tempfile
import os

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
    get_current_connection_backend,
    get_current_async_connection_backend,
)


def execute_sql(backend, sql: str, params=None):
    """Helper to execute SQL with proper options."""
    sql_upper = sql.upper().strip()
    if 'CREATE' in sql_upper or 'DROP' in sql_upper or 'ALTER' in sql_upper:
        stmt_type = StatementType.DDL
    elif sql_upper.startswith('SELECT'):
        stmt_type = StatementType.DQL
    else:
        stmt_type = StatementType.DML
    options = ExecutionOptions(stmt_type=stmt_type)
    return backend.execute(sql, params or (), options=options)


async def async_execute_sql(backend, sql: str, params=None):
    """Helper to execute SQL asynchronously with proper options."""
    sql_upper = sql.upper().strip()
    if 'CREATE' in sql_upper or 'DROP' in sql_upper or 'ALTER' in sql_upper:
        stmt_type = StatementType.DDL
    elif sql_upper.startswith('SELECT'):
        stmt_type = StatementType.DQL
    else:
        stmt_type = StatementType.DML
    options = ExecutionOptions(stmt_type=stmt_type)
    return await backend.execute(sql, params or (), options=options)


# Sync Test Model
class ContextUser(IntegerPKMixin, ActiveRecord):
    """Test User model for context tests."""
    __table_name__ = "context_users"

    id: Optional[int] = None
    name: str
    email: str


# Async Test Model
class AsyncContextUser(IntegerPKMixin, AsyncActiveRecord):
    """Test Async User model for context tests."""
    __table_name__ = "async_context_users"

    id: Optional[int] = None
    name: str
    email: str


class TestSyncActiveRecordContext:
    """Test synchronous ActiveRecord context awareness."""

    @pytest.fixture
    def db_path(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def pool(self, db_path):
        """Create connection pool."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(
                database=db_path,
                check_same_thread=False
            )
        )
        pool = BackendPool.create(config)

        # Create table
        with pool.connection() as backend:
            execute_sql(backend, """
                CREATE TABLE context_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)

        yield pool
        pool.close(timeout=1.0)

    def test_backend_without_context_returns_class_backend(self, pool, db_path):
        """Test that backend() returns class backend without context."""
        ContextUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        # Without context, should return class backend
        backend = ContextUser.backend()
        assert backend is ContextUser.__backend__

    def test_backend_in_connection_context(self, pool, db_path):
        """Test that backend() returns connection backend in connection context."""
        ContextUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as conn_backend:
            model_backend = ContextUser.backend()
            assert model_backend is conn_backend
            assert model_backend is not ContextUser.__backend__

            # Verify context functions
            assert get_current_backend() is conn_backend
            assert get_current_connection_backend() is conn_backend

    def test_backend_in_transaction_context(self, pool, db_path):
        """Test that backend() returns transaction backend in transaction context."""
        ContextUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.transaction() as tx_backend:
            model_backend = ContextUser.backend()
            assert model_backend is tx_backend

            # Verify context functions
            assert get_current_backend() is tx_backend
            assert get_current_transaction_backend() is tx_backend

    def test_nested_connection_contexts(self, pool, db_path):
        """Test nested connection contexts reuse same backend."""
        ContextUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as outer_conn:
            outer_backend = ContextUser.backend()
            assert outer_backend is outer_conn

            with pool.connection() as inner_conn:
                inner_backend = ContextUser.backend()
                # Should reuse the same connection
                assert inner_backend is outer_backend
                assert inner_conn is outer_conn

    def test_nested_transaction_contexts(self, pool, db_path):
        """Test nested transaction contexts reuse same backend."""
        ContextUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.transaction() as outer_tx:
            outer_backend = ContextUser.backend()
            assert outer_backend is outer_tx

            with pool.transaction() as inner_tx:
                inner_backend = ContextUser.backend()
                # Should reuse the same transaction
                assert inner_backend is outer_backend
                assert inner_tx is outer_tx

    def test_connection_nested_in_transaction(self, pool, db_path):
        """Test connection nested in transaction reuses transaction backend."""
        ContextUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.transaction() as tx_backend:
            tx_model_backend = ContextUser.backend()
            assert tx_model_backend is tx_backend

            with pool.connection() as conn_backend:
                # Connection inside transaction should reuse transaction backend
                conn_model_backend = ContextUser.backend()
                assert conn_model_backend is tx_backend
                assert conn_backend is tx_backend

    def test_transaction_nested_in_connection(self, pool, db_path):
        """Test transaction nested in connection."""
        ContextUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as conn_backend:
            conn_model_backend = ContextUser.backend()
            assert conn_model_backend is conn_backend

            with pool.transaction() as tx_backend:
                tx_model_backend = ContextUser.backend()
                # Transaction should use the same connection
                assert tx_model_backend is conn_backend
                assert tx_backend is conn_backend

    def test_deeply_nested_contexts(self, pool, db_path):
        """Test deeply nested contexts."""
        ContextUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as level1:
            assert ContextUser.backend() is level1

            with pool.connection() as level2:
                assert ContextUser.backend() is level1
                assert level2 is level1

                with pool.transaction() as level3:
                    assert ContextUser.backend() is level1
                    assert level3 is level1

                    with pool.connection() as level4:
                        assert ContextUser.backend() is level1
                        assert level4 is level1


class TestAsyncActiveRecordContext:
    """Test asynchronous ActiveRecord context awareness."""

    @pytest.fixture(autouse=True)
    async def cleanup_backend(self):
        """Auto cleanup backend after each test."""
        yield
        if AsyncContextUser.__backend__:
            await AsyncContextUser.__backend__.disconnect()
            AsyncContextUser.__backend__ = None

    @pytest.fixture
    async def db_path(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    async def pool(self, db_path):
        """Create async connection pool."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=db_path)
        )
        pool = await AsyncBackendPool.create(config)

        # Create table
        async with pool.connection() as backend:
            await async_execute_sql(backend, """
                CREATE TABLE async_context_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)

        yield pool
        await pool.close(timeout=1.0)

    @pytest.mark.asyncio
    async def test_backend_without_context_returns_class_backend(self, pool, db_path):
        """Test that backend() returns class backend without context."""
        await AsyncContextUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        backend = AsyncContextUser.backend()
        assert backend is AsyncContextUser.__backend__

    @pytest.mark.asyncio
    async def test_backend_in_connection_context(self, pool, db_path):
        """Test that backend() returns connection backend in async connection context."""
        await AsyncContextUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.connection() as conn_backend:
            model_backend = AsyncContextUser.backend()
            assert model_backend is conn_backend

            # Verify context functions
            assert get_current_async_backend() is conn_backend
            assert get_current_async_connection_backend() is conn_backend

    @pytest.mark.asyncio
    async def test_backend_in_transaction_context(self, pool, db_path):
        """Test that backend() returns transaction backend in async transaction context."""
        await AsyncContextUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.transaction() as tx_backend:
            model_backend = AsyncContextUser.backend()
            assert model_backend is tx_backend

            # Verify context functions
            assert get_current_async_backend() is tx_backend
            assert get_current_async_transaction_backend() is tx_backend

    @pytest.mark.asyncio
    async def test_nested_connection_contexts(self, pool, db_path):
        """Test nested async connection contexts reuse same backend."""
        await AsyncContextUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.connection() as outer_conn:
            outer_backend = AsyncContextUser.backend()
            assert outer_backend is outer_conn

            async with pool.connection() as inner_conn:
                inner_backend = AsyncContextUser.backend()
                assert inner_backend is outer_backend
                assert inner_conn is outer_conn

    @pytest.mark.asyncio
    async def test_nested_transaction_contexts(self, pool, db_path):
        """Test nested async transaction contexts reuse same backend."""
        await AsyncContextUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.transaction() as outer_tx:
            outer_backend = AsyncContextUser.backend()
            assert outer_backend is outer_tx

            async with pool.transaction() as inner_tx:
                inner_backend = AsyncContextUser.backend()
                assert inner_backend is outer_backend
                assert inner_tx is outer_tx

    @pytest.mark.asyncio
    async def test_connection_nested_in_transaction(self, pool, db_path):
        """Test async connection nested in transaction reuses transaction backend."""
        await AsyncContextUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.transaction() as tx_backend:
            tx_model_backend = AsyncContextUser.backend()
            assert tx_model_backend is tx_backend

            async with pool.connection() as conn_backend:
                conn_model_backend = AsyncContextUser.backend()
                assert conn_model_backend is tx_backend
                assert conn_backend is tx_backend


class TestSyncAsyncIsolation:
    """Test that sync and async contexts are properly isolated."""

    def test_sync_backend_without_context_is_none(self):
        """Test that get_current_backend() returns None without context."""
        assert get_current_backend() is None

    @pytest.mark.asyncio
    async def test_async_backend_without_context_is_none(self):
        """Test that get_current_async_backend() returns None without context."""
        assert get_current_async_backend() is None
