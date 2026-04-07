# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_async_transaction.py
"""Tests for async SQLite transaction manager.

This module tests the AsyncSQLiteTransactionManager class which provides
async transaction management for SQLite using aiosqlite.

Note: Tests use direct connection operations (backend._connection) to avoid
autocommit issues with aiosqlite's execute method.
"""
import logging
import sqlite3
import pytest
import pytest_asyncio
from unittest.mock import patch

from rhosocial.activerecord.backend.errors import TransactionError
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.async_transaction import AsyncSQLiteTransactionManager
from rhosocial.activerecord.backend.transaction import IsolationLevel


@pytest_asyncio.fixture
async def async_backend():
    """Create in-memory async SQLite backend."""
    backend = AsyncSQLiteBackend(database=":memory:")
    await backend.connect()
    # Create test table using raw connection
    await backend._connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    await backend._connection.commit()
    yield backend
    await backend.disconnect()


@pytest.fixture
def logger():
    """Create test logger."""
    logger = logging.getLogger("test_async_transaction")
    logger.setLevel(logging.DEBUG)
    return logger


@pytest_asyncio.fixture
async def transaction_manager(async_backend):
    """Get transaction manager from backend."""
    return async_backend.transaction_manager


@pytest.mark.asyncio
class TestAsyncSQLiteTransactionManagerInit:
    """Tests for async transaction manager initialization."""

    async def test_init(self, async_backend, logger):
        """Test transaction manager initialization."""
        manager = AsyncSQLiteTransactionManager(async_backend, logger)
        assert manager._backend == async_backend
        assert manager._backend.dialect is not None
        assert manager.is_active is False
        assert manager._savepoint_count == 0
        assert manager._logger == logger
        assert manager._transaction_level == 0
        assert manager._isolation_level == IsolationLevel.SERIALIZABLE

    async def test_init_without_logger(self, async_backend):
        """Test initialization without logger."""
        manager = AsyncSQLiteTransactionManager(async_backend)
        assert manager._logger is not None
        assert isinstance(manager._logger, logging.Logger)
        assert manager._logger.name == 'rhosocial.activerecord.transaction'


@pytest.mark.asyncio
class TestAsyncSQLiteTransactionBasics:
    """Tests for basic async transaction operations."""

    async def test_begin_transaction(self, transaction_manager):
        """Test async begin transaction."""
        with patch.object(transaction_manager, 'log') as mock_log:
            await transaction_manager.begin()
            assert transaction_manager.is_active is True
            assert transaction_manager._transaction_level == 1

            # Verify log records
            assert mock_log.call_count >= 2
            mock_log.assert_any_call(logging.DEBUG, "Beginning transaction (level 0)")
            mock_log.assert_any_call(logging.INFO,
                                     "Starting new transaction with isolation level IsolationLevel.SERIALIZABLE")

    async def test_commit_transaction(self, transaction_manager, async_backend):
        """Test async commit transaction."""
        with patch.object(transaction_manager, 'log') as mock_log:
            await transaction_manager.begin()
            # Use raw connection to execute SQL within transaction
            await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (1, 'test')")
            await transaction_manager.commit()

            assert transaction_manager.is_active is False
            assert transaction_manager._transaction_level == 0

            # Verify log records
            mock_log.assert_any_call(logging.DEBUG, "Committing transaction (level 1)")
            mock_log.assert_any_call(logging.INFO, "Committing outermost transaction")

            # Verify commit was successful using raw connection
            cursor = await async_backend._connection.execute("SELECT * FROM test WHERE id = 1")
            result = await cursor.fetchone()
            assert result is not None
            assert result[0] == 1
            assert result[1] == 'test'

    async def test_rollback_transaction(self, transaction_manager, async_backend):
        """Test async rollback transaction."""
        with patch.object(transaction_manager, 'log') as mock_log:
            await transaction_manager.begin()
            # Use raw connection to execute SQL within transaction
            await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (1, 'test')")
            await transaction_manager.rollback()

            assert transaction_manager.is_active is False
            assert transaction_manager._transaction_level == 0

            # Verify log records
            mock_log.assert_any_call(logging.DEBUG, "Rolling back transaction (level 1)")
            mock_log.assert_any_call(logging.INFO, "Rolling back outermost transaction")

            # Verify rollback was successful using raw connection
            cursor = await async_backend._connection.execute("SELECT * FROM test WHERE id = 1")
            assert await cursor.fetchone() is None


