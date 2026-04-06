# tests/providers/query_connection.py
"""
Concrete implementation of IQueryConnectionProvider for SQLite backend.

This provider sets up connection pools and models for testing
query classes context awareness (ActiveQuery, CTEQuery, SetOperationQuery).
"""
import os
import tempfile
import uuid
from typing import Type, Tuple

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.connection.pool import BackendPool, AsyncBackendPool, PoolConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

from rhosocial.activerecord.testsuite.feature.query.connection.interfaces import IQueryConnectionProvider


class SyncQueryTestUser(ActiveRecord):
    """Sync test user model for query connection pool tests."""
    __table_name__ = "test_users"
    id: int = None
    name: str
    email: str


class AsyncQueryTestUser(AsyncActiveRecord):
    """Async test user model for query connection pool tests."""
    __table_name__ = "test_users"
    id: int = None
    name: str
    email: str


class QueryConnectionProvider(IQueryConnectionProvider):
    """
    SQLite backend implementation for query connection pool context tests.
    """

    def __init__(self):
        self._temp_files = []
        self._active_backends = []
        self._active_async_backends = []

    def get_test_scenarios(self) -> list:
        """Returns available test scenarios."""
        # Use only memory scenario for connection pool tests
        return ['memory']

    def _create_temp_db(self) -> str:
        """Create a temporary database file."""
        db_path = os.path.join(
            tempfile.gettempdir(),
            f"test_query_connection_pool_{uuid.uuid4().hex}.sqlite"
        )
        self._temp_files.append(db_path)
        return db_path

    def _create_test_table(self, backend):
        """Create the test_users table."""
        try:
            backend.execute("DROP TABLE IF EXISTS test_users", options=ExecutionOptions(stmt_type=StatementType.DDL))
        except Exception:
            pass

        backend.execute("""
            CREATE TABLE test_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL
            )
        """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    def setup_sync_pool_and_model(self, scenario_name: str) -> Tuple[BackendPool, Type[ActiveRecord]]:
        """Setup sync connection pool and model for query context tests."""
        # Create connection pool
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        # Create table
        with pool.connection() as backend:
            self._create_test_table(backend)
            self._active_backends.append(backend)

        # Configure model to use a separate backend (not pool backend)
        # This tests that model.backend() returns pool context backend
        SyncQueryTestUser.configure(
            SQLiteConnectionConfig(database=":memory:"),
            SQLiteBackend
        )
        self._active_backends.append(SyncQueryTestUser.__backend__)

        return pool, SyncQueryTestUser

    def setup_async_pool_and_model(self, scenario_name: str) -> Tuple[AsyncBackendPool, Type[AsyncActiveRecord]]:
        """Setup async connection pool and model for query context tests."""
        import asyncio

        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )

        # Create pool synchronously using asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        pool = loop.run_until_complete(AsyncBackendPool.create(config))

        # Create table
        async def setup_table():
            async with pool.connection() as backend:
                try:
                    await backend.execute("DROP TABLE IF EXISTS test_users", options=ExecutionOptions(stmt_type=StatementType.DDL))
                except Exception:
                    pass
                await backend.execute("""
                    CREATE TABLE test_users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        email TEXT NOT NULL
                    )
                """, options=ExecutionOptions(stmt_type=StatementType.DDL))
                self._active_async_backends.append(backend)

        loop.run_until_complete(setup_table())

        # Configure model
        async def configure_model():
            await AsyncQueryTestUser.configure(
                SQLiteConnectionConfig(database=":memory:"),
                AsyncSQLiteBackend
            )

        loop.run_until_complete(configure_model())
        self._active_async_backends.append(AsyncQueryTestUser.__backend__)

        return pool, AsyncQueryTestUser

    def cleanup_sync(self, scenario_name: str, pool: BackendPool):
        """Cleanup after sync tests."""
        pool.close(timeout=1.0)

        # Disconnect backends
        for backend in self._active_backends:
            try:
                backend.disconnect()
            except Exception:
                pass
        self._active_backends.clear()

        # Clean up temp files
        for path in self._temp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception:
                pass
        self._temp_files.clear()

    async def cleanup_async(self, scenario_name: str, pool: AsyncBackendPool):
        """Cleanup after async tests."""
        await pool.close(timeout=1.0)

        # Disconnect backends
        for backend in self._active_async_backends:
            try:
                await backend.disconnect()
            except Exception:
                pass
        self._active_async_backends.clear()

        # Clean up temp files
        for path in self._temp_files:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception:
                pass
        self._temp_files.clear()
