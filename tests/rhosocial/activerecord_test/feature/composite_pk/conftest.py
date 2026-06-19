# tests/rhosocial/activerecord_test/feature/composite_pk/conftest.py
import pytest
try:
    from rhosocial.activerecord.testsuite.feature.composite_pk.conftest import *  # noqa: F403
except ImportError:
    pytest.skip("composite_pk testsuite not available", allow_module_level=True)
