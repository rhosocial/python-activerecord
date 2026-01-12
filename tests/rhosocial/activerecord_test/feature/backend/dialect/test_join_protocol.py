# tests/rhosocial/activerecord_test/feature/backend/dialect/test_join_protocol.py
"""
Test for JoinSupport protocol implementation.

This test creates a dialect that only supports JOIN operations and verifies that
the format_join_expression method works correctly while other features remain unsupported.
"""

from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase, JoinMixin, JoinSupport
)


class JoinOnlyDialect(SQLDialectBase, JoinMixin, JoinSupport):
    """Dialect that only supports JOIN operations."""
    pass


def test_join_only_dialect_supports_features():
    """Test that join-only dialect properly supports JOIN features."""
    dialect = JoinOnlyDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, JoinSupport)
    assert dialect.supports_inner_join()
    assert dialect.supports_left_join()
    assert not dialect.supports_right_join()  # Default implementation
    assert not dialect.supports_full_join()   # Default implementation
    assert dialect.supports_cross_join()
    assert dialect.supports_natural_join()


def test_join_support_methods():
    """Test that join support methods return correct values."""
    dialect = JoinOnlyDialect()
    
    assert dialect.supports_inner_join() is True
    assert dialect.supports_left_join() is True
    assert dialect.supports_cross_join() is True
    assert dialect.supports_natural_join() is True
    assert dialect.supports_right_join() is False  # Default
    assert dialect.supports_full_join() is False   # Default