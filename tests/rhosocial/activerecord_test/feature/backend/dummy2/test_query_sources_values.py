# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_query_sources_values.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, Subquery, QueryExpression, TableExpression
)
from rhosocial.activerecord.backend.expression.query_sources import ValuesExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestValuesExpression:
    """Tests for ValuesExpression representing VALUES clauses as data sources."""

    def test_values_expression_basic(self, dummy_dialect: DummyDialect):
        """Test basic VALUES expression."""
        values_data = [
            (1, "Alice", 25),
            (2, "Bob", 30),
            (3, "Charlie", 35)
        ]
        
        values_expr = ValuesExpression(
            dummy_dialect,
            values=values_data,
            alias="user_data",
            column_names=["id", "name", "age"]
        )
        
        sql, params = values_expr.to_sql()
        
        assert "user_data" in sql
        assert "id" in sql and "name" in sql
        # For dummy dialect, VALUES should contain the parameter placeholders
        assert params == (1, "Alice", 25, 2, "Bob", 30, 3, "Charlie", 35)

    def test_values_expression_single_row(self, dummy_dialect: DummyDialect):
        """Test VALUES expression with single row."""
        values_data = [
            (100, "Test Name", "test@example.com")
        ]
        
        values_expr = ValuesExpression(
            dummy_dialect,
            values=values_data,
            alias="single_row",
            column_names=["id", "name", "email"]
        )
        
        sql, params = values_expr.to_sql()
        
        assert "single_row" in sql
        assert params == (100, "Test Name", "test@example.com")

    def test_values_expression_with_different_types(self, dummy_dialect: DummyDialect):
        """Test VALUES expression with different data types."""
        values_data = [
            (1, "string", 3.14, True, None),
            (2, "another", 2.71, False, "value")
        ]
        
        values_expr = ValuesExpression(
            dummy_dialect,
            values=values_data,
            alias="mixed_types",
            column_names=["id", "text", "float_val", "bool_val", "nullable"]
        )
        
        sql, params = values_expr.to_sql()
        
        assert "mixed_types" in sql
        assert params == (1, "string", 3.14, True, None, 2, "another", 2.71, False, "value")

    def test_values_expression_empty_values(self, dummy_dialect: DummyDialect):
        """Test VALUES expression with empty values list."""
        values_expr = ValuesExpression(
            dummy_dialect,
            values=[],
            alias="empty_values",
            column_names=["id", "name"]
        )
        
        sql, params = values_expr.to_sql()
        
        assert "empty_values" in sql
        assert params == ()

    def test_values_expression_single_column_multiple_rows(self, dummy_dialect: DummyDialect):
        """Test VALUES expression with single column and multiple rows."""
        values_data = [
            ("value1",),
            ("value2",),
            ("value3",)
        ]
        
        values_expr = ValuesExpression(
            dummy_dialect,
            values=values_data,
            alias="single_col",
            column_names=["name"]
        )
        
        sql, params = values_expr.to_sql()
        
        assert "single_col" in sql
        assert params == ("value1", "value2", "value3")

    def test_values_expression_used_in_query_from_clause(self, dummy_dialect: DummyDialect):
        """Test VALUES expression used as FROM clause in a query."""
        values_data = [
            (1, "Product A", 10.99),
            (2, "Product B", 15.99)
        ]
        
        values_expr = ValuesExpression(
            dummy_dialect,
            values=values_data,
            alias="products",
            column_names=["id", "name", "price"]
        )
        
        # Create a query using the VALUES expression as FROM
        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "name", table="products"),
                Column(dummy_dialect, "price", table="products")
            ],
            from_=values_expr  # Using VALUES as data source
        )
        
        sql, params = query.to_sql()
        
        assert "products" in sql
        assert "name" in sql and "price" in sql
        assert params == (1, "Product A", 10.99, 2, "Product B", 15.99)

    def test_values_expression_alias_formatting(self, dummy_dialect: DummyDialect):
        """Test different alias formatting."""
        values_data = [(1, "test")]
        
        values_expr = ValuesExpression(
            dummy_dialect,
            values=values_data,
            alias="test_alias",
            column_names=["id", "name"]
        )
        
        sql, params = values_expr.to_sql()
        
        # Verify the alias is properly formatted
        assert "test_alias" in sql
        assert params == (1, "test")

    def test_values_expression_column_names_formatting(self, dummy_dialect: DummyDialect):
        """Test different column names formatting."""
        values_data = [(1, "Alice")]
        
        values_expr = ValuesExpression(
            dummy_dialect,
            values=values_data,
            alias="users",
            column_names=["user_id", "user_name"]
        )
        
        sql, params = values_expr.to_sql()
        
        assert "user_id" in sql
        assert "user_name" in sql
        assert params == (1, "Alice")

    def test_values_expression_complex_values(self, dummy_dialect: DummyDialect):
        """Test VALUES expression with complex nested data."""
        values_data = [
            (1, ["tag1", "tag2"], {"key": "value"}),
            (2, ["tag3", "tag4"], {"key2": "value2"})
        ]
        
        values_expr = ValuesExpression(
            dummy_dialect,
            values=values_data,
            alias="complex_data",
            column_names=["id", "tags", "metadata"]
        )
        
        sql, params = values_expr.to_sql()
        
        assert "complex_data" in sql
        # The params should contain the complex data as-is
        assert len(params) == 6  # 2 rows * 3 columns
        assert params[0] == 1
        assert params[1] == ["tag1", "tag2"]

    def test_values_expression_large_dataset(self, dummy_dialect: DummyDialect):
        """Test VALUES expression with larger dataset."""
        values_data = [(i, f"name_{i}", i * 10) for i in range(10)]

        values_expr = ValuesExpression(
            dummy_dialect,
            values=values_data,
            alias="large_data",
            column_names=["id", "name", "value"]
        )

        sql, params = values_expr.to_sql()

        assert "large_data" in sql
        # Should have 10 rows * 3 columns = 30 parameters
        assert len(params) == 30
        # Check that first and last values are present
        assert params[0] == 0  # first id
        assert params[-3] == 9  # last id

    def test_values_expression_without_alias(self, dummy_dialect: DummyDialect):
        """Test VALUES expression without alias."""
        values_data = [
            (1, "Alice", 25),
            (2, "Bob", 30)
        ]

        # Create ValuesExpression without alias
        values_expr = ValuesExpression(
            dummy_dialect,
            values=values_data,
            column_names=["id", "name", "age"]
        )

        sql, params = values_expr.to_sql()

        # Verify that no alias is present in the SQL
        assert "AS" not in sql.upper() or "AS " not in sql  # Check that alias is not in SQL
        # Verify column names are still present
        assert "id" in sql and "name" in sql and "age" in sql
        # Verify values are still parameterized
        assert params == (1, "Alice", 25, 2, "Bob", 30)