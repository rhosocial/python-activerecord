# tests/rhosocial/activerecord_test/feature/backend/dialect/test_wildcard_protocol.py
"""
Test for WildcardSupport protocol implementation.

This test creates a dialect that only supports wildcard expressions and verifies that
the format_wildcard method works correctly while other features remain unsupported.
"""

from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase, WildcardSupport
)


class WildcardOnlyDialect(SQLDialectBase, WildcardSupport):
    """Dialect that only supports wildcard expressions."""
    pass


def test_wildcard_only_dialect_supports_features():
    """Test that wildcard-only dialect properly supports wildcard features."""
    dialect = WildcardOnlyDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, WildcardSupport)


def test_format_wildcard_works():
    """Test that format_wildcard method works in wildcard-only dialect."""
    dialect = WildcardOnlyDialect()
    
    # Test with no table
    result = dialect.format_wildcard()
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert result[0] == "*"
    
    # Test with table
    result = dialect.format_wildcard(table="users")
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "users" in result[0]
    assert "*" in result[0]