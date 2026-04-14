# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_sqlite_3_53_features.py
"""
Tests for SQLite 3.53.0 new features.

This module tests features added in SQLite 3.53.0:
- ALTER TABLE ADD/DROP CONSTRAINT for NOT NULL and CHECK
- REINDEX EXPRESSIONS statement
- json_array_insert() and jsonb_array_insert() functions
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression import SQLiteReindexExpression
from rhosocial.activerecord.backend.impl.sqlite.functions.json import (
    json_array_insert,
    jsonb_array_insert,
)
from rhosocial.activerecord.backend.expression.core import Column, Literal


class TestSQLite353ConstraintSupport:
    """Tests for ALTER TABLE ADD/DROP CONSTRAINT support (SQLite 3.53.0+)."""

    def test_supports_add_constraint_below_353(self):
        """Test that ADD CONSTRAINT is not supported below 3.53.0."""
        dialect = SQLiteDialect(version=(3, 52, 0))
        assert dialect.supports_add_constraint() is False

    def test_supports_add_constraint_at_353(self):
        """Test that ADD CONSTRAINT is supported at 3.53.0."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        assert dialect.supports_add_constraint() is True

    def test_supports_add_constraint_above_353(self):
        """Test that ADD CONSTRAINT is supported above 3.53.0."""
        dialect = SQLiteDialect(version=(3, 54, 0))
        assert dialect.supports_add_constraint() is True

    def test_supports_drop_constraint_below_353(self):
        """Test that DROP CONSTRAINT is not supported below 3.53.0."""
        dialect = SQLiteDialect(version=(3, 52, 0))
        assert dialect.supports_drop_constraint() is False

    def test_supports_drop_constraint_at_353(self):
        """Test that DROP CONSTRAINT is supported at 3.53.0."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        assert dialect.supports_drop_constraint() is True

    def test_supports_drop_constraint_above_353(self):
        """Test that DROP CONSTRAINT is supported above 3.53.0."""
        dialect = SQLiteDialect(version=(3, 54, 0))
        assert dialect.supports_drop_constraint() is True


class TestSQLiteReindexExpression:
    """Tests for SQLite REINDEX expression."""

    def test_reindex_all(self):
        """Test REINDEX without parameters."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        expr = SQLiteReindexExpression(dialect)
        sql, params = expr.to_sql()
        assert sql == "REINDEX"
        assert params == ()

    def test_reindex_table(self):
        """Test REINDEX with table name."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        expr = SQLiteReindexExpression(dialect, table_name="users")
        sql, params = expr.to_sql()
        assert sql == 'REINDEX "users"'
        assert params == ()

    def test_reindex_index(self):
        """Test REINDEX with index name."""
        dialect = SQLiteDialect(version=(3, 35, 0))
        expr = SQLiteReindexExpression(dialect, index_name="idx_users_email")
        sql, params = expr.to_sql()
        assert sql == 'REINDEX "idx_users_email"'
        assert params == ()

    def test_reindex_expressions_supported(self):
        """Test REINDEX EXPRESSIONS on supported version."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        expr = SQLiteReindexExpression(dialect, expressions=True)
        sql, params = expr.to_sql()
        assert sql == "REINDEX EXPRESSIONS"
        assert params == ()

    def test_reindex_expressions_unsupported_version(self):
        """Test REINDEX EXPRESSIONS raises error on unsupported version."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        dialect = SQLiteDialect(version=(3, 52, 0))
        expr = SQLiteReindexExpression(dialect, expressions=True)
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            expr.to_sql()
        assert "REINDEX EXPRESSIONS" in str(exc_info.value)

    def test_reindex_mutually_exclusive_index_and_expressions(self):
        """Test that index_name and expressions are mutually exclusive."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        with pytest.raises(ValueError) as exc_info:
            SQLiteReindexExpression(dialect, index_name="idx", expressions=True)
        assert "cannot be combined" in str(exc_info.value)

    def test_reindex_mutually_exclusive_table_and_expressions(self):
        """Test that table_name and expressions are mutually exclusive."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        with pytest.raises(ValueError) as exc_info:
            SQLiteReindexExpression(dialect, table_name="users", expressions=True)
        assert "cannot be combined" in str(exc_info.value)

    def test_reindex_mutually_exclusive_index_and_table(self):
        """Test that index_name and table_name are mutually exclusive."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        with pytest.raises(ValueError) as exc_info:
            SQLiteReindexExpression(dialect, index_name="idx", table_name="users")
        assert "Cannot specify both" in str(exc_info.value)

    def test_supports_reindex_always_true(self):
        """Test that REINDEX is always supported in SQLite."""
        dialect = SQLiteDialect(version=(3, 0, 0))
        assert dialect.supports_reindex() is True

    def test_supports_reindex_expressions_version_check(self):
        """Test supports_reindex_expressions version check."""
        dialect_old = SQLiteDialect(version=(3, 52, 0))
        dialect_new = SQLiteDialect(version=(3, 53, 0))

        assert dialect_old.supports_reindex_expressions() is False
        assert dialect_new.supports_reindex_expressions() is True


class TestJsonArrayInsertFunction:
    """Tests for json_array_insert() function factory."""

    def test_json_array_insert_basic(self):
        """Test basic json_array_insert function call."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        expr = json_array_insert(dialect, "data", "new_value")
        sql, params = expr.to_sql()
        assert "JSON_ARRAY_INSERT" in sql
        assert len(params) == 2  # json_array and value are parameterized

    def test_json_array_insert_with_position(self):
        """Test json_array_insert with position parameter."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        expr = json_array_insert(dialect, "data", "new_value", position=0)
        sql, params = expr.to_sql()
        assert "JSON_ARRAY_INSERT" in sql
        assert len(params) == 3  # json_array, value, and position are parameterized

    def test_json_array_insert_with_column(self):
        """Test json_array_insert with Column expression."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        expr = json_array_insert(dialect, Column(dialect, "items"), Literal(dialect, "item"))
        sql, params = expr.to_sql()
        assert "JSON_ARRAY_INSERT" in sql


class TestJsonbArrayInsertFunction:
    """Tests for jsonb_array_insert() function factory."""

    def test_jsonb_array_insert_basic(self):
        """Test basic jsonb_array_insert function call."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        expr = jsonb_array_insert(dialect, "data", "new_value")
        sql, params = expr.to_sql()
        assert "JSONB_ARRAY_INSERT" in sql
        assert len(params) == 2  # jsonb_array and value are parameterized

    def test_jsonb_array_insert_with_position(self):
        """Test jsonb_array_insert with position parameter."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        expr = jsonb_array_insert(dialect, "data", "new_value", position=2)
        sql, params = expr.to_sql()
        assert "JSONB_ARRAY_INSERT" in sql
        assert len(params) == 3  # jsonb_array, value, and position are parameterized

    def test_jsonb_array_insert_with_column(self):
        """Test jsonb_array_insert with Column expression."""
        dialect = SQLiteDialect(version=(3, 53, 0))
        expr = jsonb_array_insert(dialect, Column(dialect, "items"), Literal(dialect, "item"))
        sql, params = expr.to_sql()
        assert "JSONB_ARRAY_INSERT" in sql
