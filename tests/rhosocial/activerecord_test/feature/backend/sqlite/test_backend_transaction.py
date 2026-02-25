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
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        backend.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, value TEXT)", options=ExecutionOptions(stmt_type=StatementType.DDL))
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
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        backend.begin_transaction()

        # Insert data
        backend.execute("INSERT INTO test (id, value) VALUES (1, 'test commit')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

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
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        backend.begin_transaction()

        # Insert data
        backend.execute("INSERT INTO test (id, value) VALUES (2, 'test rollback')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

        # Rollback transaction
        backend.rollback_transaction()
        assert backend.in_transaction is False

        # Verify data was rolled back
        result = backend.fetch_one("SELECT * FROM test WHERE id = 2")
        assert result is None

    def test_transaction_context_manager(self, backend):
        """Test transaction context manager"""
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        # Use with statement for transaction management
        with backend.transaction():
            backend.execute("INSERT INTO test (id, value) VALUES (3, 'context manager')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

        # Verify transaction was committed
        assert backend.in_transaction is False
        result = backend.fetch_one("SELECT * FROM test WHERE id = 3")
        assert result is not None
        assert result['id'] == 3
        assert result['value'] == 'context manager'

    def test_transaction_context_manager_exception(self, backend):
        """Test transaction context manager exception handling"""
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        try:
            with backend.transaction():
                backend.execute("INSERT INTO test (id, value) VALUES (4, 'context exception')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))
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
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        backend.begin_transaction()

        # Insert data
        backend.execute("INSERT INTO test (id, value) VALUES (5, 'outer')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

        # Start inner transaction
        backend.begin_transaction()

        # Insert more data
        backend.execute("INSERT INTO test (id, value) VALUES (6, 'inner')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

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
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        # Start outer transaction
        backend.begin_transaction()

        # Insert data
        backend.execute("INSERT INTO test (id, value) VALUES (7, 'outer mixed')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

        # Use context manager to start inner transaction
        with backend.transaction():
            backend.execute("INSERT INTO test (id, value) VALUES (8, 'inner mixed')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

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
        from rhosocial.activerecord.backend.options import InsertOptions
        # Use insert method with proper options
        insert_opts = InsertOptions(
            table="test",
            data={"id": 9, "value": "auto insert"},
            primary_key="id"
        )
        result = backend.insert(insert_opts)

        # Verify insertion was successful
        assert result.affected_rows == 1

        # Verify data exists
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        row = backend.fetch_one("SELECT * FROM test WHERE id = 9")
        assert row is not None
        assert row['value'] == 'auto insert'

    def test_auto_transaction_on_update(self, backend):
        """Test automatic transaction handling for update operations"""
        from rhosocial.activerecord.backend.options import InsertOptions, UpdateOptions
        from rhosocial.activerecord.backend.expression import Column, Literal, ComparisonPredicate
        # First insert data
        insert_opts = InsertOptions(
            table="test",
            data={"id": 10, "value": "before update"},
            primary_key="id"
        )
        backend.insert(insert_opts)

        # Use update method with proper options
        where_clause = ComparisonPredicate(backend.dialect, "=", Column(backend.dialect, "id"), Literal(backend.dialect, 10))
        update_opts = UpdateOptions(
            table="test",
            data={"value": "after update"},
            where=where_clause
        )
        result = backend.update(update_opts)

        # Verify update was successful
        assert result.affected_rows == 1

        # Verify data was updated
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        row = backend.fetch_one("SELECT * FROM test WHERE id = 10")
        assert row is not None
        assert row['value'] == 'after update'

    def test_auto_transaction_on_delete(self, backend):
        """Test automatic transaction handling for delete operations"""
        from rhosocial.activerecord.backend.options import InsertOptions, DeleteOptions
        from rhosocial.activerecord.backend.expression import Column, Literal, ComparisonPredicate
        # First insert data
        insert_opts = InsertOptions(
            table="test",
            data={"id": 11, "value": "to be deleted"},
            primary_key="id"
        )
        backend.insert(insert_opts)

        # Verify data was inserted
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        row = backend.fetch_one("SELECT * FROM test WHERE id = 11")
        assert row is not None

        # Use delete method with proper options
        where_clause = ComparisonPredicate(backend.dialect, "=", Column(backend.dialect, "id"), Literal(backend.dialect, 11))
        delete_opts = DeleteOptions(
            table="test",
            where=where_clause
        )
        result = backend.delete(delete_opts)

        # Verify deletion was successful
        assert result.affected_rows == 1

        # Verify data was deleted
        row = backend.fetch_one("SELECT * FROM test WHERE id = 11")
        assert row is None

    def test_transaction_with_integrity_error(self, backend):
        """Test integrity error within a transaction"""
        from rhosocial.activerecord.backend.options import InsertOptions
        # First insert data
        insert_opts = InsertOptions(
            table="test",
            data={"id": 12, "value": "unique"},
            primary_key="id"
        )
        backend.insert(insert_opts)

        # Begin transaction
        backend.begin_transaction()

        # Insert some data
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        backend.execute("INSERT INTO test (id, value) VALUES (13, 'before error')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

        # Try to insert duplicate data, should fail
        with pytest.raises(IntegrityError):
            backend.execute("INSERT INTO test (id, value) VALUES (12, 'duplicate')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

        # Rollback transaction
        backend.rollback_transaction()

        # Verify all operations within the transaction were rolled back
        row = backend.fetch_one("SELECT * FROM test WHERE id = 13")
        assert row is None

    def test_connection_context_manager(self, backend):
        """Test connection context manager"""
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        # Use with statement for connection management
        with backend as conn:
            # Use connection in the context
            conn.execute("INSERT INTO test (id, value) VALUES (14, 'connection context')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

        # Verify operation was successful
        row = backend.fetch_one("SELECT * FROM test WHERE id = 14")
        assert row is not None
        assert row['value'] == 'connection context'

    def test_disconnect_during_transaction(self, backend):
        """Test disconnecting during a transaction"""
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        # Begin transaction
        backend.begin_transaction()

        # Insert data
        backend.execute("INSERT INTO test (id, value) VALUES (15, 'disconnect test')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

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
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        backend.connect()
        backend.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)", (), options=ExecutionOptions(stmt_type=StatementType.DDL))
        backend.execute("INSERT INTO test (id, value) VALUES (1, 'temp data')", (), options=ExecutionOptions(stmt_type=StatementType.INSERT))

        # Verify file exists
        assert os.path.exists(temp_db_path)

        # Disconnect, should delete the file
        backend.disconnect()

        # Verify files were deleted
        assert not os.path.exists(temp_db_path)
        assert not os.path.exists(temp_db_path + "-wal")
        assert not os.path.exists(temp_db_path + "-shm")
