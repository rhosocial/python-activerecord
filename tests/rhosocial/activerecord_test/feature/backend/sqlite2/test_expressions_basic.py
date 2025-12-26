# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_expressions_basic.py
import pytest
from rhosocial.activerecord.backend.expression import Literal, Column, Identifier, RawSQLExpression
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

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
    ])
    def test_literal_various_types(self, sqlite_dialect_3_8_0: SQLiteDialect, value, expected_sql, expected_params):
        """Test Literal with various data types."""
        literal = Literal(sqlite_dialect_3_8_0, value)
        sql, params = literal.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    def test_literal_repr(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Literal repr method."""
        literal = Literal(sqlite_dialect_3_8_0, "test_value")
        assert repr(literal) == "Literal('test_value')"

    def test_column_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic Column functionality."""
        column = Column(sqlite_dialect_3_8_0, "name")
        sql, params = column.to_sql()
        assert sql == '"name"'
        assert params == ()

    def test_column_with_table(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Column with table specification."""
        column = Column(sqlite_dialect_3_8_0, "name", table="users")
        sql, params = column.to_sql()
        assert sql == '"users"."name"'
        assert params == ()

    def test_column_with_alias(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Column with alias."""
        column = Column(sqlite_dialect_3_8_0, "name", alias="user_name")
        sql, params = column.to_sql()
        assert sql == '"name" AS "user_name"'
        assert params == ()

    def test_column_with_table_and_alias(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Column with both table and alias."""
        column = Column(sqlite_dialect_3_8_0, "name", table="users", alias="user_name")
        sql, params = column.to_sql()
        assert sql == '"users"."name" AS "user_name"'
        assert params == ()

    def test_identifier_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic Identifier functionality."""
        identifier = Identifier(sqlite_dialect_3_8_0, "table_name")
        sql, params = identifier.to_sql()
        assert sql == '"table_name"'
        assert params == ()

    def test_identifier_with_spaces(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Identifier with spaces."""
        identifier = Identifier(sqlite_dialect_3_8_0, "column with spaces")
        sql, params = identifier.to_sql()
        assert sql == '"column with spaces"'
        assert params == ()

    def test_identifier_with_special_chars(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test Identifier with special characters."""
        identifier = Identifier(sqlite_dialect_3_8_0, "user-defined")
        sql, params = identifier.to_sql()
        assert sql == '"user-defined"'
        assert params == ()

    def test_raw_sql_expression(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test RawSQLExpression functionality."""
        raw_sql = RawSQLExpression(sqlite_dialect_3_8_0, "CURRENT_TIMESTAMP")
        sql, params = raw_sql.to_sql()
        assert sql == "CURRENT_TIMESTAMP"
        assert params == ()

    def test_raw_sql_with_params(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test RawSQLExpression with parameters."""
        raw_sql = RawSQLExpression(sqlite_dialect_3_8_0, "datetime('now', ?)", ("localtime",))
        sql, params = raw_sql.to_sql()
        assert sql == "datetime('now', ?)"
        assert params == ("localtime",)