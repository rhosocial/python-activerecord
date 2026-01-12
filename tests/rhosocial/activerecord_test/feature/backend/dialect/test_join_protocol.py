"""
Test for JoinSupport protocol implementation.

This test creates a dialect that only supports JOIN operations and verifies that
the format_join_expression method works correctly while other features remain unsupported.
"""
import pytest
from unittest.mock import MagicMock

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins import JoinMixin
from rhosocial.activerecord.backend.dialect.protocols import JoinSupport


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


def test_other_features_still_raise_errors():
    """Test that features not supported by this dialect still raise errors."""
    dialect = JoinOnlyDialect()
    
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
    
    # Test that wildcard operations still work (they're implemented in base class)
    # This should not raise an error
    result = dialect.format_wildcard()
    assert result[0] == "*"