@pytest.mark.asyncio
class TestAsyncSQLiteNestedTransactions:
    """Tests for async nested transactions (savepoints)."""

    async def test_nested_transactions(self, transaction_manager, async_backend):
        """Test async nested transactions using savepoints."""
        with patch.object(transaction_manager, 'log') as mock_log:
            # First level transaction
            await transaction_manager.begin()
            await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (1, 'level1')")

            # Verify first level transaction log
            mock_log.assert_any_call(logging.INFO,
                                     "Starting new transaction with isolation level IsolationLevel.SERIALIZABLE")
            mock_log.reset_mock()

            # Second level transaction (savepoint)
            await transaction_manager.begin()
            await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (2, 'level2')")

            # Verify second level transaction log
            mock_log.assert_any_call(logging.INFO, "Creating savepoint SP_1 for nested transaction")
            mock_log.reset_mock()

            # Rollback to second level savepoint
            await transaction_manager.rollback()

            # Verify rollback log
            mock_log.assert_any_call(logging.DEBUG, "Rolling back transaction (level 2)")
            mock_log.assert_any_call(logging.INFO, "Rolling back to savepoint SP_1 for nested transaction")

            # Verify second level transaction rolled back, but first level data remains
            cursor = await async_backend._connection.execute("SELECT * FROM test ORDER BY id")
            rows = await cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 1
            assert rows[0][1] == 'level1'

            # Commit first level transaction
            await transaction_manager.commit()

            # Verify final result
            cursor = await async_backend._connection.execute("SELECT * FROM test ORDER BY id")
            rows = await cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 1

    async def test_multiple_nested_levels(self, transaction_manager, async_backend):
        """Test multiple async nested transaction levels."""
        # Create three nested levels
        await transaction_manager.begin()  # Level 1
        await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (1, 'level1')")

        await transaction_manager.begin()  # Level 2
        await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (2, 'level2')")

        await transaction_manager.begin()  # Level 3
        await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (3, 'level3')")

        # Check transaction level
        assert transaction_manager._transaction_level == 3
        assert transaction_manager.is_active is True

        # Rollback level 3
        await transaction_manager.rollback()

        # After rollback should have only 1 and 2
        cursor = await async_backend._connection.execute("SELECT id FROM test ORDER BY id")
        ids = [row[0] for row in await cursor.fetchall()]
        assert ids == [1, 2]
        assert transaction_manager._transaction_level == 2

        # Commit level 2
        await transaction_manager.commit()
        assert transaction_manager._transaction_level == 1

        # Commit level 1
        await transaction_manager.commit()
        assert transaction_manager._transaction_level == 0
        assert transaction_manager.is_active is False

        # Check final result
        cursor = await async_backend._connection.execute("SELECT id FROM test ORDER BY id")
        ids = [row[0] for row in await cursor.fetchall()]
        assert ids == [1, 2]


@pytest.mark.asyncio
class TestAsyncSQLiteIsolationLevel:
    """Tests for async isolation level handling."""

    async def test_isolation_level_serializable(self, async_backend, logger):
        """Test async serializable isolation level."""
        manager = AsyncSQLiteTransactionManager(async_backend, logger)

        manager.isolation_level = IsolationLevel.SERIALIZABLE
        assert manager._isolation_level == IsolationLevel.SERIALIZABLE

    async def test_isolation_level_read_uncommitted(self, async_backend, logger):
        """Test async read uncommitted isolation level."""
        manager = AsyncSQLiteTransactionManager(async_backend, logger)

        manager.isolation_level = IsolationLevel.READ_UNCOMMITTED
        assert manager._isolation_level == IsolationLevel.READ_UNCOMMITTED

    async def test_unsupported_isolation_level(self, transaction_manager):
        """Test async unsupported isolation level."""
        with patch.object(transaction_manager, 'log') as mock_log:
            # SQLite does not support READ_COMMITTED
            with pytest.raises(Exception) as exc_info:
                transaction_manager.isolation_level = IsolationLevel.READ_COMMITTED

            assert "Unsupported isolation level" in str(exc_info.value)

    async def test_set_isolation_level_during_transaction(self, transaction_manager):
        """Test async setting isolation level during transaction."""
        # Begin transaction
        await transaction_manager.begin()

        with patch.object(transaction_manager, 'log'):
            # Try to change isolation level
            with pytest.raises(Exception) as exc_info:
                transaction_manager.isolation_level = IsolationLevel.SERIALIZABLE

            assert "Cannot change isolation level during active transaction" in str(exc_info.value)

        # Cleanup
        await transaction_manager.rollback()


