# tests/rhosocial/activerecord_test/feature/backend/backend/test_backend_lifecycle_async.py
"""Async twin of test_backend_lifecycle.py: AsyncSQLiteBackend lifecycle error handling."""

import os
import sqlite3
import tempfile
from unittest.mock import patch

import pytest

from rhosocial.activerecord.backend.errors import ConnectionError
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


class TestAsyncSQLiteBackendLifecycle:
    """Async lifecycle coverage twin of TestSQLiteBackendCoveragePart1"""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file path"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        yield path
        # Cleanup
        for ext in ["", "-wal", "-shm"]:
            wal_path = path + ext
            if os.path.exists(wal_path):
                try:
                    os.unlink(wal_path)
                except OSError:
                    print(f"Warning: Failed to delete file {wal_path}")

    @pytest.mark.asyncio
    async def test_set_pragma_exception_handling(self, temp_db_path):
        """Test set_pragma rejects an unknown pragma name."""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        # Unknown pragma name is rejected by the whitelist validation
        with pytest.raises(ValueError) as exc_info:
            await backend.set_pragma("invalid_pragma", "value")

        assert "Unknown PRAGMA" in str(exc_info.value)

        # Unsafe value is also rejected by the whitelist validation
        with pytest.raises(ValueError):
            await backend.set_pragma("journal_mode", "'; DROP TABLE users; --")

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_apply_pragmas_exception_handling(self, temp_db_path):
        """Test _apply_pragmas fail-fast on invalid pragma configuration."""
        config = SQLiteConnectionConfig(database=temp_db_path, pragmas={"invalid_syntax_pragma": "INVALID SQL SYNTAX"})
        backend = AsyncSQLiteBackend(connection_config=config)

        # Connecting must fail fast: an invalid pragma must never be silently
        # skipped, otherwise a safety-relevant setting would be left at its
        # default without notice.
        with pytest.raises(ConnectionError, match="Invalid pragma configuration"):
            await backend.connect()
        assert not backend.is_connected()

    @pytest.mark.asyncio
    async def test_disconnect_exception_during_close(self, temp_db_path):
        """Test disconnect() with exception during connection close"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        original_connection = backend._connection
        backend._connection = None

        # Should not raise ConnectionError
        await backend.disconnect()

        backend._connection = original_connection
        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_delete_files_exception(self, temp_db_path):
        """Test disconnect() with exception during file deletion"""
        config = SQLiteConnectionConfig(database=temp_db_path, delete_on_close=True)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        with patch("aiofiles.os.path.exists", return_value=True), patch(
            "aiofiles.os.remove", side_effect=Exception("Unexpected error")
        ):
            with pytest.raises(ConnectionError) as exc_info:
                await backend.disconnect()

            assert "Failed to delete database files" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ping_with_reconnect_failure(self, temp_db_path):
        """Test ping() method with reconnect by using invalid database"""
        config = SQLiteConnectionConfig(database="/invalid/path/to/database.db")
        backend = AsyncSQLiteBackend(connection_config=config)

        result = await backend.ping(reconnect=True)

        assert result is False

    @pytest.mark.asyncio
    async def test_ping_with_connection_error(self, temp_db_path):
        """Test ping() with connection error"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        await backend._connection.close()

        # Test without reconnect
        result = await backend.ping(reconnect=False)
        assert result is False

        # Test with reconnect
        result = await backend.ping(reconnect=True)
        assert result is True
        assert backend._connection is not None

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_pragmas_property(self, temp_db_path):
        """Test AsyncSQLiteBackend.pragmas() property"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)

        pragmas = backend.pragmas
        assert isinstance(pragmas, dict)
        assert "foreign_keys" in pragmas
        assert pragmas["foreign_keys"] == "ON"

        # Test that we get a copy, not the original
        pragmas["test_key"] = "test_value"
        assert "test_key" not in backend.pragmas

    @pytest.mark.asyncio
    async def test_get_pragma_settings_pragmas(self, temp_db_path):
        """Test pragma settings are properly retrieved from SQLiteConnectionConfig"""
        config1 = SQLiteConnectionConfig(database=temp_db_path, pragmas={"test_pragma": "test_value"})
        backend1 = AsyncSQLiteBackend(connection_config=config1)
        pragmas1 = backend1.pragmas
        assert pragmas1["test_pragma"] == "test_value", "Pragma from SQLiteConnectionConfig.pragmas should be available"

        config2 = SQLiteConnectionConfig(database=temp_db_path)
        backend2 = AsyncSQLiteBackend(connection_config=config2)
        pragmas2 = backend2.pragmas
        assert "foreign_keys" in pragmas2, "Default pragmas should be included"
        assert pragmas2["foreign_keys"] == "ON", "Default pragmas should have expected values"

        await backend2.connect()
        result = await backend2.fetch_one("PRAGMA foreign_keys")
        assert result["foreign_keys"] == 1, "Pragma should be applied to the database connection"
        await backend2.disconnect()

    @pytest.mark.asyncio
    async def test_connect_exception_handling(self, temp_db_path):
        """Test connect() exception handling"""
        config = SQLiteConnectionConfig(database="/invalid/path/database.db")
        backend = AsyncSQLiteBackend(connection_config=config)

        with pytest.raises(ConnectionError) as exc_info:
            await backend.connect()

        assert "Failed to connect" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ping_with_execute_error(self, temp_db_path):
        """Test ping() with execute error by corrupting the connection"""
        config = SQLiteConnectionConfig(database=temp_db_path)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

        class ConnectionWrapper:
            def __init__(self, conn):
                self._conn = conn

            def execute(self, sql):
                raise sqlite3.Error("Simulated execute error")

            def __getattr__(self, name):
                return getattr(self._conn, name)

        original_conn = backend._connection
        backend._connection = ConnectionWrapper(original_conn)

        # Test without reconnect
        result = await backend.ping(reconnect=False)
        assert result is False

        # Test with reconnect
        backend._connection = original_conn  # Restore for reconnect
        result = await backend.ping(reconnect=True)
        assert result is True

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_without_connection(self):
        """Test disconnect when connection is None"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)

        # Should not raise exception
        await backend.disconnect()
        assert backend._connection is None

    @pytest.mark.asyncio
    async def test_disconnect_delete_on_close_errors(self, temp_db_path):
        """Test disconnect() with delete_on_close errors"""
        config = SQLiteConnectionConfig(database=temp_db_path, delete_on_close=True)
        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()

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

        with patch("os.remove", mock_remove):
            # Should attempt retries and log warning but not raise
            await backend.disconnect()

            # Connection should still be cleared
            assert backend._connection is None

    @pytest.mark.asyncio
    async def test_disconnect_idempotent(self):
        """Test that disconnect() is idempotent and can be called multiple times safely"""
        config = SQLiteConnectionConfig(database=":memory:")
        backend = AsyncSQLiteBackend(connection_config=config)

        # Should not raise when called without a connection
        await backend.disconnect()

        # Connect and then disconnect
        await backend.connect()
        await backend.disconnect()

        # Should not raise when called again
        await backend.disconnect()
        await backend.disconnect()

        # Verify the state is clean
        assert backend._connection is None
        assert backend._cursor is None
        assert backend._transaction_manager is None
