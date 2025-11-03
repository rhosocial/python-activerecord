# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_async_returning.py
"""
Async RETURNING clause tests for AsyncSQLiteBackend

Tests RETURNING clause functionality in async context, including version compatibility
and column specification.
"""

import sys
from unittest.mock import patch

import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.dialect import ReturningOptions
from rhosocial.activerecord.backend.errors import ReturningNotSupportedError, OperationalError
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

# Import async backend from the same directory
from async_backend import AsyncSQLiteBackend


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

    @pytest.mark.asyncio
    @patch('sqlite3.sqlite_version', '3.34.0')
    async def test_returning_not_supported(self):
        """Test RETURNING not supported in older versions"""
        # This test needs to create its own backend to ensure the patch is active
        # during the check of `supports_returning`.
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        # Create table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id   INTEGER PRIMARY KEY,
                                  name TEXT
                              )
                              """)

        # Should raise error
        with pytest.raises(ReturningNotSupportedError) as exc_info:
            await backend.execute(
                "INSERT INTO users (name) VALUES (?)",
                params=("test",),
                returning=True
            )

        assert "RETURNING clause not supported" in str(exc_info.value)

        await backend.disconnect()

    @pytest.mark.asyncio
    @patch('sqlite3.sqlite_version', '3.35.0')
    async def test_returning_with_insert(self, backend):
        """Test RETURNING with INSERT"""
        # Create table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id    INTEGER PRIMARY KEY AUTOINCREMENT,
                                  name  TEXT,
                                  email TEXT
                              )
                              """)

        # Insert with RETURNING
        result = await backend.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            params=("Alice", "alice@example.com"),
            returning=ReturningOptions(enabled=True, force=True)
        )

        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]['name'] == "Alice"
        assert result.data[0]['email'] == "alice@example.com"

    @pytest.mark.asyncio
    @patch('sqlite3.sqlite_version', '3.35.0')
    async def test_returning_with_specific_columns(self, backend):
        """Test RETURNING with specific columns"""
        # Create table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id         INTEGER PRIMARY KEY AUTOINCREMENT,
                                  name       TEXT,
                                  email      TEXT,
                                  created_at TIMESTAMP
                              )
                              """)

        # Insert with specific RETURNING columns
        result = await backend.execute(
            "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
            params=("Bob", "bob@example.com", "2024-01-01 10:00:00"),
            returning=ReturningOptions(enabled=True, columns=["id", "name"], force=True)
        )

        assert result.data is not None
        assert len(result.data) == 1
        assert "id" in result.data[0]
        assert "name" in result.data[0]
        assert "email" not in result.data[0]
        assert result.data[0]['name'] == "Bob"

    @pytest.mark.asyncio
    @patch('sqlite3.sqlite_version', '3.35.0')
    async def test_returning_with_update(self, backend):
        """Test RETURNING with UPDATE"""
        # Create and populate table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id    INTEGER PRIMARY KEY,
                                  name  TEXT,
                                  email TEXT
                              )
                              """)
        await backend.execute(
            "INSERT INTO users (id, name, email) VALUES (1, 'Original', 'old@example.com')"
        )

        # Update with RETURNING
        result = await backend.execute(
            "UPDATE users SET name = ?, email = ? WHERE id = ?",
            params=("Updated", "new@example.com", 1),
            returning=ReturningOptions(enabled=True, columns=["name", "email"], force=True)
        )

        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]['name'] == "Updated"
        assert result.data[0]['email'] == "new@example.com"

    @pytest.mark.asyncio
    @patch('sqlite3.sqlite_version', '3.35.0')
    async def test_returning_with_delete(self, backend):
        """Test RETURNING with DELETE"""
        # Create and populate table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id   INTEGER PRIMARY KEY,
                                  name TEXT
                              )
                              """)
        await backend.execute("INSERT INTO users (id, name) VALUES (1, 'ToDelete')")

        # Delete with RETURNING
        result = await backend.execute(
            "DELETE FROM users WHERE id = ?",
            params=(1,),
            returning=ReturningOptions(enabled=True, columns=["id", "name"], force=True)
        )

        assert result.data is not None
        assert len(result.data) == 1
        assert result.data[0]['id'] == 1
        assert result.data[0]['name'] == "ToDelete"

        # Verify deleted
        row = await backend.fetch_one("SELECT * FROM users WHERE id = 1")
        assert row is None

    @pytest.mark.asyncio
    @patch('sqlite3.sqlite_version', '3.35.0')
    async def test_returning_invalid_columns(self, backend):
        """Test RETURNING with invalid column names"""
        # Create table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id   INTEGER PRIMARY KEY,
                                  name TEXT
                              )
                              """)

        # Invalid column
        with pytest.raises(OperationalError) as exc_info:
            await backend.execute(
                "INSERT INTO users (name) VALUES (?)",
                params=("test",),
                returning=ReturningOptions(enabled=True, columns=["nonexistent"], force=True)
            )

        assert "no such column" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_column_name_validation(self, backend):
        """Test column name validation for SQL injection"""
        # Create table
        await backend.execute("""
                              CREATE TABLE test
                              (
                                  id   INTEGER PRIMARY KEY,
                                  name TEXT
                              )
                              """)

        # Test dangerous patterns
        dangerous_patterns = [
            "id;",
            "id--",
            "idDROPx",
            "xSELECTid"
        ]

        for pattern in dangerous_patterns:
            with pytest.raises(ValueError) as exc_info:
                await backend.execute(
                    "INSERT INTO test (name) VALUES (?)",
                    params=("test",),
                    returning=ReturningOptions(enabled=True, columns=[pattern], force=True)
                )

            assert "Invalid column name" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('sqlite3.sqlite_version', '3.35.0')
    async def test_returning_with_quoted_columns(self, backend):
        """Test RETURNING with quoted column names"""
        # Create table with quoted column names
        await backend.execute('''
                              CREATE TABLE items
                              (
                                  id             INTEGER PRIMARY KEY,
                                  "special name" TEXT,
                                  "with.dot"     TEXT
                              )
                              ''')

        # Insert with RETURNING
        result = await backend.execute(
            'INSERT INTO items (id, "special name", "with.dot") VALUES (?, ?, ?)',
            params=(1, "test1", "test2"),
            returning=ReturningOptions(
                enabled=True,
                columns=['"special name"', '"with.dot"'],
                force=True
            )
        )

        assert result.data is not None
        assert len(result.data) == 1
        assert 'special name' in result.data[0]
        assert 'with.dot' in result.data[0]

    @pytest.mark.asyncio
    @patch('sqlite3.sqlite_version', '3.35.0')
    async def test_returning_multiple_rows(self, backend):
        """Test RETURNING with operations affecting multiple rows"""
        # Create and populate table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id     INTEGER PRIMARY KEY,
                                  name   TEXT,
                                  active INTEGER
                              )
                              """)
        await backend.execute("INSERT INTO users VALUES (1, 'User1', 1), (2, 'User2', 1), (3, 'User3', 0)")

        # Update multiple rows with RETURNING
        result = await backend.execute(
            "UPDATE users SET active = 0 WHERE active = 1",
            returning=ReturningOptions(enabled=True, columns=["id", "name"], force=True)
        )

        assert result.data is not None
        assert len(result.data) == 2
        assert result.data[0]['name'] in ["User1", "User2"]
        assert result.data[1]['name'] in ["User1", "User2"]

    @pytest.mark.asyncio
    async def test_supports_returning_property(self, backend):
        """Test supports_returning property"""
        version = backend.get_server_version()
        expected = version >= (3, 35, 0)

        assert backend.supports_returning == expected

    @pytest.mark.asyncio
    @patch('sqlite3.sqlite_version', '3.35.0')
    async def test_returning_with_transaction(self, backend):
        """Test RETURNING within transaction"""
        # Create table
        await backend.execute("""
                              CREATE TABLE users
                              (
                                  id   INTEGER PRIMARY KEY AUTOINCREMENT,
                                  name TEXT
                              )
                              """)

        # Transaction with RETURNING
        await backend.begin_transaction()

        result = await backend.execute(
            "INSERT INTO users (name) VALUES (?)",
            params=("TransUser",),
            returning=ReturningOptions(enabled=True, force=True)
        )

        assert result.data is not None
        assert result.data[0]['name'] == "TransUser"

        await backend.commit_transaction()

        # Verify committed
        row = await backend.fetch_one("SELECT * FROM users WHERE name = ?", params=("TransUser",))
        assert row is not None

    @pytest.mark.asyncio
    @patch('sqlite3.sqlite_version', '3.35.0')
    async def test_returning_options_variations(self, backend):
        """Test different ReturningOptions variations"""
        await backend.execute("""
                              CREATE TABLE test
                              (
                                  id    INTEGER PRIMARY KEY,
                                  name  TEXT,
                                  value INTEGER
                              )
                              """)

        # Test with boolean True
        result = await backend.execute(
            "INSERT INTO test (name, value) VALUES (?, ?)",
            params=("test1", 100),
            returning=ReturningOptions(enabled=True, force=True)
        )
        assert result.data is not None

        # Test with column list
        result = await backend.execute(
            "INSERT INTO test (name, value) VALUES (?, ?)",
            params=("test2", 200),
            returning=ReturningOptions(enabled=True, columns=["id", "name"], force=True)
        )
        assert result.data is not None
        assert "value" not in result.data[0]

        # Test with empty columns (should return all)
        result = await backend.execute(
            "INSERT INTO test (name, value) VALUES (?, ?)",
            params=("test3", 300),
            returning=ReturningOptions(enabled=True, columns=[], force=True)
        )
        assert result.data is not None
        assert "id" in result.data[0]
        assert "name" in result.data[0]
        assert "value" in result.data[0]


# Python version-specific tests
is_py38_39 = sys.version_info >= (3, 8) and sys.version_info < (3, 10)


@pytest.mark.skipif(
    not is_py38_39,
    reason="Python 3.8/3.9 specific test"
)
class TestAsyncReturningPy38:
    """Python 3.8/3.9 specific RETURNING tests"""

    @pytest_asyncio.fixture
    async def backend(self):
        """Create an in-memory async SQLite backend"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()
        yield backend
        await backend.disconnect()

    @pytest.mark.asyncio
    @patch('sqlite3.sqlite_version', '3.35.0')
    async def test_returning_compatibility_warning(self, backend):
        """Test RETURNING compatibility warning in Python 3.8/3.9"""
        # Create table
        await backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

        # Without force, should raise warning
        with pytest.raises(ReturningNotSupportedError) as exc_info:
            await backend.execute(
                "INSERT INTO test (name) VALUES (?)",
                params=("test",),
                returning=ReturningOptions(enabled=True, force=False)
            )

        assert "known issues in Python < 3.10" in str(exc_info.value)

        # With force, should work
        result = await backend.execute(
            "INSERT INTO test (name) VALUES (?)",
            params=("test",),
            returning=ReturningOptions(enabled=True, force=True)
        )

        # May have issues, but should not raise
        assert result is not None