@pytest.mark.asyncio
class TestAsyncSQLiteSavepointOperations:
    """Tests for async savepoint operations."""

    async def test_savepoint_operations(self, transaction_manager, async_backend):
        """Test async savepoint operations."""
        with patch.object(transaction_manager, 'log') as mock_log:
            # Begin main transaction
            await transaction_manager.begin()
            await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (1, 'base')")
            mock_log.reset_mock()

            # Create savepoint
            sp1 = await transaction_manager.savepoint("sp1")
            await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (2, 'sp1')")

            # Verify savepoint creation log
            mock_log.assert_any_call(logging.DEBUG, "Creating savepoint (name: sp1)")
            mock_log.assert_any_call(logging.INFO, "Creating savepoint: sp1")
            mock_log.reset_mock()

            # Rollback to savepoint
            await transaction_manager.rollback_to("sp1")

            # Verify rollback to savepoint log
            mock_log.assert_any_call(logging.DEBUG, "Rolling back to savepoint: sp1")
            mock_log.assert_any_call(logging.INFO, "Rolling back to savepoint: sp1")

            # Verify rollback to sp1 savepoint
            cursor = await async_backend._connection.execute("SELECT * FROM test ORDER BY id")
            rows = await cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 1
            assert rows[0][1] == 'base'
            mock_log.reset_mock()

            # Add new data
            await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (4, 'after-rollback')")

            # Release savepoint sp1
            await transaction_manager.release("sp1")

            # Verify release savepoint log
            mock_log.assert_any_call(logging.DEBUG, "Releasing savepoint: sp1")
            mock_log.assert_any_call(logging.INFO, "Releasing savepoint: sp1")
            mock_log.reset_mock()

            # Commit main transaction
            await transaction_manager.commit()

            # Verify final result
            cursor = await async_backend._connection.execute("SELECT * FROM test ORDER BY id")
            rows = await cursor.fetchall()
            assert len(rows) == 2
            assert rows[0][0] == 1
            assert rows[0][1] == 'base'
            assert rows[1][0] == 4

    async def test_auto_savepoint_name(self, transaction_manager):
        """Test async auto-generated savepoint names."""
        # Begin transaction
        await transaction_manager.begin()

        # Create savepoint with auto name
        sp1 = await transaction_manager.savepoint()
        assert sp1 == "SP_1"
        assert transaction_manager._savepoint_count == 1

        sp2 = await transaction_manager.savepoint()
        assert sp2 == "SP_2"
        assert transaction_manager._savepoint_count == 2

        # Rollback to first savepoint
        await transaction_manager.rollback_to(sp1)

        # Create another auto-named savepoint
        sp3 = await transaction_manager.savepoint()
        assert sp3 == "SP_3"
        assert transaction_manager._savepoint_count == 3

        # Cleanup
        await transaction_manager.rollback()


@pytest.mark.asyncio
class TestAsyncSQLiteTransactionErrors:
    """Tests for async transaction error handling."""

    async def test_commit_without_active_transaction(self, transaction_manager):
        """Test async commit without active transaction."""
        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                await transaction_manager.commit()

            assert "No active transaction to commit" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "No active transaction to commit")

    async def test_rollback_without_active_transaction(self, transaction_manager):
        """Test async rollback without active transaction."""
        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                await transaction_manager.rollback()

            assert "No active transaction to rollback" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "No active transaction to rollback")

    async def test_savepoint_without_active_transaction(self, transaction_manager):
        """Test async creating savepoint without active transaction."""
        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                await transaction_manager.savepoint("sp1")

            assert "Cannot create savepoint: no active transaction" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Cannot create savepoint: no active transaction")

    async def test_release_invalid_savepoint(self, transaction_manager):
        """Test async releasing non-existent savepoint."""
        # Begin transaction
        await transaction_manager.begin()

        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                await transaction_manager.release("nonexistent")

            assert "Invalid savepoint name: nonexistent" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Invalid savepoint name: nonexistent")

        # Cleanup
        await transaction_manager.rollback()

    async def test_rollback_to_invalid_savepoint(self, transaction_manager):
        """Test async rollback to non-existent savepoint."""
        # Begin transaction
        await transaction_manager.begin()

        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                await transaction_manager.rollback_to("nonexistent")

            assert "Invalid savepoint name: nonexistent" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Invalid savepoint name: nonexistent")

        # Cleanup
        await transaction_manager.rollback()


