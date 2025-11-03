# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_async_execute_many.py
"""
Async execute_many tests for AsyncSQLiteBackend

Tests batch execution of SQL statements with multiple parameter sets.
"""

import os
import tempfile

import pytest
import pytest_asyncio
import aiofiles.os

from rhosocial.activerecord.backend.errors import DatabaseError, QueryError
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

# Import async backend from the same directory
from async_backend import AsyncSQLiteBackend


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
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id     INTEGER PRIMARY KEY,
                                  name   TEXT,
                                  email  TEXT,
                                  active INTEGER
                              )
                              """)

        await backend.execute("""
                              CREATE TABLE posts
                              (
                                  id      INTEGER PRIMARY KEY,
                                  user_id INTEGER,
                                  title   TEXT,
                                  content TEXT,
                                  FOREIGN KEY (user_id) REFERENCES users (id)
                              )
                              """)

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
        await backend.execute("INSERT INTO users (id, name) VALUES (1, 'User 1')")

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
        large_batch = [(i, f"User {i}", f"user{i}@example.com", 1) for i in range(1, 1001)]

        result = await backend.execute_many(
            "INSERT INTO users (id, name, email, active) VALUES (?, ?, ?, ?)",
            large_batch
        )

        assert result.affected_rows == 1000

        # Verify count
        count = await backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 1000

    @pytest.mark.asyncio
    async def test_batch_with_transactions(self, backend):
        """Test execute_many within transactions"""
        await backend.begin_transaction()

        await backend.execute_many(
            "INSERT INTO users (id, name) VALUES (?, ?)",
            [(1, "User 1"), (2, "User 2")]
        )

        # Verify visible within transaction
        count = await backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 2

        # Rollback
        await backend.rollback_transaction()

        # Verify rolled back
        count = await backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 0

        # Test with commit
        await backend.begin_transaction()
        await backend.execute_many(
            "INSERT INTO users (id, name) VALUES (?, ?)",
            [(1, "User 1"), (2, "User 2")]
        )
        await backend.commit_transaction()

        # Verify persisted
        count = await backend.fetch_one("SELECT COUNT(*) as count FROM users")
        assert count["count"] == 2

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

    @pytest.mark.asyncio
    async def test_parameter_conversion(self, backend):
        """Test parameter conversion in execute_many"""
        import json
        from datetime import datetime

        # Create table with datetime column
        await backend.execute("""
                              CREATE TABLE events
                              (
                                  id         INTEGER,
                                  data       TEXT,
                                  created_at TEXT
                              )
                              """)

        # Insert with datetime objects
        params_list = [
            (1, json.dumps({"key": "value1"}), datetime(2024, 1, 1)),
            (2, json.dumps({"key": "value2"}), datetime(2024, 1, 2))
        ]

        result = await backend.execute_many(
            "INSERT INTO events (id, data, created_at) VALUES (?, ?, ?)",
            params_list
        )

        assert result.affected_rows == 2

        # Verify data conversion
        rows = await backend.fetch_all("SELECT * FROM events ORDER BY id")
        assert len(rows) == 2
        assert isinstance(rows[0]["data"], str)
        assert isinstance(rows[0]["created_at"], str)

    @pytest.mark.asyncio
    async def test_dict_params(self, backend):
        """Test execute_many with dict parameters"""
        params_list = [
            {"id": 1, "name": "User 1"},
            {"id": 2, "name": "User 2"}
        ]

        result = await backend.execute_many(
            "INSERT INTO users (id, name) VALUES (?, ?)",
            params_list
        )

        assert result.affected_rows == 2

        # Verify data
        rows = await backend.fetch_all("SELECT * FROM users ORDER BY id")
        assert len(rows) == 2
        assert rows[0]["name"] == "User 1"



    @pytest_asyncio.fixture
    async def memory_backend(self):
        """Create an in-memory async SQLite backend for concurrent tests"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()
        # Create table for the test
        await backend.execute("""
                              CREATE TABLE concurrent
                              (
                                  id    INTEGER PRIMARY KEY,
                                  value TEXT
                              )
                              """)
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
    async def test_concurrent_execute_many(self, memory_backend):
        """Test concurrent execute_many operations"""
        import asyncio

        # Run multiple execute_many concurrently
        async def batch_insert(start_id, count):
            params = [(start_id + i, f"value{start_id + i}") for i in range(count)]
            await memory_backend.execute_many(
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
        count = await memory_backend.fetch_one("SELECT COUNT(*) as count FROM concurrent")
        assert count["count"] >= 10