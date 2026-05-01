# tests/rhosocial/activerecord_test/feature/backend/named_connection/conftest.py
"""
Test fixtures for named connection tests.

This module provides fixtures for testing named connection functionality.
"""
import types
from unittest.mock import MagicMock
import pytest


@pytest.fixture
def mock_backend_cls():
    """Create a mock backend class for testing."""
    return MagicMock(name="MockBackend")


@pytest.fixture
def connection_module():
    """Create a test module with named connections."""
    from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteInMemoryConfig

    module = types.ModuleType("test_connections")

    def memory_db(backend_cls):
        """In-memory SQLite database."""
        return SQLiteInMemoryConfig()

    def custom_db(backend_cls, pool_size: int = 5):
        """Custom SQLite database with pool settings."""
        from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
        return SQLiteConnectionConfig(database=":memory:", pool_size=pool_size)

    module.memory_db = memory_db
    module.custom_db = custom_db
    return module


class TestCliArgs:
    """Helper class to create mock CLI args for testing."""

    @staticmethod
    def create(named_connection: str = None, **kwargs):
        """Create a mock args namespace."""
        from argparse import Namespace

        defaults = {
            "named_connection": named_connection,
            "connection_params": [],
        }
        defaults.update(kwargs)
        return Namespace(**defaults)
