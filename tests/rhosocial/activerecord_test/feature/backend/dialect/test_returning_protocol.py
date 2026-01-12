"""
Test for ReturningSupport protocol implementation.

This test creates a dialect that only supports RETURNING clauses and verifies that
the corresponding formatting methods work correctly while other features remain unsupported.
"""
import pytest
from unittest.mock import MagicMock

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins import ReturningMixin
from rhosocial.activerecord.backend.dialect.protocols import ReturningSupport
from rhosocial.activerecord.backend.expression.statements import ReturningClause
from rhosocial.activerecord.backend.expression.core import Column


class ReturningOnlyDialect(SQLDialectBase, ReturningMixin, ReturningSupport):
    """Dialect that only supports RETURNING clauses."""
    
    def supports_returning_clause(self) -> bool:
        return True


def test_returning_only_dialect_supports_features():
    """Test that returning-only dialect properly supports RETURNING clause features."""
    dialect = ReturningOnlyDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, ReturningSupport)
    assert dialect.supports_returning_clause()


def test_format_returning_clause_works():
    """Test that format_returning_clause method works in returning-only dialect."""
    dialect = ReturningOnlyDialect()
    
    # Create a mock ReturningClause
    class MockReturningClause:
        def __init__(self):
            self.expressions = [Column(dialect, "id"), Column(dialect, "name")]
            self.alias = None
    
    mock_clause = MockReturningClause()
    
    # This should not raise an error
    result = dialect.format_returning_clause(mock_clause)
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "RETURNING" in result[0]
    assert "id" in result[0]
    assert "name" in result[0]


def test_returning_clause_with_alias():
    """Test that format_returning_clause method works with alias."""
    dialect = ReturningOnlyDialect()
    
    # Create a mock ReturningClause with alias
    class MockReturningClause:
        def __init__(self):
            self.expressions = [Column(dialect, "id")]
            self.alias = "result"
    
    mock_clause = MockReturningClause()
    
    # This should not raise an error
    result = dialect.format_returning_clause(mock_clause)
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "RETURNING" in result[0]
    assert "result" in result[0]


def test_unsupported_returning_clause():
    """Test that unsupported RETURNING clause raises appropriate error."""
    # Create a dialect that doesn't support returning
    class NoReturningDialect(SQLDialectBase, ReturningMixin, ReturningSupport):
        def supports_returning_clause(self) -> bool:
            return False
    
    dialect = NoReturningDialect()
    
    # Create a mock ReturningClause
    class MockReturningClause:
        def __init__(self):
            self.expressions = [Column(dialect, "id")]
            self.alias = None
    
    mock_clause = MockReturningClause()
    
    # Attempting to format returning clause should raise an error
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_returning_clause(mock_clause)


def test_other_features_still_raise_errors():
    """Test that features not supported by this dialect still raise errors."""
    dialect = ReturningOnlyDialect()
    
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
    
    # Test that advanced grouping expressions still raise errors
    class MockExpr:
        def to_sql(self):
            return "col1", ()
    
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_grouping_expression("ROLLUP", [MockExpr()])