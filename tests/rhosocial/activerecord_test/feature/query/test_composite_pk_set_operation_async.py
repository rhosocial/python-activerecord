# tests/rhosocial/activerecord_test/feature/query/test_composite_pk_set_operation_async.py
"""
Bridge file for composite PK async set operation tests from the testsuite.
"""
import pytest
try:
    from rhosocial.activerecord.testsuite.feature.query.set_operations.test_composite_pk_set_operation_async import *  # noqa: F403
except ImportError:
    pytest.skip("composite_pk testsuite not available", allow_module_level=True)