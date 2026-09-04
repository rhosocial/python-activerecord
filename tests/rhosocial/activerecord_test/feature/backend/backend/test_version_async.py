# tests/rhosocial/activerecord_test/feature/backend/backend/test_version_async.py
"""Async twin of test_version.py: version detection/caching on AsyncSQLiteBackend."""

import os
import sqlite3
import tempfile
from unittest import mock

import pytest

from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.config import ConnectionConfig
from rhosocial.activerecord.backend.errors import OperationalError


class TestAsyncSQLiteVersion:
    """Async twin of TestSQLiteVersion"""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)
        # Cleanup related WAL and SHM files
        for ext in ["-wal", "-shm"]:
            wal_path = path + ext
            if os.path.exists(wal_path):
                os.unlink(wal_path)

    @pytest.mark.asyncio
    async def test_get_version_parsing(self, temp_db_path):
        """Test that the method correctly parses the SQLite version string"""
        AsyncSQLiteBackend._sqlite_version_cache = None

        config = ConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)

        version = backend.get_server_version()

        assert isinstance(version, tuple)
        assert len(version) == 3

        for component in version:
            assert isinstance(component, int)

        sqlite_version = tuple(map(int, sqlite3.sqlite_version.split(".")))
        assert version == sqlite_version

    @pytest.mark.asyncio
    async def test_version_caching(self, temp_db_path):
        """Test that the version is cached at class level between instances"""
        AsyncSQLiteBackend._sqlite_version_cache = None

        config1 = ConnectionConfig(database=temp_db_path)
        backend1 = AsyncSQLiteBackend(connection_config=config1)
        version1 = backend1.get_server_version()

        config2 = ConnectionConfig(database=temp_db_path)
        backend2 = AsyncSQLiteBackend(connection_config=config2)

        # Mock the connect method to verify it's not called
        with mock.patch.object(backend2, "connect") as mock_connect:
            version2 = backend2.get_server_version()
            mock_connect.assert_not_called()

        assert version1 == version2

        assert AsyncSQLiteBackend._sqlite_version_cache is not None
        assert AsyncSQLiteBackend._sqlite_version_cache == version1

    @pytest.mark.asyncio
    async def test_version_from_module_constant(self, temp_db_path):
        """Test that version is obtained from module constant without connection"""
        AsyncSQLiteBackend._sqlite_version_cache = None

        config = ConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)

        version = backend.get_server_version()

        expected = sqlite3.sqlite_version_info[:3]
        assert version == expected

        assert backend._connection is None

    @pytest.mark.asyncio
    async def test_version_error_handling(self, temp_db_path):
        """Test error handling by simulating errors in both module constant and fallback"""
        AsyncSQLiteBackend._sqlite_version_cache = None

        config = ConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)

        with mock.patch.object(sqlite3, "sqlite_version_info", None):
            mock_conn = mock.MagicMock()
            mock_cursor = mock.MagicMock()
            mock_cursor.execute.side_effect = sqlite3.Error("Test error")
            mock_conn.cursor.return_value = mock_cursor

            backend._connection = mock_conn

            with pytest.raises(OperationalError, match="Failed to determine SQLite version"):
                backend.get_server_version()

        backend._connection = None

    @pytest.mark.asyncio
    async def test_version_parsing_variants(self, temp_db_path):
        """Test parsing of different version string formats via fallback path"""
        AsyncSQLiteBackend._sqlite_version_cache = None

        config = ConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)

        test_cases = [
            ("3.39.4", (3, 39, 4)),
            ("3.39", (3, 39, 0)),
            ("3", (3, 0, 0)),
            ("4.0.0", (4, 0, 0)),
        ]

        for version_str, expected_tuple in test_cases:
            with mock.patch.object(sqlite3, "sqlite_version_info", None):
                mock_conn = mock.MagicMock()
                mock_cursor = mock.MagicMock()
                mock_cursor.fetchone.return_value = [version_str]
                mock_conn.cursor.return_value = mock_cursor

                backend._connection = mock_conn

                AsyncSQLiteBackend._sqlite_version_cache = None

                version = backend.get_server_version()

                assert version == expected_tuple

        backend._connection = None

    @pytest.mark.asyncio
    async def test_version_comparison(self, temp_db_path):
        """Test that version can be compared correctly for feature detection"""
        AsyncSQLiteBackend._sqlite_version_cache = None

        config = ConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)

        with mock.patch.object(sqlite3, "sqlite_version_info", (3, 35, 0)):
            version = backend.get_server_version()

            assert version == (3, 35, 0)

            assert version >= (3, 0, 0)
            assert version >= (3, 35, 0)
            assert version < (3, 36, 0)
            assert version < (4, 0, 0)

            # RETURNING clause support requires SQLite 3.35.0 or later
            assert version >= (3, 35, 0)
