# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/conftest.py
"""
Pytest configuration for async SQLite backend tests

This configuration file sets up the async testing environment and provides
common fixtures for all async tests.
"""

import pytest


def pytest_configure(config):
    """Configure pytest for async tests"""
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async (requires pytest-asyncio)"
    )



# Ensure pytest-asyncio is configured correctly
# pytest_plugins = ('pytest_asyncio',)