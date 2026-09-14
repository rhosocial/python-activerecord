# tests/rhosocial/activerecord_test/feature/backend/dummy/test_ilike_mixin.py
"""Tests for ILIKEMixin format methods."""

from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression import Column, ILIKEExpression


class TestILIKEMixinFormatMethods:
    """Tests for ILIKEMixin format_ilike_expression method.

    Note: The default implementation uses LOWER() function for case-insensitive
    comparison since the DummyDialect follows the mixin's default behavior.
    """

    def test_format_ilike_basic(self, dummy_dialect: DummyDialect):
        """Tests basic ILIKE expression formatting (uses LOWER())."""
        expr = ILIKEExpression(dummy_dialect, Column(dummy_dialect, "name"), "John%")
        sql, params = expr.to_sql()

        assert 'LOWER("name")' in sql
        assert "LIKE" in sql
        assert "LOWER(?)" in sql
        assert params == ("john%",)

    def test_format_ilike_with_negate(self, dummy_dialect: DummyDialect):
        """Tests ILIKE expression with NOT (negate=True)."""
        expr = ILIKEExpression(dummy_dialect, Column(dummy_dialect, "name"), "John%", negate=True)
        sql, params = expr.to_sql()

        assert 'LOWER("name")' in sql
        assert "NOT LIKE" in sql
        assert params == ("john%",)

    def test_format_ilike_with_column_expression(self, dummy_dialect: DummyDialect):
        """Tests ILIKE expression with Column expression."""
        expr = ILIKEExpression(dummy_dialect, Column(dummy_dialect, "email"), "%@example.com")
        sql, params = expr.to_sql()

        assert '"email"' in sql
        assert "LIKE" in sql
        assert params == ("%@example.com",)

    def test_format_ilike_with_negate_and_column(self, dummy_dialect: DummyDialect):
        """Tests NOT ILIKE expression with Column expression."""
        expr = ILIKEExpression(
            dummy_dialect, Column(dummy_dialect, "status"), "active%", negate=True
        )
        sql, params = expr.to_sql()

        assert '"status"' in sql
        assert "NOT LIKE" in sql
        assert params == ("active%",)

    def test_format_ilike_case_insensitive_matching(self, dummy_dialect: DummyDialect):
        """Tests that ILIKE pattern matching converts to lowercase."""
        expr = ILIKEExpression(dummy_dialect, Column(dummy_dialect, "name"), "John%")
        sql, params = expr.to_sql()

        assert "LIKE" in sql
        assert params == ("john%",)

    def test_format_ilike_string_column(self, dummy_dialect: DummyDialect):
        """Tests ILIKE with a bare string column name held by the expression."""
        expr = ILIKEExpression(dummy_dialect, "username", "admin%")
        sql, params = expr.to_sql()

        assert '"username"' in sql
        assert "LIKE" in sql
        assert params == ("admin%",)
