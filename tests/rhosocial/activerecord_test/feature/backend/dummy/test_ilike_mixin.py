# tests/rhosocial/activerecord_test/feature/backend/dummy/test_ilike_mixin.py
"""Tests for ILIKEMixin format methods."""
import pytest
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression import Column


class TestILIKEMixinFormatMethods:
    """Tests for ILIKEMixin format_ilike_expression method.

    Note: The default implementation uses LOWER() function for case-insensitive
    comparison since the DummyDialect follows the mixin's default behavior.
    """

    def test_format_ilike_basic(self, dummy_dialect: DummyDialect):
        """Tests basic ILIKE expression formatting (uses LOWER())."""
        sql, params = dummy_dialect.format_ilike_expression("name", "John%")

        assert 'LOWER("name")' in sql
        assert "LIKE" in sql
        assert "LOWER(?)" in sql
        assert params == ("john%",)

    def test_format_ilike_with_negate(self, dummy_dialect: DummyDialect):
        """Tests ILIKE expression with NOT (negate=True)."""
        sql, params = dummy_dialect.format_ilike_expression("name", "John%", negate=True)

        assert 'LOWER("name")' in sql
        assert "NOT LIKE" in sql
        assert params == ("john%",)

    def test_format_ilike_with_column_expression(self, dummy_dialect: DummyDialect):
        """Tests ILIKE expression with Column expression."""
        column = Column(dummy_dialect, "email")
        sql, params = dummy_dialect.format_ilike_expression(column, "%@example.com")

        assert '"email"' in sql
        assert "LIKE" in sql
        assert params == ("%@example.com",)

    def test_format_ilike_with_negate_and_column(self, dummy_dialect: DummyDialect):
        """Tests NOT ILIKE expression with Column expression."""
        column = Column(dummy_dialect, "status")
        sql, params = dummy_dialect.format_ilike_expression(column, "active%", negate=True)

        assert '"status"' in sql
        assert "NOT LIKE" in sql
        assert params == ("active%",)

    def test_format_ilike_case_insensitive_matching(self, dummy_dialect: DummyDialect):
        """Tests that ILIKE pattern matching converts to lowercase."""
        sql, params = dummy_dialect.format_ilike_expression("name", "John%")

        assert "LIKE" in sql
        assert params == ("john%",)

    def test_format_ilike_string_column(self, dummy_dialect: DummyDialect):
        """Tests ILIKE with string column name."""
        sql, params = dummy_dialect.format_ilike_expression("username", "admin%")

        assert '"username"' in sql
        assert "LIKE" in sql
        assert params == ("admin%",)
