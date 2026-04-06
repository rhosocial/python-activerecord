# tests/rhosocial/activerecord_test/feature/basic/connection/test_active_record_context.py
"""
ActiveRecord Context Test Module for SQLite backend.

This module imports and runs the shared tests from the testsuite package,
ensuring SQLite backend compatibility for ActiveRecord connection pool context awareness.
"""
from rhosocial.activerecord.testsuite.feature.basic.connection.conftest import (
    sync_pool_and_model,
    async_pool_and_model,
)

# Import shared tests from testsuite package
from rhosocial.activerecord.testsuite.feature.basic.connection.test_active_record_context import *
