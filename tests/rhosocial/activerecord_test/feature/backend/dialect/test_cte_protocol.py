# tests/rhosocial/activerecord_test/feature/backend/dialect/test_cte_protocol.py
"""
Test for CTESupport protocol implementation.

This test creates a dialect that does not support CTEs and verifies that
the CTE support flag methods properly report lack of CTE support.
"""

from rhosocial.activerecord.backend.dialect import SQLDialectBase, CTEMixin, CTESupport
from rhosocial.activerecord.backend.expression import Column, QueryExpression
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression.query_sources import CTEExpression, WithQueryExpression
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


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
        from_=NamedRelationRef(dialect, Table(dialect, "users")),
    )

    # Create CTE expression
    CTEExpression(dialect, name="user_cte", query=query, columns=["id", "name"])

    # The dialect should report no CTE support
    assert not dialect.supports_basic_cte()


def test_with_query_expression_integration_reports_no_support():
    """Test WithQueryExpression integration with no-CTE dialect."""
    dialect = NoCTEDialect()

    # Create a simple query to use in CTE
    query = QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name")],
        from_=NamedRelationRef(dialect, Table(dialect, "users")),
    )

    # Create CTE
    cte = CTEExpression(dialect, name="user_cte", query=query, columns=["id", "name"])

    # Create main query that uses the CTE
    main_query = QueryExpression(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "user_cte")),
    )

    # Create WithQueryExpression
    WithQueryExpression(dialect, ctes=[cte], main_query=main_query)

    # The dialect should report no CTE support
    assert not dialect.supports_basic_cte()


def _simple_cte(dialect):
    query = QueryExpression(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "users")),
    )
    return CTEExpression(dialect, name="user_cte", query=query, columns=["id"])


def _probed(**answers):
    """A SQLiteDialect subclass whose CTE probes answer as ``answers``."""
    namespace = {
        name: (lambda self, answer=answer: answer)
        for name, answer in answers.items()
    }
    return type("ProbedDialect", (SQLiteDialect,), namespace)


def test_with_clause_renders_through_its_own_formatter():
    """The clause is a node: its spelling is ``format_with_clause``."""
    from rhosocial.activerecord.backend.expression.query_sources import WithClause

    dialect = SQLiteDialect()
    clause = WithClause(dialect, ctes=[_simple_cte(dialect)])

    assert clause.format_method == "format_with_clause"
    sql, params = clause.to_sql()
    assert sql == 'WITH "user_cte" ("id") AS (SELECT "id" FROM "users")'
    assert params == ()


def test_with_clause_spells_recursive():
    from rhosocial.activerecord.backend.expression.query_sources import WithClause

    dialect = SQLiteDialect()
    clause = WithClause(dialect, ctes=[_simple_cte(dialect)], recursive=True)

    assert clause.to_sql()[0] == 'WITH RECURSIVE "user_cte" ("id") AS (SELECT "id" FROM "users")'


def test_empty_with_clause_renders_nothing():
    from rhosocial.activerecord.backend.expression.query_sources import WithClause

    assert WithClause(SQLiteDialect()).to_sql() == ("", ())


def test_with_clause_refuses_a_dialect_without_basic_ctes():
    """The basic-CTE probe is consulted, not decorative."""
    import pytest
    from rhosocial.activerecord.backend.dialect.exceptions import (
        UnsupportedFeatureError,
    )
    from rhosocial.activerecord.backend.expression.query_sources import WithClause

    dialect = _probed(supports_basic_cte=False)()
    clause = WithClause(dialect, ctes=[_simple_cte(dialect)])

    with pytest.raises(UnsupportedFeatureError, match="basic CTE"):
        clause.to_sql()


def test_with_clause_refuses_recursive_without_support():
    """A RECURSIVE request on a dialect without recursive CTEs is refused by name."""
    import pytest
    from rhosocial.activerecord.backend.dialect.exceptions import (
        UnsupportedFeatureError,
    )
    from rhosocial.activerecord.backend.expression.query_sources import WithClause

    dialect = _probed(supports_recursive_cte=False)()
    clause = WithClause(dialect, ctes=[_simple_cte(dialect)], recursive=True)

    with pytest.raises(UnsupportedFeatureError, match="WITH RECURSIVE"):
        clause.to_sql()


def test_with_query_expression_composes_the_clause():
    """The query composition renders byte-identically through the node."""
    dialect = SQLiteDialect()
    main = QueryExpression(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "user_cte")),
    )
    with_query = WithQueryExpression(
        dialect, ctes=[_simple_cte(dialect)], main_query=main, recursive=True
    )

    assert with_query.to_sql()[0] == (
        'WITH RECURSIVE "user_cte" ("id") AS (SELECT "id" FROM "users") '
        'SELECT "id" FROM "user_cte"'
    )
