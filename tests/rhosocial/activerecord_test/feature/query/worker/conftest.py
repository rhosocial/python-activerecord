# tests/rhosocial/activerecord_test/feature/query/worker/conftest.py
"""
Pytest configuration for query worker feature tests.
"""
import os

os.environ.setdefault(
    'TESTSUITE_QUERY_WORKER_TASKS_MODULE',
    'providers.query_worker_tasks'
)

from rhosocial.activerecord.testsuite.feature.query.conftest import *
from rhosocial.activerecord.testsuite.feature.query.worker.conftest import (
    worker_pool,
    worker_tasks,
    query_worker_connection_params,
)
