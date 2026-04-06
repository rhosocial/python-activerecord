# tests/rhosocial/activerecord_test/feature/query/connection/test_active_query_context.py
"""Test ActiveQuery context awareness with connection pool."""

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
from rhosocial.activerecord.query import ActiveQuery, AsyncActiveQuery


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
class QueryTestUser(IntegerPKMixin, ActiveRecord):
    """Test User model for query tests."""
    __table_name__ = "query_test_users"

    id: Optional[int] = None
    name: str
    email: str


# Async Test Model
class AsyncQueryTestUser(IntegerPKMixin, AsyncActiveRecord):
    """Test Async User model for query tests."""
    __table_name__ = "async_query_test_users"

    id: Optional[int] = None
    name: str
    email: str


class TestSyncActiveQueryContext:
    """Test synchronous ActiveQuery context awareness."""

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
                CREATE TABLE query_test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)
            # Insert test data
            execute_sql(backend, "INSERT INTO query_test_users (name, email) VALUES ('Alice', 'alice@test.com')")
            execute_sql(backend, "INSERT INTO query_test_users (name, email) VALUES ('Bob', 'bob@test.com')")

        yield pool
        pool.close(timeout=1.0)

    def test_query_from_model_backend_without_context(self, pool, db_path):
        """Test ActiveQuery.backend() returns class backend without context."""
        QueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        query = QueryTestUser.query()
        query_backend = query.backend()
        assert query_backend is QueryTestUser.__backend__

    def test_query_from_model_backend_in_connection_context(self, pool, db_path):
        """Test ActiveQuery.backend() returns connection backend in context."""
        QueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as conn_backend:
            query = QueryTestUser.query()
            query_backend = query.backend()
            assert query_backend is conn_backend
            assert query_backend is not QueryTestUser.__backend__

    def test_query_from_model_backend_in_transaction_context(self, pool, db_path):
        """Test ActiveQuery.backend() returns transaction backend in context."""
        QueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.transaction() as tx_backend:
            query = QueryTestUser.query()
            query_backend = query.backend()
            assert query_backend is tx_backend

    def test_independent_query_backend_without_context(self, pool, db_path):
        """Test independent ActiveQuery.backend() without context."""
        QueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        # Create query independently (not from Model.query())
        query = ActiveQuery(QueryTestUser)
        query_backend = query.backend()
        # Should fallback to model class backend
        assert query_backend is QueryTestUser.__backend__

    def test_independent_query_backend_in_connection_context(self, pool, db_path):
        """Test independent ActiveQuery.backend() in connection context."""
        QueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as conn_backend:
            # Create query independently
            query = ActiveQuery(QueryTestUser)
            query_backend = query.backend()
            # Should return context backend
            assert query_backend is conn_backend

    def test_nested_connection_contexts_reuse(self, pool, db_path):
        """Test nested connection contexts reuse for query."""
        QueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as outer_conn:
            outer_query = QueryTestUser.query()
            assert outer_query.backend() is outer_conn

            with pool.connection() as inner_conn:
                inner_query = QueryTestUser.query()
                assert inner_query.backend() is outer_conn
                assert inner_conn is outer_conn

    def test_nested_transaction_contexts_reuse(self, pool, db_path):
        """Test nested transaction contexts reuse for query."""
        QueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.transaction() as outer_tx:
            outer_query = QueryTestUser.query()
            assert outer_query.backend() is outer_tx

            with pool.transaction() as inner_tx:
                inner_query = QueryTestUser.query()
                assert inner_query.backend() is outer_tx
                assert inner_tx is outer_tx

    def test_query_execution_in_context(self, pool, db_path):
        """Test query execution in connection context."""
        QueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.connection() as backend:
            # Execute SQL to verify query uses context backend
            result = execute_sql(backend, "SELECT * FROM query_test_users")
            assert len(result.data) == 2


class TestAsyncActiveQueryContext:
    """Test asynchronous ActiveQuery context awareness."""

    @pytest.fixture(autouse=True)
    async def cleanup_backend(self):
        """Auto cleanup backend after each test."""
        yield
        if AsyncQueryTestUser.__backend__:
            await AsyncQueryTestUser.__backend__.disconnect()
            AsyncQueryTestUser.__backend__ = None

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
                CREATE TABLE async_query_test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)
            await async_execute_sql(backend, "INSERT INTO async_query_test_users (name, email) VALUES ('Alice', 'alice@test.com')")
            await async_execute_sql(backend, "INSERT INTO async_query_test_users (name, email) VALUES ('Bob', 'bob@test.com')")

        yield pool
        await pool.close(timeout=1.0)

    @pytest.mark.asyncio
    async def test_query_from_model_backend_without_context(self, pool, db_path):
        """Test AsyncActiveQuery.backend() returns class backend without context."""
        await AsyncQueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        query = AsyncQueryTestUser.query()
        query_backend = query.backend()
        assert query_backend is AsyncQueryTestUser.__backend__

    @pytest.mark.asyncio
    async def test_query_from_model_backend_in_connection_context(self, pool, db_path):
        """Test AsyncActiveQuery.backend() returns connection backend in context."""
        await AsyncQueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.connection() as conn_backend:
            query = AsyncQueryTestUser.query()
            query_backend = query.backend()
            assert query_backend is conn_backend

    @pytest.mark.asyncio
    async def test_query_from_model_backend_in_transaction_context(self, pool, db_path):
        """Test AsyncActiveQuery.backend() returns transaction backend in context."""
        await AsyncQueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.transaction() as tx_backend:
            query = AsyncQueryTestUser.query()
            query_backend = query.backend()
            assert query_backend is tx_backend

    @pytest.mark.asyncio
    async def test_independent_query_backend_in_connection_context(self, pool, db_path):
        """Test independent AsyncActiveQuery.backend() in connection context."""
        await AsyncQueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.connection() as conn_backend:
            # Create query independently
            query = AsyncActiveQuery(AsyncQueryTestUser)
            query_backend = query.backend()
            assert query_backend is conn_backend

    @pytest.mark.asyncio
    async def test_nested_connection_contexts_reuse(self, pool, db_path):
        """Test nested async connection contexts reuse for query."""
        await AsyncQueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.connection() as outer_conn:
            outer_query = AsyncQueryTestUser.query()
            assert outer_query.backend() is outer_conn

            async with pool.connection() as inner_conn:
                inner_query = AsyncQueryTestUser.query()
                assert inner_query.backend() is outer_conn
                assert inner_conn is outer_conn

    @pytest.mark.asyncio
    async def test_nested_transaction_contexts_reuse(self, pool, db_path):
        """Test nested async transaction contexts reuse for query."""
        await AsyncQueryTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.transaction() as outer_tx:
            outer_query = AsyncQueryTestUser.query()
            assert outer_query.backend() is outer_tx

            async with pool.transaction() as inner_tx:
                inner_query = AsyncQueryTestUser.query()
                assert inner_query.backend() is outer_tx
                assert inner_tx is outer_tx
