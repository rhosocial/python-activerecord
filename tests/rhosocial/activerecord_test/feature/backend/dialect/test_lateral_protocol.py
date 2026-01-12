"""
Test for LateralJoinSupport protocol implementation.

This test creates a dialect that only supports lateral joins and table functions and verifies that
the corresponding formatting methods work correctly while other features remain unsupported.
"""
import pytest
from unittest.mock import MagicMock

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins import LateralJoinMixin
from rhosocial.activerecord.backend.dialect.protocols import LateralJoinSupport
from rhosocial.activerecord.backend.expression.query_sources import (
    LateralExpression, TableFunctionExpression
)
from rhosocial.activerecord.backend.expression.core import Subquery, Column
from rhosocial.activerecord.backend.expression.statements import QueryExpression
from rhosocial.activerecord.backend.expression.core import TableExpression


class LateralOnlyDialect(SQLDialectBase, LateralJoinMixin, LateralJoinSupport):
    """Dialect that only supports lateral joins and table functions."""
    
    def supports_lateral_join(self) -> bool:
        return True


def test_lateral_only_dialect_supports_lateral_features():
    """Test that lateral-only dialect properly supports lateral join features."""
    dialect = LateralOnlyDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, LateralJoinSupport)
    assert dialect.supports_lateral_join()


def test_format_lateral_expression_works():
    """Test that format_lateral_expression method works in lateral-only dialect."""
    dialect = LateralOnlyDialect()
    
    # This should not raise an error
    result = dialect.format_lateral_expression(
        expr_sql="SELECT * FROM users",
        expr_params=(),
        alias="lateral_users",
        join_type="CROSS"
    )
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "LATERAL" in result[0]
    assert "lateral_users" in result[0]


def test_format_table_function_expression_works():
    """Test that format_table_function_expression method works in lateral-only dialect."""
    dialect = LateralOnlyDialect()
    
    # This should not raise an error
    result = dialect.format_table_function_expression(
        func_name="UNNEST",
        args_sql=["array_col"],
        args_params=(),
        alias="unested",
        column_names=["value"]
    )
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "UNNEST" in result[0]
    assert "unested" in result[0]


def test_lateral_expression_integration():
    """Test LateralExpression integration with lateral-only dialect."""
    dialect = LateralOnlyDialect()
    
    # Create a subquery to use in lateral expression
    subquery = Subquery(
        dialect,
        QueryExpression(
            dialect,
            select=[Column(dialect, "id")],
            from_=TableExpression(dialect, "other_table")
        )
    )
    
    # Create LateralExpression
    lateral_expr = LateralExpression(
        dialect,
        expression=subquery,
        alias="lateral_data"
    )
    
    # This should work without raising an error
    result = lateral_expr.to_sql()
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "LATERAL" in result[0]
    assert "lateral_data" in result[0]


def test_table_function_expression_integration():
    """Test TableFunctionExpression integration with lateral-only dialect."""
    dialect = LateralOnlyDialect()
    
    # Create a mock expression to use as argument
    class MockArg:
        def to_sql(self):
            return "array_col", ()
    
    mock_arg = MockArg()
    
    # Create TableFunctionExpression
    table_func = TableFunctionExpression(
        dialect,
        "UNNEST",
        mock_arg,
        alias="unested",
        column_names=["value"]
    )
    
    # This should work without raising an error
    result = table_func.to_sql()
    
    assert isinstance(result, tuple)
    assert len(result) == 2
    assert "UNNEST" in result[0]
    assert "unested" in result[0]


def test_other_features_still_raise_errors():
    """Test that features not supported by this dialect still raise errors."""
    dialect = LateralOnlyDialect()
    
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