# tests/rhosocial/activerecord_test/feature/backend/sqlite/introspection/conftest.py
"""
Pytest fixtures for SQLite introspection tests.

This module provides fixtures for testing SQLite backend introspection
capabilities, including database setup, table creation, and cleanup.
"""

import os
import tempfile
from typing import Generator

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.testsuite.pytest_plugin import Declaration

from support.fixtures import (
    TABLE_DEFINITIONS,
    TRIGGER_DEFINITION,
    VIEW_DEFINITION,
    IndexesDefinition,
)

# Introspection reads one real database per scenario; keep the directory serial.
DECLARATION = Declaration(
    uses_database=True,
    parallel=True,
    purpose="SQLite introspection of tables, columns, indexes and pragmas",
    passes_means="the catalog answers match the schema the fixtures created",
    fails_means="introspection reports a shape the database does not have",
)

DDL = ExecutionOptions(stmt_type=StatementType.DDL)


@pytest.fixture(autouse=True)
def reset_version_cache():
    """Reset SQLite version cache before and after each test.

    This ensures test isolation by clearing the class-level cache
    that may be modified by other tests.
    """
    # Clear cache before test
    SQLiteBackend._sqlite_version_cache = None

    yield

    # Clear cache after test
    SQLiteBackend._sqlite_version_cache = None


@pytest.fixture
def sqlite_backend() -> Generator[SQLiteBackend, None, None]:
    """Create an in-memory SQLite backend for testing.

    Yields:
        SQLiteBackend: Connected SQLite backend instance with introspected dialect.
    """
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    backend.introspect_and_adapt()
    yield backend
    backend.disconnect()


@pytest.fixture
def sqlite_file_backend() -> Generator[SQLiteBackend, None, None]:
    """Create a file-based SQLite backend for testing.

    This fixture creates a temporary database file that is automatically
    cleaned up after the test.

    Yields:
        SQLiteBackend: Connected SQLite backend instance with introspected dialect.
    """
    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    backend = SQLiteBackend(database=db_path)
    backend.connect()
    backend.introspect_and_adapt()

    yield backend

    # Cleanup
    backend.disconnect()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def backend_with_tables(sqlite_backend: SQLiteBackend) -> SQLiteBackend:
    """Create a backend with test tables.

    Creates the following tables:
    - users: User table with primary key
    - posts: Post table with foreign key to users
    - tags: Tag table
    - post_tags: Many-to-many relationship table

    Args:
        sqlite_backend: The base SQLite backend.

    Returns:
        SQLiteBackend: Backend with test tables created.
    """
    dialect = sqlite_backend.dialect
    for definition in TABLE_DEFINITIONS:
        sqlite_backend.execute(*definition(dialect).create_table.to_sql(), options=DDL)
    for statement in IndexesDefinition(dialect).create_statements:
        sqlite_backend.execute(*statement.to_sql(), options=DDL)

    return sqlite_backend


@pytest.fixture
def backend_with_view(backend_with_tables: SQLiteBackend) -> SQLiteBackend:
    """Create a backend with a test view.

    Args:
        backend_with_tables: Backend with test tables.

    Returns:
        SQLiteBackend: Backend with test view created.
    """
    view = VIEW_DEFINITION(backend_with_tables.dialect)
    backend_with_tables.execute(*view.create_view.to_sql(), options=DDL)

    return backend_with_tables


@pytest.fixture
def backend_with_trigger(backend_with_tables: SQLiteBackend) -> SQLiteBackend:
    """Create a backend with a test trigger.

    Args:
        backend_with_tables: Backend with test tables.

    Returns:
        SQLiteBackend: Backend with test trigger created.
    """
    trigger = TRIGGER_DEFINITION(backend_with_tables.dialect)
    backend_with_tables.execute(*trigger.create_trigger.to_sql(), options=DDL)

    return backend_with_tables

