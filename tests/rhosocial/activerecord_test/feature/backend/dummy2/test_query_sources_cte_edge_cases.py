# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_query_sources_cte_edge_cases.py
import pytest
from rhosocial.activerecord.backend.expression.query_sources import CTEExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCTEExpressionEdgeCases:
    """Tests for edge cases in CTEExpression.to_sql() method."""

    def test_cte_expression_with_string_query(self, dummy_dialect: DummyDialect):
        """Test CTEExpression when query is a string (covers the else branch)."""
        # This tests the else branch: query is neither BaseExpression nor tuple
        cte = CTEExpression(
            dummy_dialect,
            name="test_cte",
            query="SELECT id, name FROM users WHERE age > 18",  # String instead of BaseExpression
            columns=["id", "name"]
        )
        
        sql, params = cte.to_sql()
        
        # Should contain the CTE name and query
        assert "test_cte" in sql
        assert "SELECT id, name FROM users WHERE age > 18" in sql
        # Since query is a string, there are no additional parameters
        assert params == ()

    def test_cte_expression_with_tuple_query(self, dummy_dialect: DummyDialect):
        """Test CTEExpression when query is a tuple (covers elif branch)."""
        # This tests the elif branch: query is a tuple
        query_tuple = ("SELECT id FROM table WHERE col = ?", [123])
        
        cte = CTEExpression(
            dummy_dialect,
            name="tuple_cte",
            query=query_tuple,  # Tuple (sql, params)
            columns=["id"]
        )
        
        sql, params = cte.to_sql()
        
        assert "tuple_cte" in sql
        assert "SELECT id FROM table WHERE col = ?" in sql
        assert params == (123,)

    def test_cte_expression_with_base_expression_query(self, dummy_dialect: DummyDialect):
        """Test CTEExpression when query is a BaseExpression (covers if branch)."""
        # This tests the if branch: query is a BaseExpression
        from rhosocial.activerecord.backend.expression import Subquery
        
        subquery = Subquery(
            dummy_dialect,
            "SELECT name FROM users WHERE status = ?",
            ("active",)
        )
        
        cte = CTEExpression(
            dummy_dialect,
            name="subquery_cte",
            query=subquery,  # BaseExpression
            columns=["name"]
        )
        
        sql, params = cte.to_sql()
        
        assert "subquery_cte" in sql
        assert params == ("active",)