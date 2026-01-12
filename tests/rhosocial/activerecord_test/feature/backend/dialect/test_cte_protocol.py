"""
Test for CTESupport protocol implementation.

This test creates a dialect that only supports CTEs and verifies that
the format_cte and format_with_query methods work correctly while other
features remain unsupported.
"""
import pytest
from unittest.mock import MagicMock

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins import CTEMixin
from rhosocial.activerecord.backend.dialect.protocols import CTESupport
from rhosocial.activerecord.backend.expression.query_sources import CTEExpression, WithQueryExpression
from rhosocial.activerecord.backend.expression.statements import QueryExpression
from rhosocial.activerecord.backend.expression.core import TableExpression, Column
from rhosocial.activerecord.backend.expression.bases import BaseExpression


class CTEOnlyDialect(SQLDialectBase, CTEMixin, CTESupport):
    """Dialect that only supports CTEs."""
    
    def supports_basic_cte(self) -> bool:
        return True
    
    def supports_recursive_cte(self) -> bool:
        return True
    
    def supports_materialized_cte(self) -> bool:
        return True


def test_cte_only_dialect_supports_cte_features():
    """Test that CTE-only dialect properly supports CTE features."""
    dialect = CTEOnlyDialect()
    
    # Verify protocol implementation
    assert isinstance(dialect, CTESupport)
    assert dialect.supports_basic_cte()
    assert dialect.supports_recursive_cte()
    assert dialect.supports_materialized_cte()


def test_format_cte_works():
    """Test that format_cte method works in CTE-only dialect."""
    dialect = CTEOnlyDialect()
    
    # This should not raise an error
    result = dialect.format_cte(
        name="test_cte",
        query_sql="SELECT * FROM users",
        columns=["id", "name"]
    )
    
    assert "test_cte" in result
    assert "SELECT * FROM users" in result


def test_format_with_query_works():
    """Test that format_with_query method works in CTE-only dialect."""
    dialect = CTEOnlyDialect()
    
    # This should not raise an error
    result = dialect.format_with_query(
        cte_sql_parts=["test_cte AS (SELECT * FROM users)"],
        main_query_sql="SELECT * FROM test_cte"
    )
    
    assert "WITH" in result.upper()
    assert "test_cte" in result
    assert "SELECT * FROM users" in result


def test_cte_expression_integration():
    """Test CTEExpression integration with CTE-only dialect."""
    dialect = CTEOnlyDialect()
    
    # Create a simple query to use in CTE
    query = QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name")],
        from_=TableExpression(dialect, "users")
    )
    
    # Create CTE expression
    cte = CTEExpression(
        dialect,
        name="user_cte",
        query=query,
        columns=["id", "name"]
    )
    
    # This should work without raising an error
    sql, params = cte.to_sql()
    
    assert "user_cte" in sql
    assert "users" in sql


def test_with_query_expression_integration():
    """Test WithQueryExpression integration with CTE-only dialect."""
    dialect = CTEOnlyDialect()
    
    # Create a simple query to use in CTE
    query = QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name")],
        from_=TableExpression(dialect, "users")
    )
    
    # Create CTE
    cte = CTEExpression(
        dialect,
        name="user_cte",
        query=query,
        columns=["id", "name"]
    )
    
    # Create main query that uses the CTE
    main_query = QueryExpression(
        dialect,
        select=[Column(dialect, "id")],
        from_=TableExpression(dialect, "user_cte")
    )
    
    # Create WithQueryExpression
    with_query = WithQueryExpression(
        dialect,
        ctes=[cte],
        main_query=main_query
    )
    
    # This should work without raising an error
    sql, params = with_query.to_sql()
    
    assert "WITH" in sql.upper()
    assert "user_cte" in sql
    assert "users" in sql


def test_other_features_still_raise_errors():
    """Test that features not supported by this dialect still raise errors."""
    dialect = CTEOnlyDialect()
    
    # Test that JSON table expressions still raise errors
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_json_table_expression("", "", [], None, ())
    
    # Test that lateral expressions still raise errors  
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_lateral_expression("", (), None, "CROSS")
    
    # Test that table function expressions still raise errors
    with pytest.raises(Exception):  # Should raise UnsupportedFeatureError
        dialect.format_table_function_expression("FUNC", [], (), None, [])