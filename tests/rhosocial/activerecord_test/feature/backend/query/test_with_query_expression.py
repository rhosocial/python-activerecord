# tests/rhosocial/activerecord_test/feature/backend/query/test_with_query_expression.py
"""WithQueryExpression: combining one or more CTEs with a main query.

Covers single/multiple CTEs, recursive flag, and parameter ordering across
CTE and main-query params.
"""

import pytest

from rhosocial.activerecord.backend.expression.query_sources import CTEExpression, WithQueryExpression
from rhosocial.activerecord.backend.expression import Column, Literal, TableExpression, QueryExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


def _cte(dialect, name, sql, params=()):
    return CTEExpression(dialect, name=name, query=(sql, params))


class TestWithQueryExpressionSingle:
    """Single CTE + main query."""

    def test_single(self):
        d = DummyDialect()
        cte = _cte(d, "x", "SELECT 1")
        main = QueryExpression(d, select=[Column(d, "a")], from_=TableExpression(d, "x"))
        wq = WithQueryExpression(d, ctes=[cte], main_query=main)
        sql, params = wq.to_sql()
        assert sql == 'WITH "x" AS (SELECT 1) SELECT "a" FROM "x"'
        assert params == ()

    def test_recursive(self):
        d = DummyDialect()
        cte = _cte(d, "counter", "SELECT 1")
        main = QueryExpression(d, select=[Column(d, "a")], from_=TableExpression(d, "counter"))
        wq = WithQueryExpression(d, ctes=[cte], main_query=main, recursive=True)
        assert wq.to_sql()[0].startswith('WITH RECURSIVE "counter" AS (SELECT 1)')


class TestWithQueryExpressionMultiple:
    """Multiple CTEs + parameter ordering."""

    def test_multiple_ctes(self):
        d = DummyDialect()
        cte1 = _cte(d, "a", "SELECT ?", (1,))
        cte2 = _cte(d, "b", "SELECT ?", (2,))
        main = QueryExpression(
            d,
            select=[Column(d, "v")],
            from_=TableExpression(d, "b"),
            where=(Column(d, "id") == Literal(d, 3)),
        )
        wq = WithQueryExpression(d, ctes=[cte1, cte2], main_query=main)
        sql, params = wq.to_sql()
        assert sql.startswith('WITH "a" AS (SELECT ?), "b" AS (SELECT ?)')
        assert params == (1, 2, 3)

    def test_param_order_cte_then_main(self):
        d = DummyDialect()
        cte = CTEExpression(d, name="x", query=("SELECT ?", (10,)))
        main = QueryExpression(
            d,
            select=[Column(d, "a")],
            from_=TableExpression(d, "x"),
            where=(Column(d, "id") == Literal(d, 99)),
        )
        sql, params = WithQueryExpression(d, ctes=[cte], main_query=main).to_sql()
        assert params == (10, 99)
        assert sql == 'WITH "x" AS (SELECT ?) SELECT "a" FROM "x" WHERE "id" = ?'


class TestWithQueryExpressionEmpty:
    """Edge case: no CTEs."""

    def test_no_ctes_returns_main_only(self):
        d = DummyDialect()
        main = QueryExpression(d, select=[Column(d, "a")], from_=TableExpression(d, "t"))
        wq = WithQueryExpression(d, ctes=[], main_query=main)
        sql, params = wq.to_sql()
        assert sql == 'SELECT "a" FROM "t"'
        assert params == ()

    def test_dialect_options_stored(self):
        d = DummyDialect()
        cte = _cte(d, "x", "SELECT 1")
        main = QueryExpression(d, select=[Column(d, "a")], from_=TableExpression(d, "x"))
        wq = WithQueryExpression(d, ctes=[cte], main_query=main, dialect_options={"opt": 1})
        assert wq.dialect_options == {"opt": 1}