@pytest.mark.asyncio
class TestAsyncSQLiteTransactionLevelCounter:
    """Tests for async transaction level counter."""

    async def test_transaction_level_counter(self, transaction_manager):
        """Test async transaction nesting level counter."""
        assert transaction_manager._transaction_level == 0

        # First level transaction
        await transaction_manager.begin()
        assert transaction_manager._transaction_level == 1

        # Second level transaction
        await transaction_manager.begin()
        assert transaction_manager._transaction_level == 2

        # Third level transaction
        await transaction_manager.begin()
        assert transaction_manager._transaction_level == 3

        # Rollback one level
        await transaction_manager.rollback()
        assert transaction_manager._transaction_level == 2

        # Commit one level
        await transaction_manager.commit()
        assert transaction_manager._transaction_level == 1

        # Final commit
        await transaction_manager.commit()
        assert transaction_manager._transaction_level == 0


@pytest.mark.asyncio
class TestAsyncSQLiteLogger:
    """Tests for async transaction manager logger functionality."""

    async def test_logger_property(self, transaction_manager, async_backend):
        """Test logger property."""
        # The transaction manager uses the backend's logger
        assert transaction_manager.logger == async_backend.logger

        # Test setting new logger
        new_logger = logging.getLogger("new_async_logger")
        transaction_manager.logger = new_logger
        assert transaction_manager.logger == new_logger

        # Test setting to None uses default logger
        transaction_manager.logger = None
        assert transaction_manager.logger is not None
        assert transaction_manager.logger.name == 'rhosocial.activerecord.transaction'

        # Test setting non-logger value
        with pytest.raises(ValueError):
            transaction_manager.logger = "not a logger"

    async def test_log_method(self, transaction_manager):
        """Test log method."""
        with patch.object(transaction_manager._logger, 'log') as mock_log:
            transaction_manager.log(logging.INFO, "Test message")
            mock_log.assert_called_once_with(logging.INFO, "Test message")

            transaction_manager.log(logging.ERROR, "Error %s", "details", extra={'key': 'value'})
            mock_log.assert_called_with(logging.ERROR, "Error %s", "details", extra={'key': 'value'})


@pytest.mark.asyncio
class TestAsyncSQLiteSupportsSavepoint:
    """Tests for async savepoint support check."""

    async def test_supports_savepoint(self, transaction_manager):
        """Test supports_savepoint method."""
        assert await transaction_manager.supports_savepoint() is True


@pytest.mark.asyncio
class TestAsyncSQLiteMultipleSavepoints:
    """Tests for async multiple savepoints."""

    @pytest.mark.skipif(
        sqlite3.sqlite_version_info < (3, 6, 8),
        reason="SQLite 3.6.8+ required for savepoint"
    )
    async def test_multiple_savepoints(self, transaction_manager, async_backend):
        """Test multiple savepoints."""
        # Begin transaction
        await transaction_manager.begin()

        # Create multiple savepoints
        savepoints = []
        for i in range(5):
            await async_backend._connection.execute(f"INSERT INTO test (id, value) VALUES ({i + 1}, 'value{i + 1}')")
            sp_name = await transaction_manager.savepoint(f"sp{i + 1}")
            savepoints.append(sp_name)

        # Verify all data inserted
        cursor = await async_backend._connection.execute("SELECT COUNT(*) FROM test")
        result = await cursor.fetchone()
        assert result[0] == 5

        # Rollback to middle savepoint
        await transaction_manager.rollback_to("sp3")

        # Verify data after rollback
        cursor = await async_backend._connection.execute("SELECT COUNT(*) FROM test")
        result = await cursor.fetchone()
        assert result[0] == 3

        # Rollback to first savepoint
        await transaction_manager.rollback_to("sp1")

        # Verify data after rollback
        cursor = await async_backend._connection.execute("SELECT COUNT(*) FROM test")
        result = await cursor.fetchone()
        assert result[0] == 1

        # Commit transaction
        await transaction_manager.commit()

        # Verify final data
        cursor = await async_backend._connection.execute("SELECT * FROM test")
        row = await cursor.fetchone()
        assert row[0] == 1
        assert row[1] == 'value1'


