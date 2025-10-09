# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_version.py
import os
import sqlite3
import tempfile
from unittest import mock

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.config import ConnectionConfig


class TestSQLiteVersion:
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)
        # Cleanup related WAL and SHM files
        for ext in ['-wal', '-shm']:
            wal_path = path + ext
            if os.path.exists(wal_path):
                os.unlink(wal_path)

    def test_get_version_parsing(self, temp_db_path):
        """Test that the method correctly parses the SQLite version string"""
        # Reset class-level cache to ensure clean test
        if hasattr(SQLiteBackend, '_sqlite_version_cache'):
            delattr(SQLiteBackend, '_sqlite_version_cache')

        # Create a backend
        config = ConnectionConfig(database=temp_db_path)
        backend = SQLiteBackend(connection_config=config)

        # Get the version
        version = backend.get_server_version()

        # Check that the version is a tuple with three elements
        assert isinstance(version, tuple)
        assert len(version) == 3

        # Check that all elements are integers
        for component in version:
            assert isinstance(component, int)

        # Should match the actual sqlite3 version
        sqlite_version = tuple(map(int, sqlite3.sqlite_version.split('.')))
        assert version == sqlite_version

        backend.disconnect()

    def test_version_caching(self, temp_db_path):
        """Test that the version is cached at class level between instances"""
        # Reset class-level cache to ensure clean test
        if hasattr(SQLiteBackend, '_sqlite_version_cache'):
            delattr(SQLiteBackend, '_sqlite_version_cache')

        # Create first backend and get version
        config1 = ConnectionConfig(database=temp_db_path)
        backend1 = SQLiteBackend(connection_config=config1)
        version1 = backend1.get_server_version()

        # Create second backend and get version without connecting
        config2 = ConnectionConfig(database=temp_db_path)
        backend2 = SQLiteBackend(connection_config=config2)

        # Mock the connect method to verify it's not called
        with mock.patch.object(backend2, 'connect') as mock_connect:
            version2 = backend2.get_server_version()
            mock_connect.assert_not_called()

        # Versions should be identical
        assert version1 == version2

        # Both should be the cached version
        assert hasattr(SQLiteBackend, '_sqlite_version_cache')
        assert SQLiteBackend._sqlite_version_cache == version1

        backend1.disconnect()

    def test_version_error_handling(self, temp_db_path):
        """Test error handling by simulating a connection error"""
        # Reset class-level cache to ensure clean test
        if hasattr(SQLiteBackend, '_sqlite_version_cache'):
            delattr(SQLiteBackend, '_sqlite_version_cache')

        # Create backend
        config = ConnectionConfig(database=temp_db_path)
        backend = SQLiteBackend(connection_config=config)

        # Mock the connection cursor to raise an exception when execute is called
        with mock.patch.object(backend, '_connection') as mock_conn:
            mock_cursor = mock.MagicMock()
            mock_cursor.execute.side_effect = sqlite3.Error("Test error")
            mock_conn.cursor.return_value = mock_cursor

            # Should default to version (3, 35, 0) on error
            version = backend.get_server_version()
            assert version == (3, 35, 0)

        backend.disconnect()

    def test_version_parsing_variants(self, temp_db_path):
        """Test parsing of different version string formats"""
        # Reset class-level cache to ensure clean test
        if hasattr(SQLiteBackend, '_sqlite_version_cache'):
            delattr(SQLiteBackend, '_sqlite_version_cache')

        # Create backend
        config = ConnectionConfig(database=temp_db_path)
        backend = SQLiteBackend(connection_config=config)

        # Test various version formats
        test_cases = [
            # version_str, expected_tuple
            ("3.39.4", (3, 39, 4)),
            ("3.39", (3, 39, 0)),
            ("3", (3, 0, 0)),
            ("4.0.0", (4, 0, 0))
        ]

        for version_str, expected_tuple in test_cases:
            # Mock fetch_one to return a specific version
            with mock.patch.object(backend, '_connection') as mock_conn:
                mock_cursor = mock.MagicMock()
                mock_cursor.fetchone.return_value = [version_str]
                mock_conn.cursor.return_value = mock_cursor

                # Reset class-level cache for each test case
                if hasattr(SQLiteBackend, '_sqlite_version_cache'):
                    delattr(SQLiteBackend, '_sqlite_version_cache')

                # Get the parsed version
                version = backend.get_server_version()

                # Check that it matches expected tuple
                assert version == expected_tuple

        backend.disconnect()

    def test_version_comparison(self, temp_db_path):
        """Test that version can be compared correctly for feature detection"""
        # Reset class-level cache to ensure clean test
        if hasattr(SQLiteBackend, '_sqlite_version_cache'):
            delattr(SQLiteBackend, '_sqlite_version_cache')

        # Create backend
        config = ConnectionConfig(database=temp_db_path)
        backend = SQLiteBackend(connection_config=config)

        # Mock to return a specific version (3.35.0)
        with mock.patch.object(backend, '_connection') as mock_conn:
            mock_cursor = mock.MagicMock()
            mock_cursor.fetchone.return_value = ["3.35.0"]
            mock_conn.cursor.return_value = mock_cursor

            # Get version
            version = backend.get_server_version()

            # Should be exactly 3.35.0
            assert version == (3, 35, 0)

            # Test comparison for feature detection
            assert version >= (3, 0, 0)
            assert version >= (3, 35, 0)
            assert version < (3, 36, 0)
            assert version < (4, 0, 0)

            # RETURNING clause support requires SQLite 3.35.0 or later
            assert version >= (3, 35, 0)

        backend.disconnect()