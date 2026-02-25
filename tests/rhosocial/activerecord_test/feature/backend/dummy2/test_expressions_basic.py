# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expressions_basic.py
import pytest
from rhosocial.activerecord.backend.expression import Literal, Column, Identifier, RawSQLExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect # Explicit import for clarity, though fixture provides it

class TestBasicExpressions:
    """Tests for basic SQL expression components like Literals, Columns, and Identifiers."""

    @pytest.mark.parametrize("value, expected_sql, expected_params", [
        (123, "?", (123,)),
        ("hello world", "?", ("hello world",)),
        ("你好世界", "?", ("你好世界",)),  # Chinese
        ("こんにちは世界", "?", ("こんにちは世界",)),  # Japanese
        ("안녕하세요 세계", "?", ("안녕하세요 세계",)),  # Korean
        ("Bonjour le monde", "?", ("Bonjour le monde",)),  # French
        ("Hallo Welt", "?", ("Hallo Welt",)),  # German
        ("Привет мир", "?", ("Привет мир",)),  # Russian
        ("😀🎉🚀", "?", ("😀🎉🚀",)),  # Emoji
        ("café naïve résumé", "?", ("café naïve résumé",)),  # Accented characters
        ("مرحبا بالعالم", "?", ("مرحبا بالعالم",)),  # Arabic
        ("हैलो वर्ल्ड", "?", ("हैलो वर्ल्ड",)),  # Hindi
        (None, "?", (None,)),
        (3.14, "?", (3.14,)),
        (True, "?", (True,)),
        ([1, 2, "three"], "?", ([1, 2, "three"],)),
        ((4, 5, 6), "?", ((4, 5, 6),)),
        ([], "?", ([],)), # Empty list/tuple now passed as a single parameter
    ])
    def test_literal(self, dummy_dialect: DummyDialect, value, expected_sql, expected_params):
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
    def test_column(self, dummy_dialect: DummyDialect, name, table, alias, expected_sql, expected_params):
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
    def test_identifier(self, dummy_dialect: DummyDialect, name, expected_sql):
        """Tests identifier expressions (e.g., table names, aliases)."""
        id_expr = Identifier(dummy_dialect, name)
        sql, params = id_expr.to_sql()
        assert sql == expected_sql
        assert params == ()

    @pytest.mark.parametrize("raw_sql_string, raw_params, expected_sql, expected_params", [
        ("CURRENT_TIMESTAMP", (), "CURRENT_TIMESTAMP", ()),
        ("NOW()", (), "NOW()", ()),
        ("version()", (), "version()", ()),
        ("1 + 1", (), "1 + 1", ()),
        ("?", (None,), "?", (None,)),  # Single parameter placeholder
        ("? + ?", (None, None), "? + ?", (None, None)),  # Multiple parameter placeholders
        ("COALESCE(?, ?)", ("value", "default"), "COALESCE(?, ?)", ("value", "default")),  # Function with parameters
        ("UPPER(?)", ("text",), "UPPER(?)", ("text",)),  # Function with parameter
    ])
    def test_raw_sql_expression(self, dummy_dialect: DummyDialect, raw_sql_string, raw_params, expected_sql, expected_params):
        """Tests raw SQL expressions, ensuring their content is output directly."""
        raw_expr = RawSQLExpression(dummy_dialect, raw_sql_string, raw_params)
        sql, params = raw_expr.to_sql()
        assert sql == expected_sql
        assert params == expected_params
