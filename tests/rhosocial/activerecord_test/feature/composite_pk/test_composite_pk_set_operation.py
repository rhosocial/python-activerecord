# Bridge file for composite_pk set operation tests
import pytest
try:
    from rhosocial.activerecord.testsuite.feature.composite_pk.test_set_operation import *  # noqa: F403
except ImportError:
    pytest.skip("composite_pk testsuite not available", allow_module_level=True)
