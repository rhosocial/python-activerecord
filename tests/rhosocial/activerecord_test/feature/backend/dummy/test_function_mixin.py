# tests/rhosocial/activerecord_test/feature/backend/dummy/test_function_mixin.py
"""Tests for FunctionMixin format methods."""
import pytest
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestFunctionMixinFormatMethods:
    """Tests for FunctionMixin format_create/drop_function_statement methods."""

    def test_format_create_function_basic(self, dummy_dialect: DummyDialect):
        """Tests format_create_function_statement basic case."""
        from rhosocial.activerecord.backend.expression.statements import CreateFunctionExpression

        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="calculate_total"
        )
        sql, params = dummy_dialect.format_create_function_statement(create_func)

        assert 'CREATE FUNCTION' in sql
        assert '"calculate_total"' in sql
        assert '()' in sql
        assert params == ()

    def test_format_create_function_with_parameters(self, dummy_dialect: DummyDialect):
        """Tests format_create_function_statement with parameters."""
        from rhosocial.activerecord.backend.expression.statements import CreateFunctionExpression

        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="add_numbers",
            parameters=[
                {"name": "a", "type": "INTEGER"},
                {"name": "b", "type": "INTEGER"}
            ]
        )
        sql, params = dummy_dialect.format_create_function_statement(create_func)

        assert 'CREATE FUNCTION' in sql
        assert '"add_numbers"' in sql
        assert 'a' in sql
        assert 'INTEGER' in sql
        assert 'b' in sql
        assert params == ()

    def test_format_create_function_with_returns(self, dummy_dialect: DummyDialect):
        """Tests format_create_function_statement with RETURNS clause."""
        from rhosocial.activerecord.backend.expression.statements import CreateFunctionExpression

        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="get_count",
            returns="INTEGER"
        )
        sql, params = dummy_dialect.format_create_function_statement(create_func)

        assert 'RETURNS INTEGER' in sql
        assert params == ()

    def test_format_create_function_with_language(self, dummy_dialect: DummyDialect):
        """Tests format_create_function_statement with LANGUAGE clause."""
        from rhosocial.activerecord.backend.expression.statements import CreateFunctionExpression

        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="plpgsql_func",
            language="plpgsql"
        )
        sql, params = dummy_dialect.format_create_function_statement(create_func)

        assert 'LANGUAGE plpgsql' in sql
        assert params == ()

    def test_format_create_function_with_body(self, dummy_dialect: DummyDialect):
        """Tests format_create_function_statement with function body."""
        from rhosocial.activerecord.backend.expression.statements import CreateFunctionExpression

        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="multiply",
            parameters=[
                {"name": "x", "type": "INTEGER"},
                {"name": "y", "type": "INTEGER"}
            ],
            returns="INTEGER",
            body="RETURN x * y;"
        )
        sql, params = dummy_dialect.format_create_function_statement(create_func)

        assert 'AS' in sql
        assert '$$RETURN x * y;$$' in sql
        assert params == ()

    def test_format_create_function_or_replace(self, dummy_dialect: DummyDialect):
        """Tests format_create_function_statement with OR REPLACE."""
        from rhosocial.activerecord.backend.expression.statements import CreateFunctionExpression

        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="existing_func",
            or_replace=True
        )
        sql, params = dummy_dialect.format_create_function_statement(create_func)

        assert 'CREATE FUNCTION' in sql
        assert 'OR REPLACE' in sql
        assert '"existing_func"' in sql
        assert params == ()

    def test_format_create_function_full(self, dummy_dialect: DummyDialect):
        """Tests format_create_function_statement with all options."""
        from rhosocial.activerecord.backend.expression.statements import CreateFunctionExpression

        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="complex_func",
            parameters=[
                {"name": "input", "type": "TEXT"},
                {"name": "multiplier", "type": "INTEGER"}
            ],
            returns="TEXT",
            language="plpgsql",
            body="BEGIN RETURN REPEAT(input, multiplier); END;",
            or_replace=True
        )
        sql, params = dummy_dialect.format_create_function_statement(create_func)

        assert 'CREATE FUNCTION' in sql
        assert 'OR REPLACE' in sql
        assert '"complex_func"' in sql
        assert 'input' in sql
        assert 'TEXT' in sql
        assert 'RETURNS TEXT' in sql
        assert 'LANGUAGE plpgsql' in sql
        assert 'AS' in sql
        assert 'BEGIN' in sql
        assert params == ()

    def test_format_create_function_parameter_type_only(self, dummy_dialect: DummyDialect):
        """Tests format_create_function_statement with type-only parameters."""
        from rhosocial.activerecord.backend.expression.statements import CreateFunctionExpression

        create_func = CreateFunctionExpression(
            dummy_dialect,
            function_name="type_only_func",
            parameters=[
                {"type": "INTEGER"},
                {"type": "TEXT"}
            ]
        )
        sql, params = dummy_dialect.format_create_function_statement(create_func)

        assert 'INTEGER' in sql
        assert 'TEXT' in sql
        assert params == ()

    def test_format_drop_function_basic(self, dummy_dialect: DummyDialect):
        """Tests format_drop_function_statement basic case."""
        from rhosocial.activerecord.backend.expression.statements import DropFunctionExpression

        drop_func = DropFunctionExpression(
            dummy_dialect,
            function_name="old_function"
        )
        sql, params = dummy_dialect.format_drop_function_statement(drop_func)

        assert 'DROP FUNCTION' in sql
        assert '"old_function"' in sql
        assert params == ()

    def test_format_drop_function_if_exists(self, dummy_dialect: DummyDialect):
        """Tests format_drop_function_statement with IF EXISTS."""
        from rhosocial.activerecord.backend.expression.statements import DropFunctionExpression

        drop_func = DropFunctionExpression(
            dummy_dialect,
            function_name="maybe_function",
            if_exists=True
        )
        sql, params = dummy_dialect.format_drop_function_statement(drop_func)

        assert 'DROP FUNCTION IF EXISTS' in sql
        assert '"maybe_function"' in sql
        assert params == ()

    def test_format_drop_function_with_parameters(self, dummy_dialect: DummyDialect):
        """Tests format_drop_function_statement with parameter types."""
        from rhosocial.activerecord.backend.expression.statements import DropFunctionExpression

        drop_func = DropFunctionExpression(
            dummy_dialect,
            function_name="overloaded_func",
            parameters=["INTEGER", "TEXT"]
        )
        sql, params = dummy_dialect.format_drop_function_statement(drop_func)

        assert 'DROP FUNCTION' in sql
        assert '"overloaded_func"' in sql
        assert '(INTEGER, TEXT)' in sql
        assert params == ()

    def test_format_drop_function_with_cascade(self, dummy_dialect: DummyDialect):
        """Tests format_drop_function_statement with CASCADE."""
        from rhosocial.activerecord.backend.expression.statements import DropFunctionExpression

        drop_func = DropFunctionExpression(
            dummy_dialect,
            function_name="dependent_func",
            cascade=True
        )
        sql, params = dummy_dialect.format_drop_function_statement(drop_func)

        assert 'DROP FUNCTION' in sql
        assert 'CASCADE' in sql
        assert params == ()

    def test_format_drop_function_all_options(self, dummy_dialect: DummyDialect):
        """Tests format_drop_function_statement with all options."""
        from rhosocial.activerecord.backend.expression.statements import DropFunctionExpression

        drop_func = DropFunctionExpression(
            dummy_dialect,
            function_name="complex_func",
            if_exists=True,
            parameters=["INTEGER", "INTEGER"],
            cascade=True
        )
        sql, params = dummy_dialect.format_drop_function_statement(drop_func)

        assert 'DROP FUNCTION IF EXISTS' in sql
        assert '"complex_func"' in sql
        assert '(INTEGER, INTEGER)' in sql
        assert 'CASCADE' in sql
        assert params == ()
