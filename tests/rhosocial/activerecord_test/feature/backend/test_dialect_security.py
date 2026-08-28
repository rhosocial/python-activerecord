# tests/rhosocial/activerecord_test/feature/backend/test_dialect_security.py
"""
Tests for dialect SQL injection security fixes.

This test module verifies that string escaping and validation
methods properly sanitize user input to prevent SQL injection.
"""

import pytest

from typing import Tuple

from rhosocial.activerecord.backend.dialect import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins import PartitionMixin, ExpressionMixin, DDLColumnMixin, IdentifierMixin, TableMixin
from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
    PartitionStrategy,
)
from rhosocial.activerecord.backend.expression.functions.string import trim
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType


class TestDialect(SQLDialectBase, IdentifierMixin, ExpressionMixin, DDLColumnMixin, TableMixin, PartitionMixin, DDLTypeMixin):
    """Test dialect for security tests."""

    name = "test"

    def supports_table_partitioning(self) -> bool:
        return True

    def supports_partitioned_table_creation(self) -> bool:
        return True

    @DDLTypeMixin.handles(IntegerType)
    def format_data_type_int(self, data_type) -> Tuple[str, tuple]:
        return "INTEGER", ()

    @DDLTypeMixin.handles(VarCharType)
    def format_data_type_varchar(self, data_type) -> Tuple[str, tuple]:
        if data_type.length is not None:
            return f"VARCHAR({data_type.length})", ()
        return "VARCHAR", ()

    def format_partition_clause(self, expr) -> Tuple[str, tuple]:
        parts = []
        params = []
        for key in expr.keys:
            key_sql, key_params = key.to_sql()
            parts.append(key_sql)
            params.extend(key_params)
        return f" PARTITION BY {expr.method} ({', '.join(parts)})", tuple(params)


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
        data_type=VarCharType(255),
    )

    sql, params = dialect.format_column_definition(col_def)
    assert "VARCHAR(255)" in sql


def test_column_definition_rejects_string_data_type(dialect):
    """Test that ColumnDefinition rejects a string for data_type."""
    with pytest.raises(TypeError, match="data_type must be a DataType"):
        ColumnDefinition(
            name="test_col",
            data_type="VARCHAR(255); DROP TABLE users--",
        )


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

    sql, params = dialect.format_default_constraint(constraint)
    assert "test''s value" in sql
    assert "'; DROP" not in sql


def test_format_storage_options_string_escaping(dialect):
    """Test storage options string values are escaped."""
    storage_opts = {"key": "value's"}
    sql, params = dialect.format_storage_options(storage_opts)
    assert "value''s" in sql
    assert "'; DROP" not in sql


def test_format_storage_options_key_identifier_quoting(dialect):
    """Test storage option keys are quoted as identifiers.

    Before fix: key was embedded directly with only .upper().
    After fix: key goes through format_identifier(), so even if 'DROP TABLE'
    appears in the SQL, it's safely enclosed inside quoted identifiers.
    """
    malicious_key = 'key"; DROP TABLE users--'
    storage_opts = {malicious_key: "value"}
    sql, params = dialect.format_storage_options(storage_opts)

    # DROP TABLE may appear inside quoted identifier, that's safe.
    # Verify quotes are balanced (no breakout).
    outer_quotes = [i for i, c in enumerate(sql) if c == '"']
    assert len(outer_quotes) % 2 == 0, f"Unbalanced quotes in {sql}"


def test_format_storage_options_mixed_safe_and_malicious_keys(dialect):
    """Test that safe keys work and malicious keys are quoted in same dict."""
    safe_key = "fillfactor"
    malicious_key = 'evil"; DELETE FROM t--'
    storage_opts = {safe_key: 70, malicious_key: "x"}
    sql, params = dialect.format_storage_options(storage_opts)

    assert "fillfactor" in sql or "FILLFACTOR" in sql
    # DELETE may appear inside quoted identifier — verify balanced quotes
    outer_quotes = [i for i, c in enumerate(sql) if c == '"']
    assert len(outer_quotes) % 2 == 0, f"Unbalanced quotes in {sql}"


def test_format_storage_options_int_value_not_parameterized(dialect):
    """Numeric storage options are embedded as literals (design decision)."""
    storage_opts = {"fillfactor": 70}
    sql, params = dialect.format_storage_options(storage_opts)
    assert "70" in sql
    assert params == ()


def test_format_storage_options_none_value_uses_placeholder(dialect):
    """None or unknown type values use parameterized placeholder."""
    storage_opts = {"option": None}
    sql, params = dialect.format_storage_options(storage_opts)
    assert dialect.get_parameter_placeholder() in sql
    assert params == (None,)


def test_format_storage_options_empty(dialect):
    """Empty storage options returns empty string."""
    sql, params = dialect.format_storage_options({})
    assert sql == ""
    assert params == ()


def test_format_partition_method_validation(dialect):
    """Test partition method is allowlist-validated and columns are quoted."""
    from rhosocial.activerecord.backend.expression import Column
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        CreateTableExpression,
        ColumnDefinition,
        PartitionClause,
    )

    col_def = ColumnDefinition(name="id", data_type=IntegerType())
    expr = CreateTableExpression(
        dialect=dialect,
        table="test_table",
        columns=[col_def],
        partition=PartitionClause(
            dialect=dialect,
            method=PartitionStrategy.RANGE,
            keys=[Column(dialect, "id")],
        ),
    )
    sql, params = dialect.format_create_table_statement(expr)
    assert "PARTITION BY RANGE" in sql
    assert '"id"' in sql or '"ID"' in sql
    assert params == ()


def test_format_partition_method_rejects_invalid_method_without_echoing_value(dialect):
    """Invalid partition method is rejected before SQL generation."""
    from rhosocial.activerecord.backend.expression import Column
    from rhosocial.activerecord.backend.expression.statements.ddl_table import (
        PartitionClause,
    )

    malicious_method = "RANGE); DROP TABLE users; --"

    with pytest.raises(TypeError) as exc_info:
        PartitionClause(
            dialect=dialect,
            method=malicious_method,
            keys=[Column(dialect, "id")],
        )

    message = str(exc_info.value)
    assert "method must be a PartitionStrategy" in message
    assert malicious_method not in message


@pytest.fixture
def dialect():
    """Create a test dialect."""
    return TestDialect()


# ── SQLite PRAGMA escaping & whitelist ─────────────────────────────────


def test_format_identifier_prevents_name_injection():
    """format_identifier must double-quote embedded quotes."""
    from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
    d = SQLDialectBase()
    # core base wraps in double-quotes and escapes embedded "
    assert d.format_identifier("normal") == '"normal"'
    assert d.format_identifier('it"self') == '"it""self"'
    assert d.format_identifier("") == '""'
