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


# ============================================================
# format_identifier — identifier quoting and escaping
# ============================================================

def test_format_identifier_simple(dialect):
    """Simple identifier is wrapped in double quotes."""
    result = dialect.format_identifier("users")
    assert result == '"users"'


def test_format_identifier_with_double_quote(dialect):
    """Identifier containing double quote is properly escaped.

    Before fix: _quote_identifier did not escape internal quotes.
    format_identifier always did. After fix, _quote_identifier delegates
    to format_identifier, so both paths are safe.
    """
    result = dialect.format_identifier('table"name')
    assert result == '"table""name"'


def test_format_identifier_injection_attempt(dialect):
    """Identifier with SQL injection payload is safely quoted."""
    payload = 'users"; DROP TABLE users--'
    result = dialect.format_identifier(payload)
    # The embedded " becomes "", so the entire string stays inside one pair of quotes
    assert result == '"users""; DROP TABLE users--"'


def test_format_identifier_empty_string(dialect):
    """Empty identifier produces empty double quotes."""
    result = dialect.format_identifier("")
    assert result == '""'


# ============================================================
# format_column_info_query — uses format_identifier for table_name
# ============================================================

def test_format_column_info_query_with_malicious_table_name(dialect):
    """Column info query safely quotes malicious table names.

    The malicious content appears inside the quoted identifier,
    which makes it a table name literal, not executable SQL.
    Balanced quotes = no breakout.
    """
    from rhosocial.activerecord.backend.expression.introspection import ColumnInfoExpression

    expr = ColumnInfoExpression(dialect, table_name='t"; DROP TABLE users--')
    sql, params = dialect.format_column_info_query(expr)
    # DROP TABLE appears inside the quoted identifier — verify balanced quotes
    assert sql.count('"') % 2 == 0, f"Unbalanced quotes: {sql}"


def test_format_column_info_query_normal_table(dialect):
    """Column info query with normal table name works."""
    from rhosocial.activerecord.backend.expression.introspection import ColumnInfoExpression

    expr = ColumnInfoExpression(dialect, table_name="users")
    sql, params = dialect.format_column_info_query(expr)
    assert '"users"' in sql
    assert params == ()


# ============================================================
# format_index_info_query — uses format_identifier for table_name
# ============================================================

def test_format_index_info_query_with_malicious_table_name(dialect):
    """Index info query safely quotes malicious table names.

    DELETE appears inside the quoted identifier — verify balanced quotes.
    """
    from rhosocial.activerecord.backend.expression.introspection import IndexInfoExpression

    expr = IndexInfoExpression(dialect, table_name='t"; DELETE FROM users--')
    sql, params = dialect.format_index_info_query(expr)
    assert sql.count('"') % 2 == 0, f"Unbalanced quotes: {sql}"


# ============================================================
# format_foreign_key_query — uses format_identifier for table_name
# ============================================================

def test_format_foreign_key_query_with_malicious_table_name(dialect):
    """Foreign key query safely quotes malicious table names.

    DROP TABLE appears inside the quoted identifier — verify balanced quotes.
    """
    from rhosocial.activerecord.backend.expression.introspection import ForeignKeyExpression

    expr = ForeignKeyExpression(dialect, table_name='t"; DROP TABLE users--')
    sql, params = dialect.format_foreign_key_query(expr)
    assert sql.count('"') % 2 == 0, f"Unbalanced quotes: {sql}"


# ============================================================
# format_drop_virtual_table — manual quoting replaced with format_identifier
# ============================================================

def test_format_drop_virtual_table_normal(dialect):
    """Drop virtual table with normal table name."""
    sql, params = dialect.format_drop_virtual_table("my_fts_table", if_exists=False)
    assert sql == 'DROP TABLE "my_fts_table"'
    assert params == ()


def test_format_drop_virtual_table_if_exists(dialect):
    """Drop virtual table with IF EXISTS."""
    sql, params = dialect.format_drop_virtual_table("my_fts_table", if_exists=True)
    assert sql == 'DROP TABLE IF EXISTS "my_fts_table"'
    assert params == ()


def test_format_drop_virtual_table_with_malicious_name(dialect):
    """Drop virtual table with malicious name is safely quoted.

    Before fix: f'DROP TABLE "{table_name}"' — no escaping of internal ".
    After fix: uses format_identifier which escapes " to "".
    """
    sql, params = dialect.format_drop_virtual_table('t"; DROP TABLE users--', if_exists=False)
    assert "DROP TABLE" not in sql.split('"')[1::2] if len(sql.split('"')) > 2 else "DROP TABLE users" not in sql
    assert sql.count('"') % 2 == 0, f"Unbalanced quotes: {sql}"


# ============================================================
# format_create_trigger_statement — function_name quoting
# ============================================================

