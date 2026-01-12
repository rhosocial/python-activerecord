"""
Test for WindowFunctionSupport protocol implementation.

This test creates a dialect that only supports window functions and verifies that
the window function formatting methods work correctly while other features remain unsupported.
"""
import pytest
from unittest.mock import MagicMock

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins import WindowFunctionMixin
from rhosocial.activerecord.backend.dialect.protocols import WindowFunctionSupport
from rhosocial.activerecord.backend.expression.advanced_functions import (
    WindowFunctionCall, WindowSpecification, WindowFrameSpecification
)
from rhosocial.activerecord.backend.expression.core import Column


class WindowOnlyDialect(SQLDialectBase, WindowFunctionMixin, WindowFunctionSupport):
    """Dialect that only supports window functions."""
    
    def supports_window_functions(self) -> bool:
        return True
    
    def supports_window_frame_clause(self) -> bool:
        return True


def test_window_only_dialect_supports_window_features():
    """Test that window-only dialect properly supports window function features."""
    dialect = WindowOnlyDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, WindowFunctionSupport)
    assert dialect.supports_window_functions()
    assert dialect.supports_window_frame_clause()


def test_format_window_function_call_works():
    """Test that format_window_function_call method works in window-only dialect."""
    dialect = WindowOnlyDialect()
    
    # Create a mock window function call
    class MockWindowFunctionCall:
        def __init__(self):
            self.function_name = "ROW_NUMBER"
            self.args = []
            self.window_spec = None
            self.alias = None
    
    mock_call = MockWindowFunctionCall()
    
    # This should not raise an error
    result = dialect.format_window_function_call(mock_call)
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "ROW_NUMBER" in result[0]


def test_format_window_specification_works():
    """Test that format_window_specification method works in window-only dialect."""
    dialect = WindowOnlyDialect()

    # Create a mock window specification with at least one component
    class MockWindowSpec:
        def __init__(self):
            # Add an order_by component to avoid the ValueError
            class MockExpr:
                def to_sql(self):
                    return "col1", ()
            self.partition_by = []
            self.order_by = [MockExpr()]
            self.frame = None

    mock_spec = MockWindowSpec()

    # This should not raise an error
    result = dialect.format_window_specification(mock_spec)

    assert isinstance(result, tuple)
    assert len(result) == 2


def test_format_window_frame_specification_works():
    """Test that format_window_frame_specification method works in window-only dialect."""
    dialect = WindowOnlyDialect()
    
    # Create a mock window frame specification
    class MockFrameSpec:
        def __init__(self):
            self.frame_type = "ROWS"
            self.start_frame = "UNBOUNDED PRECEDING"
            self.end_frame = None
    
    mock_spec = MockFrameSpec()
    
    # This should not raise an error
    result = dialect.format_window_frame_specification(mock_spec)
    
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_window_clause_and_definition_methods():
    """Test window clause and definition methods."""
    dialect = WindowOnlyDialect()

    # Test format_window_clause
    class MockWindowClause:
        def __init__(self):
            self.definitions = []

    mock_clause = MockWindowClause()

    with pytest.raises(ValueError):  # Should raise error for empty definitions
        dialect.format_window_clause(mock_clause)

    # Test format_window_definition
    class MockWindowSpec:
        def __init__(self):
            # Add an order_by component to avoid the ValueError in format_window_specification
            class MockExpr:
                def to_sql(self):
                    return "col1", ()
            self.partition_by = []
            self.order_by = [MockExpr()]
            self.frame = None

    class MockWindowDef:
        def __init__(self):
            self.name = "w1"
            self.specification = MockWindowSpec()

    mock_def = MockWindowDef()

    # This should not raise an error
    result = dialect.format_window_definition(mock_def)

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "w1" in result[0]


def test_other_features_still_raise_errors():
    """Test that features not supported by this dialect still raise errors."""
    dialect = WindowOnlyDialect()
    
    # Test that CTE methods still raise errors
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_cte("test", "SELECT 1")
    
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_with_query([], "SELECT 1")
    
    # Test that JSON table expressions still raise errors
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_json_table_expression("", "", [], None, ())
    
    # Test that lateral expressions still raise errors  
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_lateral_expression("", (), None, "CROSS")
    
    # Test that table function expressions still raise errors
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_table_function_expression("FUNC", [], (), None, [])