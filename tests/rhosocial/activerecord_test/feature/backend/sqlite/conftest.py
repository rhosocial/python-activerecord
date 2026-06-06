# tests/rhosocial/activerecord_test/feature/backend/sqlite/conftest.py
"""
Pytest fixtures for SQLite backend tests.
"""

import os
import tempfile
from typing import Generator

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


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
