# tests/rhosocial/activerecord_test/feature/basic/test_derived_field_async.py
"""
Bridge file for async derived field tests from the testsuite.
"""
import pytest
try:
    from rhosocial.activerecord.testsuite.feature.basic.fields.test_derived_field_async import *  # noqa: F403
except ImportError:
    pytest.skip("derived_field testsuite not available", allow_module_level=True)