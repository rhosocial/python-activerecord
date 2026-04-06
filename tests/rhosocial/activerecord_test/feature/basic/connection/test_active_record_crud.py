# tests/rhosocial/activerecord_test/feature/basic/connection/test_active_record_crud.py
"""Test ActiveRecord CRUD operations with connection pool context awareness."""

from typing import Optional
import pytest
import tempfile
import os
import threading
import asyncio

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
class CrudTestUser(IntegerPKMixin, ActiveRecord):
    """Test User model for CRUD tests."""
    __table_name__ = "crud_test_users"

    id: Optional[int] = None
    name: str
    email: str


# Async Test Model
class AsyncCrudTestUser(IntegerPKMixin, AsyncActiveRecord):
    """Test Async User model for CRUD tests."""
    __table_name__ = "async_crud_test_users"

    id: Optional[int] = None
    name: str
    email: str


class TestSyncActiveRecordCRUD:
    """Test synchronous ActiveRecord CRUD with connection pool."""

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
                CREATE TABLE crud_test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)

        yield pool
        pool.close(timeout=1.0)

    def test_create_in_transaction(self, pool, db_path):
        """Test model create() in transaction context."""
        # Configure model to use the same database
        CrudTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.transaction() as backend:
            user = CrudTestUser(name="Alice", email="alice@test.com")
            user.save()

        # Verify committed
        with pool.connection() as backend:
            result = execute_sql(backend, "SELECT * FROM crud_test_users")
            assert len(result.data) == 1
            assert result.data[0]['name'] == "Alice"

    def test_update_in_transaction(self, pool, db_path):
        """Test model update in transaction context."""
        CrudTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        # Create user first
        with pool.connection() as backend:
            execute_sql(backend, "INSERT INTO crud_test_users (name, email) VALUES ('Bob', 'bob@test.com')")

        # Update in transaction
        with pool.transaction() as backend:
            execute_sql(backend, "UPDATE crud_test_users SET name = 'Robert' WHERE name = 'Bob'")

        # Verify updated
        with pool.connection() as backend:
            result = execute_sql(backend, "SELECT * FROM crud_test_users WHERE name = 'Robert'")
            assert len(result.data) == 1

    def test_delete_in_transaction(self, pool, db_path):
        """Test model delete in transaction context."""
        CrudTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        # Create user first
        with pool.connection() as backend:
            execute_sql(backend, "INSERT INTO crud_test_users (name, email) VALUES ('Charlie', 'charlie@test.com')")

        # Delete in transaction
        with pool.transaction() as backend:
            execute_sql(backend, "DELETE FROM crud_test_users WHERE name = 'Charlie'")

        # Verify deleted
        with pool.connection() as backend:
            result = execute_sql(backend, "SELECT * FROM crud_test_users")
            assert len(result.data) == 0

    def test_transaction_rollback_on_create(self, pool, db_path):
        """Test that create is rolled back on error."""
        CrudTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        try:
            with pool.transaction():
                execute_sql(pool.connection().__enter__(), "INSERT INTO crud_test_users (name, email) VALUES ('Dave', 'dave@test.com')")
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify rollback
        with pool.connection() as backend:
            result = execute_sql(backend, "SELECT * FROM crud_test_users")
            assert len(result.data) == 0

    def test_nested_transaction_reuses_connection(self, pool, db_path):
        """Test that nested transactions reuse the same connection."""
        CrudTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        with pool.transaction() as outer_tx:
            outer_backend = CrudTestUser.backend()

            # Nested transaction should reuse connection
            with pool.transaction() as inner_tx:
                inner_backend = CrudTestUser.backend()
                assert inner_backend is outer_backend

                execute_sql(inner_backend, "INSERT INTO crud_test_users (name, email) VALUES ('Eve', 'eve@test.com')")

        # Verify committed
        with pool.connection() as backend:
            result = execute_sql(backend, "SELECT * FROM crud_test_users")
            assert len(result.data) == 1


class TestAsyncActiveRecordCRUD:
    """Test asynchronous ActiveRecord CRUD with connection pool."""

    @pytest.fixture(autouse=True)
    async def cleanup_backend(self):
        """Auto cleanup backend after each test."""
        yield
        if AsyncCrudTestUser.__backend__:
            await AsyncCrudTestUser.__backend__.disconnect()
            AsyncCrudTestUser.__backend__ = None

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
                CREATE TABLE async_crud_test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)

        yield pool
        await pool.close(timeout=1.0)

    @pytest.mark.asyncio
    async def test_create_in_transaction(self, pool, db_path):
        """Test async model create() in transaction context."""
        await AsyncCrudTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.transaction() as backend:
            await async_execute_sql(backend, "INSERT INTO async_crud_test_users (name, email) VALUES ('Alice', 'alice@test.com')")

        # Verify committed
        async with pool.connection() as backend:
            result = await async_execute_sql(backend, "SELECT * FROM async_crud_test_users")
            assert len(result.data) == 1

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_create(self, pool, db_path):
        """Test that async create is rolled back on error."""
        await AsyncCrudTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        try:
            async with pool.transaction() as backend:
                await async_execute_sql(backend, "INSERT INTO async_crud_test_users (name, email) VALUES ('Dave', 'dave@test.com')")
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Verify rollback
        async with pool.connection() as backend:
            result = await async_execute_sql(backend, "SELECT * FROM async_crud_test_users")
            assert len(result.data) == 0

    @pytest.mark.asyncio
    async def test_nested_transaction_reuses_connection(self, pool, db_path):
        """Test that nested async transactions reuse the same connection."""
        await AsyncCrudTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        async with pool.transaction() as outer_tx:
            outer_backend = AsyncCrudTestUser.backend()

            async with pool.transaction() as inner_tx:
                inner_backend = AsyncCrudTestUser.backend()
                assert inner_backend is outer_backend

                await async_execute_sql(inner_backend, "INSERT INTO async_crud_test_users (name, email) VALUES ('Eve', 'eve@test.com')")

        # Verify committed
        async with pool.connection() as backend:
            result = await async_execute_sql(backend, "SELECT * FROM async_crud_test_users")
            assert len(result.data) == 1


