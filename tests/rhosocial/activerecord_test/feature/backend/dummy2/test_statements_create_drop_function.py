# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_create_drop_function.py
import pytest
from rhosocial.activerecord.backend.expression.statements import (
    CreateFunctionExpression, DropFunctionExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCreateFunctionStatements:
    """Tests for CREATE FUNCTION statements."""

    def test_basic_create_function(self, dummy_dialect: DummyDialect):
        """Tests basic CREATE FUNCTION."""
        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="calculate_total"
        )
        sql, params = create_func.to_sql()

        assert "CREATE FUNCTION" in sql
        assert '"calculate_total"' in sql
        assert "()" in sql
        assert params == ()

    def test_create_function_with_parameters(self, dummy_dialect: DummyDialect):
        """Tests CREATE FUNCTION with parameters."""
        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="calculate_total",
            parameters=[
                {"name": "price", "type": "DECIMAL(10,2)"},
                {"name": "quantity", "type": "INTEGER"}
            ]
        )
        sql, params = create_func.to_sql()

        assert "price" in sql
        assert "DECIMAL(10,2)" in sql
        assert "quantity" in sql
        assert "INTEGER" in sql
        assert params == ()

    def test_create_function_with_returns(self, dummy_dialect: DummyDialect):
        """Tests CREATE FUNCTION with RETURN clause."""
        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="get_user_count",
            returns="INTEGER"
        )
        sql, params = create_func.to_sql()

        assert "RETURNS INTEGER" in sql
        assert params == ()

    def test_create_function_with_language(self, dummy_dialect: DummyDialect):
        """Tests CREATE FUNCTION with LANGUAGE clause."""
        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="plpgsql_function",
            language="plpgsql"
        )
        sql, params = create_func.to_sql()

        assert "LANGUAGE plpgsql" in sql

    def test_create_function_with_body(self, dummy_dialect: DummyDialect):
        """Tests CREATE FUNCTION with body."""
        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="add_numbers",
            parameters=[
                {"name": "a", "type": "INTEGER"},
                {"name": "b", "type": "INTEGER"}
            ],
            returns="INTEGER",
            body="RETURN a + b;"
        )
        sql, params = create_func.to_sql()

        assert "AS" in sql
        assert "$$RETURN a + b;$$" in sql

    def test_create_function_or_replace(self, dummy_dialect: DummyDialect):
        """Tests CREATE OR REPLACE FUNCTION."""
        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="existing_function",
            or_replace=True
        )
        sql, params = create_func.to_sql()

        assert "OR REPLACE" in sql


class TestDropFunctionStatements:
    """Tests for DROP FUNCTION statements."""

    def test_basic_drop_function(self, dummy_dialect: DummyDialect):
        """Tests basic DROP FUNCTION."""
        drop_func = DropFunctionExpression(
            dummy_dialect,
            function_name="old_function"
        )
        sql, params = drop_func.to_sql()

        assert sql == 'DROP FUNCTION "old_function"'
        assert params == ()

    def test_drop_function_if_exists(self, dummy_dialect: DummyDialect):
        """Tests DROP FUNCTION IF EXISTS."""
        drop_func = DropFunctionExpression(
            dummy_dialect,
            function_name="maybe_exists",
            if_exists=True
        )
        sql, params = drop_func.to_sql()

        assert "IF EXISTS" in sql
        assert '"maybe_exists"' in sql

    def test_drop_function_with_parameters(self, dummy_dialect: DummyDialect):
        """Tests DROP FUNCTION with parameter types."""
        drop_func = DropFunctionExpression(
            dummy_dialect,
            function_name="calculate_total",
            parameters=["INTEGER", "INTEGER"]
        )
        sql, params = drop_func.to_sql()

        assert "INTEGER, INTEGER" in sql

    def test_drop_function_with_cascade(self, dummy_dialect: DummyDialect):
        """Tests DROP FUNCTION with CASCADE."""
        drop_func = DropFunctionExpression(
            dummy_dialect,
            function_name="dependent_function",
            cascade=True
        )
        sql, params = drop_func.to_sql()

        assert "CASCADE" in sql
