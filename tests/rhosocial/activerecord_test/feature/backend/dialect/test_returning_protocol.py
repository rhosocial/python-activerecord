"""
Test for ReturningSupport protocol implementation.

This test creates a dialect that does not support RETURNING clauses and verifies that
the corresponding capability flags work correctly.
"""
import pytest

from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase, ReturningMixin, ReturningSupport, UnsupportedFeatureError
)
from rhosocial.activerecord.backend.expression import Column


class NoReturningDialect(SQLDialectBase, ReturningMixin, ReturningSupport):
    """Dialect that does not support RETURNING clauses."""

    def supports_returning_clause(self) -> bool:
        return False


class OnlyInsertReturningDialect(SQLDialectBase, ReturningMixin, ReturningSupport):
    """Dialect that only supports RETURNING for INSERT."""

    def supports_returning_insert(self) -> bool:
        return True

    def supports_returning_update(self) -> bool:
        return False

    def supports_returning_delete(self) -> bool:
        return False

    def supports_returning_clause(self) -> bool:
        return False


def test_no_returning_dialect_does_not_support_features():
    """Test that no-returning dialect properly indicates lack of RETURNING clause features."""
    dialect = NoReturningDialect()

    assert isinstance(dialect, ReturningSupport)
    assert not dialect.supports_returning_clause()
    assert not dialect.supports_returning_insert()
    assert not dialect.supports_returning_update()
    assert not dialect.supports_returning_delete()


def test_dml_specific_returning_support():
    """Test that DML-specific returning support flags work correctly."""
    dialect = OnlyInsertReturningDialect()

    assert isinstance(dialect, ReturningSupport)
    assert dialect.supports_returning_insert()
    assert not dialect.supports_returning_update()
    assert not dialect.supports_returning_delete()


def test_supports_returning_clause_is_and_of_dml():
    """Test that supports_returning_clause behavior matches the AND of DML-specific flags."""
    dialect = OnlyInsertReturningDialect()

    assert not dialect.supports_returning_clause()
    assert dialect.supports_returning_insert()
    assert not dialect.supports_returning_update()
    assert not dialect.supports_returning_delete()


class TestFormatDmlReturningErrors:
    """Test that UnsupportedFeatureError is raised for DML RETURNING when unsupported."""

    def test_format_insert_returning_unsupported(self):
        """Test INSERT RETURNING raises error when insert returning is unsupported."""
        from unittest.mock import MagicMock

        dialect = NoReturningDialect()
        dialect.strict_validation = False
        mock_expr = MagicMock()
        mock_expr.into.to_sql.return_value = ("test_table", ())
        mock_expr.columns = []
        mock_expr.source = None
        mock_expr.on_conflict = None
        mock_expr.returning = MagicMock()

        with pytest.raises(UnsupportedFeatureError, match="RETURNING clause in INSERT"):
            dialect.format_insert_statement(mock_expr)

    def test_format_update_returning_unsupported(self):
        """Test UPDATE RETURNING raises error when update returning is unsupported."""
        from unittest.mock import MagicMock

        dialect = NoReturningDialect()
        mock_expr = MagicMock()
        mock_expr.table.to_sql.return_value = ("test_table", ())
        mock_expr.assignments = {}
        mock_expr.from_ = None
        mock_expr.where = None
        mock_expr.returning = MagicMock()

        with pytest.raises(UnsupportedFeatureError, match="RETURNING clause in UPDATE"):
            dialect.format_update_statement(mock_expr)

    def test_format_delete_returning_unsupported(self):
        """Test DELETE RETURNING raises error when delete returning is unsupported."""
        from unittest.mock import MagicMock

        dialect = NoReturningDialect()
        dialect.strict_validation = False
        mock_table = MagicMock()
        mock_table.to_sql.return_value = ("test_table", ())
        mock_expr = MagicMock()
        mock_expr.tables = [mock_table]
        mock_expr.using = None
        mock_expr.where = None
        mock_expr.returning = MagicMock()

        with pytest.raises(UnsupportedFeatureError, match="RETURNING clause in DELETE"):
            dialect.format_delete_statement(mock_expr)
