# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_serialization.py
"""
Tests for SQLite-specific expression serialization.

These tests verify that SQLite-specific expressions (not available in other backends)
can be serialized and deserialized correctly.
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.reindex import SQLiteReindexExpression
from rhosocial.activerecord.backend.impl.sqlite.expression.vacuum import (
    SQLiteVacuumExpression,
    SQLiteAnalyzeExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.attach import (
    SQLiteAttachExpression,
    SQLiteDetachExpression,
)
from rhosocial.activerecord.backend.expression.serialization import serialize, deserialize
from rhosocial.activerecord.backend.expression.introspection import TableListExpression


@pytest.fixture
def sqlite_dialect():
    """Provides a SQLiteDialect instance with version 3.53.0+ for REINDEX support."""
    return SQLiteDialect(version=(3, 53, 0))


class TestSQLiteSpecificExpressionSerialization:
    """SQLite-specific expression serialization tests."""

    def test_reindex_expression_table_name(self, sqlite_dialect):
        """Test REINDEX with table_name."""
        expr = SQLiteReindexExpression(sqlite_dialect, table_name="users")
        spec = serialize(expr)
        restored = deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_reindex_expression_index_name(self, sqlite_dialect):
        """Test REINDEX with index_name."""
        expr = SQLiteReindexExpression(sqlite_dialect, index_name="idx_users")
        spec = serialize(expr)
        restored = deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_reindex_expression_expressions(self, sqlite_dialect):
        """Test REINDEX with expressions=True (requires SQLite 3.53.0+)."""
        expr = SQLiteReindexExpression(sqlite_dialect, expressions=True)
        spec = serialize(expr)
        restored = deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_reindex_expression_with_dialect_options(self, sqlite_dialect):
        """Test REINDEX with dialect_options."""
        expr = SQLiteReindexExpression(sqlite_dialect, table_name="users", dialect_options={"temp": True})
        spec = serialize(expr)
        assert spec["params"]["dialect_options"] == {"temp": True}
        restored = deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()


class TestSQLiteMaintenanceExpressionSerialization:
    """SQLite VACUUM / ANALYZE / ATTACH / DETACH serialization tests."""

    def test_vacuum_expression_roundtrip(self, sqlite_dialect):
        expr = SQLiteVacuumExpression(sqlite_dialect)
        spec = serialize(expr)
        restored = deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_vacuum_into_expression_roundtrip(self, sqlite_dialect):
        expr = SQLiteVacuumExpression(sqlite_dialect, into="backup.db")
        restored = deserialize(serialize(expr), sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_analyze_expression_roundtrip(self, sqlite_dialect):
        expr = SQLiteAnalyzeExpression(sqlite_dialect)
        restored = deserialize(serialize(expr), sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_attach_expression_roundtrip(self, sqlite_dialect):
        expr = SQLiteAttachExpression(sqlite_dialect, database="aux.db", schema="aux")
        restored = deserialize(serialize(expr), sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_detach_expression_roundtrip(self, sqlite_dialect):
        expr = SQLiteDetachExpression(sqlite_dialect, schema="aux")
        restored = deserialize(serialize(expr), sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()


class TestSQLiteIntrospectionExpressionSerialization:
    """SQLite introspection expression serialization tests."""

    def test_table_list_expression_roundtrip(self, sqlite_dialect):
        """Test TableListExpression round-trip."""
        expr = TableListExpression(sqlite_dialect, schema="main", include_views=True)
        spec = serialize(expr)
        restored = deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_table_list_expression_default_params(self, sqlite_dialect):
        """
        Test TableListExpression with default parameters.

        The generic introspection-based get_params() returns every declared
        __init__ parameter (including schema=None) for round-trip
        completeness. This test verifies that serialization preserves the
        full parameter set and the round-trip is lossless.
        """
        expr = TableListExpression(sqlite_dialect)
        spec = serialize(expr)
        assert "schema" in spec["params"]
        assert spec["params"]["schema"] is None
        assert spec["params"]["include_views"] is True
        restored = deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()
