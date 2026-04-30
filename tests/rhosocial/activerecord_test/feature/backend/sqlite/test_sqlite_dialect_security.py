# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_sqlite_dialect_security.py
"""
Tests for SQLite dialect SQL injection security fixes.

This test module verifies that string escaping and validation
methods properly sanitize user input to prevent SQL injection.
Tests are run against the actual SQLite dialect.
"""
import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)


@pytest.fixture
def dialect():
    """Create a SQLite test dialect."""
    return SQLiteDialect()


def test_sqlite_escape_sql_string(dialect):
    """Test SQLite inherits _escape_sql_string."""
    result = dialect._escape_sql_string("test's value")
    assert result == "test''s value"


def test_sqlite_validate_data_type(dialect):
    """Test SQLite inherits _validate_data_type."""
    assert dialect._validate_data_type("TEXT")
    assert dialect._validate_data_type("INTEGER")
    assert dialect._validate_data_type("REAL")
    assert dialect._validate_data_type("BLOB")
    assert not dialect._validate_data_type("TEXT; DROP TABLE users--")


def test_sqlite_format_column_definition_data_type_validation(dialect):
    """Test column definition validates data_type."""
    col_def = ColumnDefinition(
        name="test_col",
        data_type="TEXT",
    )

    sql, params = dialect.format_column_definition(col_def)
    assert "TEXT" in sql


def test_sqlite_format_column_definition_data_type_rejects_injection(dialect):
    """Test that malicious data_type is rejected."""
    col_def = ColumnDefinition(
        name="test_col",
        data_type="TEXT; DROP TABLE users--",
    )

    with pytest.raises(ValueError, match="Invalid data type"):
        dialect.format_column_definition(col_def)


def test_sqlite_format_default_constraint_string_escaping(dialect):
    """Test DEFAULT constraint string is escaped."""
    constraint = ColumnConstraint(
        constraint_type=ColumnConstraintType.DEFAULT,
        default_value="test's value",
    )

    sql, params = dialect._format_default_constraint(constraint)
    assert "test''s value" in sql
    assert "'; DROP" not in sql


def test_sqlite_format_storage_options_string_escaping(dialect):
    """Test storage options string values are escaped."""
    storage_opts = {"key": "value's"}
    sql, params = dialect._format_storage_options(storage_opts)
    assert "value''s" in sql
    assert "'; DROP" not in sql


def test_sqlite_format_cast_expression_valid(dialect):
    """Test that CAST expression validates target_type."""
    sql, params = dialect.format_cast_expression("column", "TEXT", (), None)
    assert "TEXT" in sql


def test_sqlite_format_cast_expression_rejects_injection(dialect):
    """Test that malicious target_type is rejected."""
    with pytest.raises(ValueError, match="Invalid target type"):
        dialect.format_cast_expression("column", "TEXT; DROP TABLE users--", (), None)