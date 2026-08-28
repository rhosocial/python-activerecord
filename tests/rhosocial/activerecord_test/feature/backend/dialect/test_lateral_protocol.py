# tests/rhosocial/activerecord_test/feature/backend/dialect/test_lateral_protocol.py
"""
Test for LateralJoinSupport protocol implementation.

This test creates a dialect that does not support lateral joins and table functions and verifies that
the corresponding formatting methods raise appropriate errors.
"""

import pytest

from rhosocial.activerecord.backend.dialect import SQLDialectBase, LateralJoinMixin, LateralJoinSupport
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.mixins import IdentifierMixin, DQLMixin, ExpressionMixin
from rhosocial.activerecord.backend.expression import Column, QueryExpression, TableExpression, Subquery
from rhosocial.activerecord.backend.expression.query_sources import LateralExpression, TableFunctionExpression


class NoLateralDialect(
    SQLDialectBase, IdentifierMixin, ExpressionMixin, DQLMixin, LateralJoinMixin, LateralJoinSupport
):
    """Dialect that does not support lateral joins and table functions."""

    def supports_lateral_join(self) -> bool:
        return False


def test_no_lateral_dialect_does_not_support_lateral_features():
    """Test that no-lateral dialect properly indicates lack of lateral join features."""
    dialect = NoLateralDialect()

    # Verify protocol implementation
    assert isinstance(dialect, LateralJoinSupport)
    assert not dialect.supports_lateral_join()


def test_format_lateral_expression_reports_no_support():
    """Test that format_lateral_expression raises when the dialect reports no support."""
    dialect = NoLateralDialect()

    assert not dialect.supports_lateral_join()
    with pytest.raises(UnsupportedFeatureError) as excinfo:
        dialect.format_lateral_expression("(SELECT 1)", (), "lateral_data", "CROSS")
    assert "LATERAL join" in str(excinfo.value)


def test_lateral_expression_integration_reports_no_support():
    """Test LateralExpression integration with no-lateral dialect."""
    dialect = NoLateralDialect()

    # Create a subquery to use in lateral expression
    subquery = Subquery(
        dialect, QueryExpression(dialect, select=[Column(dialect, "id")], from_=TableExpression(dialect, "other_table"))
    )

    # Create LateralExpression
    LateralExpression(dialect, expression=subquery, alias="lateral_data")

    # The dialect should report no lateral join support
    assert not dialect.supports_lateral_join()


def test_table_function_expression_integration_reports_no_support():
    """Test TableFunctionExpression integration with no-lateral dialect."""
    dialect = NoLateralDialect()

    # Create a mock expression to use as argument
    class MockArg:
        def to_sql(self):
            return "array_col", ()

    mock_arg = MockArg()

    # Create TableFunctionExpression
    TableFunctionExpression(dialect, "UNNEST", mock_arg, alias="unested", column_names=["value"])

    # The dialect should report no lateral join support (which covers table functions)
    assert not dialect.supports_lateral_join()
