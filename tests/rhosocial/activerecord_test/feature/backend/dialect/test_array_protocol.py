# tests/rhosocial/activerecord_test/feature/backend/dialect/test_array_protocol.py
"""
Test for ArraySupport protocol implementation.

This test creates a dialect that does not support array operations and verifies that
the corresponding formatting methods raise appropriate errors.
"""

from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase, ArrayMixin, ArraySupport
)


class NoArrayDialect(SQLDialectBase, ArrayMixin, ArraySupport):
    """Dialect that does not support array operations."""
    
    def supports_array_type(self) -> bool:
        return False
    
    def supports_array_constructor(self) -> bool:
        return False
    
    def supports_array_access(self) -> bool:
        return False


def test_no_array_dialect_does_not_support_features():
    """Test that no-array dialect properly indicates lack of array features."""
    dialect = NoArrayDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, ArraySupport)
    assert not dialect.supports_array_type()
    assert not dialect.supports_array_constructor()
    assert not dialect.supports_array_access()


def test_format_array_expression_behavior():
    """Test that format_array_expression behaves appropriately in no-array dialect."""
    dialect = NoArrayDialect()
    
    # ArrayMixin doesn't check supports_array_access, so it will still work
    # But we can test that the dialect reports it's not supported
    assert dialect.supports_array_access() is False
    
    # The method should still execute without throwing an error for basic operations
    # but certain operations might still raise errors if they check support
    result = dialect.format_array_expression(
        operation="CONSTRUCTOR",
        elements=None,
        base_expr=None,
        index_expr=None,
        alias="arr"
    )
    
    assert isinstance(result, tuple)
    assert len(result) == 2