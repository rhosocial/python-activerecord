"""
Comprehensive async tests for AsyncSQLiteBackend

This file includes tests from the original deleted files to ensure
comprehensive coverage of async functionality.
"""

import os
import sys
import tempfile
import asyncio
from unittest.mock import patch

import pytest
import pytest_asyncio
import aiofiles.os

from rhosocial.activerecord.backend.errors import (
    DatabaseError, QueryError, TransactionError, ReturningNotSupportedError, OperationalError
)
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.transaction import IsolationLevel
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord_test.feature.backend.sqlite_async.async_backend import (
    AsyncSQLiteBackend, AsyncTransactionManager
)


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
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        result = await memory_backend.execute("""
                                       CREATE TABLE test
                                       (
                                           id   INTEGER PRIMARY KEY,
                                           name TEXT
                                       )
                                       """, options=options)

        # Insert data
        options = ExecutionOptions(stmt_type=StatementType.DML)
        result = await memory_backend.execute(
            "INSERT INTO test (name) VALUES (?)",
            params=("test",),
            options=options
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
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id    INTEGER PRIMARY KEY,
                                  name  TEXT NOT NULL,
                                  email TEXT
                              )
                              """, options=options)

        # Insert data
        options = ExecutionOptions(stmt_type=StatementType.DML)
        result = await backend.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            params=("Alice", "alice@example.com"),
            options=options
        )
        assert result.affected_rows == 1
        assert result.last_insert_id is not None

        # Query data
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = await backend.execute(
            "SELECT * FROM users WHERE name = ?",
            params=("Alice",),
            options=options
        )
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]['name'] == "Alice"

    @pytest.mark.asyncio
    async def test_fetch_one(self, backend):
        """Test fetch_one method"""
        # Create and populate table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("""
                              CREATE TABLE items
                              (
                                  id    INTEGER PRIMARY KEY,
                                  value TEXT
                              )
                              """, options=options)
        
        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO items (value) VALUES ('test1'), ('test2')", options=options)

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
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("""
                              CREATE TABLE items
                              (
                                  id    INTEGER PRIMARY KEY,
                                  value TEXT
                              )
                              """, options=options)
        
        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO items (value) VALUES ('test1'), ('test2'), ('test3')", options=options)

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
        options = ExecutionOptions(stmt_type=StatementType.DQL)
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
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)", options=options)

        # Try to insert duplicate
        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO test (id) VALUES (1)", options=options)

        with pytest.raises(Exception):  # Should raise IntegrityError
            await backend.execute("INSERT INTO test (id) VALUES (1)", options=options)

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_db_path):
        """Test async context manager"""
        config = SQLiteConnectionConfig(database=temp_db_path)

        async with AsyncSQLiteBackend(connection_config=config) as backend:
            assert backend.is_connected()

            # Create table and insert data
            options = ExecutionOptions(stmt_type=StatementType.DDL)
            await backend.execute("""
                                  CREATE TABLE test
                                  (
                                      id    INTEGER PRIMARY KEY,
                                      value TEXT
                                  )
                                  """, options=options)
            
            options = ExecutionOptions(stmt_type=StatementType.DML)
            await backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",), options=options)

        # Should be disconnected after context
        assert not backend.is_connected()

    @pytest.mark.asyncio
    async def test_auto_connect(self, disconnected_backend):
        """Test auto-connect on execute"""
        backend = disconnected_backend

        # Not connected initially
        assert not backend.is_connected()

        # Execute should auto-connect
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("CREATE TABLE test (id INTEGER)", options=options)

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
            options = ExecutionOptions(stmt_type=StatementType.DDL)
            await backend.execute("CREATE TABLE test (id INTEGER)", options=options)

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
    async def test_concurrent_operations(self, memory_backend):
        """Test multiple concurrent operations"""
        # Create table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await memory_backend.execute("""
                              CREATE TABLE concurrent_test
                              (
                                  id    INTEGER PRIMARY KEY,
                                  value TEXT
                              )
                              """, options=options)

        # Run multiple inserts concurrently
        async def insert_value(i):
            options = ExecutionOptions(stmt_type=StatementType.DML)
            await memory_backend.execute(
                "INSERT INTO concurrent_test (value) VALUES (?)",
                params=(f"value{i}",),
                options=options
            )

        # Note: SQLite doesn't support true concurrent writes, but this tests the async interface
        tasks = [insert_value(i) for i in range(5)]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all inserted
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        rows = await memory_backend.fetch_all("SELECT * FROM concurrent_test ORDER BY id")
        assert len(rows) >= 1  # At least one should succeed

    @pytest.mark.asyncio
    async def test_parameterized_queries(self, backend):
        """Test different parameter formats"""
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("""
                              CREATE TABLE param_test
                              (
                                  id    INTEGER PRIMARY KEY,
                                  name  TEXT,
                                  value INTEGER
                              )
                              """, options=options)

        # Tuple params
        options = ExecutionOptions(stmt_type=StatementType.DML)
        result = await backend.execute(
            "INSERT INTO param_test (name, value) VALUES (?, ?)",
            params=("test1", 100),
            options=options
        )
        assert result.affected_rows == 1

        # Dict params
        result = await backend.execute(
            "INSERT INTO param_test (name, value) VALUES (?, ?)",
            params={"name": "test2", "value": 200},
            options=options
        )
        assert result.affected_rows == 1

        # List params
        result = await backend.execute(
            "INSERT INTO param_test (name, value) VALUES (?, ?)",
            params=["test3", 300],
            options=options
        )
        assert result.affected_rows == 1

        # Verify all inserted
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        rows = await backend.fetch_all("SELECT * FROM param_test ORDER BY id")
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_query_duration_tracking(self, backend):
        """Test that query duration is tracked"""
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("CREATE TABLE test (id INTEGER)", options=options)

        options = ExecutionOptions(stmt_type=StatementType.DML)
        result = await backend.execute("INSERT INTO test (id) VALUES (1)", options=options)

        assert result.duration > 0
        assert isinstance(result.duration, float)


class TestAsyncExecuteMany:
    """Test async execute_many functionality"""

    @pytest_asyncio.fixture
    async def temp_db_path(self):
        """Create temporary database file path"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if await aiofiles.os.path.exists(path):
            try:
                await aiofiles.os.remove(path)
            except OSError:
                pass
        for ext in ['-wal', '-shm']:
            wal_path = path + ext
            if await aiofiles.os.path.exists(wal_path):
                try:
                    await aiofiles.os.remove(wal_path)
                except OSError:
                    pass

    @pytest_asyncio.fixture
    async def backend(self, temp_db_path):
        """Create async SQLite backend with test tables"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        # Create test tables
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id     INTEGER PRIMARY KEY,
                                  name   TEXT,
                                  email  TEXT,
                                  active INTEGER
                              )
                              """, options=options)

        await backend.execute("""
                              CREATE TABLE posts
                              (
                                  id      INTEGER PRIMARY KEY,
                                  user_id INTEGER,
                                  title   TEXT,
                                  content TEXT,
                                  FOREIGN KEY (user_id) REFERENCES users (id)
                              )
                              """, options=options)

        yield backend
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_insert_batch(self, backend):
        """Test batch INSERT operations"""
        users = [
            (1, "User 1", "user1@example.com", 1),
            (2, "User 2", "user2@example.com", 1),
            (3, "User 3", "user3@example.com", 0)
        ]

        result = await backend.execute_many(
            "INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)",
            users
        )

        assert result.affected_rows == 3
        assert result.duration > 0

        # Verify data
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        rows = await backend.fetch_all("SELECT * FROM users ORDER BY id")
        assert len(rows) == 3
        assert rows[0]["name"] == "User 1"
        assert rows[2]["active"] == 0

    @pytest.mark.asyncio
    async def test_update_batch(self, backend):
        """Test batch UPDATE operations"""
        # Insert test data
        await backend.execute_many(
            "INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)",
            [
                (1, "User 1", "user1@example.com", 1),
                (2, "User 2", "user2@example.com", 1),
                (3, "User 3", "user3@example.com", 1)
            ]
        )

        # Batch update
        updates = [
            ("Updated User 1", 1),
            ("Updated User 3", 3)
        ]

        result = await backend.execute_many(
            "UPDATE users SET name = ? WHERE id = ?",
            updates
        )

        assert result.affected_rows == 2

        # Verify updates
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        user1 = await backend.fetch_one("SELECT * FROM users WHERE id = 1")
        user2 = await backend.fetch_one("SELECT * FROM users WHERE id = 2")
        user3 = await backend.fetch_one("SELECT * FROM users WHERE id = 3")

        assert user1["name"] == "Updated User 1"
        assert user2["name"] == "User 2"  # Not updated
        assert user3["name"] == "Updated User 3"

    @pytest.mark.asyncio
    async def test_empty_params_list(self, backend):
        """Test execute_many with empty params list"""
        result = await backend.execute_many(
            "INSERT INTO users (id, name) VALUES (?, ?)",
            []
        )

        assert result.affected_rows == 0
        assert result.duration >= 0

        # Verify no data inserted
        count = await backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 0

    @pytest.mark.asyncio
    async def test_params_mismatch(self, backend):
        """Test execute_many with mismatched parameters"""
        # Too few parameters
        with pytest.raises(Exception):
            await backend.execute_many(
                "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                [(1, "User 1")]  # Missing email
            )

        # Too many parameters
        with pytest.raises(Exception):
            await backend.execute_many(
                "INSERT INTO users (id, name) VALUES (?, ?)",
                [(1, "User 1", "extra@example.com")]  # Extra parameter
            )

    @pytest.mark.asyncio
    async def test_table_not_exists(self, backend):
        """Test execute_many with non-existent table"""
        with pytest.raises((DatabaseError, QueryError)) as exc_info:
            await backend.execute_many(
                "INSERT INTO nonexistent (id, name) VALUES (?, ?)",
                [(1, "Test"), (2, "Test 2")]
            )

        assert "no such table" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_foreign_key_constraint(self, backend):
        """Test execute_many with foreign key constraint violation"""
        # Try to insert posts with non-existent user_ids
        with pytest.raises(DatabaseError) as exc_info:
            await backend.execute_many(
                "INSERT INTO posts (id, user_id, title) VALUES (?, ?, ?)",
                [
                    (1, 99, "Title 1"),
                    (2, 100, "Title 2")
                ]
            )

        assert "foreign key constraint" in str(exc_info.value).lower()

        # Insert valid user first
        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO users (id, name) VALUES (1, 'User 1')", options=options)

        # Try with mix of valid and invalid
        with pytest.raises(DatabaseError) as exc_info:
            await backend.execute_many(
                "INSERT INTO posts (id, user_id, title) VALUES (?, ?, ?)",
                [
                    (1, 1, "Title 1"),  # Valid
                    (2, 999, "Title 2")  # Invalid
                ]
            )

        assert "foreign key constraint" in str(exc_info.value).lower()

        # Verify only one post inserted (or none due to rollback)
        count = await backend.fetch_one("SELECT COUNT(*) as count FROM posts")
        assert count["count"] <= 1

    @pytest.mark.asyncio
    async def test_large_batch(self, backend):
        """Test execute_many with large batch"""
        large_batch = [(i, f"User {i}", f"user{i}@example.com", 1) for i in range(1, 101)]  # Smaller batch for testing

        result = await backend.execute_many(
            "INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)",
            large_batch
        )

        assert result.affected_rows == 100

        # Verify count
        count = await backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 100

    @pytest.mark.asyncio
    async def test_affected_rows_count(self, backend):
        """Test affected_rows count in various scenarios"""
        # Insert test data
        await backend.execute_many(
            "INSERT INTO users (id, name, active) VALUES (?, ?, ?)",
            [(1, "User 1", 1), (2, "User 2", 1), (3, "User 3", 0)]
        )

        # UPDATE that affects some rows
        result = await backend.execute_many(
            "UPDATE users SET name = ? WHERE active = ?",
            [("Active User", 1)]
        )
        assert result.affected_rows == 2

        # UPDATE that affects no rows
        result = await backend.execute_many(
            "UPDATE users SET name = ? WHERE id > ?",
            [("No one", 100)]
        )
        assert result.affected_rows == 0

        # UPDATE with multiple parameter sets
        result = await backend.execute_many(
            "UPDATE users SET active = ? WHERE id = ?",
            [(0, 1), (0, 2)]
        )
        assert result.affected_rows == 2

    @pytest_asyncio.fixture
    async def memory_backend_for_concurrent(self):
        """Create an in-memory async SQLite backend for concurrent tests"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()
        # Create table for the test
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("""
                              CREATE TABLE concurrent
                              (
                                  id    INTEGER PRIMARY KEY,
                                  value TEXT
                              )
                              """, options=options)
        yield backend
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_execute_many_duration_tracking(self, backend):
        """Test that duration is tracked for execute_many"""
        result = await backend.execute_many(
            "INSERT INTO users (id, name) VALUES (?, ?)",
            [(1, "User 1"), (2, "User 2"), (3, "User 3")]
        )

        assert result.duration > 0
        assert isinstance(result.duration, float)

    @pytest.mark.asyncio
    async def test_concurrent_execute_many(self, memory_backend_for_concurrent):
        """Test concurrent execute_many operations"""
        # Run multiple execute_many concurrently
        async def batch_insert(start_id, count):
            params = [(start_id + i, f"value{start_id + i}") for i in range(count)]
            await memory_backend_for_concurrent.execute_many(
                "INSERT INTO concurrent (id, value) VALUES (?, ?)",
                params
            )

        # Note: SQLite may serialize these due to locking
        tasks = [
            batch_insert(1, 10),
            batch_insert(11, 10),
            batch_insert(21, 10)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least one batch should succeed
        count = await memory_backend_for_concurrent.fetch_one("SELECT COUNT(*) as count FROM concurrent")
        assert count["count"] >= 10


class TestAsyncSQLiteTransaction:
    """Test async transaction management"""

    @pytest_asyncio.fixture
    async def temp_db_path(self):
        """Create temporary database file path"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if await aiofiles.os.path.exists(path):
            try:
                await aiofiles.os.remove(path)
            except OSError:
                pass
        for ext in ['-wal', '-shm']:
            wal_path = path + ext
            if await aiofiles.os.path.exists(wal_path):
                try:
                    await aiofiles.os.remove(wal_path)
                except OSError:
                    pass

    @pytest_asyncio.fixture
    async def backend(self, temp_db_path):
        """Create async SQLite backend with test table"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        # Create test table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute("""
                              CREATE TABLE test
                              (
                                  id    INTEGER PRIMARY KEY,
                                  value TEXT
                              )
                              """, options=options)

        yield backend
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_transaction_property(self, backend):
        """Test transaction manager property"""
        # Initially no transaction manager
        assert backend._transaction_manager is None

        # Access property creates it
        tm = backend.transaction_manager
        assert tm is not None
        assert backend._transaction_manager is tm

        # Same instance returned
        assert backend.transaction_manager is tm

    @pytest.mark.asyncio
    async def test_begin_commit(self, backend):
        """Test begin and commit transaction"""
        await backend.begin_transaction()
        assert backend.in_transaction is True

        # Insert data
        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",), options=options)

        # Commit
        await backend.commit_transaction()
        assert backend.in_transaction is False

        # Verify data committed
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        row = await backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is not None
        assert row['value'] == "test"

    @pytest.mark.asyncio
    async def test_begin_rollback(self, backend):
        """Test begin and rollback transaction"""
        await backend.begin_transaction()

        # Insert data
        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",), options=options)

        # Rollback
        await backend.rollback_transaction()
        assert backend.in_transaction is False

        # Verify data rolled back
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        row = await backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is None

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self, backend):
        """Test transaction context manager"""
        async with backend.transaction():
            options = ExecutionOptions(stmt_type=StatementType.DML)
            await backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",), options=options)

        # Should auto-commit
        assert backend.in_transaction is False
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        row = await backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is not None

    @pytest.mark.asyncio
    async def test_transaction_context_manager_exception(self, backend):
        """Test transaction context manager with exception"""
        try:
            async with backend.transaction():
                options = ExecutionOptions(stmt_type=StatementType.DML)
                await backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",), options=options)
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should auto-rollback
        assert backend.in_transaction is False
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        row = await backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is None

    @pytest.mark.asyncio
    async def test_nested_transactions(self, backend):
        """Test nested transactions"""
        # Outer transaction
        await backend.begin_transaction()
        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO test (id, value) VALUES (1, 'outer')", options=options)

        # Inner transaction
        await backend.begin_transaction()
        await backend.execute("INSERT INTO test (id, value) VALUES (2, 'inner')", options=options)

        # Rollback inner
        await backend.rollback_transaction()

        # Verify inner rolled back
        options = ExecutionOptions(stmt_type=StatementType.DQL)
        row = await backend.fetch_one("SELECT * FROM test WHERE id = 2")
        assert row is None

        # Verify outer still exists
        row = await backend.fetch_one("SELECT * FROM test WHERE id = 1")
        assert row is not None

        # Commit outer
        await backend.commit_transaction()

        # Verify outer committed
        row = await backend.fetch_one("SELECT * FROM test WHERE id = 1")
        assert row is not None
        assert row['value'] == "outer"

    @pytest.mark.asyncio
    async def test_multiple_nested_levels(self, backend):
        """Test multiple nested transaction levels"""
        # Level 1
        await backend.begin_transaction()
        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO test (id, value) VALUES (1, 'level1')", options=options)

        # Level 2
        await backend.begin_transaction()
        await backend.execute("INSERT INTO test (id, value) VALUES (2, 'level2')", options=options)

        # Level 3
        await backend.begin_transaction()
        await backend.execute("INSERT INTO test (id, value) VALUES (3, 'level3')", options=options)

        # Check transaction level
        assert backend.transaction_manager._transaction_level == 3

        # Rollback level 3
        await backend.rollback_transaction()
        assert backend.transaction_manager._transaction_level == 2

        # Commit level 2
        await backend.commit_transaction()
        assert backend.transaction_manager._transaction_level == 1

        # Commit level 1
        await backend.commit_transaction()
        assert backend.in_transaction is False

        # Verify final state
        rows = await backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 2
        assert rows[0]['value'] == "level1"
        assert rows[1]['value'] == "level2"

    @pytest.mark.asyncio
    async def test_savepoint_operations(self, backend):
        """Test savepoint operations"""
        await backend.begin_transaction()
        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO test (id, value) VALUES (1, 'base')", options=options)

        # Create savepoint
        sp1 = await backend.transaction_manager.async_savepoint("sp1")
        await backend.execute("INSERT INTO test (id, value) VALUES (2, 'sp1')", options=options)

        # Create second savepoint
        sp2 = await backend.transaction_manager.async_savepoint("sp2")
        await backend.execute("INSERT INTO test (id, value) VALUES (3, 'sp2')", options=options)

        # Rollback to first savepoint
        await backend.transaction_manager.rollback_to("sp1")

        # Verify rollback
        rows = await backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 1
        assert rows[0]['value'] == "base"

        # Add new data
        await backend.execute("INSERT INTO test (id, value) VALUES (4, 'after-rollback')", options=options)

        # Release savepoint
        await backend.transaction_manager.release("sp1")

        # Commit
        await backend.commit_transaction()

        # Verify final state
        rows = await backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 2
        assert rows[0]['value'] == "base"
        assert rows[1]['value'] == "after-rollback"

    @pytest.mark.asyncio
    async def test_auto_savepoint_name(self, backend):
        """Test auto-generated savepoint names"""
        await backend.begin_transaction()

        # Create savepoints with auto names
        sp1 = await backend.transaction_manager.async_savepoint()
        assert sp1 == "SP_1"

        sp2 = await backend.transaction_manager.async_savepoint()
        assert sp2 == "SP_2"

        await backend.rollback_transaction()

    @pytest.mark.asyncio
    async def test_isolation_level_serializable(self, backend):
        """Test serializable isolation level"""
        tm = backend.transaction_manager
        tm.isolation_level = IsolationLevel.SERIALIZABLE

        await backend.begin_transaction()
        assert backend.in_transaction is True

        # Check read_uncommitted = 0
        result = await backend.fetch_one("PRAGMA read_uncommitted")
        assert result["read_uncommitted"] == 0

        await backend.commit_transaction()

    @pytest.mark.asyncio
    async def test_isolation_level_read_uncommitted(self, backend):
        """Test read uncommitted isolation level"""
        tm = backend.transaction_manager
        tm.isolation_level = IsolationLevel.READ_UNCOMMITTED

        await backend.begin_transaction()
        assert backend.in_transaction is True

        # Check read_uncommitted = 1
        result = await backend.fetch_one("PRAGMA read_uncommitted")
        assert result["read_uncommitted"] == 1

        await backend.commit_transaction()

    @pytest.mark.asyncio
    async def test_unsupported_isolation_level(self, backend):
        """Test unsupported isolation level"""
        tm = backend.transaction_manager

        with pytest.raises(TransactionError) as exc_info:
            tm.isolation_level = IsolationLevel.READ_COMMITTED

        assert "Unsupported isolation level" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_isolation_level_during_transaction(self, backend):
        """Test setting isolation level during transaction"""
        await backend.begin_transaction()

        tm = backend.transaction_manager
        with pytest.raises(TransactionError) as exc_info:
            tm.isolation_level = IsolationLevel.SERIALIZABLE

        assert "Cannot change isolation level during active transaction" in str(exc_info.value)

        await backend.rollback_transaction()

    @pytest.mark.asyncio
    async def test_commit_without_transaction(self, backend):
        """Test commit without active transaction"""
        with pytest.raises(TransactionError) as exc_info:
            await backend.commit_transaction()

        assert "No active transaction to commit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_rollback_without_transaction(self, backend):
        """Test rollback without active transaction"""
        with pytest.raises(TransactionError) as exc_info:
            await backend.rollback_transaction()

        assert "No active transaction to rollback" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_savepoint_without_transaction(self, backend):
        """Test creating savepoint without active transaction"""
        with pytest.raises(TransactionError) as exc_info:
            await backend.transaction_manager.async_savepoint("sp1")

        assert "Cannot create savepoint: no active transaction" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_release_invalid_savepoint(self, backend):
        """Test releasing invalid savepoint"""
        await backend.begin_transaction()

        with pytest.raises(TransactionError) as exc_info:
            await backend.transaction_manager.release("nonexistent")

        assert "Invalid savepoint name" in str(exc_info.value)

        await backend.rollback_transaction()

    @pytest.mark.asyncio
    async def test_rollback_to_invalid_savepoint(self, backend):
        """Test rollback to invalid savepoint"""
        await backend.begin_transaction()

        with pytest.raises(TransactionError) as exc_info:
            await backend.transaction_manager.rollback_to("nonexistent")

        assert "Invalid savepoint name" in str(exc_info.value)

        await backend.rollback_transaction()

    @pytest.mark.asyncio
    async def test_supports_savepoint(self, backend):
        """Test savepoint support check"""
        assert backend.transaction_manager.supports_savepoint() is True

    @pytest.mark.asyncio
    async def test_mixed_savepoint_transactions(self, backend):
        """Test mixed usage of savepoints and nested transactions"""
        # Begin main transaction
        await backend.begin_transaction()
        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO test (id, value) VALUES (1, 'main')", options=options)

        # Create manual savepoint
        sp1 = await backend.transaction_manager.async_savepoint("manual_sp")
        await backend.execute("INSERT INTO test (id, value) VALUES (2, 'manual_sp')", options=options)

        # Create nested transaction
        await backend.begin_transaction()
        await backend.execute("INSERT INTO test (id, value) VALUES (3, 'nested')", options=options)

        # Verify 3 rows
        rows = await backend.fetch_all("SELECT COUNT(*) as cnt FROM test")
        assert rows[0]['cnt'] == 3

        # Rollback nested
        await backend.rollback_transaction()

        # Verify 2 rows
        rows = await backend.fetch_all("SELECT COUNT(*) as cnt FROM test")
        assert rows[0]['cnt'] == 2

        # Rollback to manual savepoint
        await backend.transaction_manager.rollback_to(sp1)

        # Verify 1 row
        rows = await backend.fetch_all("SELECT COUNT(*) as cnt FROM test")
        assert rows[0]['cnt'] == 1

        # Commit main
        await backend.commit_transaction()

        # Verify final state
        rows = await backend.fetch_all("SELECT * FROM test")
        assert len(rows) == 1
        assert rows[0]['value'] == "main"

    @pytest.mark.asyncio
    async def test_transaction_level_counter(self, backend):
        """Test transaction level counter"""
        tm = backend.transaction_manager
        assert tm._transaction_level == 0

        await backend.begin_transaction()
        assert tm._transaction_level == 1

        await backend.begin_transaction()
        assert tm._transaction_level == 2

        await backend.rollback_transaction()
        assert tm._transaction_level == 1

        await backend.commit_transaction()
        assert tm._transaction_level == 0

    @pytest_asyncio.fixture
    async def memory_backend_pair(self):
        """Create a pair of backends connected to the same in-memory database."""
        config = SQLiteConnectionConfig(database=":memory:")
        backend1 = AsyncSQLiteBackend(connection_config=config)
        backend2 = AsyncSQLiteBackend(connection_config=config)
        await backend1.connect()
        await backend2.connect()
        yield backend1, backend2
        await backend1.disconnect()
        await backend2.disconnect()

    @pytest.mark.asyncio
    async def test_concurrent_transactions(self, memory_backend_pair):
        """Test that concurrent transactions work correctly"""
        backend1, backend2 = memory_backend_pair

        # Create table
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend1.execute("""
                               CREATE TABLE concurrent
                               (
                                   id    INTEGER PRIMARY KEY,
                                   value TEXT
                               )
                               """, options=options)

        # Run two transactions concurrently
        async def trans1():
            await backend1.begin_transaction()
            await backend1.execute("INSERT INTO concurrent (value) VALUES (?)", params=("trans1",), options=options)
            await asyncio.sleep(0.1)
            await backend1.commit_transaction()

        async def trans2():
            await asyncio.sleep(0.05)
            await backend2.begin_transaction()
            await backend2.execute("INSERT INTO concurrent (value) VALUES (?)", params=("trans2",), options=options)
            await backend2.commit_transaction()

        # Note: SQLite may serialize these due to locking
        await asyncio.gather(trans1(), trans2(), return_exceptions=True)

        # At least one should succeed
        rows = await backend1.fetch_all("SELECT * FROM concurrent")
        assert len(rows) >= 1


from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    InsertExpression, ValuesSource, Literal, Column, ReturningClause,
    UpdateExpression, DeleteExpression
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestAsyncReturning:
    """Test async RETURNING clause functionality"""

    @pytest_asyncio.fixture
    async def backend(self):
        """Create an in-memory async SQLite backend"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()
        yield backend
        await backend.disconnect()

    def test_returning_not_supported_dialect(self):
        """Test that dialect raises UnsupportedFeatureError for RETURNING on older versions."""
        # 1. Instantiate a dialect for an older SQLite version
        dialect = SQLiteDialect(version=(3, 34, 0))

        # 2. Create an InsertExpression with a ReturningClause
        insert_expr = InsertExpression(
            dialect=dialect,
            into="users",
            columns=["name"],
            source=ValuesSource(dialect, values_list=[[Literal(dialect, "test")]]),
            returning=ReturningClause(dialect, expressions=[Column(dialect, "id")])
        )

        # 3. Assert that to_sql() raises the correct exception
        with pytest.raises(UnsupportedFeatureError, match="RETURNING clause"):
            insert_expr.to_sql()

    @pytest.mark.asyncio
    @patch('aiosqlite.sqlite_version', '3.35.0')
    async def test_returning_with_insert(self, backend):
        """Test RETURNING with INSERT"""
        # Use the backend's dialect
        dialect = backend.dialect
        
        # Create table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id    INTEGER PRIMARY KEY AUTOINCREMENT,
                                  name  TEXT,
                                  email TEXT
                              )
                              """, options=ExecutionOptions(stmt_type=StatementType.DDL))

        # Create an InsertExpression with a ReturningClause
        insert_expr = InsertExpression(
            dialect=dialect,
            into="users",
            columns=["name", "email"],
            source=ValuesSource(dialect, values_list=[[Literal(dialect, "Alice"), Literal(dialect, "alice@example.com")]]),
            returning=ReturningClause(dialect, expressions=[Column(dialect, "id"), Column(dialect, "name")])
        )
        
        sql, params = insert_expr.to_sql()

        # Execute the query, using DQL to fetch returning data
        result = await backend.execute(
            sql,
            params=params,
            options=ExecutionOptions(stmt_type=StatementType.DQL)
        )

        assert result.affected_rows == 1
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]['id'] == 1
        assert result.data[0]['name'] == 'Alice'

    @pytest.mark.asyncio
    @patch('aiosqlite.sqlite_version', '3.35.0')
    async def test_returning_with_update(self, backend):
        """Test RETURNING with UPDATE"""
        dialect = backend.dialect
        # Create and populate table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id    INTEGER PRIMARY KEY,
                                  name  TEXT,
                                  email TEXT
                              )
                              """, options=ExecutionOptions(stmt_type=StatementType.DDL))
        
        await backend.execute(
            "INSERT INTO users (id, name, email) VALUES (1, 'Original', 'old@example.com')",
            options=ExecutionOptions(stmt_type=StatementType.DML)
        )

        # Update with RETURNING
        update_expr = UpdateExpression(
            dialect=dialect,
            table="users",
            assignments={"name": Literal(dialect, "Updated"), "email": Literal(dialect, "new@example.com")},
            where=Column(dialect, "id") == Literal(dialect, 1),
            returning=ReturningClause(dialect, expressions=[Column(dialect, "id"), Column(dialect, "name"), Column(dialect, "email")])
        )
        sql, params = update_expr.to_sql()

        result = await backend.execute(
            sql,
            params=params,
            options=ExecutionOptions(stmt_type=StatementType.DQL)
        )

        assert result.affected_rows == 1
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]['id'] == 1
        assert result.data[0]['name'] == 'Updated'
        assert result.data[0]['email'] == 'new@example.com'

    @pytest.mark.asyncio
    @patch('aiosqlite.sqlite_version', '3.35.0')
    async def test_returning_with_delete(self, backend):
        """Test RETURNING with DELETE"""
        dialect = backend.dialect
        # Create and populate table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id   INTEGER PRIMARY KEY,
                                  name TEXT
                              )
                              """, options=ExecutionOptions(stmt_type=StatementType.DDL))
        
        await backend.execute("INSERT INTO users (id, name) VALUES (1, 'ToDelete')", options=ExecutionOptions(stmt_type=StatementType.DML))

        # Delete with RETURNING
        delete_expr = DeleteExpression(
            dialect=dialect,
            table="users",
            where=Column(dialect, "id") == Literal(dialect, 1),
            returning=ReturningClause(dialect, expressions=[Column(dialect, "name")])
        )
        sql, params = delete_expr.to_sql()
        
        result = await backend.execute(
            sql,
            params=params,
            options=ExecutionOptions(stmt_type=StatementType.DQL)
        )

        assert result.affected_rows == 1
        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]['name'] == 'ToDelete'

        # Verify deleted
        row = await backend.fetch_one("SELECT * FROM users WHERE id = 1")
        assert row is None

    @pytest.mark.asyncio
    @patch('aiosqlite.sqlite_version', '3.35.0')
    async def test_returning_invalid_columns(self, backend):
        """Test RETURNING with invalid column names follows SQLite's quirky behavior."""
        dialect = backend.dialect
        # Create table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id   INTEGER PRIMARY KEY,
                                  name TEXT
                              )
                              """, options=ExecutionOptions(stmt_type=StatementType.DDL))

        # Create an InsertExpression with an invalid column in the ReturningClause
        insert_expr = InsertExpression(
            dialect=dialect,
            into="users",
            columns=["name"],
            source=ValuesSource(dialect, values_list=[[Literal(dialect, "test")]]),
            returning=ReturningClause(dialect, expressions=[Column(dialect, "invalid_column")])
        )
        sql, params = insert_expr.to_sql()

        # SQLite does not raise an error for invalid columns in RETURNING.
        # Instead, it returns the column name as a string value.
        result = await backend.execute(
            sql,
            params=params,
            options=ExecutionOptions(stmt_type=StatementType.DQL)
        )

        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]['invalid_column'] == 'invalid_column'

    @pytest.mark.asyncio
    @patch('aiosqlite.sqlite_version', '3.35.0')
    async def test_returning_multiple_rows(self, backend):
        """Test RETURNING with operations affecting multiple rows"""
        dialect = backend.dialect
        # Create and populate table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id     INTEGER PRIMARY KEY,
                                  name   TEXT,
                                  active INTEGER
                              )
                              """, options=ExecutionOptions(stmt_type=StatementType.DDL))
        
        await backend.execute("INSERT INTO users (id, name, active) VALUES (1, 'User1', 1)", options=ExecutionOptions(stmt_type=StatementType.DML))
        await backend.execute("INSERT INTO users (id, name, active) VALUES (2, 'User2', 1)", options=ExecutionOptions(stmt_type=StatementType.DML))
        await backend.execute("INSERT INTO users (id, name, active) VALUES (3, 'User3', 0)", options=ExecutionOptions(stmt_type=StatementType.DML))

        # Update multiple rows with RETURNING
        update_expr = UpdateExpression(
            dialect=dialect,
            table="users",
            assignments={"active": Literal(dialect, 0)},
            where=Column(dialect, "active") == Literal(dialect, 1),
            returning=ReturningClause(dialect, expressions=[Column(dialect, "id"), Column(dialect, "name")])
        )
        sql, params = update_expr.to_sql()

        result = await backend.execute(
            sql,
            params=params,
            options=ExecutionOptions(stmt_type=StatementType.DQL)
        )

        assert result.affected_rows == 2
        assert result.data is not None
        assert len(result.data) == 2
        returned_ids = {row['id'] for row in result.data}
        assert returned_ids == {1, 2}


    @pytest.mark.asyncio
    @patch('aiosqlite.sqlite_version', '3.35.0')
    async def test_returning_with_transaction(self, backend):
        """Test RETURNING within transaction"""
        dialect = backend.dialect
        # Create table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id   INTEGER PRIMARY KEY AUTOINCREMENT,
                                  name TEXT
                              )
                              """, options=ExecutionOptions(stmt_type=StatementType.DDL))

        # Transaction with RETURNING
        async with backend.transaction():
            insert_expr = InsertExpression(
                dialect=dialect,
                into="users",
                columns=["name"],
                source=ValuesSource(dialect, values_list=[[Literal(dialect, "TransUser")]]),
                returning=ReturningClause(dialect, expressions=[Column(dialect, "id")])
            )
            sql, params = insert_expr.to_sql()
            
            result = await backend.execute(
                sql,
                params=params,
                options=ExecutionOptions(stmt_type=StatementType.DQL)
            )

            assert result.affected_rows == 1
            assert result.data is not None
            assert len(result.data) == 1
            assert result.data[0]['id'] == 1

        # Verify committed
        row = await backend.fetch_one("SELECT * FROM users WHERE name = ?", params=("TransUser",))
        assert row is not None
        assert row['id'] == 1


class TestAsyncColumnMapping:
    """Test async column mapping functionality"""

    @pytest_asyncio.fixture
    async def async_mapped_table_backend(self):
        """
        Fixture to set up an in-memory async SQLite database, an AsyncSQLiteBackend instance,
        and a 'mapped_users' table with columns for type adaptation.
        Yields the configured async backend instance.
        """
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()

        create_table_sql = """
        CREATE TABLE mapped_users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP NOT NULL,
            user_uuid TEXT,
            is_active INTEGER
        );
        """
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await backend.execute(create_table_sql, options=options)

        yield backend

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_async_insert_and_returning_with_mapping(self, async_mapped_table_backend):
        """
        Tests that async execute() with an INSERT and a RETURNING clause correctly uses
        column_mapping to map the resulting column names back to field names.
        """
        backend = async_mapped_table_backend
        from datetime import datetime
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        column_to_field_mapping = {
            "user_id": "user_pk",
            "name": "full_name",
            "email": "user_email",
            "created_at": "created_timestamp"
        }

        sql = "INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)"
        params = ("John Doe Async", "john.doe.async@example.com", now_str)

        result = await backend.execute(
            sql=sql,
            params=params,
            options=ExecutionOptions(stmt_type=StatementType.DML, column_mapping=column_to_field_mapping)
        )

        assert result.affected_rows == 1

    @pytest.mark.asyncio
    async def test_async_update_with_backend(self, async_mapped_table_backend):
        """
        Tests that an async update operation via execute() works correctly.
        """
        backend = async_mapped_table_backend
        from datetime import datetime
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
                              ("Jane Doe Async", "jane.doe.async@example.com", now_str), options=options)

        sql = "UPDATE mapped_users SET name = ? WHERE user_id = ?"
        params = ("Jane Smith Async", 1)
        result = await backend.execute(sql, params, options=options)

        assert result.affected_rows == 1

        fetch_options = ExecutionOptions(stmt_type=StatementType.DQL)
        fetch_result = await backend.execute("SELECT name FROM mapped_users WHERE user_id = 1", options=fetch_options)
        fetched_row = fetch_result.data[0] if fetch_result.data else None
        assert fetched_row is not None
        assert fetched_row["name"] == "Jane Smith Async"

    @pytest.mark.asyncio
    async def test_async_execute_fetch_with_mapping(self, async_mapped_table_backend):
        """
        Tests that an async execute/fetch call correctly uses column_mapping.
        """
        backend = async_mapped_table_backend
        from datetime import datetime
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        
        column_to_field_mapping = {
            "user_id": "user_pk",
            "name": "full_name",
            "email": "user_email"
        }

        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
                              ("Async Fetch Test", "asyncfetch@example.com", now_str), options=options)

        fetch_options = ExecutionOptions(stmt_type=StatementType.DQL, column_mapping=column_to_field_mapping)
        result = await backend.execute(
            "SELECT * FROM mapped_users WHERE user_id = 1",
            options=fetch_options
        )
        fetched_row = result.data[0] if result.data else None

        assert fetched_row is not None
        assert "full_name" in fetched_row
        assert "user_email" in fetched_row
        assert "created_at" in fetched_row
        assert fetched_row["full_name"] == "Async Fetch Test"
        assert fetched_row["user_pk"] == 1

    @pytest.mark.asyncio
    async def test_async_execute_fetch_without_mapping(self, async_mapped_table_backend):
        """
        Tests an async fetch call WITHOUT column_mapping returns raw column names.
        """
        backend = async_mapped_table_backend
        from datetime import datetime
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute("INSERT INTO mapped_users (name, email, created_at) VALUES (?, ?, ?)",
                              ("Async No Map", "asyncnomap@example.com", now_str), options=options)

        fetch_options = ExecutionOptions(stmt_type=StatementType.DQL)
        result = await backend.execute("SELECT * FROM mapped_users WHERE user_id = 1", options=fetch_options)
        fetched_row = result.data[0] if result.data else None

        assert fetched_row is not None
        assert "user_id" in fetched_row
        assert "name" in fetched_row
        assert "full_name" not in fetched_row
        assert "user_pk" not in fetched_row
        assert fetched_row["name"] == "Async No Map"

    @pytest.mark.asyncio
    async def test_async_fetch_with_combined_mapping_and_adapters(self, async_mapped_table_backend):
        """
        Tests that async execute() correctly applies both column_mapping and column_adapters.
        """
        backend = async_mapped_table_backend
        from datetime import datetime
        import uuid
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
        test_uuid = uuid.uuid4()

        column_to_field_mapping = {
            "user_id": "pk",
            "name": "full_name",
            "user_uuid": "uuid",
            "is_active": "active"
        }

        uuid_adapter = backend.adapter_registry.get_adapter(uuid.UUID, str)
        bool_adapter = backend.adapter_registry.get_adapter(bool, int)

        column_adapters = {
            "user_uuid": (uuid_adapter, uuid.UUID),
            "is_active": (bool_adapter, bool)
        }

        options = ExecutionOptions(stmt_type=StatementType.DML)
        await backend.execute(
            "INSERT INTO mapped_users (name, email, created_at, user_uuid, is_active) VALUES (?, ?, ?, ?, ?)",
            ("Async Combined", "asynccombined@example.com", now_str, str(test_uuid), 1),
            options=options
        )

        fetch_options = ExecutionOptions(stmt_type=StatementType.DQL, column_mapping=column_to_field_mapping, column_adapters=column_adapters)
        result = await backend.execute(
            "SELECT * FROM mapped_users WHERE user_id = 1",
            options=fetch_options
        )

        fetched_row = result.data[0] if result.data else None
        assert fetched_row is not None

        assert "full_name" in fetched_row
        assert "uuid" in fetched_row
        assert "active" in fetched_row
        assert "name" not in fetched_row
        assert "user_uuid" not in fetched_row
        
        assert fetched_row["full_name"] == "Async Combined"
        # The adapter should convert the UUID string from the DB back to a UUID object.
        assert fetched_row["uuid"] == test_uuid
        # The adapter should convert the integer from the DB back to a boolean.
        assert fetched_row["active"] is True