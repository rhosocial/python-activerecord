# tests/rhosocial/activerecord_test/feature/backend/dialect/test_advanced_grouping_protocol.py
"""
Test for AdvancedGroupingSupport protocol implementation.

This test creates a dialect that does not support advanced grouping operations (ROLLUP, CUBE, GROUPING SETS)
and verifies that the corresponding formatting methods raise appropriate errors.
"""
import pytest

from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase, AdvancedGroupingMixin, AdvancedGroupingSupport, UnsupportedFeatureError
)


class NoAdvancedGroupingDialect(SQLDialectBase, AdvancedGroupingMixin, AdvancedGroupingSupport):
    """Dialect that does not support advanced grouping operations."""
    
    def supports_rollup(self) -> bool:
        return False
    
    def supports_cube(self) -> bool:
        return False
    
    def supports_grouping_sets(self) -> bool:
        return False


def test_no_advanced_grouping_dialect_does_not_support_features():
    """Test that no-advanced grouping dialect properly indicates lack of advanced grouping features."""
    dialect = NoAdvancedGroupingDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, AdvancedGroupingSupport)
    assert not dialect.supports_rollup()
    assert not dialect.supports_cube()
    assert not dialect.supports_grouping_sets()


def test_format_grouping_expression_rollup_raises_error():
    """Test that format_grouping_expression method raises error for ROLLUP in no-advanced grouping dialect."""
    dialect = NoAdvancedGroupingDialect()
    
    # Create a mock expression
    class MockExpr:
        def to_sql(self):
            return "col1", ()
    
    mock_expr = [MockExpr()]
    
    # This should raise an error
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_grouping_expression("ROLLUP", mock_expr)


def test_format_grouping_expression_cube_raises_error():
    """Test that format_grouping_expression method raises error for CUBE in no-advanced grouping dialect."""
    dialect = NoAdvancedGroupingDialect()
    
    # Create a mock expression
    class MockExpr:
        def to_sql(self):
            return "col1", ()
    
    mock_expr = [MockExpr()]
    
    # This should raise an error
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_grouping_expression("CUBE", mock_expr)


def test_format_grouping_expression_grouping_sets_raises_error():
    """Test that format_grouping_expression method raises error for GROUPING SETS in no-advanced grouping dialect."""
    dialect = NoAdvancedGroupingDialect()
    
    # Create a mock expression - GROUPING SETS expects a list of lists
    class MockExpr:
        def to_sql(self):
            return "col1", ()
    
    mock_expr = [[MockExpr()]]
    
    # This should raise an error
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_grouping_expression("GROUPING SETS", mock_expr)