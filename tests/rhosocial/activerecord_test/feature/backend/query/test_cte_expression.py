# tests/rhosocial/activerecord_test/feature/backend/query/test_cte_expression.py
"""CTEExpression construction and to_sql rendering.

Covers the three accepted query-parameter forms (BaseExpression, (sql, params)
tuple, and raw string) plus columns / materialized / dialect_options passthrough.
"""

import pytest

from rhosocial.activerecord.backend.expression.query_sources import CTEExpression
from rhosocial.activerecord.backend.expression import Column, Literal, TableExpression, QueryExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


def _query(dialect):
    return QueryExpression(dialect, select=[Column(dialect, "a")], from_=TableExpression(dialect, "tbl"))


class TestCTEExpressionQueryForms:
    """The three query-parameter forms."""

    def test_base_expression_query(self):
        d = DummyDialect()
        cte = CTEExpression(d, name="x", query=_query(d))
        sql, params = cte.to_sql()
        assert sql == '"x" AS (SELECT "a" FROM "tbl")'
        assert params == ()

    def test_tuple_query(self):
        d = DummyDialect()
        cte = CTEExpression(d, name="x", query=("SELECT ?", (5,)))
        sql, params = cte.to_sql()
        assert sql == '"x" AS (SELECT ?)'
        assert params == (5,)

    def test_tuple_query_list_params_normalized(self):
        d = DummyDialect()
        cte = CTEExpression(d, name="x", query=("SELECT ?", [7]))
        sql, params = cte.to_sql()
        assert params == (7,)
        assert isinstance(params, tuple)

    def test_raw_string_query(self):
        d = DummyDialect()
        cte = CTEExpression(d, name="x", query="SELECT 1")
        sql, params = cte.to_sql()
        assert sql == '"x" AS (SELECT 1)'
        assert params == ()


class TestCTEExpressionOptions:
    """columns / materialized / dialect_options rendering."""

    def test_columns(self):
        d = DummyDialect()
        cte = CTEExpression(d, name="x", query="SELECT 1", columns=["a", "b"])
        assert cte.to_sql()[0] == '"x" ("a", "b") AS (SELECT 1)'

    def test_materialized(self):
        d = DummyDialect()
        cte = CTEExpression(d, name="x", query="SELECT 1", materialized=True)
        assert cte.to_sql()[0] == '"x" AS MATERIALIZED (SELECT 1)'

    def test_not_materialized(self):
        d = DummyDialect()
        cte = CTEExpression(d, name="x", query="SELECT 1", materialized=False)
        assert cte.to_sql()[0] == '"x" AS NOT MATERIALIZED (SELECT 1)'

    def test_dialect_options_stored(self):
        d = DummyDialect()
        cte = CTEExpression(d, name="x", query="SELECT 1", dialect_options={"x": 1})
        assert cte.dialect_options == {"x": 1}

    def test_default_dialect_options_empty(self):
        d = DummyDialect()
        cte = CTEExpression(d, name="x", query="SELECT 1")
        assert cte.dialect_options == {}


class TestCTEExpressionRoundTrip:
    """Round-trip through an expression with parameters."""

    def test_param_passthrough(self):
        d = DummyDialect()
        inner = QueryExpression(
            d,
            select=[Column(d, "a")],
            from_=TableExpression(d, "tbl"),
            where=(Column(d, "id") == Literal(d, 42)),
        )
        cte = CTEExpression(d, name="x", query=inner)
        sql, params = cte.to_sql()
        assert "42" in sql or 42 in params
        assert sql.startswith('"x" AS (SELECT "a" FROM "tbl" WHERE "id" = ')