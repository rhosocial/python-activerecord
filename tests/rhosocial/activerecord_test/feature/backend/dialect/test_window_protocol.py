# tests/rhosocial/activerecord_test/feature/backend/dialect/test_window_protocol.py
"""
Test for WindowFunctionSupport protocol implementation.

This test creates a dialect that does not support window functions and verifies that
the window function formatting methods raise appropriate errors.
"""
import pytest

from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase, WindowFunctionMixin, WindowFunctionSupport, UnsupportedFeatureError
)


class NoWindowDialect(SQLDialectBase, WindowFunctionMixin, WindowFunctionSupport):
    """Dialect that does not support window functions."""
    
    def supports_window_functions(self) -> bool:
        return False
    
    def supports_window_frame_clause(self) -> bool:
        return False


def test_no_window_dialect_does_not_support_window_features():
    """Test that no-window dialect properly indicates lack of window function support."""
    dialect = NoWindowDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, WindowFunctionSupport)
    assert not dialect.supports_window_functions()
    assert not dialect.supports_window_frame_clause()


def test_format_window_function_call_raises_error():
    """Test that format_window_function_call method raises error in no-window dialect."""
    dialect = NoWindowDialect()
    
    # Create a mock window function call
    class MockWindowFunctionCall:
        def __init__(self):
            self.function_name = "ROW_NUMBER"
            self.args = []
            self.window_spec = None
            self.alias = None
    
    mock_call = MockWindowFunctionCall()
    
    # This should raise an error
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_window_function_call(mock_call)


def test_format_window_specification_raises_error():
    """Test that format_window_specification method raises error in no-window dialect."""
    dialect = NoWindowDialect()
    
    # Create a mock window specification
    class MockWindowSpec:
        def __init__(self):
            # Add an order_by component to avoid the ValueError in format_window_specification
            class MockExpr:
                def to_sql(self):
                    return "col1", ()
            self.partition_by = []
            self.order_by = [MockExpr()]
            self.frame = None
    
    mock_spec = MockWindowSpec()
    
    # This should raise an error
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_window_specification(mock_spec)


def test_format_window_frame_specification_raises_error():
    """Test that format_window_frame_specification method raises error in no-window dialect."""
    dialect = NoWindowDialect()
    
    # Create a mock window frame specification
    class MockFrameSpec:
        def __init__(self):
            self.frame_type = "ROWS"
            self.start_frame = "UNBOUNDED PRECEDING"
            self.end_frame = None
    
    mock_spec = MockFrameSpec()
    
    # This should raise an error
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_window_frame_specification(mock_spec)


def test_window_clause_and_definition_methods_raise_error():
    """Test window clause and definition methods raise errors."""
    dialect = NoWindowDialect()
    
    # Test format_window_clause raises error
    class MockWindowClause:
        def __init__(self):
            self.definitions = []
    
    mock_clause = MockWindowClause()
    
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_window_clause(mock_clause)
    
    # Test format_window_definition raises error
    class MockWindowDef:
        def __init__(self):
            # Add an order_by component to avoid the ValueError in format_window_specification
            class MockExpr:
                def to_sql(self):
                    return "col1", ()
            self.name = "w1"
            class MockWindowSpec:
                def __init__(self):
                    self.partition_by = []
                    self.order_by = [MockExpr()]
                    self.frame = None
            self.specification = MockWindowSpec()
    
    mock_def = MockWindowDef()
    
    # This should raise an error
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_window_definition(mock_def)