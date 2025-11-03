# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_async_transaction.py
"""
Async transaction tests for AsyncSQLiteBackend

Tests async transaction management including begin, commit, rollback,
nested transactions, and savepoints.
"""

import os
import pytest_asyncio
import tempfile
import aiofiles.os

import pytest

from rhosocial.activerecord.backend.errors import TransactionError
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.transaction import IsolationLevel

# Import async backend from the same directory
from async_backend import AsyncSQLiteBackend


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
        await backend.execute("""
                              CREATE TABLE test
                              (
                                  id    INTEGER PRIMARY KEY,
                                  value TEXT
                              )
                              """)

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
        await backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",))

        # Commit
        await backend.commit_transaction()
        assert backend.in_transaction is False

        # Verify data committed
        row = await backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is not None
        assert row['value'] == "test"

    @pytest.mark.asyncio
    async def test_begin_rollback(self, backend):
        """Test begin and rollback transaction"""
        await backend.begin_transaction()

        # Insert data
        await backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",))

        # Rollback
        await backend.rollback_transaction()
        assert backend.in_transaction is False

        # Verify data rolled back
        row = await backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is None

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self, backend):
        """Test transaction context manager"""
        async with backend.transaction():
            await backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",))

        # Should auto-commit
        assert backend.in_transaction is False
        row = await backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is not None

    @pytest.mark.asyncio
    async def test_transaction_context_manager_exception(self, backend):
        """Test transaction context manager with exception"""
        try:
            async with backend.transaction():
                await backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",))
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Should auto-rollback
        assert backend.in_transaction is False
        row = await backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is None

    @pytest.mark.asyncio
    async def test_nested_transactions(self, backend):
        """Test nested transactions"""
        # Outer transaction
        await backend.begin_transaction()
        await backend.execute("INSERT INTO test (id, value) VALUES (1, 'outer')")

        # Inner transaction
        await backend.begin_transaction()
        await backend.execute("INSERT INTO test (id, value) VALUES (2, 'inner')")

        # Rollback inner
        await backend.rollback_transaction()

        # Verify inner rolled back
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
        await backend.execute("INSERT INTO test (id, value) VALUES (1, 'level1')")

        # Level 2
        await backend.begin_transaction()
        await backend.execute("INSERT INTO test (id, value) VALUES (2, 'level2')")

        # Level 3
        await backend.begin_transaction()
        await backend.execute("INSERT INTO test (id, value) VALUES (3, 'level3')")

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
        await backend.execute("INSERT INTO test (id, value) VALUES (1, 'base')")

        # Create savepoint
        sp1 = await backend.transaction_manager.async_savepoint("sp1")
        await backend.execute("INSERT INTO test (id, value) VALUES (2, 'sp1')")

        # Create second savepoint
        sp2 = await backend.transaction_manager.async_savepoint("sp2")
        await backend.execute("INSERT INTO test (id, value) VALUES (3, 'sp2')")

        # Rollback to first savepoint
        await backend.transaction_manager.rollback_to("sp1")

        # Verify rollback
        rows = await backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 1
        assert rows[0]['value'] == "base"

        # Add new data
        await backend.execute("INSERT INTO test (id, value) VALUES (4, 'after-rollback')")

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
        await backend.execute("INSERT INTO test (id, value) VALUES (1, 'main')")

        # Create manual savepoint
        sp1 = await backend.transaction_manager.async_savepoint("manual_sp")
        await backend.execute("INSERT INTO test (id, value) VALUES (2, 'manual_sp')")

        # Create nested transaction
        await backend.begin_transaction()
        await backend.execute("INSERT INTO test (id, value) VALUES (3, 'nested')")

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

    @pytest.mark.asyncio
    async def test_disconnect_during_transaction(self, temp_db_path):
        """Test disconnecting during transaction"""
        # Use a dedicated backend for this test to avoid state conflicts
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()
        await backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")

        await backend.begin_transaction()
        await backend.execute("INSERT INTO test (value) VALUES (?)", params=("test",))

        # Disconnect
        await backend.disconnect()

        # Transaction state should be reset
        assert backend._transaction_manager is None
        assert backend._connection is None

        # Reconnect and verify rollback
        await backend.connect()
        row = await backend.fetch_one("SELECT * FROM test WHERE value = ?", params=("test",))
        assert row is None

        await backend.disconnect()

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
        import asyncio
        backend1, backend2 = memory_backend_pair

        # Create table
        await backend1.execute("""
                               CREATE TABLE concurrent
                               (
                                   id    INTEGER PRIMARY KEY,
                                   value TEXT
                               )
                               """)

        # Run two transactions concurrently
        async def trans1():
            await backend1.begin_transaction()
            await backend1.execute("INSERT INTO concurrent (value) VALUES (?)", params=("trans1",))
            await asyncio.sleep(0.1)
            await backend1.commit_transaction()

        async def trans2():
            await asyncio.sleep(0.05)
            await backend2.begin_transaction()
            await backend2.execute("INSERT INTO concurrent (value) VALUES (?)", params=("trans2",))
            await backend2.commit_transaction()

        # Note: SQLite may serialize these due to locking
        await asyncio.gather(trans1(), trans2(), return_exceptions=True)

        # At least one should succeed
        rows = await backend1.fetch_all("SELECT * FROM concurrent")
        assert len(rows) >= 1