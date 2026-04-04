# tests/rhosocial/activerecord_test/feature/basic/test_worker_crud.py
"""
WorkerPool CRUD tests for basic feature.

This file imports and runs the tests defined in the testsuite.
"""
# Import fixtures from testsuite
from rhosocial.activerecord.testsuite.feature.worker.conftest import (
    worker_pool,
    worker_connection_params,
)

# Import tests from testsuite
from rhosocial.activerecord.testsuite.feature.worker.test_concurrent_crud import *
