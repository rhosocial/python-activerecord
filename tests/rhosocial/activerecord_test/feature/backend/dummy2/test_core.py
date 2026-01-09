# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_core.py
"""
Tests for the core SQL expression components in core.py
"""
import pytest
from rhosocial.activerecord.backend.expression import (
    Literal, Column, FunctionCall, Subquery, TableExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestLiteral:
    """Tests for Literal class."""

    def test_literal_basic(self, dummy_dialect: DummyDialect):
        """Test basic Literal functionality."""
        literal = Literal(dummy_dialect, "test_value")
        assert literal.value == "test_value"
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == ("test_value",)

    def test_literal_repr(self, dummy_dialect: DummyDialect):
        """Test Literal repr method."""
        literal = Literal(dummy_dialect, "test_value")
        assert repr(literal) == "Literal('test_value')"

    def test_literal_numeric_values(self, dummy_dialect: DummyDialect):
        """Test Literal with numeric values."""
        for value in [42, 3.14, -5]:
            literal = Literal(dummy_dialect, value)
            sql, params = literal.to_sql()
            assert sql == "?"
            assert params == (value,)

    def test_literal_none_value(self, dummy_dialect: DummyDialect):
        """Test Literal with None value."""
        literal = Literal(dummy_dialect, None)
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == (None,)


class TestColumn:
    """Tests for Column class."""

    def test_column_basic(self, dummy_dialect: DummyDialect):
        """Test basic Column functionality."""
        col = Column(dummy_dialect, "name")
        assert col.name == "name"
        assert col.table is None
        assert col.alias is None
        sql, params = col.to_sql()
        assert '"name"' in sql

    def test_column_with_table(self, dummy_dialect: DummyDialect):
        """Test Column with table specification."""
        col = Column(dummy_dialect, "name", table="users")
        assert col.name == "name"
        assert col.table == "users"
        sql, params = col.to_sql()
        assert '"users"."name"' in sql

    def test_column_with_alias(self, dummy_dialect: DummyDialect):
        """Test Column with alias."""
        col = Column(dummy_dialect, "name", alias="n")
        assert col.name == "name"
        assert col.alias == "n"
        sql, params = col.to_sql()
        assert "AS" in sql

    def test_column_with_table_and_alias(self, dummy_dialect: DummyDialect):
        """Test Column with both table and alias."""
        col = Column(dummy_dialect, "name", table="users", alias="n")
        sql, params = col.to_sql()
        assert '"users"."name"' in sql
        assert "AS" in sql
        assert '"n"' in sql


class TestFunctionCall:
    """Tests for FunctionCall class."""

    def test_function_call_basic(self, dummy_dialect: DummyDialect):
        """Test basic FunctionCall functionality."""
        func = FunctionCall(dummy_dialect, "UPPER", Column(dummy_dialect, "name"))
        sql, params = func.to_sql()
        assert "UPPER(" in sql
        assert '"name"' in sql

    def test_function_call_with_multiple_args(self, dummy_dialect: DummyDialect):
        """Test FunctionCall with multiple arguments."""
        func = FunctionCall(
            dummy_dialect, 
            "CONCAT", 
            Column(dummy_dialect, "first_name"), 
            Literal(dummy_dialect, " "), 
            Column(dummy_dialect, "last_name")
        )
        sql, params = func.to_sql()
        assert "CONCAT(" in sql
        assert params == (" ",)

    def test_function_call_with_distinct(self, dummy_dialect: DummyDialect):
        """Test FunctionCall with DISTINCT keyword."""
        func = FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id"), is_distinct=True)
        sql, params = func.to_sql()
        assert "DISTINCT" in sql

    def test_function_call_with_alias(self, dummy_dialect: DummyDialect):
        """Test FunctionCall with alias."""
        func = FunctionCall(dummy_dialect, "SUM", Column(dummy_dialect, "amount"), alias="total")
        sql, params = func.to_sql()
        assert "AS" in sql
        assert "total" in sql

    def test_function_call_no_args(self, dummy_dialect: DummyDialect):
        """Test FunctionCall with no arguments."""
        func = FunctionCall(dummy_dialect, "NOW")
        sql, params = func.to_sql()
        assert "NOW()" in sql


class TestSubquery:
    """Tests for Subquery class."""

    def test_subquery_basic(self, dummy_dialect: DummyDialect):
        """Test basic Subquery functionality."""
        subquery = Subquery(dummy_dialect, "SELECT id FROM users WHERE age > ?", (25,))
        sql, params = subquery.to_sql()
        assert sql == "(SELECT id FROM users WHERE age > ?)"
        assert params == (25,)

    def test_subquery_with_alias(self, dummy_dialect: DummyDialect):
        """Test Subquery with alias - this covers the missing branch."""
        subquery = Subquery(dummy_dialect, "SELECT id FROM users", (), alias="user_subq")
        sql, params = subquery.to_sql()
        # This should call dialect.format_subquery which is tested in dialect-specific tests
        # Just verify the structure is correct
        assert "(" in sql
        assert "SELECT id FROM users" in sql

    def test_subquery_from_string(self, dummy_dialect: DummyDialect):
        """Test Subquery initialization with string input."""
        subquery = Subquery(dummy_dialect, "SELECT * FROM products WHERE price > ?", (100,))
        sql, params = subquery.to_sql()
        assert sql == '(SELECT * FROM products WHERE price > ?)'
        assert params == (100,)

    def test_subquery_from_existing_subquery(self, dummy_dialect: DummyDialect):
        """Test Subquery initialization with existing Subquery object."""
        original_subquery = Subquery(dummy_dialect, "SELECT id FROM users WHERE active = ?", (True,), alias="active_users")
        new_subquery = Subquery(dummy_dialect, original_subquery)
        sql, params = new_subquery.to_sql()
        assert sql == '(SELECT id FROM users WHERE active = ?) AS "active_users"'
        assert params == (True,)

    def test_subquery_from_base_expression(self, dummy_dialect: DummyDialect):
        """Test Subquery initialization with BaseExpression (has to_sql method)."""
        from rhosocial.activerecord.backend.expression.statements import QueryExpression
        from rhosocial.activerecord.backend.expression.query_parts import WhereClause

        # Create a simple query expression to use as base expression
        query_expr = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "orders"),
            where=WhereClause(dummy_dialect, condition=Column(dummy_dialect, "status") == Literal(dummy_dialect, "pending"))
        )

        subquery = Subquery(dummy_dialect, query_expr)
        sql, params = subquery.to_sql()
        assert sql == '(SELECT "id" FROM "orders" WHERE "status" = ?)'
        assert params == ("pending",)

    def test_subquery_from_non_expression_object(self, dummy_dialect: DummyDialect):
        """Test Subquery initialization with non-expression object (defaults to string conversion)."""
        # Use an arbitrary object that doesn't have to_sql method
        class CustomObject:
            def __str__(self):
                return "CUSTOM SQL STRING"

        obj = CustomObject()
        subquery = Subquery(dummy_dialect, obj)
        sql, params = subquery.to_sql()
        assert sql == '(CUSTOM SQL STRING)'
        assert params == ()

    def test_subquery_from_sql_query_and_params_tuple(self, dummy_dialect: DummyDialect):
        """Test Subquery initialization with SQLQueryAndParams tuple (str, tuple) - covers the missing branch."""
        # This tests the elif bases.is_sql_query_and_params(query): branch
        query_tuple = ("SELECT id FROM users WHERE age > ?", (25,))
        subquery = Subquery(dummy_dialect, query_tuple)
        sql, params = subquery.to_sql()
        assert sql == "(SELECT id FROM users WHERE age > ?)"
        assert params == (25,)

    def test_subquery_from_sql_query_and_params_tuple_with_none_params(self, dummy_dialect: DummyDialect):
        """Test Subquery initialization with SQLQueryAndParams tuple where params is None."""
        # This simulates a case where the second element of the tuple is None
        # Though in practice, SQLQueryAndParams expects a tuple, not None
        # We'll test the branch by directly checking the is_sql_query_and_params function
        from rhosocial.activerecord.backend.expression.bases import is_sql_query_and_params

        # Verify that is_sql_query_and_params correctly identifies the tuple format
        valid_tuple = ("SELECT * FROM table", (1, 2, 3))
        assert is_sql_query_and_params(valid_tuple) is True

        # Test with a tuple that has None as second element (this should return True now)
        valid_tuple_with_none = ("SELECT * FROM table", None)
        assert is_sql_query_and_params(valid_tuple_with_none) is True

        # Test with a tuple that has wrong length (this should return False)
        invalid_tuple_length = ("SELECT * FROM table", (1,), "extra")
        assert is_sql_query_and_params(invalid_tuple_length) is False

        # Test with a tuple that has non-string first element (this should return False)
        invalid_tuple_first = (123, (1, 2, 3))
        assert is_sql_query_and_params(invalid_tuple_first) is False

        # Test with a tuple that has non-tuple second element (this should return False)
        invalid_tuple_second = ("SELECT * FROM table", [1, 2, 3])
        assert is_sql_query_and_params(invalid_tuple_second) is False

    def test_subquery_from_sql_query_and_params_tuple_with_none_as_params(self, dummy_dialect: DummyDialect):
        """Test Subquery initialization with SQLQueryAndParams tuple where params is None."""
        # This tests how Subquery handles (str, None) tuples
        query_tuple = ("SELECT id FROM users WHERE active = ?", None)
        subquery = Subquery(dummy_dialect, query_tuple)
        sql, params = subquery.to_sql()
        assert sql == "(SELECT id FROM users WHERE active = ?)"
        # When params is None, it should be converted to an empty tuple
        assert params == ()


