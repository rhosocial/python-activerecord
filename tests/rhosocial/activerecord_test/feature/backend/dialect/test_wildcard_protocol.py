"""
Test for WildcardSupport protocol implementation.

This test creates a dialect that only supports wildcard expressions and verifies that
the format_wildcard method works correctly while other features remain unsupported.
"""
import pytest
from unittest.mock import MagicMock

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.protocols import WildcardSupport


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


def test_other_features_still_raise_errors():
    """Test that features not supported by this dialect still raise errors."""
    dialect = WildcardOnlyDialect()
    
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
    
    # Test that returning clause still raises errors
    class MockReturningClause:
        def __init__(self):
            self.expressions = []
            self.alias = None
    
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_returning_clause(MockReturningClause())
    
    # Test that upsert operations still raise errors
    class MockOnConflictClause:
        def __init__(self):
            self.conflict_target = ["id"]
            self.do_nothing = False
            self.update_assignments = {"name": "new_name"}
            self.update_where = None
    
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_on_conflict_clause(MockOnConflictClause())
    
    # Test that array operations still raise errors
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_array_expression(
            operation="CONSTRUCTOR",
            elements=None,
            base_expr=None,
            index_expr=None,
            alias="arr"
        )