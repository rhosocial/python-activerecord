# tests/rhosocial/activerecord_test/feature/query/connection/test_cte_query_context.py
"""Test CTEQuery context awareness with connection pool."""

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
from rhosocial.activerecord.query import CTEQuery, AsyncCTEQuery


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
class CteTestUser(IntegerPKMixin, ActiveRecord):
    """Test User model for CTE tests."""
    __table_name__ = "cte_test_users"

    id: Optional[int] = None
    name: str
    email: str
    parent_id: Optional[int] = None


# Async Test Model
class AsyncCteTestUser(IntegerPKMixin, AsyncActiveRecord):
    """Test Async User model for CTE tests."""
    __table_name__ = "async_cte_test_users"

    id: Optional[int] = None
    name: str
    email: str
    parent_id: Optional[int] = None


class TestSyncCTEQueryContext:
    """Test synchronous CTEQuery context awareness."""

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
                CREATE TABLE cte_test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    parent_id INTEGER
                )
            """)
            # Insert test data
            execute_sql(backend, "INSERT INTO cte_test_users (name, email, parent_id) VALUES ('Alice', 'alice@test.com', NULL)")
            execute_sql(backend, "INSERT INTO cte_test_users (name, email, parent_id) VALUES ('Bob', 'bob@test.com', 1)")

        yield pool
        pool.close(timeout=1.0)

    def test_cte_query_backend_without_context(self, pool, db_path):
        """Test CTEQuery.backend() returns constructor backend without context."""
        original_backend = SQLiteBackend(database=db_path)
        cte = CTEQuery(original_backend)
        cte_backend = cte.backend()
        assert cte_backend is original_backend

    def test_cte_query_backend_in_connection_context(self, pool, db_path):
        """Test CTEQuery.backend() returns connection backend in context."""
        original_backend = SQLiteBackend(database=db_path)

        with pool.connection() as conn_backend:
            cte = CTEQuery(original_backend)
            cte_backend = cte.backend()
            assert cte_backend is conn_backend
            assert cte_backend is not original_backend

    def test_cte_query_backend_in_transaction_context(self, pool, db_path):
        """Test CTEQuery.backend() returns transaction backend in context."""
        original_backend = SQLiteBackend(database=db_path)

        with pool.transaction() as tx_backend:
            cte = CTEQuery(original_backend)
            cte_backend = cte.backend()
            assert cte_backend is tx_backend
            assert cte_backend is not original_backend

    def test_nested_connection_contexts_reuse(self, pool, db_path):
        """Test nested connection contexts reuse for CTE query."""
        original_backend = SQLiteBackend(database=db_path)

        with pool.connection() as outer_conn:
            outer_cte = CTEQuery(original_backend)
            assert outer_cte.backend() is outer_conn

            with pool.connection() as inner_conn:
                inner_cte = CTEQuery(original_backend)
                assert inner_cte.backend() is outer_conn
                assert inner_conn is outer_conn

    def test_nested_transaction_contexts_reuse(self, pool, db_path):
        """Test nested transaction contexts reuse for CTE query."""
        original_backend = SQLiteBackend(database=db_path)

        with pool.transaction() as outer_tx:
            outer_cte = CTEQuery(original_backend)
            assert outer_cte.backend() is outer_tx

            with pool.transaction() as inner_tx:
                inner_cte = CTEQuery(original_backend)
                assert inner_cte.backend() is outer_tx
                assert inner_tx is outer_tx

    def test_cte_query_from_model_in_context(self, pool, db_path):
        """Test CTEQuery created from model query in context."""
        CteTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as conn_backend:
            query = CteTestUser.query()
            # The query's backend should be the context backend
            assert query.backend() is conn_backend


class TestAsyncCTEQueryContext:
    """Test asynchronous CTEQuery context awareness."""

    @pytest.fixture(autouse=True)
    async def cleanup_backend(self):
        """Auto cleanup backend after each test."""
        yield
        if AsyncCteTestUser.__backend__:
            await AsyncCteTestUser.__backend__.disconnect()
            AsyncCteTestUser.__backend__ = None

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
                CREATE TABLE async_cte_test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL,
                    parent_id INTEGER
                )
            """)
            await async_execute_sql(backend, "INSERT INTO async_cte_test_users (name, email, parent_id) VALUES ('Alice', 'alice@test.com', NULL)")
            await async_execute_sql(backend, "INSERT INTO async_cte_test_users (name, email, parent_id) VALUES ('Bob', 'bob@test.com', 1)")

        yield pool
        await pool.close(timeout=1.0)

    @pytest.mark.asyncio
    async def test_cte_query_backend_without_context(self, pool, db_path):
        """Test AsyncCTEQuery.backend() returns constructor backend without context."""
        original_backend = AsyncSQLiteBackend(database=db_path)
        cte = AsyncCTEQuery(original_backend)
        cte_backend = cte.backend()
        assert cte_backend is original_backend

    @pytest.mark.asyncio
    async def test_cte_query_backend_in_connection_context(self, pool, db_path):
        """Test AsyncCTEQuery.backend() returns connection backend in context."""
        original_backend = AsyncSQLiteBackend(database=db_path)

        async with pool.connection() as conn_backend:
            cte = AsyncCTEQuery(original_backend)
            cte_backend = cte.backend()
            assert cte_backend is conn_backend
            assert cte_backend is not original_backend

    @pytest.mark.asyncio
    async def test_cte_query_backend_in_transaction_context(self, pool, db_path):
        """Test AsyncCTEQuery.backend() returns transaction backend in context."""
        original_backend = AsyncSQLiteBackend(database=db_path)

        async with pool.transaction() as tx_backend:
            cte = AsyncCTEQuery(original_backend)
            cte_backend = cte.backend()
            assert cte_backend is tx_backend
            assert cte_backend is not original_backend

    @pytest.mark.asyncio
    async def test_nested_connection_contexts_reuse(self, pool, db_path):
        """Test nested async connection contexts reuse for CTE query."""
        original_backend = AsyncSQLiteBackend(database=db_path)

        async with pool.connection() as outer_conn:
            outer_cte = AsyncCTEQuery(original_backend)
            assert outer_cte.backend() is outer_conn

            async with pool.connection() as inner_conn:
                inner_cte = AsyncCTEQuery(original_backend)
                assert inner_cte.backend() is outer_conn
                assert inner_conn is outer_conn

    @pytest.mark.asyncio
    async def test_nested_transaction_contexts_reuse(self, pool, db_path):
        """Test nested async transaction contexts reuse for CTE query."""
        original_backend = AsyncSQLiteBackend(database=db_path)

        async with pool.transaction() as outer_tx:
            outer_cte = AsyncCTEQuery(original_backend)
            assert outer_cte.backend() is outer_tx

            async with pool.transaction() as inner_tx:
                inner_cte = AsyncCTEQuery(original_backend)
                assert inner_cte.backend() is outer_tx
                assert inner_tx is outer_tx

    @pytest.mark.asyncio
    async def test_cte_query_from_model_in_context(self, pool, db_path):
        """Test AsyncCTEQuery created from model query in context."""
        await AsyncCteTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.connection() as conn_backend:
            query = AsyncCteTestUser.query()
            assert query.backend() is conn_backend
