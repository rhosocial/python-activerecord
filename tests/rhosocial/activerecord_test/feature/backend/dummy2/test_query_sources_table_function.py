# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_query_sources_table_function.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall, Subquery
)
from rhosocial.activerecord.backend.expression.query_sources import TableFunctionExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestTableFunctionExpression:
    """Tests for TableFunctionExpression representing table-valued functions."""

    def test_table_function_basic(self, dummy_dialect: DummyDialect):
        """Test basic table function expression."""
        arg1 = Literal(dummy_dialect, "input_data")
        arg2 = Literal(dummy_dialect, 42)
        
        table_func = TableFunctionExpression(
            dummy_dialect,
            "UNNEST",
            arg1,
            arg2,
            alias="unnested_data"
        )
        
        sql, params = table_func.to_sql()
        
        assert "UNNEST" in sql.upper()
        assert "unnested_data" in sql
        assert params == ("input_data", 42)

    def test_table_function_with_column_names(self, dummy_dialect: DummyDialect):
        """Test table function with specified column names."""
        arg = Literal(dummy_dialect, ["a", "b", "c"])
        
        table_func = TableFunctionExpression(
            dummy_dialect,
            "UNNEST",
            arg,
            alias="array_data",
            column_names=["value", "index"]
        )
        
        sql, params = table_func.to_sql()
        
        assert "UNNEST" in sql.upper()
        assert "array_data" in sql
        assert "value" in sql or "index" in sql
        assert params == (["a", "b", "c"],)

    def test_table_function_with_multiple_args(self, dummy_dialect: DummyDialect):
        """Test table function with multiple arguments."""
        arg1 = Literal(dummy_dialect, "data1")
        arg2 = Literal(dummy_dialect, "data2")
        arg3 = Literal(dummy_dialect, 100)
        
        table_func = TableFunctionExpression(
            dummy_dialect,
            "SOME_TABLE_FUNCTION",
            arg1,
            arg2,
            arg3,
            alias="multi_arg_result"
        )
        
        sql, params = table_func.to_sql()
        
        assert "SOME_TABLE_FUNCTION" in sql.upper()
        assert "multi_arg_result" in sql
        assert params == ("data1", "data2", 100)

    def test_table_function_with_function_call_argument(self, dummy_dialect: DummyDialect):
        """Test table function with function call as argument."""
        func_arg = FunctionCall(dummy_dialect, "ARRAY_AGG", Column(dummy_dialect, "column_name"))
        
        table_func = TableFunctionExpression(
            dummy_dialect,
            "UNNEST",
            func_arg,
            alias="func_result"
        )
        
        sql, params = table_func.to_sql()
        
        assert "UNNEST" in sql.upper()
        assert "func_result" in sql

    def test_table_function_with_subquery_argument(self, dummy_dialect: DummyDialect):
        """Test table function with subquery as argument."""
        subquery = Subquery(dummy_dialect, "SELECT array_column FROM some_table WHERE id = ?", (123,))
        
        table_func = TableFunctionExpression(
            dummy_dialect,
            "JSON_TABLE",
            subquery,
            alias="json_result"
        )
        
        sql, params = table_func.to_sql()
        
        assert "JSON_TABLE" in sql.upper()
        assert "json_result" in sql
        assert params == (123,)

    def test_table_function_in_query_context(self, dummy_dialect: DummyDialect):
        """Test table function used in a query FROM clause."""
        from rhosocial.activerecord.backend.expression import QueryExpression
        
        arg = Literal(dummy_dialect, ["item1", "item2", "item3"])
        
        table_func = TableFunctionExpression(
            dummy_dialect,
            "UNNEST",
            arg,
            alias="items",
            column_names=["item_value"]
        )
        
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "item_value", table="items")],
            from_=table_func
        )
        
        sql, params = query.to_sql()
        
        assert "UNNEST" in sql.upper()
        assert "items" in sql
        assert "item_value" in sql
        assert params == (["item1", "item2", "item3"],)

    def test_table_function_various_function_names(self, dummy_dialect: DummyDialect):
        """Test different table function names."""
        functions_to_test = [
            "UNNEST",
            "JSON_TABLE", 
            "GENERATE_SERIES",
            "REGEXP_EXTRACT_ALL"
        ]
        
        for func_name in functions_to_test:
            arg = Literal(dummy_dialect, "test_data")
            
            table_func = TableFunctionExpression(
                dummy_dialect,
                func_name,
                arg,
                alias="test_alias"
            )
            
            sql, params = table_func.to_sql()
            
            assert func_name in sql.upper()
            assert "test_alias" in sql
            assert params == ("test_data",)

    def test_table_function_no_column_names(self, dummy_dialect: DummyDialect):
        """Test table function without specified column names."""
        arg = Literal(dummy_dialect, [1, 2, 3])
        
        table_func = TableFunctionExpression(
            dummy_dialect,
            "UNNEST",
            arg,
            alias="unnest_result"
        )
        
        sql, params = table_func.to_sql()
        
        assert "UNNEST" in sql.upper()
        assert "unnest_result" in sql
        assert params == ([1, 2, 3],)

    def test_table_function_empty_args(self, dummy_dialect: DummyDialect):
        """Test table function with no arguments."""
        table_func = TableFunctionExpression(
            dummy_dialect,
            "GENERATE_SERIES",  # This function might not need args in some contexts
            alias="empty_args_result"
        )
        
        sql, params = table_func.to_sql()
        
        assert "GENERATE_SERIES" in sql.upper()
        assert "empty_args_result" in sql
        assert params == ()

    def test_table_function_complex_arguments(self, dummy_dialect: DummyDialect):
        """Test table function with complex nested arguments."""
        # Create a function call as argument
        inner_func = FunctionCall(dummy_dialect, "ARRAY_CONSTRUCT", Literal(dummy_dialect, "a"), Literal(dummy_dialect, "b"))

        table_func = TableFunctionExpression(
            dummy_dialect,
            "FLATTEN",
            inner_func,
            alias="complex_result",
            column_names=["path", "value", "type"]
        )

        sql, params = table_func.to_sql()

        assert "FLATTEN" in sql.upper()
        assert "complex_result" in sql
        # May contain references to the inner function
        assert params == ("a", "b")

    def test_table_function_without_alias(self, dummy_dialect: DummyDialect):
        """Test table function expression without alias."""
        arg1 = Literal(dummy_dialect, "input_data")
        arg2 = Literal(dummy_dialect, 42)

        # Create TableFunctionExpression without alias
        table_func = TableFunctionExpression(
            dummy_dialect,
            "UNNEST",
            arg1,
            arg2,
            column_names=["value", "number"]
        )

        sql, params = table_func.to_sql()

        # Verify that no alias is present in the SQL
        assert "AS" not in sql.upper() or "AS " not in sql  # Check that alias is not in SQL
        # Verify function name is still present
        assert "UNNEST" in sql.upper()
        # Verify column names are still present
        assert "value" in sql and "number" in sql
        # Verify values are still parameterized
        assert params == ("input_data", 42)