def test_format_create_trigger_function_name_quoted(dialect):
    """Trigger function name is identifier-quoted in CALL statement.

    Before fix: f"CALL {expr.function_name}();" — raw embedded.
    After fix: uses format_identifier which quotes the function name.
    """
    from rhosocial.activerecord.backend.expression.statements.ddl_trigger import (
        CreateTriggerExpression, TriggerTiming, TriggerEvent, TriggerLevel,
    )

    expr = CreateTriggerExpression(
        dialect=dialect,
        trigger_name="test_trigger",
        timing=TriggerTiming.AFTER,
        events=[TriggerEvent.INSERT],
        table_name="users",
        level=TriggerLevel.ROW,
        function_name='my_func',
    )
    sql, params = dialect.format_create_trigger_statement(expr)
    assert '"my_func"' in sql


def test_format_create_trigger_malicious_function_name(dialect):
    """Trigger with malicious function name is safely quoted.

    The injection payload appears inside the quoted function name identifier.
    Balanced quotes = no breakout from identifier context.
    """
    from rhosocial.activerecord.backend.expression.statements.ddl_trigger import (
        CreateTriggerExpression, TriggerTiming, TriggerEvent, TriggerLevel,
    )

    expr = CreateTriggerExpression(
        dialect=dialect,
        trigger_name="test_trigger",
        timing=TriggerTiming.AFTER,
        events=[TriggerEvent.INSERT],
        table_name="users",
        level=TriggerLevel.ROW,
        function_name='f"; DROP TABLE users--',
    )
    sql, params = dialect.format_create_trigger_statement(expr)
    assert sql.count('"') % 2 == 0, f"Unbalanced quotes: {sql}"


# ============================================================
# Integration: format_storage_options via SQLite dialect
# ============================================================

def test_sqlite_format_storage_options_key_identifier_quoting(dialect):
    """Storage option keys are identifier-quoted in SQLite dialect."""
    malicious_key = 'key"; DROP TABLE users--'
    storage_opts = {malicious_key: "value"}
    sql, params = dialect._format_storage_options(storage_opts)
    # "DROP TABLE" appears inside the quoted identifier — safe.
    # Verify balanced quotes (no breakout).
    assert sql.count('"') % 2 == 0, f"Unbalanced quotes in {sql}"


# ============================================================
# Integration test: unquoted vs quoted identifier injection
# Demonstrates why proper escaping matters
# ============================================================

def test_identifier_quoting_prevents_breakout(dialect):
    """Demonstrate that without quote-escaping, injection is possible.

    This test proves the importance of format_identifier's escaping.
    A naive f'"{name}"' without escaping allows breakout:
      name = 'x"; DROP TABLE users--'
      naive = f'DROP TABLE "{name}"'
      Result: DROP TABLE "x"; DROP TABLE users--"
      The " after x closes the identifier, and DROP TABLE users executes.

    With format_identifier:
      escaped = name.replace('"', '""')
      quoted = f'"{escaped}"'  →  "x""; DROP TABLE users--"
      The entire payload stays inside one identifier context.
    """
    malicious_name = 'x"; DROP TABLE users--'

    # Simulate the UNSAFE pattern (no escaping)
    unsafe_result = f'DROP TABLE "{malicious_name}"'
    # This has a dangling unclosed quote after users--
    # But the ; DROP TABLE users-- is already outside the identifier

    # Safe pattern via format_identifier
    safe_result = dialect.format_identifier(malicious_name)

    # Verify unsafe pattern produces unbalanced quotes (injection possible)
    # unsafe_result: DROP TABLE "x"; DROP TABLE users--"
    #                               ^^ quote closes after x, then DROP TABLE executes
    unsafe_quote_count = unsafe_result.count('"')
    assert unsafe_quote_count % 2 != 0 or unsafe_quote_count > 2, \
        f"Unsafe quoting {unsafe_result} — odd quotes means injection succeeded"

    # Verify safe pattern produces even quotes (no breakout)
    assert safe_result.count('"') % 2 == 0, \
        f"format_identifier produced unbalanced quotes: {safe_result}"


def test_format_identifier_vs_naive_quoting(dialect):
    """Compare format_identifier output vs naive quoting for various payloads.

    This parametrized-style test shows the behavioral difference between
    proper escaping (format_identifier) and naive quoting.
    """
    test_cases = [
        # (name, naive_has_issue, description)
        ('normal_table', False, "Normal name: both work"),
        ('t"', True, "Single trailing quote: naive breaks"),
        ('"; DROP', True, "Quote-semicolon: naive injection"),
        ('x"; DELETE', True, "Quote-semicolon-DELETE: naive injection"),
    ]
    for name, naive_has_issue, desc in test_cases:
        safe = dialect.format_identifier(name)
        naive = f'"{name}"'

        # format_identifier always produces even quote count
        assert safe.count('"') % 2 == 0, \
            f"format_identifier('{name}'): {safe} — unbalanced quotes"

        if naive_has_issue:
            # Naive quoting produces odd or excessive quotes
            # which means the identifier boundary is broken
            assert naive.count('"') % 2 != 0 or \
                   name.count('"') > 0 and '";' in naive, \
                f"Expected naive quoting of '{name}' to have issues, got: {naive}"