@pytest.mark.asyncio
class TestAsyncSQLiteMixedSavepointTransactions:
    """Tests for async mixed usage of savepoints and nested transactions."""

    async def test_mixed_savepoint_transactions(self, transaction_manager, async_backend):
        """Test mixed usage of savepoints and nested transactions."""
        # Begin main transaction
        await transaction_manager.begin()
        await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (1, 'main')")

        # Create manual savepoint
        sp1 = await transaction_manager.savepoint("manual_sp")
        await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (2, 'manual_sp')")

        # Create nested transaction (internally uses savepoint)
        await transaction_manager.begin()
        await async_backend._connection.execute("INSERT INTO test (id, value) VALUES (3, 'nested')")

        # Should now have 3 rows
        cursor = await async_backend._connection.execute("SELECT COUNT(*) FROM test")
        result = await cursor.fetchone()
        assert result[0] == 3

        # Rollback nested transaction
        await transaction_manager.rollback()

        # Should have 2 rows remaining
        cursor = await async_backend._connection.execute("SELECT COUNT(*) FROM test")
        result = await cursor.fetchone()
        assert result[0] == 2

        # Rollback to manual savepoint
        await transaction_manager.rollback_to(sp1)

        # Should have 1 row remaining
        cursor = await async_backend._connection.execute("SELECT COUNT(*) FROM test")
        result = await cursor.fetchone()
        assert result[0] == 1

        # Commit main transaction
        await transaction_manager.commit()

        # Verify final result
        cursor = await async_backend._connection.execute("SELECT * FROM test")
        row = await cursor.fetchone()
        assert row[0] == 1
        assert row[1] == 'main'


@pytest.mark.asyncio
class TestAsyncSQLiteTransactionErrorHandling:
    """Tests for async transaction error handling."""

    async def test_transaction_error_handling(self):
        """Test async transaction error handling."""
        import sqlite3

        # Use a real backend but mock the execute method to raise errors
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()

        manager = AsyncSQLiteTransactionManager(backend)

        # Mock the execute method to raise errors
        with patch.object(backend, 'execute', side_effect=sqlite3.Error("Mock error")):
            with patch.object(manager, 'log') as mock_log:
                # Test begin failure
                with pytest.raises(TransactionError) as exc_info:
                    await manager.begin()

                assert "Failed to begin transaction" in str(exc_info.value)
                assert "Mock error" in str(exc_info.value)
                mock_log.assert_any_call(logging.ERROR, "Failed to begin transaction: Mock error")

        # Test commit failure (manually set transaction level)
        manager._transaction_level = 1

        with patch.object(backend, 'execute', side_effect=sqlite3.Error("Mock error")):
            with patch.object(manager, 'log') as mock_log:
                with pytest.raises(TransactionError) as exc_info:
                    await manager.commit()

                assert "Failed to commit transaction" in str(exc_info.value)
                assert "Mock error" in str(exc_info.value)
                mock_log.assert_any_call(logging.ERROR, "Failed to commit transaction: Mock error")

                # Ensure transaction_level restored on failure
                assert manager._transaction_level == 1

        # Test rollback failure
        with patch.object(backend, 'execute', side_effect=sqlite3.Error("Mock error")):
            with patch.object(manager, 'log') as mock_log:
                with pytest.raises(TransactionError) as exc_info:
                    await manager.rollback()

                assert "Failed to rollback transaction" in str(exc_info.value)
                assert "Mock error" in str(exc_info.value)
                mock_log.assert_any_call(logging.ERROR, "Failed to rollback transaction: Mock error")

                # Ensure transaction_level restored on failure
                assert manager._transaction_level == 1

        # Test savepoint failure
        manager._transaction_level = 1  # Ensure we're in a "transaction"
        with patch.object(backend, 'execute', side_effect=sqlite3.Error("Mock error")):
            with patch.object(manager, 'log') as mock_log:
                with pytest.raises(TransactionError) as exc_info:
                    await manager.savepoint("sp1")

                assert "Failed to create savepoint" in str(exc_info.value)
                assert any("Failed to create savepoint" in str(call) for call in mock_log.call_args_list
                           if call[0][0] == logging.ERROR)

        # Manually add savepoint to active list to test subsequent operations
        manager._active_savepoints.append("sp1")

        # Test release failure
        with patch.object(backend, 'execute', side_effect=sqlite3.Error("Mock error")):
            with patch.object(manager, 'log') as mock_log:
                with pytest.raises(TransactionError) as exc_info:
                    await manager.release("sp1")

                assert "Failed to release savepoint" in str(exc_info.value)
                mock_log.assert_any_call(logging.ERROR, "Failed to release savepoint sp1: Mock error")

        # Test rollback_to failure
        manager._active_savepoints.append("sp1")  # Re-add for test
        with patch.object(backend, 'execute', side_effect=sqlite3.Error("Mock error")):
            with patch.object(manager, 'log') as mock_log:
                with pytest.raises(TransactionError) as exc_info:
                    await manager.rollback_to("sp1")

                assert "Failed to rollback to savepoint" in str(exc_info.value)
                mock_log.assert_any_call(logging.ERROR, "Failed to rollback to savepoint sp1: Mock error")

        # Cleanup
        await backend.disconnect()
