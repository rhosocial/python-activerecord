# tests/rhosocial/activerecord_test/feature/basic/connection/conftest.py
"""
Pytest fixtures for basic connection pool context awareness tests.

This module imports fixtures from the testsuite package for SQLite backend.
"""
from rhosocial.activerecord.testsuite.feature.basic.connection.conftest import (
    sync_pool_and_model,
    async_pool_and_model,
    sync_pool_for_crud,
    async_pool_for_crud,
)
