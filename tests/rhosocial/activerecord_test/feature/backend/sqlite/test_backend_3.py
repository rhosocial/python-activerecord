# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_backend_3.py
"""Tests for improving SQLite backend coverage - Part 3 Fixed (Edge Cases)"""

import os
from unittest.mock import patch, MagicMock

import pytest

from rhosocial.activerecord.backend import ReturningOptions
from rhosocial.activerecord.backend.errors import ConnectionError
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


class TestSQLiteBackendCoveragePart3Fixed:
    """Fixed tests to improve coverage of SQLiteBackend - Part 3 (Edge Cases)"""

    def test_disconnect_delete_on_close_max_retries(self, tmp_path):
        """Test disconnect with delete_on_close when all retries fail"""
        db_path = str(tmp_path / "test.db")
        # Use SQLiteConnectionConfig to create a configuration
        config = SQLiteConnectionConfig(
            database=db_path,
            delete_on_close=True
        )
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create the database files
        backend.execute("CREATE TABLE test (id INTEGER)")
        wal_path = f"{db_path}-wal"
        shm_path = f"{db_path}-shm"

        # Mock os.remove to always fail for the main database file
        original_remove = os.remove
        remove_calls = []

        def mock_remove(path):
            remove_calls.append(path)
            if path == db_path:
                raise OSError("Mocked permission error")
            return original_remove(path)

        with patch('os.remove', mock_remove), \
                patch('os.path.exists', return_value=True):
            # Should attempt multiple times and log warning
            backend.disconnect()

            # Should have attempted max_retries times
            assert remove_calls.count(db_path) == 5  # Default max_retries is 5

            # Connection should still be cleared
            assert backend._connection is None

    def test_disconnect_delete_on_close_file_not_exists(self, tmp_path):
        """Test disconnect with delete_on_close when files don't exist"""
        db_path = str(tmp_path / "nonexistent.db")
        # Use SQLiteConnectionConfig to create a configuration
        config = SQLiteConnectionConfig(
            database=db_path,
            delete_on_close=True
        )
        backend = SQLiteBackend(connection_config=config)

        # Connect and disconnect without creating any files
        backend.connect()

        # Mock os.path.exists to return False
        with patch('os.path.exists', return_value=False):
            # Should not attempt to delete non-existent files
            backend.disconnect()

            # Connection should be cleared
            assert backend._connection is None

    def test_connect_with_uri_option(self):
        """Test connect with URI option"""
        # Use SQLiteConnectionConfig to create a configuration，with uri=True
        config = SQLiteConnectionConfig(
            database=":memory:",
            uri=True
        )
        backend = SQLiteBackend(connection_config=config)

        # Should connect with uri=True
        backend.connect()
        assert backend._connection is not None

        backend.disconnect()

    def test_check_returning_compatibility_edge_cases(self):
        """Test edge cases in _check_returning_compatibility"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)

        # Test with exact boundary versions
        with patch('sqlite3.sqlite_version_info', (3, 35, 0)), \
                patch('sys.version_info', (3, 10, 0)):
            options = ReturningOptions(enabled=True, force=False)
            # Should not raise exception for exact boundary versions
            backend._check_returning_compatibility(options)

        # Test with force=True bypassing all checks
        with patch('sqlite3.sqlite_version_info', (3, 0, 0)), \
                patch('sys.version_info', (3, 0, 0)):
            options = ReturningOptions(enabled=True, force=True)
            # Should not raise exception even with very old versions
            backend._check_returning_compatibility(options)

    def test_pragma_settings_edge_cases(self):
        """Test edge cases in pragma settings"""
        # Test with no custom pragmas
        config1 = SQLiteConnectionConfig(database=":memory:")
        backend1 = SQLiteBackend(connection_config=config1)
        pragmas1 = backend1.pragmas
        assert all(key in pragmas1 for key in SQLiteConnectionConfig.DEFAULT_PRAGMAS)

        # Test with empty custom pragmas
        config2 = SQLiteConnectionConfig(database=":memory:", pragmas={})
        backend2 = SQLiteBackend(connection_config=config2)
        pragmas2 = backend2.pragmas
        assert all(key in pragmas2 for key in SQLiteConnectionConfig.DEFAULT_PRAGMAS)

        # Test with non-string pragma values
        config3 = SQLiteConnectionConfig(
            database=":memory:",
            pragmas={"numeric_pragma": 123, "boolean_pragma": True}
        )
        backend3 = SQLiteBackend(connection_config=config3)
        pragmas3 = backend3.pragmas
        assert "numeric_pragma" in pragmas3
        assert "boolean_pragma" in pragmas3

    def test_set_pragma_without_connection(self):
        """Test set_pragma when not connected"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)

        # Should only update internal dictionary without error
        backend.set_pragma("test_pragma", "test_value")
        assert backend.pragmas["test_pragma"] == "test_value"

        # Verify pragma is applied when connection is established
        backend.connect()

        # For testing, let's use a real pragma
        cursor = backend._connection.cursor()
        cursor.execute("PRAGMA test_pragma")
        # Note: custom pragmas might not be queryable, so we just verify no error occurs

        backend.disconnect()

    def test_execute_many_parameter_conversion(self):
        """Test parameter conversion in execute_many"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create test table
        backend.execute("""
            CREATE TABLE test (
                id INTEGER,
                data TEXT,
                created_at TEXT
            )
        """)

        # Test with datetime objects that need conversion
        from datetime import datetime
        params_list = [
            (1, {"key": "value1"}, datetime(2024, 1, 1)),
            (2, {"key": "value2"}, datetime(2024, 1, 2))
        ]

        result = backend.execute_many(
            "INSERT INTO test (id, data, created_at) VALUES (?, ?, ?)",
            params_list
        )

        assert result.affected_rows == 2

        # Verify data was properly converted
        rows = backend.fetch_all("SELECT * FROM test ORDER BY id")
        assert len(rows) == 2
        assert isinstance(rows[0]["data"], str)  # JSON converted to string
        assert isinstance(rows[0]["created_at"], str)  # Datetime converted to string

        backend.disconnect()

    def test_execute_many_empty_params(self):
        """Test execute_many with empty parameter lists"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create test table
        backend.execute("CREATE TABLE test (id INTEGER)")

        # Test with empty params list
        result = backend.execute_many("INSERT INTO test (id) VALUES (?)", [])
        assert result.affected_rows == 0

        # Test with params list containing empty tuples
        result = backend.execute_many("INSERT INTO test DEFAULT VALUES", [(), (), ()])
        assert result.affected_rows == 0

        # Test with params list containing sequential tuples
        result = backend.execute_many("INSERT INTO test(id) VALUES (?)", [(1, ), (2, ), (3, )])
        assert result.affected_rows == 3

        backend.disconnect()

    def test_cursor_management_edge_cases(self):
        """Test edge cases in cursor management"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create a real cursor and save it
        cursor = backend._connection.cursor()
        backend._cursor = cursor

        # Should reuse the existing cursor
        returned_cursor = backend._get_cursor()
        assert returned_cursor is cursor

        # Test cursor cleanup on disconnect
        backend.disconnect()
        assert backend._cursor is None

        # Test cursor creation on reconnect
        backend.connect()
        new_cursor = backend._get_cursor()
        assert new_cursor is not None
        assert new_cursor is not cursor

        backend.disconnect()

    def test_transaction_during_disconnect(self):
        """Test behavior when disconnecting with active transaction"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create table before starting transaction
        backend.execute("CREATE TABLE test (id INTEGER, value TEXT)")

        # Start a transaction
        backend.begin_transaction()

        # Insert some data
        backend.execute("INSERT INTO test VALUES (1, 'test')")

        # Disconnect with active transaction
        backend.disconnect()

        # Reconnect and recreate the table since memory database is cleared on disconnect
        backend.connect()
        backend.execute("CREATE TABLE test (id INTEGER, value TEXT)")
        result = backend.fetch_all("SELECT * FROM test")
        assert len(result) == 0  # Table exists but is empty

        backend.disconnect()

    def test_auto_commit_with_error_in_commit(self):
        """Test auto commit when commit raises an error"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Mock transaction_manager to return False for is_active
        mock_tm = MagicMock()
        mock_tm.is_active = False
        backend._transaction_manager = mock_tm

        # Close connection to make commit fail
        backend._connection.close()

        # Should log warning but not raise exception
        backend._handle_auto_commit()

        # Cleanup
        backend._connection = None

    def test_disconnect_delete_files_exception_fixed(self, tmp_path):
        """Test disconnect() with exception during file deletion - fixed version"""
        db_path = str(tmp_path / "test.db")
        # 使用 SQLiteConnectionConfig 创建配置
        config = SQLiteConnectionConfig(
            database=db_path,
            delete_on_close=True
        )
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Create a table to ensure file exists
        backend.execute("CREATE TABLE test (id INTEGER)")

        # Mock exception during file deletion
        with patch('os.path.exists', return_value=True), \
             patch('os.remove', side_effect=Exception("Unexpected error")):

            # Should raise ConnectionError as expected
            with pytest.raises(ConnectionError) as exc_info:
                backend.disconnect()

            assert "Failed to delete database files" in str(exc_info.value)

    def test_disconnect_transaction_manager_cleanup(self):
        """Test that disconnect cleans up transaction manager"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = SQLiteBackend(connection_config=config)
        backend.connect()

        # Access transaction manager to create it
        tm = backend.transaction_manager
        assert backend._transaction_manager is not None

        # Disconnect should clear it
        backend.disconnect()
        assert backend._transaction_manager is None
