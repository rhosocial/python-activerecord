# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_core.py
"""
Tests for the core SQL expression components in core.py
"""
import pytest
from rhosocial.activerecord.backend.expression import (
    Literal, Column, FunctionCall, Subquery, TableExpression
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestLiteral:
    """Tests for Literal class."""

    def test_literal_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic Literal functionality - this is common across all versions, so we only test one."""
        literal = Literal(sqlite_dialect_3_8_0, "test_value")
        assert literal.value == "test_value"
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == ("test_value",)

    def test_literal_repr(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Literal repr method."""
        literal = Literal(sqlite_dialect_3_8_0, "test_value")
        assert repr(literal) == "Literal('test_value')"

    def test_literal_none(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Literal with None value."""
        literal = Literal(sqlite_dialect_3_8_0, None)
        assert literal.value is None
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == (None,)

    def test_literal_numeric(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Literal with numeric value."""
        literal = Literal(sqlite_dialect_3_8_0, 42)
        assert literal.value == 42
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == (42,)

    def test_literal_float(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Literal with float value."""
        literal = Literal(sqlite_dialect_3_8_0, 3.14)
        assert literal.value == 3.14
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == (3.14,)

    def test_literal_boolean(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Literal with boolean value."""
        literal = Literal(sqlite_dialect_3_8_0, True)
        assert literal.value is True
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == (True,)


class TestColumn:
    """Tests for Column class."""

    def test_column_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic Column functionality."""
        column = Column(sqlite_dialect_3_8_0, "name")
        assert column.name == "name"
        assert column.table is None
        assert column.alias is None
        sql, params = column.to_sql()
        assert sql == '"name"'
        assert params == ()

    def test_column_with_table(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Column with table specification."""
        column = Column(sqlite_dialect_3_8_0, "name", table="users")
        assert column.name == "name"
        assert column.table == "users"
        sql, params = column.to_sql()
        assert sql == '"users"."name"'
        assert params == ()

    def test_column_with_alias(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Column with alias."""
        column = Column(sqlite_dialect_3_8_0, "name", alias="user_name")
        assert column.name == "name"
        assert column.alias == "user_name"
        sql, params = column.to_sql()
        assert sql == '"name" AS "user_name"'
        assert params == ()

    def test_column_with_table_and_alias(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Column with both table and alias."""
        column = Column(sqlite_dialect_3_8_0, "name", table="users", alias="user_name")
        assert column.name == "name"
        assert column.table == "users"
        assert column.alias == "user_name"
        sql, params = column.to_sql()
        assert sql == '"users"."name" AS "user_name"'
        assert params == ()


class TestTableExpression:
    """Tests for TableExpression class."""

    def test_table_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic TableExpression functionality."""
        table = TableExpression(sqlite_dialect_3_8_0, "users")
        assert table.name == "users"
        assert table.alias is None
        sql, params = table.to_sql()
        assert sql == '"users"'
        assert params == ()

    def test_table_with_alias(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test TableExpression with alias."""
        table = TableExpression(sqlite_dialect_3_8_0, "users", alias="u")
        assert table.name == "users"
        assert table.alias == "u"
        sql, params = table.to_sql()
        assert sql == '"users" AS "u"'
        assert params == ()


class TestFunctionCall:
    """Tests for FunctionCall class."""

    def test_function_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic FunctionCall functionality."""
        func = FunctionCall(sqlite_dialect_3_8_0, "COUNT", Column(sqlite_dialect_3_8_0, "id"))
        sql, params = func.to_sql()
        assert sql == 'COUNT("id")'
        assert params == ()

    def test_function_with_alias(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test FunctionCall with alias."""
        func = FunctionCall(sqlite_dialect_3_8_0, "COUNT", Column(sqlite_dialect_3_8_0, "id"), alias="total")
        sql, params = func.to_sql()
        assert sql == 'COUNT("id") AS "total"'
        assert params == ()

    def test_function_with_distinct(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test FunctionCall with DISTINCT flag."""
        func = FunctionCall(sqlite_dialect_3_8_0, "COUNT", Column(sqlite_dialect_3_8_0, "id"), is_distinct=True)
        sql, params = func.to_sql()
        assert sql == 'COUNT(DISTINCT "id")'
        assert params == ()

    def test_function_multiple_args(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test FunctionCall with multiple arguments."""
        func = FunctionCall(
            sqlite_dialect_3_8_0,
            "CONCAT",
            Column(sqlite_dialect_3_8_0, "first_name"),
            Literal(sqlite_dialect_3_8_0, " "),
            Column(sqlite_dialect_3_8_0, "last_name")
        )
        sql, params = func.to_sql()
        assert sql == 'CONCAT("first_name", ?, "last_name")'
        assert params == (" ",)


class TestSubquery:
    """Tests for Subquery class."""

    def test_subquery_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic Subquery functionality."""
        subquery = Subquery(
            sqlite_dialect_3_8_0,
            "SELECT id FROM users WHERE active = ?",
            (True,)
        )
        sql, params = subquery.to_sql()
        assert sql == "(SELECT id FROM users WHERE active = ?)"
        assert params == (True,)

    def test_subquery_with_alias(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Subquery with alias."""
        subquery = Subquery(
            sqlite_dialect_3_8_0,
            "SELECT id FROM users WHERE active = ?",
            (True,),
            alias="active_users"
        )
        sql, params = subquery.to_sql()
        assert sql == "(SELECT id FROM users WHERE active = ?) AS \"active_users\""
        assert params == (True,)


class TestVersionSpecificFeatures:
    """Tests for version-specific features that should only be tested on appropriate versions."""

    def test_cte_support_3_8_3(self, sqlite_dialect_3_8_3: SQLiteDialect):
        """Test that CTE is supported from version 3.8.3."""
        assert sqlite_dialect_3_8_3.supports_basic_cte() is True
        assert sqlite_dialect_3_8_3.supports_recursive_cte() is True

    def test_cte_not_supported_3_8_0(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that CTE is not supported in version 3.8.0."""
        # CTE support starts from version 3.8.3, so 3.8.0 should not support it
        assert sqlite_dialect_3_8_0.supports_basic_cte() is False

    def test_window_functions_3_25_0(self, sqlite_dialect_3_25_0: SQLiteDialect):
        """Test that window functions are supported from version 3.25.0."""
        assert sqlite_dialect_3_25_0.supports_window_functions() is True
        assert sqlite_dialect_3_25_0.supports_window_frame_clause() is True

    def test_returning_clause_3_35_0(self, sqlite_dialect_3_35_0: SQLiteDialect):
        """Test that RETURNING clause is supported from version 3.35.0."""
        assert sqlite_dialect_3_35_0.supports_returning_clause() is True

    def test_json_support_3_38_0(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test that JSON functions are supported from version 3.38.0."""
        assert sqlite_dialect_3_38_0.supports_json_type() is True
        assert sqlite_dialect_3_38_0.get_json_access_operator() == "->"

    def test_filter_clause_3_30_0(self, sqlite_dialect_3_30_0: SQLiteDialect):
        """Test that FILTER clause is supported from version 3.30.0."""
        assert sqlite_dialect_3_30_0.supports_filter_clause() is True