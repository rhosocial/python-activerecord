"""
Test for JSONSupport protocol implementation.

This test creates a dialect that only supports JSON features and verifies that
the JSON formatting methods work correctly while other features remain unsupported.
"""
import pytest
from unittest.mock import MagicMock

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins import JSONMixin
from rhosocial.activerecord.backend.dialect.protocols import JSONSupport
from rhosocial.activerecord.backend.expression.query_sources import JSONTableExpression, JSONTableColumn


class JSONOnlyDialect(SQLDialectBase, JSONMixin, JSONSupport):
    """Dialect that only supports JSON features."""
    
    def supports_json_type(self) -> bool:
        return True
    
    def get_json_access_operator(self) -> str:
        return "->"
    
    def supports_json_table(self) -> bool:
        return True  # Enable JSON_TABLE support for this dialect


def test_json_only_dialect_supports_json_features():
    """Test that JSON-only dialect properly supports JSON features."""
    dialect = JSONOnlyDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, JSONSupport)
    assert dialect.supports_json_type()
    assert dialect.get_json_access_operator() == "->"
    assert dialect.supports_json_table()


def test_format_json_expression_works():
    """Test that format_json_expression method works in JSON-only dialect."""
    dialect = JSONOnlyDialect()
    
    # This should not raise an error
    result = dialect.format_json_expression("json_col", "$.name", "->", "alias")
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "json_col" in result[0]
    assert "alias" in result[0]


def test_format_json_table_expression_works():
    """Test that format_json_table_expression method works in JSON-only dialect."""
    dialect = JSONOnlyDialect()
    
    # This should not raise an error since supports_json_table returns True
    result = dialect.format_json_table_expression(
        json_col_sql="json_data",
        path="$.items[*]",
        columns=[{"name": "id", "type": "INTEGER", "path": "$.id"}],
        alias="parsed_items",
        params=()
    )
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "JSON_TABLE" in result[0]
    assert "parsed_items" in result[0]


def test_json_table_expression_integration():
    """Test JSONTableExpression integration with JSON-only dialect."""
    dialect = JSONOnlyDialect()
    
    # Create JSONTableExpression
    json_table = JSONTableExpression(
        dialect,
        json_column="json_data",
        path="$[*]",
        columns=[JSONTableColumn("id", "INTEGER", "$.id"), JSONTableColumn("name", "TEXT", "$.name")],
        alias="parsed_json"
    )
    
    # This should work without raising an error
    result = json_table.to_sql()
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "JSON_TABLE" in result[0]
    assert "parsed_json" in result[0]


def test_other_features_still_raise_errors():
    """Test that features not supported by this dialect still raise errors."""
    dialect = JSONOnlyDialect()
    
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
    
    # Test that lateral expressions still raise errors  
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_lateral_expression("", (), None, "CROSS")
    
    # Test that table function expressions still raise errors
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_table_function_expression("FUNC", [], (), None, [])