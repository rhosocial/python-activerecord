# tests/rhosocial/activerecord_test/feature/basic/test_composite_pk_crud_async.py
"""
Bridge file for composite PK async CRUD tests from the testsuite.
"""
import pytest
try:
    from rhosocial.activerecord.testsuite.feature.basic.crud.test_composite_pk_crud_async import *  # noqa: F403
except ImportError:
    pytest.skip("composite_pk testsuite not available", allow_module_level=True)