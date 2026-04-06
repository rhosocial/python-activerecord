# tests/rhosocial/activerecord_test/feature/query/connection/test_set_operation_context.py
"""Test SetOperationQuery context awareness with connection pool."""

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
class SetOpTestUser(IntegerPKMixin, ActiveRecord):
    """Test User model for set operation tests."""
    __table_name__ = "setop_test_users"

    id: Optional[int] = None
    name: str
    email: str


# Async Test Model
class AsyncSetOpTestUser(IntegerPKMixin, AsyncActiveRecord):
    """Test Async User model for set operation tests."""
    __table_name__ = "async_setop_test_users"

    id: Optional[int] = None
    name: str
    email: str


class TestSyncSetOperationQueryContext:
    """Test synchronous SetOperationQuery context awareness."""

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
                CREATE TABLE setop_test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)
            # Insert test data
            execute_sql(backend, "INSERT INTO setop_test_users (name, email) VALUES ('Alice', 'alice@test.com')")
            execute_sql(backend, "INSERT INTO setop_test_users (name, email) VALUES ('Bob', 'bob@test.com')")
            execute_sql(backend, "INSERT INTO setop_test_users (name, email) VALUES ('Charlie', 'charlie@test.com')")

        yield pool
        pool.close(timeout=1.0)

    def test_union_backend_without_context(self, pool, db_path):
        """Test SetOperationQuery.backend() returns left backend without context."""
        SetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        q1 = SetOpTestUser.query()
        q2 = SetOpTestUser.query()
        union_query = q1.union(q2)
        union_backend = union_query.backend()
        # Should return left query's backend (class backend)
        assert union_backend is SetOpTestUser.__backend__

    def test_union_backend_in_connection_context(self, pool, db_path):
        """Test SetOperationQuery.backend() returns connection backend in context."""
        SetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as conn_backend:
            q1 = SetOpTestUser.query()
            q2 = SetOpTestUser.query()
            union_query = q1.union(q2)
            union_backend = union_query.backend()
            assert union_backend is conn_backend

    def test_union_backend_in_transaction_context(self, pool, db_path):
        """Test SetOperationQuery.backend() returns transaction backend in context."""
        SetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.transaction() as tx_backend:
            q1 = SetOpTestUser.query()
            q2 = SetOpTestUser.query()
            union_query = q1.union(q2)
            union_backend = union_query.backend()
            assert union_backend is tx_backend

    def test_intersect_backend_in_connection_context(self, pool, db_path):
        """Test INTERSECT backend in connection context."""
        SetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as conn_backend:
            q1 = SetOpTestUser.query()
            q2 = SetOpTestUser.query()
            intersect_query = q1.intersect(q2)
            intersect_backend = intersect_query.backend()
            assert intersect_backend is conn_backend

    def test_except_backend_in_connection_context(self, pool, db_path):
        """Test EXCEPT backend in connection context."""
        SetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as conn_backend:
            q1 = SetOpTestUser.query()
            q2 = SetOpTestUser.query()
            except_query = q1.except_(q2)
            except_backend = except_query.backend()
            assert except_backend is conn_backend

    def test_union_backend_in_connection_context(self, pool, db_path):
        """Test nested connection contexts reuse for set operation."""
        SetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as outer_conn:
            q1 = SetOpTestUser.query()
            q2 = SetOpTestUser.query()
            outer_union = q1.union(q2)
            assert outer_union.backend() is outer_conn

            with pool.connection() as inner_conn:
                q3 = SetOpTestUser.query()
                q4 = SetOpTestUser.query()
                inner_union = q3.union(q4)
                assert inner_union.backend() is outer_conn
                assert inner_conn is outer_conn

    def test_nested_transaction_contexts_reuse(self, pool, db_path):
        """Test nested transaction contexts reuse for set operation."""
        SetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.transaction() as outer_tx:
            q1 = SetOpTestUser.query()
            q2 = SetOpTestUser.query()
            outer_union = q1.union(q2)
            assert outer_union.backend() is outer_tx

            with pool.transaction() as inner_tx:
                q3 = SetOpTestUser.query()
                q4 = SetOpTestUser.query()
                inner_union = q3.union(q4)
                assert inner_union.backend() is outer_tx
                assert inner_tx is outer_tx


