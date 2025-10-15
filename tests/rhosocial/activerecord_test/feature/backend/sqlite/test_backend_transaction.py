# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_backend_transaction.py
import os
import tempfile

import pytest

from rhosocial.activerecord.backend.errors import (
    IntegrityError
)
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.transaction import SQLiteTransactionManager
from rhosocial.activerecord.backend.config import ConnectionConfig


class TestSQLiteBackendTransaction:
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file path"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            self._retry_delete(path)
        # Clean up related WAL and SHM files
        for ext in ['-wal', '-shm']:
            wal_path = path + ext
            if os.path.exists(wal_path):
                self._retry_delete(wal_path)

    def _retry_delete(self, file_path, max_retries=5, retry_delay=0.1):
        """Try to delete a file, retry if failed
        
        Args:
            file_path: Path of the file to delete
            max_retries: Maximum number of retry attempts
            retry_delay: Retry interval time (seconds)
        """
        import time
        for attempt in range(max_retries):
            try:
                os.unlink(file_path)
                return  # Deletion successful, return directly
            except OSError as e:
                if attempt < max_retries - 1:  # If not the last attempt
                    time.sleep(retry_delay)  # Wait for a while before retrying
                else:
                    # All retries failed, log error but don't raise exception
                    print(f"Warning: Failed to delete file {file_path}: {e}")

    @pytest.fixture
    def config(self, temp_db_path):
        """Create database configuration"""
        return ConnectionConfig(database=temp_db_path)

    @pytest.fixture
    def backend(self, config):
        """Create SQLite backend"""
        backend = SQLiteBackend(connection_config=config)
        # Ensure table exists
        backend.connect()
        backend.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, value TEXT)")
        return backend

    def test_transaction_property(self, backend):
        """Test transaction manager property"""
        assert backend._transaction_manager is None

        # Accessing the property should create a transaction manager
        assert isinstance(backend.transaction_manager, SQLiteTransactionManager)
        assert backend._transaction_manager is not None

        # Accessing again should return the same instance
        assert backend.transaction_manager is backend._transaction_manager

    def test_begin_transaction(self, backend):
        """Test beginning a transaction"""
        backend.begin_transaction()
        assert backend.in_transaction is True
        assert backend.transaction_manager.is_active is True

    def test_commit_transaction(self, backend):
        """Test committing a transaction"""
        backend.begin_transaction()

        # Insert data
        backend.execute("INSERT INTO test (id, value) VALUES (1, 'test commit')")

        # Commit transaction
        backend.commit_transaction()
        assert backend.in_transaction is False

        # Verify data was committed
        result = backend.fetch_one("SELECT * FROM test WHERE id = 1")
        assert result is not None
        assert result['id'] == 1
        assert result['value'] == 'test commit'

    def test_rollback_transaction(self, backend):
        """Test rolling back a transaction"""
        backend.begin_transaction()

        # Insert data
        backend.execute("INSERT INTO test (id, value) VALUES (2, 'test rollback')")

        # Rollback transaction
        backend.rollback_transaction()
        assert backend.in_transaction is False

        # Verify data was rolled back
        result = backend.fetch_one("SELECT * FROM test WHERE id = 2")
        assert result is None

    def test_transaction_context_manager(self, backend):
        """Test transaction context manager"""
        # Use with statement for transaction management
        with backend.transaction():
            backend.execute("INSERT INTO test (id, value) VALUES (3, 'context manager')")

        # Verify transaction was committed
        assert backend.in_transaction is False
        result = backend.fetch_one("SELECT * FROM test WHERE id = 3")
        assert result is not None
        assert result['id'] == 3
        assert result['value'] == 'context manager'

    def test_transaction_context_manager_exception(self, backend):
        """Test transaction context manager exception handling"""
        try:
            with backend.transaction():
                backend.execute("INSERT INTO test (id, value) VALUES (4, 'context exception')")
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Verify transaction was rolled back
        assert backend.in_transaction is False
        result = backend.fetch_one("SELECT * FROM test WHERE id = 4")
        assert result is None

    def test_nested_transactions(self, backend):
        """Test nested transactions"""
        # Start outer transaction
        backend.begin_transaction()

        # Insert data
        backend.execute("INSERT INTO test (id, value) VALUES (5, 'outer')")

        # Start inner transaction
        backend.begin_transaction()

        # Insert more data
        backend.execute("INSERT INTO test (id, value) VALUES (6, 'inner')")

        # Rollback inner transaction
        backend.rollback_transaction()

        # Verify inner transaction was rolled back
        result = backend.fetch_one("SELECT * FROM test WHERE id = 6")
        assert result is None

        # Verify outer transaction data still exists
        result = backend.fetch_one("SELECT * FROM test WHERE id = 5")
        assert result is not None
        assert result['value'] == 'outer'

        # Commit outer transaction
        backend.commit_transaction()

        # Verify outer transaction was committed successfully
        result = backend.fetch_one("SELECT * FROM test WHERE id = 5")
        assert result is not None
        assert result['value'] == 'outer'

    def test_mixed_nested_transactions(self, backend):
        """Test mixed nested transactions (including context manager)"""
        # Start outer transaction
        backend.begin_transaction()

        # Insert data
        backend.execute("INSERT INTO test (id, value) VALUES (7, 'outer mixed')")

        # Use context manager to start inner transaction
        with backend.transaction():
            backend.execute("INSERT INTO test (id, value) VALUES (8, 'inner mixed')")

        # Verify inner transaction was committed successfully
        result = backend.fetch_all("SELECT * FROM test WHERE id IN (7, 8) ORDER BY id")
        assert len(result) == 2
        assert result[0]['value'] == 'outer mixed'
        assert result[1]['value'] == 'inner mixed'

        # Rollback outer transaction
        backend.rollback_transaction()

        # Verify all data was rolled back
        result = backend.fetch_all("SELECT * FROM test WHERE id IN (7, 8)")
        assert len(result) == 0

    def test_auto_transaction_on_insert(self, backend):
        """Test automatic transaction handling for insert operations"""
        # Use insert method
        result = backend.insert("test", {"id": 9, "value": "auto insert"})

        # Verify insertion was successful
        assert result.affected_rows == 1
        assert result.last_insert_id == 9

        # Verify data exists
        row = backend.fetch_one("SELECT * FROM test WHERE id = 9")
        assert row is not None
        assert row['value'] == 'auto insert'

    def test_auto_transaction_on_update(self, backend):
        """Test automatic transaction handling for update operations"""
        # First insert data
        backend.insert("test", {"id": 10, "value": "before update"})

        # Use update method
        result = backend.update("test", {"value": "after update"}, "id = ?", (10,))

        # Verify update was successful
        assert result.affected_rows == 1

        # Verify data was updated
        row = backend.fetch_one("SELECT * FROM test WHERE id = 10")
        assert row is not None
        assert row['value'] == 'after update'

    def test_auto_transaction_on_delete(self, backend):
        """Test automatic transaction handling for delete operations"""
        # First insert data
        backend.insert("test", {"id": 11, "value": "to be deleted"})

        # Verify data was inserted
        row = backend.fetch_one("SELECT * FROM test WHERE id = 11")
        assert row is not None

        # Use delete method
        result = backend.delete("test", "id = ?", (11,))

        # Verify deletion was successful
        assert result.affected_rows == 1

        # Verify data was deleted
        row = backend.fetch_one("SELECT * FROM test WHERE id = 11")
        assert row is None

    def test_transaction_with_integrity_error(self, backend):
        """Test integrity error within a transaction"""
        # First insert data
        backend.insert("test", {"id": 12, "value": "unique"})

        # Begin transaction
        backend.begin_transaction()

        # Insert some data
        backend.execute("INSERT INTO test (id, value) VALUES (13, 'before error')")

        # Try to insert duplicate data, should fail
        with pytest.raises(IntegrityError):
            backend.execute("INSERT INTO test (id, value) VALUES (12, 'duplicate')")

        # Rollback transaction
        backend.rollback_transaction()

        # Verify all operations within the transaction were rolled back
        row = backend.fetch_one("SELECT * FROM test WHERE id = 13")
        assert row is None

    def test_connection_context_manager(self, backend):
        """Test connection context manager"""
        # Use with statement for connection management
        with backend as conn:
            # Use connection in the context
            conn.execute("INSERT INTO test (id, value) VALUES (14, 'connection context')")

        # Verify operation was successful
        row = backend.fetch_one("SELECT * FROM test WHERE id = 14")
        assert row is not None
        assert row['value'] == 'connection context'

    def test_disconnect_during_transaction(self, backend):
        """Test disconnecting during a transaction"""
        # Begin transaction
        backend.begin_transaction()

        # Insert data
        backend.execute("INSERT INTO test (id, value) VALUES (15, 'disconnect test')")

        # Disconnect
        backend.disconnect()

        # Verify transaction state was reset
        assert backend._transaction_manager is None
        assert backend._connection is None
        assert backend.in_transaction is False

        # Reconnect and verify data was rolled back
        backend.connect()
        row = backend.fetch_one("SELECT * FROM test WHERE id = 15")
        assert row is None

    def test_delete_on_close(self, temp_db_path):
        """Test deleting database file on close"""
        # Create backend with delete_on_close
        config = SQLiteConnectionConfig(database=temp_db_path, delete_on_close=True)
        backend = SQLiteBackend(connection_config=config)

        # Connect and create table
        backend.connect()
        backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        backend.execute("INSERT INTO test (id, value) VALUES (1, 'temp data')")

        # Verify file exists
        assert os.path.exists(temp_db_path)

        # Disconnect, should delete the file
        backend.disconnect()

        # Verify files were deleted
        assert not os.path.exists(temp_db_path)
        assert not os.path.exists(temp_db_path + "-wal")
        assert not os.path.exists(temp_db_path + "-shm")