class TestTableExpression:
    """Tests for TableExpression class."""

    def test_table_expression_basic(self, dummy_dialect: DummyDialect):
        """Test basic TableExpression functionality."""
        table = TableExpression(dummy_dialect, "users")
        sql, params = table.to_sql()
        assert '"users"' in sql

    def test_table_expression_with_alias(self, dummy_dialect: DummyDialect):
        """Test TableExpression with alias."""
        table = TableExpression(dummy_dialect, "users", alias="u")
        sql, params = table.to_sql()
        assert '"users"' in sql
        assert "AS" in sql
        assert '"u"' in sql

    def test_table_expression_with_temporal_options(self, dummy_dialect: DummyDialect):
        """Test TableExpression with temporal options - this covers the missing branch."""
        temporal_opts = {"as_of": "2023-01-01", "for_system_time": "AS OF"}
        table = TableExpression(dummy_dialect, "users", alias="u", temporal_options=temporal_opts)
        sql, params = table.to_sql()
        # This should call dialect.format_temporal_options
        # The exact output depends on the dialect implementation
        assert '"users"' in sql

    def test_table_expression_empty_temporal_options(self, dummy_dialect: DummyDialect):
        """Test TableExpression with empty temporal options."""
        table = TableExpression(dummy_dialect, "users", temporal_options={})
        sql, params = table.to_sql()
        assert '"users"' in sql
        # Should not call format_temporal_options since dict is empty

    def test_table_expression_with_temporal_options_that_returns_none(self, dummy_dialect: DummyDialect):
        """Test TableExpression with temporal options when dialect returns None from format_temporal_options."""
        # Mock the dialect's format_temporal_options to return None
        original_method = dummy_dialect.format_temporal_options
        def mock_format_temporal_options(options):
            return None
        dummy_dialect.format_temporal_options = mock_format_temporal_options

        temporal_opts = {"as_of": "2023-01-01"}
        table = TableExpression(dummy_dialect, "users", alias="u", temporal_options=temporal_opts)
        sql, params = table.to_sql()

        # Restore original method
        dummy_dialect.format_temporal_options = original_method

        # Should still work but not include temporal options since dialect returned None
        assert '"users"' in sql

    def test_format_join_expression_without_condition_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that format_join_expression raises ValueError for join types that require conditions."""
        from rhosocial.activerecord.backend.expression.query_parts import JoinExpression
        from rhosocial.activerecord.backend.expression.core import TableExpression

        # Create a JoinExpression without using or condition (should raise error for non-CROSS joins)
        left_table = TableExpression(dummy_dialect, "users")
        right_table = TableExpression(dummy_dialect, "orders")

        join_expr = JoinExpression(
            dummy_dialect,
            left_table=left_table,
            right_table=right_table,
            join_type="INNER JOIN",  # INNER JOIN requires a condition
            condition=None,  # No condition provided
            using=None  # No USING clause provided
        )

        with pytest.raises(ValueError, match=r"INNER JOIN requires a condition or USING clause."):
            dummy_dialect.format_join_expression(join_expr)

    def test_format_join_expression_with_cross_join_without_condition_succeeds(self, dummy_dialect: DummyDialect):
        """Tests that format_join_expression works for CROSS JOIN without condition."""
        from rhosocial.activerecord.backend.expression.query_parts import JoinExpression
        from rhosocial.activerecord.backend.expression.core import TableExpression

        # Create a JoinExpression for CROSS JOIN (doesn't require a condition)
        left_table = TableExpression(dummy_dialect, "users")
        right_table = TableExpression(dummy_dialect, "orders")

        join_expr = JoinExpression(
            dummy_dialect,
            left_table=left_table,
            right_table=right_table,
            join_type="CROSS JOIN",  # CROSS JOIN doesn't require a condition
            condition=None,  # No condition provided
            using=None  # No USING clause provided
        )

        sql, params = dummy_dialect.format_join_expression(join_expr)

        assert "CROSS JOIN" in sql
        assert '"users"' in sql
        assert '"orders"' in sql
        assert params == ()

    def test_format_temporal_options_with_empty_options_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that format_temporal_options raises ValueError when called with empty options."""
        with pytest.raises(ValueError, match=r"Temporal options cannot be empty. If no temporal options are needed, don't call format_temporal_options."):
            dummy_dialect.format_temporal_options({})