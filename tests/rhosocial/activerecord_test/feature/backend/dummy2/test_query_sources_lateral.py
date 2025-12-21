# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_query_sources_lateral.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, Subquery, FunctionCall, QueryExpression, TableExpression
)
from rhosocial.activerecord.backend.expression.query_sources import (
    LateralExpression, TableFunctionExpression, ValuesExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestLateralExpression:
    """Tests for LateralExpression representing LATERAL joins/subqueries."""

    def test_lateral_subquery_basic(self, dummy_dialect: DummyDialect):
        """Test basic LATERAL subquery expression."""
        lateral_query = Subquery(
            dummy_dialect, 
            "SELECT user_id, order_date FROM orders WHERE user_id = users.id LIMIT ?", 
            (5,)
        )
        
        lateral_expr = LateralExpression(
            dummy_dialect,
            expression=lateral_query,
            alias="user_orders"
        )
        
        sql, params = lateral_expr.to_sql()
        
        assert "LATERAL" in sql.upper()
        assert "user_orders" in sql
        assert params == (5,)

    def test_lateral_table_function(self, dummy_dialect: DummyDialect):
        """Test LATERAL with table function expression."""
        table_func = TableFunctionExpression(
            dummy_dialect,
            "UNNEST",
            Literal(dummy_dialect, [1, 2, 3]),
            alias="unnested",
            column_names=["value"]
        )
        
        lateral_expr = LateralExpression(
            dummy_dialect,
            expression=table_func,
            alias="lateral_unnest"
        )
        
        sql, params = lateral_expr.to_sql()
        
        assert "LATERAL" in sql.upper()
        assert "lateral_unnest" in sql
        assert params == ([1, 2, 3],)

    def test_lateral_with_cross_join_type(self, dummy_dialect: DummyDialect):
        """Test LATERAL expression with CROSS join type."""
        lateral_query = Subquery(
            dummy_dialect,
            "SELECT * FROM related_table WHERE parent_id = main_table.id",
            ()
        )
        
        lateral_expr = LateralExpression(
            dummy_dialect,
            expression=lateral_query,
            alias="related_data",
            join_type="CROSS"
        )
        
        sql, params = lateral_expr.to_sql()
        
        assert "LATERAL" in sql.upper()
        assert "CROSS" in sql.upper() or "CROSS" in sql
        assert "related_data" in sql
        assert params == ()

    def test_lateral_with_inner_join_type(self, dummy_dialect: DummyDialect):
        """Test LATERAL expression with INNER join type."""
        lateral_query = Subquery(
            dummy_dialect,
            "SELECT item_id, quantity FROM order_items WHERE order_id = orders.id",
            ()
        )
        
        lateral_expr = LateralExpression(
            dummy_dialect,
            expression=lateral_query,
            alias="items",
            join_type="INNER"
        )
        
        sql, params = lateral_expr.to_sql()
        
        assert "LATERAL" in sql.upper()
        assert "INNER" in sql.upper() or "INNER" in sql
        assert "items" in sql
        assert params == ()

    def test_lateral_used_in_query_from_clause(self, dummy_dialect: DummyDialect):
        """Test LATERAL expression used in a query FROM clause."""
        # Create lateral expression
        lateral_query = Subquery(
            dummy_dialect,
            "SELECT COUNT(*) as order_count FROM orders WHERE user_id = users.id",
            ()
        )

        lateral_expr = LateralExpression(
            dummy_dialect,
            expression=lateral_query,
            alias="user_stats"
        )

        # Create query using just the lateral expression as FROM
        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "order_count", table="user_stats")
            ],
            from_=lateral_expr  # Use lateral expression directly
        )

        sql, params = query.to_sql()

        assert "LATERAL" in sql.upper()
        assert "user_stats" in sql
        assert params == ()

    def test_lateral_with_values_expression(self, dummy_dialect: DummyDialect):
        """Test LATERAL with ValuesExpression."""
        values_expr = ValuesExpression(
            dummy_dialect,
            values=[(1, "test"), (2, "data")],
            alias="value_table",
            column_names=["id", "name"]
        )
        
        lateral_expr = LateralExpression(
            dummy_dialect,
            expression=values_expr,
            alias="lateral_values"
        )
        
        sql, params = lateral_expr.to_sql()
        
        assert "LATERAL" in sql.upper()
        assert "lateral_values" in sql
        assert params == (1, "test", 2, "data")

    def test_lateral_expression_complex_subquery(self, dummy_dialect: DummyDialect):
        """Test LATERAL with complex subquery involving functions."""
        # Complex subquery that might reference outer query
        complex_query = QueryExpression(
            dummy_dialect,
            select=[
                FunctionCall(dummy_dialect, "SUM", Column(dummy_dialect, "amount")),
                Column(dummy_dialect, "category")
            ],
            from_=TableExpression(dummy_dialect, "transactions"),
            # In a real scenario, this would reference outer query columns
        )
        
        lateral_expr = LateralExpression(
            dummy_dialect,
            expression=complex_query,
            alias="aggregated_data"
        )
        
        sql, params = lateral_expr.to_sql()
        
        assert "LATERAL" in sql.upper()
        assert "aggregated_data" in sql

    def test_lateral_with_different_join_types(self, dummy_dialect: DummyDialect):
        """Test LATERAL with different join types."""
        lateral_query = Subquery(dummy_dialect, "SELECT 1 as dummy", ())
        
        join_types = ["CROSS", "INNER", "LEFT", "RIGHT"]  # Basic join types
        
        for join_type in join_types:
            lateral_expr = LateralExpression(
                dummy_dialect,
                expression=lateral_query,
                alias=f"lateral_{join_type.lower()}",
                join_type=join_type
            )
            
            sql, params = lateral_expr.to_sql()
            
            assert "LATERAL" in sql.upper()
            assert f"lateral_{join_type.lower()}" in sql
            assert params == ()

    def test_lateral_expression_parameters_handling(self, dummy_dialect: DummyDialect):
        """Test that parameters from lateral expression are properly handled."""
        lateral_query = Subquery(
            dummy_dialect,
            "SELECT * FROM table WHERE col1 = ? AND col2 = ?",
            ("value1", "value2")
        )
        
        lateral_expr = LateralExpression(
            dummy_dialect,
            expression=lateral_query,
            alias="param_lateral"
        )
        
        sql, params = lateral_expr.to_sql()
        
        assert "LATERAL" in sql.upper()
        assert "param_lateral" in sql
        assert params == ("value1", "value2")

    def test_lateral_with_alias_formatting(self, dummy_dialect: DummyDialect):
        """Test various alias formatting for lateral expressions."""
        lateral_query = Subquery(dummy_dialect, "SELECT NULL as empty", ())
        
        lateral_expr = LateralExpression(
            dummy_dialect,
            expression=lateral_query,
            alias="formatted_alias"
        )
        
        sql, params = lateral_expr.to_sql()
        
        assert "LATERAL" in sql.upper()
        assert "formatted_alias" in sql
        assert params == ()