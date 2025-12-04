# tests/rhosocial/activerecord_test/backend/common/test_sync_transaction.py
import pytest
from unittest.mock import patch
import logging
from rhosocial.activerecord.backend.errors import TransactionError, IsolationLevelError
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.transaction import IsolationLevel

# This test file now uses a real SQLite backend to validate transaction logic.

@pytest.fixture
def backend():
    """Provides a real, connected in-memory SQLite backend for each test."""
    config = SQLiteConnectionConfig(database=":memory:")
    # The actual backend class is tested, not a mock
    backend = SQLiteBackend(connection_config=config)
    backend.connect()
    # Provide a simple table for transaction tests
    backend.execute("CREATE TABLE test_data (id INTEGER, name TEXT)")
    yield backend
    backend.disconnect()

class TestRealTransactionManager:
    def test_begin_commit_cycle(self, backend):
        """Test a simple begin -> commit cycle against a real database."""
        tm = backend.transaction_manager
        
        assert not tm.is_active
        tm.begin()
        assert tm.is_active
        
        backend.execute("INSERT INTO test_data (id, name) VALUES (1, 'test')")
        
        tm.commit()
        assert not tm.is_active
        
        # Verify the data is in the database
        result = backend.fetch_one("SELECT * FROM test_data WHERE id = 1")
        assert result is not None
        assert result['name'] == 'test'

    def test_begin_rollback_cycle(self, backend):
        """Test a simple begin -> rollback cycle against a real database."""
        tm = backend.transaction_manager
        tm.begin()
        backend.execute("INSERT INTO test_data (id, name) VALUES (1, 'test')")
        tm.rollback()
        assert not tm.is_active

        # Verify the data is NOT in the database
        result = backend.fetch_one("SELECT * FROM test_data WHERE id = 1")
        assert result is None

    def test_context_manager_success(self, backend):
        """Test the context manager for a successful transaction."""
        with backend.transaction_manager.transaction():
            backend.execute("INSERT INTO test_data (id, name) VALUES (1, 'committed')")

        result = backend.fetch_one("SELECT * FROM test_data WHERE id = 1")
        assert result is not None
        assert result['name'] == 'committed'

    def test_context_manager_exception(self, backend):
        """Test the context manager rolling back on exception."""
        with pytest.raises(ValueError):
            with backend.transaction_manager.transaction():
                backend.execute("INSERT INTO test_data (id, name) VALUES (1, 'rolled_back')")
                raise ValueError("Simulating an error")

        # Verify the data was rolled back
        result = backend.fetch_one("SELECT * FROM test_data WHERE id = 1")
        assert result is None

    def test_nested_transaction_rollback(self, backend):
        """Test that rolling back a nested transaction (savepoint) works."""
        tm = backend.transaction_manager
        tm.begin() # Outer transaction
        backend.execute("INSERT INTO test_data (id, name) VALUES (1, 'outer')")

        tm.begin() # Nested transaction (creates savepoint)
        backend.execute("INSERT INTO test_data (id, name) VALUES (2, 'inner')")
        
        # Verify both records are visible inside the nested transaction
        count_res = backend.fetch_one("SELECT COUNT(*) as c FROM test_data")
        assert count_res['c'] == 2

        tm.rollback() # Rolls back to the savepoint

        # Verify the inner insert was rolled back, but the outer is still there
        count_res = backend.fetch_one("SELECT COUNT(*) as c FROM test_data")
        assert count_res['c'] == 1
        outer_rec = backend.fetch_one("SELECT * FROM test_data WHERE id = 1")
        assert outer_rec['name'] == 'outer'

        tm.commit() # Commits the outer transaction

        # Verify the final state
        final_count = backend.fetch_one("SELECT COUNT(*) as c FROM test_data")
        assert final_count['c'] == 1
    
    def test_explicit_savepoints(self, backend):
        """Test explicit savepoint management against a real database."""
        tm = backend.transaction_manager
        tm.begin()
        backend.execute("INSERT INTO test_data (id, name) VALUES (1, 'initial')")

        sp1 = tm.savepoint("SP1")
        backend.execute("INSERT INTO test_data (id, name) VALUES (2, 'savepoint_data')")
        
        count_res = backend.fetch_one("SELECT COUNT(*) as c FROM test_data")
        assert count_res['c'] == 2

        tm.rollback_to(sp1)

        # Verify rollback to savepoint
        count_res = backend.fetch_one("SELECT COUNT(*) as c FROM test_data")
        assert count_res['c'] == 1

        tm.release(sp1)
        tm.commit()

        # Verify final state
        final_count = backend.fetch_one("SELECT COUNT(*) as c FROM test_data")
        assert final_count['c'] == 1
        assert backend.fetch_one("SELECT name FROM test_data")['name'] == 'initial'

    def test_error_on_changing_isolation_level_when_active(self, backend):
        """Test error when changing isolation level during a transaction."""
        tm = backend.transaction_manager
        tm.begin()
        with pytest.raises(TransactionError):
            tm.isolation_level = IsolationLevel.READ_COMMITTED
        tm.rollback()

    def test_explicit_savepoint_release(self, backend):
        """Test explicitly releasing a savepoint."""
        tm = backend.transaction_manager
        tm.begin()
        backend.execute("INSERT INTO test_data (id, name) VALUES (1, 'one')")
        sp1 = tm.savepoint("SP1")
        backend.execute("INSERT INTO test_data (id, name) VALUES (2, 'two')")
        tm.release(sp1) # Release the savepoint
        
        # After release, we can't roll back to it
        with pytest.raises(TransactionError, match="Invalid savepoint name: SP1"):
            tm.rollback_to("SP1")

        tm.commit()
        count_res = backend.fetch_one("SELECT COUNT(*) as c FROM test_data")
        assert count_res['c'] == 2

    def test_rollback_to_removes_later_savepoints(self, backend):
        """Test that rolling back to a savepoint removes subsequent savepoints."""
        tm = backend.transaction_manager
        tm.begin()
        sp1 = tm.savepoint("SP1")
        sp2 = tm.savepoint("SP2")
        
        assert "SP1" in tm._active_savepoints
        assert "SP2" in tm._active_savepoints

        tm.rollback_to("SP1")

        assert "SP1" in tm._active_savepoints
        assert "SP2" not in tm._active_savepoints
        
        tm.commit()

    def test_error_on_releasing_invalid_savepoint(self, backend):
        """Test error when releasing a non-existent savepoint."""
        tm = backend.transaction_manager
        tm.begin()
        with pytest.raises(TransactionError, match="Invalid savepoint name: BADSAVEPOINT"):
            tm.release("BADSAVEPOINT")
        tm.rollback()

    def test_failed_commit_restores_transaction_level(self, backend):
        """Test that a failed commit restores the transaction level."""
        tm = backend.transaction_manager
        
        # Patch the _do_commit method on the class to simulate a failure
        with patch('rhosocial.activerecord.backend.impl.sqlite.transaction.SQLiteTransactionManager._do_commit', side_effect=Exception("Commit failed")):
            tm.begin()
            assert tm.transaction_level == 1
            with pytest.raises(TransactionError, match="Failed to commit transaction"):
                tm.commit()
            # Check that the level was restored
            assert tm.transaction_level == 1
            
            # Since the original rollback is also affected by the patch, 
            # we manually reset the state for test isolation.
            tm._transaction_level = 0

    def test_failed_begin_raises_transaction_error(self, backend):
        """Test that a failed begin operation raises TransactionError."""
        tm = backend.transaction_manager
        with patch('rhosocial.activerecord.backend.impl.sqlite.transaction.SQLiteTransactionManager._do_begin', side_effect=Exception("Begin failed")):
            with pytest.raises(TransactionError, match="Failed to begin transaction"):
                tm.begin()
            assert not tm.is_active

    def test_failed_rollback_restores_transaction_level(self, backend):
        """Test that a failed rollback operation restores the transaction level."""
        tm = backend.transaction_manager
        
        with patch('rhosocial.activerecord.backend.impl.sqlite.transaction.SQLiteTransactionManager._do_rollback', side_effect=Exception("Rollback failed")):
            tm.begin()
            assert tm.transaction_level == 1
            with pytest.raises(TransactionError, match="Failed to rollback transaction"):
                tm.rollback()
            # The transaction level should be restored on failure
            assert tm.is_active
            assert tm.transaction_level == 1
        
        # Manually clean up the 'leaked' transaction from the test
        tm._transaction_level = 0
        
    def test_nested_commit_with_no_savepoint_warning(self, backend, caplog):
        """Test that a warning is logged if a nested commit finds no savepoint."""
        tm = backend.transaction_manager
        tm.begin()
        tm.begin() # Level 2
        
        # Manually clear the savepoints to simulate an abnormal state
        tm._active_savepoints.clear()
        
        with caplog.at_level(logging.WARNING):
            tm.commit() # This should now log a warning
        
        assert "No savepoint found for commit, continuing" in caplog.text
        tm.commit() # Commit the outer transaction
