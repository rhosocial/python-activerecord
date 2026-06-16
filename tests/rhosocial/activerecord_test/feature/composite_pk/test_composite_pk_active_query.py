# Bridge file for composite_pk ActiveQuery tests
import pytest
try:
    from rhosocial.activerecord.testsuite.feature.composite_pk.test_active_query import *  # noqa: F403
except ImportError:
    pytest.skip("composite_pk testsuite not available", allow_module_level=True)
