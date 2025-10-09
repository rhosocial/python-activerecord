# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_transaction.py
import logging
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from rhosocial.activerecord.backend.errors import TransactionError
from rhosocial.activerecord.backend.impl.sqlite.transaction import SQLiteTransactionManager
from rhosocial.activerecord.backend.transaction import IsolationLevel


class TestSQLiteTransactionManager:
    @pytest.fixture
    def connection(self):
        """Create in-memory SQLite connection"""
        conn = sqlite3.connect(":memory:")
        # Set auto-commit mode to match actual implementation
        conn.isolation_level = None
        # Create test table
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        return conn

    @pytest.fixture
    def logger(self):
        """Create test logger"""
        logger = logging.getLogger("test_transaction")
        logger.setLevel(logging.DEBUG)
        return logger

    @pytest.fixture
    def transaction_manager(self, connection, logger):
        """Create transaction manager"""
        return SQLiteTransactionManager(connection, logger)

    def test_init(self, connection, logger):
        """Test transaction manager initialization"""
        manager = SQLiteTransactionManager(connection, logger)
        assert manager._connection == connection
        assert manager._connection.isolation_level is None
        assert manager.is_active is False
        assert manager._savepoint_count == 0
        assert manager._logger == logger
        assert manager._transaction_level == 0
        assert manager._isolation_level == IsolationLevel.SERIALIZABLE

    def test_init_without_logger(self, connection):
        """Test initialization without logger"""
        manager = SQLiteTransactionManager(connection)
        assert manager._logger is not None
        assert isinstance(manager._logger, logging.Logger)
        assert manager._logger.name == 'transaction'

    def test_logger_property(self, transaction_manager, logger):
        """Test logger property"""
        assert transaction_manager.logger == logger

        # Test setting new logger
        new_logger = logging.getLogger("new_logger")
        transaction_manager.logger = new_logger
        assert transaction_manager.logger == new_logger

        # Test setting to None uses default logger
        transaction_manager.logger = None
        assert transaction_manager.logger is not None
        assert transaction_manager.logger.name == 'transaction'

        # Test setting non-logger value
        with pytest.raises(ValueError):
            transaction_manager.logger = "not a logger"

    def test_log_method(self, transaction_manager):
        """Test log method"""
        with patch.object(transaction_manager._logger, 'log') as mock_log:
            transaction_manager.log(logging.INFO, "Test message")
            mock_log.assert_called_once_with(logging.INFO, "Test message")

            transaction_manager.log(logging.ERROR, "Error %s", "details", extra={'key': 'value'})
            mock_log.assert_called_with(logging.ERROR, "Error %s", "details", extra={'key': 'value'})

    def test_begin_transaction(self, transaction_manager):
        """Test begin transaction"""
        with patch.object(transaction_manager, 'log') as mock_log:
            transaction_manager.begin()
            assert transaction_manager.is_active is True
            assert transaction_manager._transaction_level == 1

            # Verify log records
            assert mock_log.call_count >= 2
            mock_log.assert_any_call(logging.DEBUG, "Beginning transaction (level 0)")
            mock_log.assert_any_call(logging.INFO,
                                     "Starting new transaction with isolation level IsolationLevel.SERIALIZABLE")

            # Verify transaction actually started
            with pytest.raises(sqlite3.OperationalError):
                transaction_manager._connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")

    def test_commit_transaction(self, transaction_manager):
        """Test commit transaction"""
        with patch.object(transaction_manager, 'log') as mock_log:
            transaction_manager.begin()
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'test')")
            transaction_manager.commit()

            assert transaction_manager.is_active is False
            assert transaction_manager._transaction_level == 0

            # Verify log records
            mock_log.assert_any_call(logging.DEBUG, "Committing transaction (level 1)")
            mock_log.assert_any_call(logging.INFO, "Committing outermost transaction")

            # Verify commit was successful
            cursor = transaction_manager._connection.execute("SELECT * FROM test WHERE id = 1")
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == 1
            assert result[1] == 'test'

    def test_rollback_transaction(self, transaction_manager):
        """Test rollback transaction"""
        with patch.object(transaction_manager, 'log') as mock_log:
            transaction_manager.begin()
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'test')")
            transaction_manager.rollback()

            assert transaction_manager.is_active is False
            assert transaction_manager._transaction_level == 0

            # Verify log records
            mock_log.assert_any_call(logging.DEBUG, "Rolling back transaction (level 1)")
            mock_log.assert_any_call(logging.INFO, "Rolling back outermost transaction")

            # Verify rollback was successful
            cursor = transaction_manager._connection.execute("SELECT * FROM test WHERE id = 1")
            assert cursor.fetchone() is None

    def test_nested_transactions(self, transaction_manager):
        """Test nested transactions (using savepoints)"""
        with patch.object(transaction_manager, 'log') as mock_log:
            # First level transaction
            transaction_manager.begin()
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'level1')")

            # Verify first level transaction log
            mock_log.assert_any_call(logging.INFO,
                                     "Starting new transaction with isolation level IsolationLevel.SERIALIZABLE")
            mock_log.reset_mock()

            # Second level transaction (savepoint)
            transaction_manager.begin()
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (2, 'level2')")

            # Verify second level transaction log
            mock_log.assert_any_call(logging.INFO, "Creating savepoint LEVEL1 for nested transaction")
            mock_log.reset_mock()

            # Rollback to second level savepoint
            transaction_manager.rollback()

            # Verify rollback log
            mock_log.assert_any_call(logging.DEBUG, "Rolling back transaction (level 2)")
            mock_log.assert_any_call(logging.INFO, "Rolling back to savepoint LEVEL1 for nested transaction")

            # Verify second level transaction rolled back, but first level data remains
            cursor = transaction_manager._connection.execute("SELECT * FROM test ORDER BY id")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 1
            assert rows[0][1] == 'level1'

            # Commit first level transaction
            transaction_manager.commit()

            # Verify final result
            cursor = transaction_manager._connection.execute("SELECT * FROM test ORDER BY id")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 1
            assert rows[0][1] == 'level1'

    def test_multiple_nested_levels(self, transaction_manager):
        """Test multiple nested transaction levels"""
        # Create three nested levels
        transaction_manager.begin()  # Level 1
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'level1')")

        transaction_manager.begin()  # Level 2
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (2, 'level2')")

        transaction_manager.begin()  # Level 3
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (3, 'level3')")

        # Check transaction level
        assert transaction_manager._transaction_level == 3
        assert transaction_manager.is_active is True

        # Rollback level 3
        transaction_manager.rollback()

        # After rollback should have only 1 and 2
        cursor = transaction_manager._connection.execute("SELECT id FROM test ORDER BY id")
        ids = [row[0] for row in cursor.fetchall()]
        assert ids == [1, 2]
        assert transaction_manager._transaction_level == 2

        # Commit level 2
        transaction_manager.commit()
        assert transaction_manager._transaction_level == 1

        # Commit level 1
        transaction_manager.commit()
        assert transaction_manager._transaction_level == 0
        assert transaction_manager.is_active is False

        # Check final result
        cursor = transaction_manager._connection.execute("SELECT id FROM test ORDER BY id")
        ids = [row[0] for row in cursor.fetchall()]
        assert ids == [1, 2]

    def test_isolation_level_serializable(self, connection, logger):
        """Test serializable isolation level"""
        with patch.object(logging.Logger, 'log') as mock_log:
            manager = SQLiteTransactionManager(connection, logger)
            manager.isolation_level = IsolationLevel.SERIALIZABLE

            # Verify log records
            mock_log.assert_any_call(logging.DEBUG, "Setting isolation level to IsolationLevel.SERIALIZABLE")
            # mock_log.assert_any_call(logging.INFO, "Isolation level set to IsolationLevel.SERIALIZABLE")

            manager.begin()

            # Verify correct isolation level syntax used
            # SQLite SERIALIZABLE corresponds to IMMEDIATE keyword
            assert manager.is_active is True

            # Check read_uncommitted set to 0 (SERIALIZABLE default)
            cursor = connection.execute("PRAGMA read_uncommitted")
            result = cursor.fetchone()
            assert result[0] == 0

            manager.commit()

    def test_isolation_level_read_uncommitted(self, connection, logger):
        """Test read uncommitted isolation level"""
        manager = SQLiteTransactionManager(connection, logger)
        with patch.object(manager, 'log') as mock_log:
            manager.isolation_level = IsolationLevel.READ_UNCOMMITTED

            # Verify log records
            mock_log.assert_any_call(logging.DEBUG, "Setting isolation level to IsolationLevel.READ_UNCOMMITTED")
            # mock_log.assert_any_call(logging.INFO, "Isolation level set to IsolationLevel.READ_UNCOMMITTED")

            manager.begin()

            # Verify correct isolation level syntax used
            # SQLite READ_UNCOMMITTED corresponds to DEFERRED keyword
            assert manager.is_active is True

            # Check read_uncommitted set to 1
            cursor = connection.execute("PRAGMA read_uncommitted")
            result = cursor.fetchone()
            assert result[0] == 1

            manager.commit()

    def test_unsupported_isolation_level(self, transaction_manager):
        """Test unsupported isolation level"""
        with patch.object(transaction_manager, 'log') as mock_log:
            # SQLite does not support READ_COMMITTED
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.isolation_level = IsolationLevel.READ_COMMITTED

            assert "Unsupported isolation level" in str(exc_info.value)

            # Verify log records
            mock_log.assert_any_call(logging.DEBUG, "Setting isolation level to IsolationLevel.READ_COMMITTED")
            mock_log.assert_any_call(logging.ERROR, "Unsupported isolation level: IsolationLevel.READ_COMMITTED")

    def test_set_isolation_level_during_transaction(self, transaction_manager):
        """Test setting isolation level during transaction"""
        # Begin transaction
        transaction_manager.begin()

        with patch.object(transaction_manager, 'log') as mock_log:
            # Try to change isolation level
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.isolation_level = IsolationLevel.SERIALIZABLE

            assert "Cannot change isolation level during active transaction" in str(exc_info.value)

            # Verify log records
            mock_log.assert_any_call(logging.DEBUG, "Setting isolation level to IsolationLevel.SERIALIZABLE")
            mock_log.assert_any_call(logging.ERROR, "Cannot change isolation level during active transaction")

        # Cleanup
        transaction_manager.rollback()

    def test_savepoint_operations(self, transaction_manager):
        """Test savepoint operations"""
        with patch.object(transaction_manager, 'log') as mock_log:
            # Begin main transaction
            transaction_manager.begin()
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'base')")
            mock_log.reset_mock()

            # Create savepoint
            sp1 = transaction_manager.savepoint("sp1")
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (2, 'sp1')")

            # Verify savepoint creation log
            mock_log.assert_any_call(logging.DEBUG, "Creating savepoint (name: sp1)")
            mock_log.assert_any_call(logging.INFO, "Creating savepoint: sp1")
            mock_log.reset_mock()

            # Create second savepoint
            sp2 = transaction_manager.savepoint("sp2")
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (3, 'sp2')")

            # Verify savepoint creation log
            mock_log.assert_any_call(logging.DEBUG, "Creating savepoint (name: sp2)")
            mock_log.assert_any_call(logging.INFO, "Creating savepoint: sp2")
            mock_log.reset_mock()

            # Rollback to first savepoint
            transaction_manager.rollback_to("sp1")

            # Verify rollback to savepoint log
            mock_log.assert_any_call(logging.DEBUG, "Rolling back to savepoint: sp1")
            mock_log.assert_any_call(logging.INFO, "Rolling back to savepoint: sp1")

            # Verify rollback to sp1 savepoint
            cursor = transaction_manager._connection.execute("SELECT * FROM test ORDER BY id")
            rows = cursor.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 1
            assert rows[0][1] == 'base'
            mock_log.reset_mock()

            # Add new data
            transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (4, 'after-rollback')")

            # Release savepoint sp1
            transaction_manager.release("sp1")

            # Verify release savepoint log
            mock_log.assert_any_call(logging.DEBUG, "Releasing savepoint: sp1")
            mock_log.assert_any_call(logging.INFO, "Releasing savepoint: sp1")
            mock_log.reset_mock()

            # Commit main transaction
            transaction_manager.commit()

            # Verify commit log
            mock_log.assert_any_call(logging.DEBUG, "Committing transaction (level 1)")
            mock_log.assert_any_call(logging.INFO, "Committing outermost transaction")

            # Verify final result
            cursor = transaction_manager._connection.execute("SELECT * FROM test ORDER BY id")
            rows = cursor.fetchall()
            assert len(rows) == 2
            assert rows[0][0] == 1
            assert rows[0][1] == 'base'
            assert rows[1][0] == 4
            assert rows[1][1] == 'after-rollback'

    def test_auto_savepoint_name(self, transaction_manager):
        """Test auto-generated savepoint names"""
        # Begin transaction
        transaction_manager.begin()

        # Create savepoint with auto name
        sp1 = transaction_manager.savepoint()
        assert sp1 == "SP_1"
        assert transaction_manager._savepoint_count == 1

        sp2 = transaction_manager.savepoint()
        assert sp2 == "SP_2"
        assert transaction_manager._savepoint_count == 2

        # Rollback to first savepoint
        transaction_manager.rollback_to(sp1)

        # Create another auto-named savepoint
        sp3 = transaction_manager.savepoint()
        assert sp3 == "SP_3"
        assert transaction_manager._savepoint_count == 3

        # Cleanup
        transaction_manager.rollback()

    def test_transaction_error_handling(self):
        """Test transaction error handling"""
        # Mock connection with execution exceptions
        bad_connection = MagicMock()
        bad_connection.execute.side_effect = sqlite3.Error("Mock error")

        manager = SQLiteTransactionManager(bad_connection)

        with patch.object(manager, 'log') as mock_log:
            # Test begin failure
            with pytest.raises(TransactionError) as exc_info:
                manager.begin()

            assert "Failed to begin transaction: Mock error" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Failed to begin transaction: Mock error")

            # Test commit failure (manually set transaction level)
            manager._transaction_level = 1
            # No longer need to set _active flag since is_active now only depends on _transaction_level

            with pytest.raises(TransactionError) as exc_info:
                manager.commit()

            assert "Failed to commit transaction: Mock error" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Failed to commit transaction: Mock error")

            # Ensure transaction_level restored on failure
            assert manager._transaction_level == 1

            # Test rollback failure
            with pytest.raises(TransactionError) as exc_info:
                manager.rollback()

            assert "Failed to rollback transaction: Mock error" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Failed to rollback transaction: Mock error")

            # Ensure transaction_level restored on failure
            assert manager._transaction_level == 1

            # Test savepoint failure
            with pytest.raises(TransactionError) as exc_info:
                manager.savepoint("sp1")

            assert "Failed to create savepoint" in str(exc_info.value)
            assert any("Failed to create savepoint" in args[1] for args, kwargs in mock_log.call_args_list
                       if args[0] == logging.ERROR)

            # Manually add savepoint to active list to test subsequent operations
            manager._active_savepoints.append("sp1")

            # Test release failure
            with pytest.raises(TransactionError) as exc_info:
                manager.release("sp1")

            assert "Failed to release savepoint" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Failed to release savepoint sp1: Mock error")

            # Test rollback_to failure
            with pytest.raises(TransactionError) as exc_info:
                manager.rollback_to("sp1")

            assert "Failed to rollback to savepoint" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Failed to rollback to savepoint sp1: Mock error")

    def test_commit_without_active_transaction(self, transaction_manager):
        """Test commit without active transaction"""
        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.commit()

            assert "No active transaction to commit" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "No active transaction to commit")

    def test_rollback_without_active_transaction(self, transaction_manager):
        """Test rollback without active transaction"""
        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.rollback()

            assert "No active transaction to rollback" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "No active transaction to rollback")

    def test_savepoint_without_active_transaction(self, transaction_manager):
        """Test creating savepoint without active transaction"""
        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.savepoint("sp1")

            assert "Cannot create savepoint: no active transaction" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Cannot create savepoint: no active transaction")

    def test_release_invalid_savepoint(self, transaction_manager):
        """Test releasing non-existent savepoint"""
        # Begin transaction
        transaction_manager.begin()

        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.release("nonexistent")

            assert "Invalid savepoint name: nonexistent" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Invalid savepoint name: nonexistent")

        # Cleanup
        transaction_manager.rollback()

    def test_rollback_to_invalid_savepoint(self, transaction_manager):
        """Test rollback to non-existent savepoint"""
        # Begin transaction
        transaction_manager.begin()

        with patch.object(transaction_manager, 'log') as mock_log:
            with pytest.raises(TransactionError) as exc_info:
                transaction_manager.rollback_to("nonexistent")

            assert "Invalid savepoint name: nonexistent" in str(exc_info.value)
            mock_log.assert_any_call(logging.ERROR, "Invalid savepoint name: nonexistent")

        # Cleanup
        transaction_manager.rollback()

    def test_supports_savepoint(self, transaction_manager):
        """Test savepoint support check"""
        assert transaction_manager.supports_savepoint() is True

    @pytest.mark.skipif(sqlite3.sqlite_version_info < (3, 6, 8), reason="SQLite 3.6.8+ required for savepoint")
    def test_multiple_savepoints(self, transaction_manager):
        """Test multiple savepoints"""
        # Begin transaction
        transaction_manager.begin()

        ## Create multiple savepoints
        savepoints = []
        for i in range(5):
            transaction_manager._connection.execute(f"INSERT INTO test (id, value) VALUES ({i + 1}, 'value{i + 1}')")
            sp_name = transaction_manager.savepoint(f"sp{i + 1}")
            savepoints.append(sp_name)

        # Verify all data inserted
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 5

        # Rollback to middle savepoint
        transaction_manager.rollback_to("sp3")

        # Verify data after rollback
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 3

        # Rollback to first savepoint
        transaction_manager.rollback_to("sp1")

        # Verify data after rollback
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 1

        # Commit transaction
        transaction_manager.commit()

        # Verify final data
        cursor = transaction_manager._connection.execute("SELECT * FROM test")
        row = cursor.fetchone()
        assert row[0] == 1
        assert row[1] == 'value1'

    def test_transaction_level_counter(self, transaction_manager):
        """Test transaction nesting level counter"""
        assert transaction_manager._transaction_level == 0

        # First level transaction
        transaction_manager.begin()
        assert transaction_manager._transaction_level == 1

        # Second level transaction
        transaction_manager.begin()
        assert transaction_manager._transaction_level == 2

        # Third level transaction
        transaction_manager.begin()
        assert transaction_manager._transaction_level == 3

        # Rollback one level
        transaction_manager.rollback()
        assert transaction_manager._transaction_level == 2

        # Commit one level
        transaction_manager.commit()
        assert transaction_manager._transaction_level == 1

        # Final commit
        transaction_manager.commit()
        assert transaction_manager._transaction_level == 0

    def test_mixed_savepoint_transactions(self, transaction_manager):
        """Test mixed usage of savepoints and nested transactions"""
        # Begin main transaction
        transaction_manager.begin()
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (1, 'main')")

        # Create manual savepoint
        sp1 = transaction_manager.savepoint("manual_sp")
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (2, 'manual_sp')")

        # Create nested transaction (internally uses savepoint)
        transaction_manager.begin()
        transaction_manager._connection.execute("INSERT INTO test (id, value) VALUES (3, 'nested')")

        # Should now have 3 rows
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 3

        # Rollback nested transaction
        transaction_manager.rollback()

        # Should have 2 rows remaining
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 2

        # Rollback to manual savepoint
        transaction_manager.rollback_to(sp1)

        # Should have 1 row remaining
        cursor = transaction_manager._connection.execute("SELECT COUNT(*) FROM test")
        assert cursor.fetchone()[0] == 1

        # Commit main transaction
        transaction_manager.commit()

        # Verify final result
        cursor = transaction_manager._connection.execute("SELECT * FROM test")
        row = cursor.fetchone()
        assert row[0] == 1
        assert row[1] == 'main'