class TestConcurrentActiveRecordOperations:
    """Test concurrent ActiveRecord operations with connection pool."""

    @pytest.fixture
    def db_path(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_concurrent_creates_different_connections(self, db_path):
        """Test concurrent creates use different connections."""
        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(
                database=db_path,
                check_same_thread=False
            )
        )
        pool = BackendPool.create(config)

        CrudTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        # Create table
        with pool.connection() as backend:
            execute_sql(backend, """
                CREATE TABLE crud_test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)

        connections_used = []
        lock = threading.Lock()
        errors = []

        def worker(worker_id):
            try:
                with pool.connection() as backend:
                    with lock:
                        connections_used.append(id(backend))
                    execute_sql(backend, f"INSERT INTO crud_test_users (name, email) VALUES ('user_{worker_id}', 'user_{worker_id}@test.com')")
            except Exception as e:
                with lock:
                    errors.append((worker_id, str(e)))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert len(errors) == 0, f"Errors: {errors}"

        # Verify all records created
        with pool.connection() as backend:
            result = execute_sql(backend, "SELECT COUNT(*) as cnt FROM crud_test_users")
            assert result.data[0]['cnt'] == 5

        pool.close(timeout=1.0)

    def test_concurrent_transactions_isolation(self, db_path):
        """Test concurrent transactions are isolated."""
        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(
                database=db_path,
                check_same_thread=False
            )
        )
        pool = BackendPool.create(config)

        CrudTestUser.configure(
            SQLiteConnectionConfig(database=db_path, check_same_thread=False),
            SQLiteBackend
        )

        # Create table
        with pool.connection() as backend:
            execute_sql(backend, """
                CREATE TABLE crud_test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)

        errors = []
        lock = threading.Lock()
        barrier = threading.Barrier(3)

        def writer(name, value):
            try:
                barrier.wait(timeout=5.0)
                with pool.transaction() as backend:
                    execute_sql(backend, f"INSERT INTO crud_test_users (name, email) VALUES ('{name}', '{value}@test.com')")
            except Exception as e:
                with lock:
                    errors.append((name, str(e)))

        threads = [
            threading.Thread(target=writer, args=('writer1', 'w1')),
            threading.Thread(target=writer, args=('writer2', 'w2')),
            threading.Thread(target=writer, args=('writer3', 'w3')),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        assert len(errors) == 0, f"Errors: {errors}"

        # Verify all records
        with pool.connection() as backend:
            result = execute_sql(backend, "SELECT COUNT(*) as cnt FROM crud_test_users")
            assert result.data[0]['cnt'] == 3

        pool.close(timeout=1.0)


class TestAsyncConcurrentActiveRecordOperations:
    """Test async concurrent ActiveRecord operations."""

    @pytest.fixture(autouse=True)
    async def cleanup_backend(self):
        """Auto cleanup backend after each test."""
        yield
        if AsyncCrudTestUser.__backend__:
            await AsyncCrudTestUser.__backend__.disconnect()
            AsyncCrudTestUser.__backend__ = None

    @pytest.fixture
    async def db_path(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_concurrent_async_operations(self, db_path):
        """Test concurrent async operations."""
        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=db_path)
        )
        pool = await AsyncBackendPool.create(config)

        await AsyncCrudTestUser.configure(
            SQLiteConnectionConfig(database=db_path),
            AsyncSQLiteBackend
        )

        # Create table
        async with pool.connection() as backend:
            await async_execute_sql(backend, """
                CREATE TABLE async_crud_test_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL
                )
            """)

        errors = []

        async def worker(worker_id):
            try:
                async with pool.connection() as backend:
                    await async_execute_sql(backend, f"INSERT INTO async_crud_test_users (name, email) VALUES ('user_{worker_id}', 'user_{worker_id}@test.com')")
            except Exception as e:
                errors.append((worker_id, str(e)))

        await asyncio.gather(*[worker(i) for i in range(5)])

        assert len(errors) == 0, f"Errors: {errors}"

        # Verify all records
        async with pool.connection() as backend:
            result = await async_execute_sql(backend, "SELECT COUNT(*) as cnt FROM async_crud_test_users")
            assert result.data[0]['cnt'] == 5

        await pool.close(timeout=1.0)
