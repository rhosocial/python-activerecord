import pytest
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

@pytest.fixture
def dummy_dialect():
    """Provides a DummyDialect instance that supports all features."""
    return DummyDialect()