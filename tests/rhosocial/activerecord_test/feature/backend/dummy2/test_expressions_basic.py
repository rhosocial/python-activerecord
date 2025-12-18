import pytest
from rhosocial.activerecord.backend.expression import Literal, Column, Identifier, RawSQLExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect # Explicit import for clarity, though fixture provides it

class TestBasicExpressions:
    """Tests for basic SQL expression components like Literals, Columns, and Identifiers."""

    @pytest.mark.parametrize("value, expected_sql, expected_params", [
        (123, "?", (123,)),
        ("hello world", "?", ("hello world",)),
        (None, "?", (None,)),
        (3.14, "?", (3.14,)),
        (True, "?", (True,)),
        ([1, 2, "three"], "?", ([1, 2, "three"],)),
        ((4, 5, 6), "?", ((4, 5, 6),)),
        ([], "?", ([],)), # Empty list/tuple now passed as a single parameter
    ])
    def test_literal(self, dummy_dialect, value, expected_sql, expected_params):
        """Tests various types of literal values."""
        lit = Literal(dummy_dialect, value)
        sql, params = lit.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    @pytest.mark.parametrize("name, table, alias, expected_sql, expected_params", [
        ("user_name", None, None, '"user_name"', ()),
        ("id", "users", None, '"users"."id"', ()),
        ("product_id", None, "pid", '"product_id" AS "pid"', ()),
        ("column with spaces", "my_table", "cws", '"my_table"."column with spaces" AS "cws"', ()),
    ])
    def test_column(self, dummy_dialect, name, table, alias, expected_sql, expected_params):
        """Tests different forms of column expressions."""
        col_expr = Column(dummy_dialect, name, table=table, alias=alias)
        sql, params = col_expr.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    @pytest.mark.parametrize("name, expected_sql", [
        ("my_table", '"my_table"'),
        ("another_identifier", '"another_identifier"'),
        ("id with space", '"id with space"'),
    ])
    def test_identifier(self, dummy_dialect, name, expected_sql):
        """Tests identifier expressions (e.g., table names, aliases)."""
        id_expr = Identifier(dummy_dialect, name)
        sql, params = id_expr.to_sql()
        assert sql == expected_sql
        assert params == ()

    @pytest.mark.parametrize("raw_sql_string, expected_params", [
        ("CURRENT_TIMESTAMP", ()),
        ("NOW()", ()),
        ("version()", ()),
        ("1 + 1", ()),
    ])
    def test_raw_sql_expression(self, dummy_dialect, raw_sql_string, expected_params):
        """Tests raw SQL expressions, ensuring their content is output directly."""
        raw_expr = RawSQLExpression(dummy_dialect, raw_sql_string)
        sql, params = raw_expr.to_sql()
        assert sql == raw_sql_string
        assert params == expected_params
