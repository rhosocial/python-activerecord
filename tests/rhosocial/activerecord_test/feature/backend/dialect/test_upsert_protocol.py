"""
Test for UpsertSupport protocol implementation.

This test creates a dialect that only supports upsert operations and verifies that
the corresponding formatting methods work correctly while other features remain unsupported.
"""
import pytest
from unittest.mock import MagicMock

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins import UpsertMixin
from rhosocial.activerecord.backend.dialect.protocols import UpsertSupport


class UpsertOnlyDialect(SQLDialectBase, UpsertMixin, UpsertSupport):
    """Dialect that only supports upsert operations."""
    
    def supports_upsert(self) -> bool:
        return True
    
    def get_upsert_syntax_type(self) -> str:
        return "ON CONFLICT"


def test_upsert_only_dialect_supports_features():
    """Test that upsert-only dialect properly supports upsert features."""
    dialect = UpsertOnlyDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, UpsertSupport)
    assert dialect.supports_upsert()
    assert dialect.get_upsert_syntax_type() == "ON CONFLICT"


def test_format_on_conflict_clause_works():
    """Test that format_on_conflict_clause method works in upsert-only dialect."""
    dialect = UpsertOnlyDialect()
    
    # Create a mock OnConflictClause
    class MockOnConflictClause:
        def __init__(self):
            self.conflict_target = ["id"]
            self.do_nothing = False
            self.update_assignments = {"name": "new_name"}
            self.update_where = None
    
    mock_clause = MockOnConflictClause()
    
    # This should not raise an error
    result = dialect.format_on_conflict_clause(mock_clause)
    
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_upsert_syntax_type():
    """Test that get_upsert_syntax_type returns correct value."""
    dialect = UpsertOnlyDialect()
    
    assert dialect.get_upsert_syntax_type() == "ON CONFLICT"
    
    # Test another dialect with different syntax
    class MySQLOnDuplicateDialect(SQLDialectBase, UpsertMixin, UpsertSupport):
        def supports_upsert(self) -> bool:
            return True
        
        def get_upsert_syntax_type(self) -> str:
            return "ON DUPLICATE KEY"
    
    mysql_dialect = MySQLOnDuplicateDialect()
    assert mysql_dialect.get_upsert_syntax_type() == "ON DUPLICATE KEY"


def test_other_features_still_raise_errors():
    """Test that features not supported by this dialect still raise errors."""
    dialect = UpsertOnlyDialect()
    
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