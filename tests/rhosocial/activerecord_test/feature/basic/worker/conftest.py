# tests/rhosocial/activerecord_test/feature/basic/worker/conftest.py
"""
Pytest configuration for basic worker tests.

This file imports fixtures from the corresponding testsuite, making them
available to the tests in this directory.
"""
from rhosocial.activerecord.testsuite.feature.basic.worker.conftest import (
    worker_connection_params,
    user_class_for_worker,
    async_user_class_for_worker,
)
