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

    def test_literal_basic(self, sqlite_dialect: SQLiteDialect):
        """Test basic Literal functionality."""
        literal = Literal(sqlite_dialect, "test_value")
        assert literal.value == "test_value"
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == ("test_value",)

    def test_literal_repr(self, sqlite_dialect: SQLiteDialect):
        """Test Literal repr method."""
        literal = Literal(sqlite_dialect, "test_value")
        assert repr(literal) == "Literal('test_value')"

    def test_literal_none(self, sqlite_dialect: SQLiteDialect):
        """Test Literal with None value."""
        literal = Literal(sqlite_dialect, None)
        assert literal.value is None
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == (None,)

    def test_literal_numeric(self, sqlite_dialect: SQLiteDialect):
        """Test Literal with numeric value."""
        literal = Literal(sqlite_dialect, 42)
        assert literal.value == 42
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == (42,)

    def test_literal_float(self, sqlite_dialect: SQLiteDialect):
        """Test Literal with float value."""
        literal = Literal(sqlite_dialect, 3.14)
        assert literal.value == 3.14
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == (3.14,)

    def test_literal_boolean(self, sqlite_dialect: SQLiteDialect):
        """Test Literal with boolean value."""
        literal = Literal(sqlite_dialect, True)
        assert literal.value is True
        sql, params = literal.to_sql()
        assert sql == "?"
        assert params == (True,)


class TestColumn:
    """Tests for Column class."""

    def test_column_basic(self, sqlite_dialect: SQLiteDialect):
        """Test basic Column functionality."""
        column = Column(sqlite_dialect, "name")
        assert column.name == "name"
        assert column.table is None
        assert column.alias is None
        sql, params = column.to_sql()
        assert sql == '"name"'
        assert params == ()

    def test_column_with_table(self, sqlite_dialect: SQLiteDialect):
        """Test Column with table specification."""
        column = Column(sqlite_dialect, "name", table="users")
        assert column.name == "name"
        assert column.table == "users"
        sql, params = column.to_sql()
        assert sql == '"users"."name"'
        assert params == ()

    def test_column_with_alias(self, sqlite_dialect: SQLiteDialect):
        """Test Column with alias."""
        column = Column(sqlite_dialect, "name", alias="user_name")
        assert column.name == "name"
        assert column.alias == "user_name"
        sql, params = column.to_sql()
        assert sql == '"name" AS "user_name"'
        assert params == ()

    def test_column_with_table_and_alias(self, sqlite_dialect: SQLiteDialect):
        """Test Column with both table and alias."""
        column = Column(sqlite_dialect, "name", table="users", alias="user_name")
        assert column.name == "name"
        assert column.table == "users"
        assert column.alias == "user_name"
        sql, params = column.to_sql()
        assert sql == '"users"."name" AS "user_name"'
        assert params == ()


class TestTableExpression:
    """Tests for TableExpression class."""

    def test_table_basic(self, sqlite_dialect: SQLiteDialect):
        """Test basic TableExpression functionality."""
        table = TableExpression(sqlite_dialect, "users")
        assert table.name == "users"
        assert table.alias is None
        sql, params = table.to_sql()
        assert sql == '"users"'
        assert params == ()

    def test_table_with_alias(self, sqlite_dialect: SQLiteDialect):
        """Test TableExpression with alias."""
        table = TableExpression(sqlite_dialect, "users", alias="u")
        assert table.name == "users"
        assert table.alias == "u"
        sql, params = table.to_sql()
        assert sql == '"users" AS "u"'
        assert params == ()


class TestFunctionCall:
    """Tests for FunctionCall class."""

    def test_function_basic(self, sqlite_dialect: SQLiteDialect):
        """Test basic FunctionCall functionality."""
        func = FunctionCall(sqlite_dialect, "COUNT", Column(sqlite_dialect, "id"))
        sql, params = func.to_sql()
        assert sql == 'COUNT("id")'
        assert params == ()

    def test_function_with_alias(self, sqlite_dialect: SQLiteDialect):
        """Test FunctionCall with alias."""
        func = FunctionCall(sqlite_dialect, "COUNT", Column(sqlite_dialect, "id"), alias="total")
        sql, params = func.to_sql()
        assert sql == 'COUNT("id") AS "total"'
        assert params == ()

    def test_function_with_distinct(self, sqlite_dialect: SQLiteDialect):
        """Test FunctionCall with DISTINCT flag."""
        func = FunctionCall(sqlite_dialect, "COUNT", Column(sqlite_dialect, "id"), is_distinct=True)
        sql, params = func.to_sql()
        assert sql == 'COUNT(DISTINCT "id")'
        assert params == ()

    def test_function_multiple_args(self, sqlite_dialect: SQLiteDialect):
        """Test FunctionCall with multiple arguments."""
        func = FunctionCall(
            sqlite_dialect,
            "CONCAT",
            Column(sqlite_dialect, "first_name"),
            Literal(sqlite_dialect, " "),
            Column(sqlite_dialect, "last_name")
        )
        sql, params = func.to_sql()
        assert sql == 'CONCAT("first_name", ?, "last_name")'
        assert params == (" ",)


class TestSubquery:
    """Tests for Subquery class."""

    def test_subquery_basic(self, sqlite_dialect: SQLiteDialect):
        """Test basic Subquery functionality."""
        subquery = Subquery(
            sqlite_dialect,
            "SELECT id FROM users WHERE active = ?",
            (True,)
        )
        sql, params = subquery.to_sql()
        assert sql == "(SELECT id FROM users WHERE active = ?)"
        assert params == (True,)

    def test_subquery_with_alias(self, sqlite_dialect: SQLiteDialect):
        """Test Subquery with alias."""
        subquery = Subquery(
            sqlite_dialect,
            "SELECT id FROM users WHERE active = ?",
            (True,),
            alias="active_users"
        )
        sql, params = subquery.to_sql()
        assert sql == "(SELECT id FROM users WHERE active = ?) AS \"active_users\""
        assert params == (True,)