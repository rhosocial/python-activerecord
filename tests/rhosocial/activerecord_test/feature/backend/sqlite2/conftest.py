# tests/rhosocial/activerecord_test/feature/backend/sqlite2/conftest.py
import os

import pytest
from typing import Generator
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


@pytest.fixture(params=["memory", "file"])
def db_path(request) -> str:
    """Returns the test database path"""
    if request.param == "memory":
        return ":memory:"  # Use an in-memory database for easy testing
    elif request.param == "file":
        return "tests.activerecord_test.implementations.sqlite.sqlite"
    return None


@pytest.fixture
def db(db_path) -> Generator[SQLiteBackend, None, None]:
    """Provides database connectivity"""
    backend = SQLiteBackend(database=db_path)
    backend.connect()
    yield backend
    backend.disconnect()

    # Clean up the files after the test is over
    if db_path != ":memory:" and os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def setup_test_table(db):
    """Create a test table"""
    db.execute("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            created_at DATETIME
        )
    """)
    yield
    db.execute("DROP TABLE IF EXISTS test_table")
