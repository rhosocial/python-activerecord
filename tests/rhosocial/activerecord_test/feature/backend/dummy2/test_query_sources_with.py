# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_query_sources_with.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, Subquery, FunctionCall,
    QueryExpression, TableExpression
)
from rhosocial.activerecord.backend.expression.query_sources import (
    CTEExpression, WithQueryExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCTEAndWithQueryExpressions:
    """Tests for CTEExpression and WithQueryExpression with comprehensive parameter support."""

    def test_basic_cte_expression(self, dummy_dialect: DummyDialect):
        """Test basic CTE expression generation."""
        query = Subquery(dummy_dialect, "SELECT id, name FROM users WHERE age > ?", (25,))
        cte = CTEExpression(dummy_dialect, name="adult_users", query=query)
        
        sql, params = cte.to_sql()
        
        # The exact format depends on the dialect's implementation
        assert "adult_users" in sql
        assert params == (25,)

    def test_cte_expression_with_columns(self, dummy_dialect: DummyDialect):
        """Test CTE expression with explicit column names."""
        query = Subquery(dummy_dialect, "SELECT id, name FROM users", ())
        cte = CTEExpression(
            dummy_dialect, 
            name="user_data", 
            query=query, 
            columns=["user_id", "user_name"]
        )
        
        sql, params = cte.to_sql()
        
        assert "user_data" in sql
        assert "user_id" in sql
        assert "user_name" in sql
        assert params == ()

    def test_recursive_cte_expression(self, dummy_dialect: DummyDialect):
        """Test recursive CTE expression."""
        query = Subquery(dummy_dialect, "SELECT id, parent_id FROM tree WHERE parent_id IS NULL UNION ALL SELECT t.id, t.parent_id FROM tree t JOIN tree_cte c ON t.parent_id = c.id", ())
        cte = CTEExpression(
            dummy_dialect,
            name="tree_cte",
            query=query,
            recursive=True
        )
        
        sql, params = cte.to_sql()
        
        assert "RECURSIVE" in sql.upper()
        assert "tree_cte" in sql
        assert params == ()

    def test_cte_expression_with_materialized(self, dummy_dialect: DummyDialect):
        """Test CTE expression with materialization hint."""
        query = Subquery(dummy_dialect, "SELECT * FROM large_table WHERE condition = ?", (True,))
        
        # Test MATERIALIZED
        cte_materialized = CTEExpression(
            dummy_dialect,
            name="cached_data",
            query=query,
            materialized=True
        )
        
        sql_mat, params_mat = cte_materialized.to_sql()
        assert "MATERIALIZED" in sql_mat.upper()
        assert params_mat == (True,)
        
        # Test NOT MATERIALIZED
        cte_not_materialized = CTEExpression(
            dummy_dialect,
            name="non_cached_data",
            query=query,
            materialized=False
        )
        
        sql_not_mat, params_not_mat = cte_not_materialized.to_sql()
        assert "NOT MATERIALIZED" in sql_not_mat.upper()
        assert params_not_mat == (True,)

    def test_cte_expression_with_dialect_options(self, dummy_dialect: DummyDialect):
        """Test CTE expression with dialect-specific options."""
        query = Subquery(dummy_dialect, "SELECT id FROM simple_table", ())
        cte = CTEExpression(
            dummy_dialect,
            name="dialect_specific_cte",
            query=query,
            dialect_options={"some_hint": "value", "optimizer": "advanced"}
        )
        
        sql, params = cte.to_sql()
        
        # The dialect options are passed to the dialect, but the basic SQL should still work
        assert "dialect_specific_cte" in sql
        assert params == ()

    def test_with_query_expression_basic(self, dummy_dialect: DummyDialect):
        """Test basic WithQuery expression with single CTE."""
        cte_query = Subquery(dummy_dialect, "SELECT id, name FROM users WHERE status = ?", ("active",))
        cte = CTEExpression(dummy_dialect, name="active_users", query=cte_query)
        
        main_query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "active_users")
        )
        
        with_query = WithQueryExpression(dummy_dialect, ctes=[cte], main_query=main_query)
        
        sql, params = with_query.to_sql()
        
        assert "WITH" in sql.upper()
        assert "active_users" in sql
        assert params == ("active",)

    def test_with_query_expression_multiple_ctes(self, dummy_dialect: DummyDialect):
        """Test WithQuery expression with multiple CTEs."""
        cte1_query = Subquery(dummy_dialect, "SELECT id, name FROM users WHERE age > ?", (18,))
        cte1 = CTEExpression(dummy_dialect, name="adults", query=cte1_query)
        
        cte2_query = Subquery(dummy_dialect, "SELECT user_id, COUNT(*) as order_count FROM orders GROUP BY user_id", ())
        cte2 = CTEExpression(dummy_dialect, name="user_orders", query=cte2_query)
        
        main_query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "name", table="adults"),
                Column(dummy_dialect, "order_count", table="user_orders")
            ],
            from_=TableExpression(dummy_dialect, "adults")
        )
        
        with_query = WithQueryExpression(dummy_dialect, ctes=[cte1, cte2], main_query=main_query)
        
        sql, params = with_query.to_sql()
        
        assert "WITH" in sql.upper()
        assert "adults" in sql
        assert "user_orders" in sql
        assert params == (18,)

    def test_with_query_expression_with_dialect_options(self, dummy_dialect: DummyDialect):
        """Test WithQuery expression with dialect-specific options."""
        cte_query = Subquery(dummy_dialect, "SELECT id FROM simple_table", ())
        cte = CTEExpression(dummy_dialect, name="simple_cte", query=cte_query)
        
        main_query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "simple_cte")
        )
        
        with_query = WithQueryExpression(
            dummy_dialect, 
            ctes=[cte], 
            main_query=main_query,
            dialect_options={"optimizer": "fast", "cache": "true"}
        )
        
        sql, params = with_query.to_sql()
        
        # The dialect options are passed to the dialect, but the basic SQL should still work
        assert "WITH" in sql.upper()
        assert "simple_cte" in sql
        assert params == ()

    def test_cte_with_complex_query(self, dummy_dialect: DummyDialect):
        """Test CTE with complex query involving multiple clauses."""
        # Create a complex query with various clauses
        from_clause = TableExpression(dummy_dialect, "products")
        
        complex_query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "category"),
                FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")),
                FunctionCall(dummy_dialect, "AVG", Column(dummy_dialect, "price"))
            ],
            from_=from_clause,
            group_by_having=None,  # Will be set properly
        )
        
        # Create the group by having clause
        from rhosocial.activerecord.backend.expression.query_parts import GroupByHavingClause
        group_by_having = GroupByHavingClause(
            dummy_dialect,
            group_by=[Column(dummy_dialect, "category")],
            having=FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")) > Literal(dummy_dialect, 5)
        )
        complex_query.group_by_having = group_by_having  # Set directly since it's not in constructor
        
        cte = CTEExpression(
            dummy_dialect,
            name="popular_categories",
            query=complex_query,
            columns=["category", "count", "avg_price"]
        )
        
        sql, params = cte.to_sql()
        
        assert "popular_categories" in sql
        assert "category" in sql
        assert params == (5,)

    def test_with_query_preserves_params_from_ctes_and_main_query(self, dummy_dialect: DummyDialect):
        """Test that WithQuery properly combines parameters from CTEs and main query."""
        # CTE with parameters
        cte_query = Subquery(dummy_dialect, "SELECT id FROM users WHERE age > ?", (25,))
        cte = CTEExpression(dummy_dialect, name="adults", query=cte_query)
        
        # Main query with parameters
        main_query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "adults"),
            where=None  # Will be set properly
        )
        
        from rhosocial.activerecord.backend.expression.query_parts import WhereClause
        where_clause = WhereClause(
            dummy_dialect,
            condition=Column(dummy_dialect, "id") < Literal(dummy_dialect, 1000)
        )
        main_query.where = where_clause  # Set directly
        
        with_query = WithQueryExpression(dummy_dialect, ctes=[cte], main_query=main_query)
        
        sql, params = with_query.to_sql()
        
        # Should contain parameters from both CTE and main query
        assert 25 in params  # from CTE
        assert 1000 in params  # from main query
        assert len(params) >= 2  # at least both parameters

    def test_cte_expression_parameter_validation(self, dummy_dialect: DummyDialect):
        """Test CTE expression with various parameter combinations."""
        # Test with all parameters set
        query = Subquery(dummy_dialect, "SELECT col1, col2 FROM table WHERE id = ?", (123,))
        cte = CTEExpression(
            dummy_dialect,
            name="test_cte",
            query=query,
            columns=["col1", "col2"],
            recursive=True,
            materialized=False,
            dialect_options={"hint": "value"}
        )
        
        sql, params = cte.to_sql()
        
        assert "test_cte" in sql
        assert "col1" in sql
        assert "RECURSIVE" in sql.upper()
        assert "NOT MATERIALIZED" in sql.upper()
        assert params == (123,)