# tests/rhosocial/activerecord_test/feature/backend/dialect/test_cte_protocol.py
"""
Test for CTESupport protocol implementation.

This test creates a dialect that does not support CTEs and verifies that
the CTE support flag methods properly report lack of CTE support.
"""

from rhosocial.activerecord.backend.dialect import SQLDialectBase, CTEMixin, CTESupport
from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonPredicate,
    Literal,
    QueryStatement,
)
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression.query_sources import CTEClause, WithStatement
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


def test_cte_clause_integration_reports_no_support():
    """Test CTEClause integration with no-CTE dialect."""
    dialect = NoCTEDialect()

    # Create a simple query to use in CTE
    query = QueryStatement(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name")],
        from_=NamedRelationRef(dialect, Table(dialect, "users")),
    )

    # Create CTE expression
    CTEClause(dialect, name="user_cte", query=query, columns=["id", "name"])

    # The dialect should report no CTE support
    assert not dialect.supports_basic_cte()


def test_with_statement_integration_reports_no_support():
    """Test WithStatement integration with no-CTE dialect."""
    dialect = NoCTEDialect()

    # Create a simple query to use in CTE
    query = QueryStatement(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name")],
        from_=NamedRelationRef(dialect, Table(dialect, "users")),
    )

    # Create CTE
    cte = CTEClause(dialect, name="user_cte", query=query, columns=["id", "name"])

    # Create main query that uses the CTE
    main_query = QueryStatement(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "user_cte")),
    )

    # Create WithStatement
    WithStatement(dialect, ctes=[cte], query=main_query)

    # The dialect should report no CTE support
    assert not dialect.supports_basic_cte()


def _simple_cte(dialect):
    query = QueryStatement(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "users")),
    )
    return CTEClause(dialect, name="user_cte", query=query, columns=["id"])


def _probed(**answers):
    """A SQLiteDialect subclass whose CTE probes answer as ``answers``."""
    namespace = {
        name: (lambda self, answer=answer: answer)
        for name, answer in answers.items()
    }
    return type("ProbedDialect", (SQLiteDialect,), namespace)


def _simple_main_query(dialect):
    return QueryStatement(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "user_cte")),
    )


def test_cte_clause_is_the_node_for_one_definition():
    """A single CTE definition renders through its own formatter."""
    dialect = SQLiteDialect()
    cte = _simple_cte(dialect)

    assert cte.format_method == "format_cte_clause"
    sql, params = cte.to_sql()
    assert sql == '"user_cte" ("id") AS (SELECT "id" FROM "users")'
    assert params == ()


def test_with_statement_renders_through_its_own_formatter():
    """The statement is a node: its spelling is ``format_with_statement``."""
    dialect = SQLiteDialect()
    stmt = WithStatement(dialect, ctes=[_simple_cte(dialect)], query=_simple_main_query(dialect))

    assert stmt.format_method == "format_with_statement"
    sql, params = stmt.to_sql()
    assert sql == (
        'WITH "user_cte" ("id") AS (SELECT "id" FROM "users") '
        'SELECT "id" FROM "user_cte"'
    )
    assert params == ()


def test_with_statement_spells_recursive():
    dialect = SQLiteDialect()
    stmt = WithStatement(
        dialect, ctes=[_simple_cte(dialect)], query=_simple_main_query(dialect), recursive=True
    )

    assert stmt.to_sql()[0] == (
        'WITH RECURSIVE "user_cte" ("id") AS (SELECT "id" FROM "users") '
        'SELECT "id" FROM "user_cte"'
    )


def test_with_statement_without_ctes_renders_the_bare_query():
    """No CTE definitions: the statement is the query, so a plain query needs no wrapper."""
    dialect = SQLiteDialect()
    stmt = WithStatement(dialect, query=_simple_main_query(dialect))

    assert stmt.to_sql()[0] == 'SELECT "id" FROM "user_cte"'


def test_with_statement_refuses_a_dialect_without_basic_ctes():
    """The basic-CTE probe is consulted, not decorative."""
    import pytest
    from rhosocial.activerecord.backend.dialect.exceptions import (
        UnsupportedFeatureError,
    )

    dialect = _probed(supports_basic_cte=False)()
    stmt = WithStatement(dialect, ctes=[_simple_cte(dialect)], query=_simple_main_query(dialect))

    with pytest.raises(UnsupportedFeatureError, match="basic CTE"):
        stmt.to_sql()


def test_with_statement_refuses_recursive_without_support():
    """A RECURSIVE request on a dialect without recursive CTEs is refused by name."""
    import pytest
    from rhosocial.activerecord.backend.dialect.exceptions import (
        UnsupportedFeatureError,
    )

    dialect = _probed(supports_recursive_cte=False)()
    stmt = WithStatement(
        dialect, ctes=[_simple_cte(dialect)], query=_simple_main_query(dialect), recursive=True
    )

    with pytest.raises(UnsupportedFeatureError, match="WITH RECURSIVE"):
        stmt.to_sql()


def test_with_statement_places_cte_params_before_query_params():
    """Parameter order follows the rendered text order."""
    dialect = SQLiteDialect()
    cte = CTEClause(
        dialect,
        name="user_cte",
        query=QueryStatement(
            dialect,
            select=[Column(dialect, "id")],
            from_=NamedRelationRef(dialect, Table(dialect, "users")),
            where=ComparisonPredicate(dialect, "=", Column(dialect, "id"), Literal(dialect, 7)),
        ),
    )
    main = QueryStatement(
        dialect,
        select=[Column(dialect, "id")],
        from_=NamedRelationRef(dialect, Table(dialect, "user_cte")),
        where=ComparisonPredicate(dialect, "=", Column(dialect, "id"), Literal(dialect, 9)),
    )

    assert WithStatement(dialect, ctes=[cte], query=main).to_sql()[1] == (7, 9)
