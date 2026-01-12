"""
Test for AdvancedGroupingSupport protocol implementation.

This test creates a dialect that only supports advanced grouping operations (ROLLUP, CUBE, GROUPING SETS) 
and verifies that the corresponding formatting methods work correctly while other features remain unsupported.
"""
import pytest
from unittest.mock import MagicMock

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins import AdvancedGroupingMixin
from rhosocial.activerecord.backend.dialect.protocols import AdvancedGroupingSupport


class AdvancedGroupingOnlyDialect(SQLDialectBase, AdvancedGroupingMixin, AdvancedGroupingSupport):
    """Dialect that only supports advanced grouping operations."""
    
    def supports_rollup(self) -> bool:
        return True
    
    def supports_cube(self) -> bool:
        return True
    
    def supports_grouping_sets(self) -> bool:
        return True


def test_advanced_grouping_only_dialect_supports_features():
    """Test that advanced grouping-only dialect properly supports advanced grouping features."""
    dialect = AdvancedGroupingOnlyDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, AdvancedGroupingSupport)
    assert dialect.supports_rollup()
    assert dialect.supports_cube()
    assert dialect.supports_grouping_sets()


def test_format_grouping_expression_rollup_works():
    """Test that format_grouping_expression method works for ROLLUP in advanced grouping-only dialect."""
    dialect = AdvancedGroupingOnlyDialect()
    
    # Create a mock expression
    class MockExpr:
        def to_sql(self):
            return "col1", ()
    
    mock_expr = [MockExpr()]
    
    # This should not raise an error
    result = dialect.format_grouping_expression("ROLLUP", mock_expr)
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "ROLLUP" in result[0]


def test_format_grouping_expression_cube_works():
    """Test that format_grouping_expression method works for CUBE in advanced grouping-only dialect."""
    dialect = AdvancedGroupingOnlyDialect()
    
    # Create a mock expression
    class MockExpr:
        def to_sql(self):
            return "col1", ()
    
    mock_expr = [MockExpr()]
    
    # This should not raise an error
    result = dialect.format_grouping_expression("CUBE", mock_expr)
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "CUBE" in result[0]


def test_format_grouping_expression_grouping_sets_works():
    """Test that format_grouping_expression method works for GROUPING SETS in advanced grouping-only dialect."""
    dialect = AdvancedGroupingOnlyDialect()

    # Create mock expressions - GROUPING SETS expects a list of lists
    class MockExpr:
        def to_sql(self):
            return "col1", ()

    # For GROUPING SETS, expressions should be a list of lists of expressions
    mock_expr = [[MockExpr()]]

    # This should not raise an error
    result = dialect.format_grouping_expression("GROUPING SETS", mock_expr)

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "GROUPING SETS" in result[0]


def test_unsupported_grouping_operations():
    """Test that unsupported grouping operations raise appropriate errors."""
    # Create a dialect that doesn't support cube
    class NoCubeDialect(SQLDialectBase, AdvancedGroupingMixin, AdvancedGroupingSupport):
        def supports_rollup(self) -> bool:
            return True
        
        def supports_cube(self) -> bool:
            return False  # Cube not supported
        
        def supports_grouping_sets(self) -> bool:
            return True
    
    dialect = NoCubeDialect()
    
    # Create a mock expression
    class MockExpr:
        def to_sql(self):
            return "col1", ()
    
    mock_expr = [MockExpr()]
    
    # Attempting to format CUBE should raise an error
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_grouping_expression("CUBE", mock_expr)


def test_other_features_still_raise_errors():
    """Test that features not supported by this dialect still raise errors."""
    dialect = AdvancedGroupingOnlyDialect()
    
    # Test that CTE methods still raise errors
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_cte("test", "SELECT 1")
    
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_with_query([], "SELECT 1")
    
    # Test that window function methods still raise errors
    class MockWindowCall:
        def __init__(self):
            self.function_name = "ROW_NUMBER"
            self.args = []
            self.window_spec = None
            self.alias = None
    
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_window_function_call(MockWindowCall())
    
    # Test that JSON table expressions still raise errors
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_json_table_expression("", "", [], None, ())
    
    # Test that lateral expressions still raise errors  
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_lateral_expression("", (), None, "CROSS")
    
    # Test that table function expressions still raise errors
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_table_function_expression("FUNC", [], (), None, [])