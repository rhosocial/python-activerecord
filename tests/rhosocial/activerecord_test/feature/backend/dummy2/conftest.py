import pytest
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

# Note for developers:
# This test suite for the 'expression-dialect' system currently requires
# the 'rhosocial-activerecord-capabilities' plugin to be disabled.
# This is due to a refactoring of the backend that causes conflicts with
# the plugin's test collection phase for other parts of the test suite.
#
# To run these tests, please use the following command:
# pytest tests/rhosocial/activerecord_test/feature/backend/dummy2/ -p no:rhosocial-activerecord-capabilities

@pytest.fixture
def dummy_dialect():
    """Provides a DummyDialect instance that supports all features."""
    return DummyDialect()
