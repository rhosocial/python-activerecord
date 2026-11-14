# tests/rhosocial/activerecord_test/feature/backend/sqlite/conftest.py
"""
Pytest fixtures for SQLite backend tests.
"""

import os
import tempfile
from typing import Generator

import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

from support.fixtures import (
    TABLE_DEFINITIONS,
    TRIGGER_DEFINITION,
    VIEW_DEFINITION,
    IndexesDefinition,
)

DDL = ExecutionOptions(stmt_type=StatementType.DDL)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_functions(functions): Skip test if the backend dialect "
        "does not support the required functions. "
        "Usage: @pytest.mark.requires_functions(['json_extract_text'])",
    )
    config.addinivalue_line(
        "markers",
        "requires_protocol(protocol_and_method): Skip test if the backend "
        "dialect does not support the required protocol or method. "
        "Usage: @pytest.mark.requires_protocol((None, 'supports_fts5'))",
    )


def _get_backend_from_item(item):
    """Resolve the backend fixture value from a pytest Item."""
    backend = item.funcargs.get("backend")
    if backend is not None:
        return backend
    # Fallback: class-level fixture cache
    try:
        fixture_defs = item._fixtureinfo.name2fixturedefs.get("backend", [])
        if fixture_defs:
            return fixture_defs[0].cached_result[0]
    except (AttributeError, IndexError):
        pass
    return None


def _process_requires_functions(item, backend):
    """Process requires_functions marker and skip if unsupported."""
    marker = item.get_closest_marker("requires_functions")
    if marker is None:
        return True

    required_functions = marker.args[0] if marker.args else []
    if not required_functions:
        return True

    dialect = backend.dialect
    supported = dialect.supports_functions()
    unsupported = [fn for fn in required_functions if not supported.get(fn, False)]
    if unsupported:
        pytest.skip(
            f"Skipping test - backend dialect does not support "
            f"required functions: {', '.join(unsupported)}"
        )
    return True


def _process_requires_protocol(item, backend):
    """Process requires_protocol marker and skip if unsupported."""
    marker = item.get_closest_marker("requires_protocol")
    if marker is None:
        return True

    protocol_class, method_name = marker.args[0] if marker.args else (None, None)
    dialect = backend.dialect

    if protocol_class is not None and not isinstance(dialect, protocol_class):
        pytest.skip(
            f"Skipping test - backend dialect does not implement " f"{protocol_class.__name__}"
        )

    if method_name is not None:
        method = getattr(dialect, method_name, None)
        if method is None or (callable(method) and not method()):
            readable = method_name.replace("supports_", "").replace("_", " ").title()
            pytest.skip(f"Skipping test - backend dialect does not support {readable}")

    return True


def pytest_runtest_call(item):
    """Process requires_functions and requires_protocol markers."""
    if not item.get_closest_marker("requires_functions") and not item.get_closest_marker(
        "requires_protocol"
    ):
        return

    backend = _get_backend_from_item(item)
    if backend is None:
        return

    _process_requires_functions(item, backend)
    _process_requires_protocol(item, backend)


@pytest.fixture
def sqlite_file_backend() -> Generator[SQLiteBackend, None, None]:
    """Create a file-based SQLite backend for tests requiring real files."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    backend = SQLiteBackend(database=db_path)
    backend.connect()
    backend.introspect_and_adapt()

    yield backend

    backend.disconnect()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def temp_db_path():
    """Create temporary database file path"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        _retry_delete(path)
    # Clean up related WAL and SHM files
    for ext in ["-wal", "-shm"]:
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
    await backend.introspect_and_adapt()

    try:
        yield backend
    finally:
        # Disconnect and cleanup
        await backend.disconnect()


@pytest_asyncio.fixture
async def async_sqlite_memory_backend():
    """Provides an in-memory AsyncSQLiteBackend instance for testing."""
    backend = AsyncSQLiteBackend(database=":memory:")
    await backend.connect()
    await backend.introspect_and_adapt()

    try:
        yield backend
    finally:
        await backend.disconnect()


@pytest_asyncio.fixture
async def async_backend_with_tables(async_sqlite_backend):
    """Create a backend with test tables.

    Creates the following tables:
    - users: User table with primary key
    - posts: Post table with foreign key to users
    - tags: Tag table
    - post_tags: Many-to-many relationship table
    """
    dialect = async_sqlite_backend.dialect
    for definition in TABLE_DEFINITIONS:
        await async_sqlite_backend.execute(*definition(dialect).create_table.to_sql(), options=DDL)
    for statement in IndexesDefinition(dialect).create_statements:
        await async_sqlite_backend.execute(*statement.to_sql(), options=DDL)

    return async_sqlite_backend


@pytest_asyncio.fixture
async def async_backend_with_view(async_backend_with_tables):
    """Create a backend with a test view."""
    view = VIEW_DEFINITION(async_backend_with_tables.dialect)
    await async_backend_with_tables.execute(*view.create_view.to_sql(), options=DDL)
    return async_backend_with_tables


@pytest_asyncio.fixture
async def async_backend_with_trigger(async_backend_with_tables):
    """Create a backend with a test trigger."""
    trigger = TRIGGER_DEFINITION(async_backend_with_tables.dialect)
    await async_backend_with_tables.execute(*trigger.create_trigger.to_sql(), options=DDL)
    return async_backend_with_tables


@pytest.fixture
def sqlite_backend():
    """In-memory SQLite backend for shared tests."""
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    backend.introspect_and_adapt()
    yield backend
    backend.disconnect()
