# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_async_backend_basic.py
"""
Basic async tests for AsyncSQLiteBackend

Tests basic async operations like connect, disconnect, execute, fetch, etc.
"""

import os
import pytest
import tempfile
import aiofiles
import pytest_asyncio

from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
# Import async backend from the same directory
from async_backend import AsyncSQLiteBackend


class TestAsyncSQLiteBackendBasic:
    """Test basic async operations"""

    @pytest_asyncio.fixture
    async def temp_db_path(self):
        """Create temporary database file path"""
        import aiofiles.os
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if await aiofiles.os.path.exists(path):
            try:
                await aiofiles.os.remove(path)
            except OSError:
                pass
        # Clean up related WAL and SHM files
        for ext in ['-wal', '-shm']:
            wal_path = path + ext
            if await aiofiles.os.path.exists(wal_path):
                try:
                    await aiofiles.os.remove(wal_path)
                except OSError:
                    pass

    @pytest_asyncio.fixture
    async def backend(self, temp_db_path):
        """Create async SQLite backend"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()
        yield backend
        await backend.disconnect()

    @pytest_asyncio.fixture
    async def memory_backend(self):
        """Create an in-memory async SQLite backend"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()
        yield backend
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, disconnected_backend):
        """Test connect and disconnect"""
        backend = disconnected_backend

        # Initially not connected
        assert not backend.is_connected()

        # Connect
        await backend.connect()
        assert backend.is_connected()

        # Disconnect
        await backend.disconnect()
        assert not backend.is_connected()

    @pytest.mark.asyncio
    async def test_memory_database(self, memory_backend):
        """Test with in-memory database"""
        # Create table
        result = await memory_backend.execute("""
                                       CREATE TABLE test
                                       (
                                           id   INTEGER PRIMARY KEY,
                                           name TEXT
                                       )
                                       """)

        # Insert data
        result = await memory_backend.execute(
            "INSERT INTO test (name) VALUES (?)",
            params=("test",)
        )
        assert result.affected_rows == 1
        assert result.last_insert_id is not None

        # Query data
        row = await memory_backend.fetch_one("SELECT * FROM test WHERE id = ?", params=(result.last_insert_id,))
        assert row is not None
        assert row['name'] == "test"

    @pytest.mark.asyncio
    async def test_execute_query(self, backend):
        """Test executing queries"""
        # Create table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id    INTEGER PRIMARY KEY,
                                  name  TEXT NOT NULL,
                                  email TEXT
                              )
                              """)

        # Insert data
        result = await backend.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            params=("Alice", "alice@example.com")
        )
        assert result.affected_rows == 1
        assert result.last_insert_id is not None

        # Query data
        result = await backend.execute(
            "SELECT * FROM users WHERE name = ?",
            params=("Alice",),
            returning=True
        )
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]['name'] == "Alice"

    @pytest.mark.asyncio
    async def test_fetch_one(self, backend):
        """Test fetch_one method"""
        # Create and populate table
        await backend.execute("""
                              CREATE TABLE items
                              (
                                  id    INTEGER PRIMARY KEY,
                                  value TEXT
                              )
                              """)
        await backend.execute("INSERT INTO items (value) VALUES ('test1'), ('test2')")

        # Fetch one
        row = await backend.fetch_one("SELECT * FROM items WHERE value = ?", params=("test1",))
        assert row is not None
        assert row['value'] == "test1"

        # Fetch non-existent
        row = await backend.fetch_one("SELECT * FROM items WHERE value = ?", params=("nonexistent",))
        assert row is None

    @pytest.mark.asyncio
    async def test_fetch_all(self, backend):
        """Test fetch_all method"""
        # Create and populate table
        await backend.execute("""
                              CREATE TABLE items
                              (
                                  id    INTEGER PRIMARY KEY,
                                  value TEXT
                              )
                              """)
        await backend.execute("INSERT INTO items (value) VALUES ('test1'), ('test2'), ('test3')")

        # Fetch all
        rows = await backend.fetch_all("SELECT * FROM items ORDER BY value")
        assert len(rows) == 3
        assert rows[0]['value'] == "test1"
        assert rows[1]['value'] == "test2"
        assert rows[2]['value'] == "test3"

        # Fetch with condition
        rows = await backend.fetch_all("SELECT * FROM items WHERE value LIKE ?", params=("test%",))
        assert len(rows) == 3

    @pytest_asyncio.fixture
    async def pragma_backend(self, temp_db_path):
        """Create an async SQLite backend with specific PRAGMA settings"""
        config = SQLiteConnectionConfig(
            database=temp_db_path,
            pragmas={"synchronous": "NORMAL", "cache_size": "5000"}
        )
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()
        yield backend
        await backend.disconnect()

    @pytest_asyncio.fixture
    async def disconnected_backend(self, temp_db_path):
        """Create a disconnected async SQLite backend for testing"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)
        yield backend
        # Ensure cleanup even if test connects the backend
        if backend.is_connected():
            await backend.disconnect()

    @pytest.mark.asyncio
    async def test_ping(self, disconnected_backend):
        """Test ping method"""
        backend = disconnected_backend

        # Not connected, should reconnect
        result = await backend.ping(reconnect=True)
        assert result is True
        assert backend.is_connected()

        # Already connected, should return True
        result = await backend.ping(reconnect=False)
        assert result is True

    @pytest.mark.asyncio
    async def test_pragma_settings(self, pragma_backend):
        """Test PRAGMA settings"""
        # Verify pragma settings
        assert pragma_backend.pragmas["synchronous"] == "NORMAL"
        assert pragma_backend.pragmas["cache_size"] == "5000"

        # Query actual pragma values
        result = await pragma_backend.fetch_one("PRAGMA synchronous")
        assert result["synchronous"] == 1  # NORMAL = 1

        result = await pragma_backend.fetch_one("PRAGMA cache_size")
        assert result["cache_size"] == 5000

    @pytest.mark.asyncio
    async def test_server_version(self, memory_backend):
        """Test get_server_version"""
        version = memory_backend.get_server_version()
        assert isinstance(version, tuple)
        assert len(version) == 3
        assert all(isinstance(v, int) for v in version)

    @pytest.mark.asyncio
    async def test_error_handling(self, backend):
        """Test error handling"""
        # Create table
        await backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")

        # Try to insert duplicate
        await backend.execute("INSERT INTO test (id) VALUES (1)")

        with pytest.raises(Exception):  # Should raise IntegrityError
            await backend.execute("INSERT INTO test (id) VALUES (1)")

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_db_path):
        """Test async context manager"""
        config = SQLiteConnectionConfig(database=temp_db_path)

        async with AsyncSQLiteBackend(connection_config=config) as backend:
            assert backend.is_connected()

            # Create table and insert data
            await backend.execute("""
                                  CREATE TABLE test
                                  (
                                      id    INTEGER PRIMARY KEY,
                                      value TEXT
                                  )
                                  """)
            await backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",))

        # Should be disconnected after context
        assert not backend.is_connected()

    @pytest.mark.asyncio
    async def test_auto_connect(self, disconnected_backend):
        """Test auto-connect on execute"""
        backend = disconnected_backend

        # Not connected initially
        assert not backend.is_connected()

        # Execute should auto-connect
        await backend.execute("CREATE TABLE test (id INTEGER)")

        # Now connected
        assert backend.is_connected()

    @pytest.mark.asyncio
    async def test_delete_on_close(self):
        """Test delete_on_close option"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        try:
            config = SQLiteConnectionConfig(database=path, delete_on_close=True)
            backend = AsyncSQLiteBackend(connection_config=config)

            await backend.connect()
            await backend.execute("CREATE TABLE test (id INTEGER)")

            # File should exist
            assert await aiofiles.os.path.exists(path)

            # Disconnect
            await backend.disconnect()

            # File should be deleted
            assert not await aiofiles.os.path.exists(path)
        finally:
            # Cleanup if test fails
            if await aiofiles.os.path.exists(path):
                await aiofiles.os.remove(path)

    @pytest.mark.asyncio
    async def test_supports_returning(self, memory_backend):
        """Test supports_returning property"""
        # Check based on version
        version = memory_backend.get_server_version()
        expected = version >= (3, 35, 0)

        assert memory_backend.supports_returning == expected

    @pytest.mark.asyncio
    async def test_is_sqlite_property(self, memory_backend):
        """Test is_sqlite property"""
        assert memory_backend.is_sqlite is True

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, memory_backend):
        """Test multiple concurrent operations"""
        import asyncio

        # Create table
        await memory_backend.execute("""
                              CREATE TABLE concurrent_test
                              (
                                  id    INTEGER PRIMARY KEY,
                                  value TEXT
                              )
                              """)

        # Run multiple inserts concurrently
        async def insert_value(i):
            await memory_backend.execute(
                "INSERT INTO concurrent_test (value) VALUES (?)",
                params=(f"value{i}",)
            )

        # Note: SQLite doesn't support true concurrent writes, but this tests the async interface
        tasks = [insert_value(i) for i in range(5)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all inserted
        rows = await memory_backend.fetch_all("SELECT * FROM concurrent_test ORDER BY id")
        assert len(rows) >= 1  # At least one should succeed

    @pytest.mark.asyncio
    async def test_parameterized_queries(self, backend):
        """Test different parameter formats"""
        await backend.execute("""
                              CREATE TABLE param_test
                              (
                                  id    INTEGER PRIMARY KEY,
                                  name  TEXT,
                                  value INTEGER
                              )
                              """)

        # Tuple params
        result = await backend.execute(
            "INSERT INTO param_test (name, value) VALUES (?, ?)",
            params=("test1", 100)
        )
        assert result.affected_rows == 1

        # Dict params
        result = await backend.execute(
            "INSERT INTO param_test (name, value) VALUES (?, ?)",
            params={"name": "test2", "value": 200}
        )
        assert result.affected_rows == 1

        # List params
        result = await backend.execute(
            "INSERT INTO param_test (name, value) VALUES (?, ?)",
            params=["test3", 300]
        )
        assert result.affected_rows == 1

        # Verify all inserted
        rows = await backend.fetch_all("SELECT * FROM param_test ORDER BY id")
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_query_duration_tracking(self, backend):
        """Test that query duration is tracked"""
        await backend.execute("CREATE TABLE test (id INTEGER)")

        result = await backend.execute("INSERT INTO test (id) VALUES (1)")

        assert result.duration > 0
        assert isinstance(result.duration, float)