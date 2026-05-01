# tests/rhosocial/activerecord_test/feature/backend/test_dialect_security.py
"""
Tests for dialect SQL injection security fixes.

This test module verifies that string escaping and validation
methods properly sanitize user input to prevent SQL injection.
"""
import pytest

from rhosocial.activerecord.backend.dialect import SQLDialectBase
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.statements import (
    CreateTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.functions.string import trim


class TestDialect(SQLDialectBase):
    """Test dialect for security tests."""

    name = "test"


def test_escape_sql_string_basic(dialect):
    """Test basic single quote escaping."""
    result = dialect._escape_sql_string("test")
    assert result == "test"

    result = dialect._escape_sql_string("it's")
    assert result == "it''s"

    result = dialect._escape_sql_string("'")
    assert result == "''"


def test_escape_sql_string_multiple_quotes(dialect):
    """Test escaping multiple single quotes."""
    result = dialect._escape_sql_string("it's John's car")
    assert result == "it''s John''s car"

    result = dialect._escape_sql_string("''")
    assert result == "''''"


def test_validate_data_type_valid(dialect):
    """Test valid data types pass validation."""
    assert dialect._validate_data_type("VARCHAR(255)")
    assert dialect._validate_data_type("INTEGER")
    assert dialect._validate_data_type("NUMERIC(10, 2)")
    assert dialect._validate_data_type("TIMESTAMP WITHOUT TIME ZONE")
    assert dialect._validate_data_type("INT")


def test_validate_data_type_invalid(dialect):
    """Test invalid data types are rejected."""
    assert not dialect._validate_data_type("VARCHAR(255); DROP TABLE users--")
    assert not dialect._validate_data_type("/* comment */ INTEGER")
    assert not dialect._validate_data_type("INTEGER; DELETE FROM users")
    assert not dialect._validate_data_type("' OR '1'='1")


def test_format_column_definition_data_type_validation(dialect):
    """Test that column definition validates data_type."""
    col_def = ColumnDefinition(
        name="test_col",
        data_type="VARCHAR(255)",
    )

    sql, params = dialect.format_column_definition(col_def)
    assert "VARCHAR(255)" in sql


def test_format_column_definition_data_type_rejects_injection(dialect):
    """Test that malicious data_type is rejected."""
    col_def = ColumnDefinition(
        name="test_col",
        data_type="VARCHAR(255); DROP TABLE users--",
    )

    with pytest.raises(ValueError, match="Invalid data type"):
        dialect.format_column_definition(col_def)


def test_format_cast_expression_valid(dialect):
    """Test that CAST expression validates target_type."""
    sql, params = dialect.format_cast_expression("column", "INTEGER", (), None)
    assert "INTEGER" in sql


def test_format_cast_expression_rejects_injection(dialect):
    """Test that malicious target_type is rejected."""
    with pytest.raises(ValueError, match="Invalid target type"):
        dialect.format_cast_expression("column", "INTEGER; DROP TABLE users--", (), None)


def test_trim_direction_validation(dialect):
    """Test trim direction is validated."""
    col = Column(dialect, "name")

    result = trim(dialect, col, " ", "BOTH")
    assert result is not None

    result = trim(dialect, col, " ", "LEADING")
    assert result is not None

    result = trim(dialect, col, " ", "TRAILING")
    assert result is not None


def test_trim_direction_rejects_invalid(dialect):
    """Test that invalid trim direction is rejected."""
    dialect = TestDialect()
    col = Column(dialect, "name")

    with pytest.raises(ValueError, match="Invalid trim direction"):
        trim(dialect, col, " ", "BOTH; DROP TABLE users--")

    with pytest.raises(ValueError, match="Invalid trim direction"):
        trim(dialect, col, " ", "invalid")


def test_format_default_constraint_string_escaping(dialect):
    """Test DEFAULT constraint string is escaped."""
    constraint = ColumnConstraint(
        constraint_type=ColumnConstraintType.DEFAULT,
        default_value="test's value",
    )

    sql, params = dialect._format_default_constraint(constraint)
    assert "test''s value" in sql
    assert "'; DROP" not in sql


def test_format_storage_options_string_escaping(dialect):
    """Test storage options string values are escaped."""
    storage_opts = {"key": "value's"}
    sql, params = dialect._format_storage_options(storage_opts)
    assert "value''s" in sql
    assert "'; DROP" not in sql


@pytest.fixture
def dialect():
    """Create a test dialect."""
    return TestDialect()