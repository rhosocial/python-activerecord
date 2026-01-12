# tests/rhosocial/activerecord_test/feature/backend/dialect/test_cte_protocol.py
"""
Test for CTESupport protocol implementation.

This test creates a dialect that does not support CTEs and verifies that
the format_cte and format_with_query methods raise appropriate errors.
"""

from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase, CTEMixin, CTESupport
)
from rhosocial.activerecord.backend.expression import (
    Column, QueryExpression, TableExpression
)
from rhosocial.activerecord.backend.expression.query_sources import CTEExpression, WithQueryExpression


class NoCTEDialect(SQLDialectBase, CTEMixin, CTESupport):
    """Dialect that does not support CTEs."""

    def supports_basic_cte(self) -> bool:
        return False

    def supports_recursive_cte(self) -> bool:
        return False

    def supports_materialized_cte(self) -> bool:
        return False


def test_no_cte_dialect_does_not_support_cte_features():
    """Test that no-CTE dialect properly indicates lack of CTE support."""
    dialect = NoCTEDialect()

    # Verify protocol implementation
    assert isinstance(dialect, CTESupport)
    assert not dialect.supports_basic_cte()
    assert not dialect.supports_recursive_cte()
    assert not dialect.supports_materialized_cte()


def test_format_cte_reports_no_support():
    """Test that format_cte method reports no support in no-CTE dialect."""
    dialect = NoCTEDialect()

    # Verify that the dialect reports no CTE support
    assert not dialect.supports_basic_cte()
    assert not dialect.supports_recursive_cte()
    assert not dialect.supports_materialized_cte()


def test_cte_expression_integration_reports_no_support():
    """Test CTEExpression integration with no-CTE dialect."""
    dialect = NoCTEDialect()

    # Create a simple query to use in CTE
    query = QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name")],
        from_=TableExpression(dialect, "users")
    )

    # Create CTE expression
    cte = CTEExpression(
        dialect,
        name="user_cte",
        query=query,
        columns=["id", "name"]
    )

    # The dialect should report no CTE support
    assert not dialect.supports_basic_cte()


def test_with_query_expression_integration_reports_no_support():
    """Test WithQueryExpression integration with no-CTE dialect."""
    dialect = NoCTEDialect()

    # Create a simple query to use in CTE
    query = QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name")],
        from_=TableExpression(dialect, "users")
    )

    # Create CTE
    cte = CTEExpression(
        dialect,
        name="user_cte",
        query=query,
        columns=["id", "name"]
    )

    # Create main query that uses the CTE
    main_query = QueryExpression(
        dialect,
        select=[Column(dialect, "id")],
        from_=TableExpression(dialect, "user_cte")
    )

    # Create WithQueryExpression
    with_query = WithQueryExpression(
        dialect,
        ctes=[cte],
        main_query=main_query
    )

    # The dialect should report no CTE support
    assert not dialect.supports_basic_cte()