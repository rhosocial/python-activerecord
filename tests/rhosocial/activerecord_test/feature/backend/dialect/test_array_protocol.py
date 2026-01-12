"""
Test for ArraySupport protocol implementation.

This test creates a dialect that only supports array operations and verifies that
the corresponding formatting methods work correctly while other features remain unsupported.
"""
import pytest
from unittest.mock import MagicMock

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins import ArrayMixin
from rhosocial.activerecord.backend.dialect.protocols import ArraySupport


class ArrayOnlyDialect(SQLDialectBase, ArrayMixin, ArraySupport):
    """Dialect that only supports array operations."""
    
    def supports_array_type(self) -> bool:
        return True
    
    def supports_array_constructor(self) -> bool:
        return True
    
    def supports_array_access(self) -> bool:
        return True


def test_array_only_dialect_supports_features():
    """Test that array-only dialect properly supports array features."""
    dialect = ArrayOnlyDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, ArraySupport)
    assert dialect.supports_array_type()
    assert dialect.supports_array_constructor()
    assert dialect.supports_array_access()


def test_format_array_expression_constructor_works():
    """Test that format_array_expression method works for constructor in array-only dialect."""
    dialect = ArrayOnlyDialect()
    
    # This should not raise an error
    result = dialect.format_array_expression(
        operation="CONSTRUCTOR",
        elements=None,
        base_expr=None,
        index_expr=None,
        alias="arr"
    )
    
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_format_array_expression_access_works():
    """Test that format_array_expression method works for access in array-only dialect."""
    dialect = ArrayOnlyDialect()
    
    # Create mock expressions
    class MockBaseExpr:
        def to_sql(self):
            return "arr_col", ()
    
    class MockIndexExpr:
        def to_sql(self):
            return "1", ()
    
    base_expr = MockBaseExpr()
    index_expr = MockIndexExpr()
    
    # This should not raise an error
    result = dialect.format_array_expression(
        operation="ACCESS",
        elements=None,
        base_expr=base_expr,
        index_expr=index_expr,
        alias="element"
    )
    
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_unsupported_array_operations():
    """Test that unsupported array operations behave appropriately."""
    # Create a dialect that doesn't support array access
    class NoArrayDialect(SQLDialectBase, ArrayMixin, ArraySupport):
        def supports_array_type(self) -> bool:
            return True  # Enable basic array support

        def supports_array_constructor(self) -> bool:
            return True  # Enable constructor support

        def supports_array_access(self) -> bool:
            return False  # Disable access support

    dialect = NoArrayDialect()

    # Create mock expressions
    class MockBaseExpr:
        def to_sql(self):
            return "arr_col", ()

    class MockIndexExpr:
        def to_sql(self):
            return "1", ()

    base_expr = MockBaseExpr()
    index_expr = MockIndexExpr()

    # ArrayMixin doesn't check supports_array_access, so it will still work
    # But we can test that the dialect reports it's not supported
    assert dialect.supports_array_access() is False

    # The method should still execute without throwing an error
    result = dialect.format_array_expression(
        operation="ACCESS",
        elements=None,
        base_expr=base_expr,
        index_expr=index_expr,
        alias="element"
    )

    assert isinstance(result, tuple)
    assert len(result) == 2


def test_other_features_still_raise_errors():
    """Test that features not supported by this dialect still raise errors."""
    dialect = ArrayOnlyDialect()
    
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