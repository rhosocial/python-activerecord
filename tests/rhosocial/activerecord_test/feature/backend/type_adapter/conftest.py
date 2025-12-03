# tests/rhosocial/activerecord_test/feature/backend/type_adapter/conftest.py
import os
import pytest
import logging
from typing import Generator
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.interface import IActiveRecord


@pytest.fixture(params=["memory"])
def db_path(request) -> str:
    """Returns the test database path. For these tests, we only need in-memory."""
    if request.param == "memory":
        # Use a shared in-memory database to ensure the connection is consistent
        # across different parts of the test setup if needed.
        return "file:type_adapter_test?mode=memory&cache=shared"
    return None


@pytest.fixture
def db(db_path) -> Generator[SQLiteBackend, None, None]:
    """Provides a synchronous database backend connection."""
    # Set logging level for the ActiveRecord logger to DEBUG
    logger = logging.getLogger('activerecord')
    logger.setLevel(logging.DEBUG)
    # Ensure it has a handler if running outside of a configured environment
    if not logger.handlers:
        logger.addHandler(logging.StreamHandler())

    backend = SQLiteBackend(database=db_path)
    backend.connect()
    yield backend
    backend.disconnect()