class TestAsyncSetOperationQueryContext:
    """Test asynchronous SetOperationQuery context awareness."""

    @pytest.fixture(autouse=True)
    async def cleanup_backend(self):
        """Auto cleanup backend after each test."""
        yield
        if AsyncSetOpTestUser.__backend__:
            await AsyncSetOpTestUser.__backend__.disconnect()
            AsyncSetOpTestUser.__backend__ = None

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
                CREATE TABLE async_setop_test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)
            await async_execute_sql(backend, "INSERT INTO async_setop_test_users (name, email) VALUES ('Alice', 'alice@test.com')")
            await async_execute_sql(backend, "INSERT INTO async_setop_test_users (name, email) VALUES ('Bob', 'bob@test.com')")
            await async_execute_sql(backend, "INSERT INTO async_setop_test_users (name, email) VALUES ('Charlie', 'charlie@test.com')")

        yield pool
        await pool.close(timeout=1.0)

    @pytest.mark.asyncio
    async def test_union_backend_without_context(self, pool, db_path):
        """Test AsyncSetOperationQuery.backend() returns left backend without context."""
        await AsyncSetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        q1 = AsyncSetOpTestUser.query()
        q2 = AsyncSetOpTestUser.query()
        union_query = q1.union(q2)
        union_backend = union_query.backend()
        assert union_backend is AsyncSetOpTestUser.__backend__

    @pytest.mark.asyncio
    async def test_union_backend_in_connection_context(self, pool, db_path):
        """Test AsyncSetOperationQuery.backend() returns connection backend in context."""
        await AsyncSetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.connection() as conn_backend:
            q1 = AsyncSetOpTestUser.query()
            q2 = AsyncSetOpTestUser.query()
            union_query = q1.union(q2)
            union_backend = union_query.backend()
            assert union_backend is conn_backend

    @pytest.mark.asyncio
    async def test_union_backend_in_transaction_context(self, pool, db_path):
        """Test AsyncSetOperationQuery.backend() returns transaction backend in context."""
        await AsyncSetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.transaction() as tx_backend:
            q1 = AsyncSetOpTestUser.query()
            q2 = AsyncSetOpTestUser.query()
            union_query = q1.union(q2)
            union_backend = union_query.backend()
            assert union_backend is tx_backend

    @pytest.mark.asyncio
    async def test_intersect_backend_in_connection_context(self, pool, db_path):
        """Test async INTERSECT backend in connection context."""
        await AsyncSetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.connection() as conn_backend:
            q1 = AsyncSetOpTestUser.query()
            q2 = AsyncSetOpTestUser.query()
            intersect_query = q1.intersect(q2)
            intersect_backend = intersect_query.backend()
            assert intersect_backend is conn_backend

    @pytest.mark.asyncio
    async def test_except_backend_in_connection_context(self, pool, db_path):
        """Test async EXCEPT backend in connection context."""
        await AsyncSetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.connection() as conn_backend:
            q1 = AsyncSetOpTestUser.query()
            q2 = AsyncSetOpTestUser.query()
            except_query = q1.except_(q2)
            except_backend = except_query.backend()
            assert except_backend is conn_backend

    @pytest.mark.asyncio
    async def test_nested_connection_contexts_reuse(self, pool, db_path):
        """Test nested async connection contexts reuse for set operation."""
        await AsyncSetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.connection() as outer_conn:
            q1 = AsyncSetOpTestUser.query()
            q2 = AsyncSetOpTestUser.query()
            outer_union = q1.union(q2)
            assert outer_union.backend() is outer_conn

            async with pool.connection() as inner_conn:
                q3 = AsyncSetOpTestUser.query()
                q4 = AsyncSetOpTestUser.query()
                inner_union = q3.union(q4)
                assert inner_union.backend() is outer_conn
                assert inner_conn is outer_conn

    @pytest.mark.asyncio
    async def test_nested_transaction_contexts_reuse(self, pool, db_path):
        """Test nested async transaction contexts reuse for set operation."""
        await AsyncSetOpTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.transaction() as outer_tx:
            q1 = AsyncSetOpTestUser.query()
            q2 = AsyncSetOpTestUser.query()
            outer_union = q1.union(q2)
            assert outer_union.backend() is outer_tx

            async with pool.transaction() as inner_tx:
                q3 = AsyncSetOpTestUser.query()
                q4 = AsyncSetOpTestUser.query()
                inner_union = q3.union(q4)
                assert inner_union.backend() is outer_tx
                assert inner_tx is outer_tx
