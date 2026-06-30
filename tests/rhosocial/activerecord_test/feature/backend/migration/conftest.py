# tests/rhosocial/activerecord_test/feature/backend/migration/conftest.py
"""
Test fixtures for migration tests.
"""

from unittest.mock import MagicMock

import pytest

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend


@pytest.fixture
def mock_dialect():
    """Create a mock dialect for testing."""
    dialect = MagicMock()
    dialect._prepare_value = MagicMock(side_effect=lambda v: v)
    dialect._format_value = MagicMock(
        side_effect=lambda v: f"'{v}'" if isinstance(v, str) else str(v)
    )
    return dialect


@pytest.fixture
def sqlite_backend():
    """Create a real in-memory SQLite backend for integration testing."""
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    yield backend
    backend.disconnect()
