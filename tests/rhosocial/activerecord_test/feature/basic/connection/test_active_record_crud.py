# tests/rhosocial/activerecord_test/feature/basic/connection/test_active_record_crud.py
"""
ActiveRecord CRUD Test Module for SQLite backend.

This module imports and runs the shared tests from the testsuite package,
ensuring SQLite backend compatibility for CRUD operations with connection pool.
"""
from rhosocial.activerecord.testsuite.feature.basic.connection.conftest import (
    sync_pool_for_crud,
    async_pool_for_crud,
)

# Import shared tests from testsuite package
from rhosocial.activerecord.testsuite.feature.basic.connection.test_active_record_crud import *
