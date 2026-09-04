# tests/rhosocial/activerecord_test/feature/backend/introspection/conftest.py
"""
SQLite version-cache isolation for introspection tests.

The introspectors cache the SQLite version at class level; an autouse reset
keeps each test isolated from cache mutations performed by other tests.
Both sync and async backend classes carry their own cache and are reset.
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend


@pytest.fixture(autouse=True)
def reset_version_cache():
    """Reset SQLite version cache before and after each test."""
    # Clear cache before test
    SQLiteBackend._sqlite_version_cache = None
    AsyncSQLiteBackend._sqlite_version_cache = None

    yield

    # Clear cache after test
    SQLiteBackend._sqlite_version_cache = None
    AsyncSQLiteBackend._sqlite_version_cache = None
