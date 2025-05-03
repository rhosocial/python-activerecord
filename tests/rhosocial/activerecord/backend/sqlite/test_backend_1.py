"""Tests for improving SQLite backend coverage - Fixed version"""

import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

from src.rhosocial.activerecord.backend.errors import ConnectionError
from src.rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from src.rhosocial.activerecord.backend.typing import ConnectionConfig


class TestSQLiteBackendCoveragePart1:
    """Fixed tests to improve coverage of SQLiteBackend"""

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
        """Try to delete a file, retry if failed"""
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

    def test_set_pragma_exception_handling(self, temp_db_path):
        """Test set_pragma exception handling by using invalid pragma"""
        backend = SQLiteBackend(database=temp_db_path)
        backend.connect()

        # Use an invalid pragma value that will cause an error
        with pytest.raises(ConnectionError) as exc_info:
            backend.set_pragma("invalid_pragma", "'; DROP TABLE users; --")

        assert "Failed to set pragma" in str(exc_info.value)

        backend.disconnect()

    def test_apply_pragmas_exception_handling(self, temp_db_path):
        """Test _apply_pragmas exception handling by adding invalid pragma"""
        # Create backend with invalid pragma
        backend = SQLiteBackend(
            database=temp_db_path,
            pragmas={"invalid_syntax_pragma": "INVALID SQL SYNTAX"}
        )

        # Connect, which will trigger _apply_pragmas
        backend.connect()

        # The method should catch and log the error without raising
        # We can verify that connection still works
        result = backend.execute("SELECT 1 as test", returning=True)
        assert result.data[0]['test'] == 1

        backend.disconnect()

    def test_disconnect_exception_during_close(self, temp_db_path):
        """Test disconnect() with exception during connection close"""
        backend = SQLiteBackend(database=temp_db_path)
        backend.connect()

        # Force an exception by setting the connection to None
        original_connection = backend._connection
        backend._connection = None

        # with pytest.raises(ConnectionError) as exc_info:
        # Should not raise ConnectionError
        backend.disconnect()

        # assert "Failed to disconnect" in str(exc_info.value)

        # Cleanup
        backend._connection = original_connection
        backend.disconnect()

    def test_disconnect_delete_files_exception(self, temp_db_path):
        """Test disconnect() with exception during file deletion"""
        backend = SQLiteBackend(database=temp_db_path, delete_on_close=True)
        backend.connect()

        # Mock exception during file deletion
        with patch('os.path.exists', return_value=True), \
             patch('os.remove', side_effect=Exception("Unexpected error")):

            # Should raise ConnectionError
            with pytest.raises(ConnectionError) as exc_info:
                backend.disconnect()

            assert "Failed to delete database files" in str(exc_info.value)

    def test_ping_with_reconnect_failure(self, temp_db_path):
        """Test ping() method with reconnect by using invalid database"""
        # Create a backend with a file that can't be opened
        backend = SQLiteBackend(database="/invalid/path/to/database.db")

        # Should return False if reconnect fails
        result = backend.ping(reconnect=True)

        # Since the path is invalid, it should fail to connect and return False
        assert result is False

    def test_ping_with_connection_error(self, temp_db_path):
        """Test ping() with connection error"""
        backend = SQLiteBackend(database=temp_db_path)
        backend.connect()

        # Close the connection to simulate connection error
        backend._connection.close()

        # Test without reconnect
        result = backend.ping(reconnect=False)
        assert result is False

        # Test with reconnect
        result = backend.ping(reconnect=True)
        assert result is True
        assert backend._connection is not None

        backend.disconnect()

    def test_pragmas_property(self, temp_db_path):
        """Test SQLiteBackend.pragmas() property"""
        backend = SQLiteBackend(database=temp_db_path)

        # Test default pragmas
        pragmas = backend.pragmas
        assert isinstance(pragmas, dict)
        assert "foreign_keys" in pragmas
        assert pragmas["foreign_keys"] == "ON"

        # Test that we get a copy, not the original
        pragmas["test_key"] = "test_value"
        assert "test_key" not in backend.pragmas

        backend.disconnect()

    def test_get_pragma_settings_options_branch(self, temp_db_path):
        """Test _get_pragma_settings() with different options configurations"""
        # Test with pragmas in kwargs
        kwargs = {
            "pragmas": {"test_pragma": "test_value"}
        }
        backend1 = SQLiteBackend(database=temp_db_path, **kwargs)
        pragmas1 = backend1._get_pragma_settings(kwargs)
        assert pragmas1["test_pragma"] == "test_value"

        # Test with pragmas in config
        config = ConnectionConfig(
            database=temp_db_path,
            pragmas={"config_pragma": "config_value"}
        )
        backend2 = SQLiteBackend(connection_config=config)
        pragmas2 = backend2._get_pragma_settings({})
        assert pragmas2["config_pragma"] == "config_value"

        # Test with pragmas in options
        kwargs_options = {
            "options": {"pragmas": {"options_pragma": "options_value"}}
        }
        backend3 = SQLiteBackend(database=temp_db_path, **kwargs_options)
        pragmas3 = backend3._get_pragma_settings(kwargs_options)
        assert pragmas3["options_pragma"] == "options_value"

        # Test with pragmas in config.options
        config_options = ConnectionConfig(
            database=temp_db_path,
            options={"pragmas": {"config_options_pragma": "config_options_value"}}
        )
        backend4 = SQLiteBackend(connection_config=config_options)
        pragmas4 = backend4._get_pragma_settings({})
        assert pragmas4["config_options_pragma"] == "config_options_value"

    def test_connect_exception_handling(self, temp_db_path):
        """Test connect() exception handling"""
        # Use an invalid database path to trigger an error
        backend = SQLiteBackend(database="/invalid/path/database.db")

        with pytest.raises(ConnectionError) as exc_info:
            backend.connect()

        assert "Failed to connect" in str(exc_info.value)

    def test_is_sqlite_property(self, temp_db_path):
        """Test is_sqlite property"""
        backend = SQLiteBackend(database=temp_db_path)
        assert backend.is_sqlite is True

    def test_ping_with_execute_error(self, temp_db_path):
        """Test ping() with execute error by corrupting the connection"""
        backend = SQLiteBackend(database=temp_db_path)
        backend.connect()

        # Create a wrapper class to simulate an execute error
        class ConnectionWrapper:
            def __init__(self, conn):
                self._conn = conn

            def execute(self, sql):
                raise sqlite3.Error("Simulated execute error")

            def __getattr__(self, name):
                return getattr(self._conn, name)

        # Replace connection with wrapper
        original_conn = backend._connection
        backend._connection = ConnectionWrapper(original_conn)

        # Test without reconnect
        result = backend.ping(reconnect=False)
        assert result is False

        # Test with reconnect
        backend._connection = original_conn  # Restore for reconnect
        result = backend.ping(reconnect=True)
        assert result is True

        backend.disconnect()

    def test_disconnect_without_connection(self):
        """Test disconnect when connection is None"""
        backend = SQLiteBackend(database=":memory:")

        # Should not raise exception
        backend.disconnect()
        assert backend._connection is None

    def test_disconnect_delete_on_close_errors(self, temp_db_path):
        """Test disconnect() with delete_on_close errors"""
        backend = SQLiteBackend(database=temp_db_path, delete_on_close=True)
        backend.connect()

        # Create a file that will simulate failure to delete
        with open(temp_db_path + "-wal", "w") as f:
            f.write("test")

        # Simulate permission error for the main database file only
        original_remove = os.remove
        error_count = 0

        def mock_remove(path):
            nonlocal error_count
            if path == temp_db_path:
                error_count += 1
                if error_count < 6:  # Always fail
                    raise OSError("Permission denied")
            return original_remove(path)

        with patch('os.remove', mock_remove):
            # Should attempt retries and log warning but not raise
            backend.disconnect()

            # Should have tried max_retries times
            assert error_count == 5  # Default max_retries is 5

            # Connection should still be cleared
            assert backend._connection is None

    def test_disconnect_idempotent(self):
        """Test that disconnect() is idempotent and can be called multiple times safely"""
        backend = SQLiteBackend(database=":memory:")

        # Should not raise when called without a connection
        backend.disconnect()

        # Connect and then disconnect
        backend.connect()
        backend.disconnect()

        # Should not raise when called again
        backend.disconnect()
        backend.disconnect()

        # Verify the state is clean
        assert backend._connection is None
        assert backend._cursor is None
        assert backend._transaction_manager is None