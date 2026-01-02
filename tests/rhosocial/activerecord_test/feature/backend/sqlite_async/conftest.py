# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/conftest.py
"""
Pytest configuration for async SQLite backend tests

This configuration file sets up the async testing environment and provides
common fixtures for all async tests.
"""
import os
import tempfile
import pytest
import pytest_asyncio
from rhosocial.activerecord_test.feature.backend.sqlite_async.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


def pytest_configure(config):
    """Configure pytest for async tests"""
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async (requires pytest-asyncio)"
    )


@pytest.fixture
def temp_db_path():
    """Create temporary database file path"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        _retry_delete(path)
    # Clean up related WAL and SHM files
    for ext in ['-wal', '-shm']:
        wal_path = path + ext
        if os.path.exists(wal_path):
            _retry_delete(wal_path)


def _retry_delete(file_path, max_retries=5, retry_delay=0.1):
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


@pytest_asyncio.fixture
async def async_sqlite_backend(temp_db_path):
    """Provides an AsyncSQLiteBackend instance for testing."""
    config = SQLiteConnectionConfig(database=temp_db_path)
    backend = AsyncSQLiteBackend(connection_config=config)

    # Connect to the database
    await backend.connect()

    try:
        yield backend
    finally:
        # Disconnect and cleanup
        await backend.disconnect()