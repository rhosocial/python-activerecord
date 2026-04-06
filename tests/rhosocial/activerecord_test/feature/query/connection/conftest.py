# tests/rhosocial/activerecord_test/feature/query/connection/conftest.py
"""
Pytest fixtures for query connection pool context awareness tests.

This module imports fixtures from the testsuite package for SQLite backend.
"""
from rhosocial.activerecord.testsuite.feature.query.connection.conftest import (
    sync_pool_and_model,
    async_pool_and_model,
)
