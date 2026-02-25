# tests/rhosocial/activerecord_test/feature/backend/dialect/test_json_protocol.py
"""
Test for JSONSupport protocol implementation.

This test creates a dialect that does not support JSON features and verifies that
the JSON formatting methods raise appropriate errors.
"""
import pytest

from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase, JSONMixin, JSONSupport, UnsupportedFeatureError
)
from rhosocial.activerecord.backend.expression.query_sources import JSONTableExpression, JSONTableColumn


class NoJSONDialect(SQLDialectBase, JSONMixin, JSONSupport):
    """Dialect that does not support JSON features."""
    
    def supports_json_type(self) -> bool:
        return False
    
    def get_json_access_operator(self) -> str:
        return "->"
    
    def supports_json_table(self) -> bool:
        return False  # Disable JSON_TABLE support for this dialect


def test_no_json_dialect_does_not_support_json_features():
    """Test that no-JSON dialect properly indicates lack of JSON features."""
    dialect = NoJSONDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, JSONSupport)
    assert not dialect.supports_json_type()
    assert dialect.get_json_access_operator() == "->"
    assert not dialect.supports_json_table()


def test_format_json_expression_works_but_other_features_raise_error():
    """Test that some JSON methods work while others raise errors."""
    dialect = NoJSONDialect()
    
    # format_json_expression should work since it doesn't check supports_json_type
    # but JSON table expression should raise an error
    with pytest.raises(UnsupportedFeatureError):
        dialect.format_json_table_expression(
            json_col_sql="json_data",
            path="$.items[*]",
            columns=[{"name": "id", "type": "INTEGER", "path": "$.id"}],
            alias="parsed_items",
            params=()
        )


def test_json_table_expression_integration_raises_error():
    """Test JSONTableExpression integration raises error with no-JSON dialect."""
    dialect = NoJSONDialect()
    
    # Create JSONTableExpression
    json_table = JSONTableExpression(
        dialect,
        json_column="json_data",
        path="$[*]",
        columns=[JSONTableColumn("id", "INTEGER", "$.id"), JSONTableColumn("name", "TEXT", "$.name")],
        alias="parsed_json"
    )
    
    # This should raise an error
    with pytest.raises(UnsupportedFeatureError):
        json_table.to_sql()