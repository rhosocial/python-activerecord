# tests/rhosocial/activerecord_test/feature/backend/query/test_cte_integration.py
"""End-to-end CTE execution against a real SQLite database.

Builds CTE/WithQuery expressions and executes them via the backend to verify
the generated SQL is correct and returns the expected rows.
"""

import pytest

from rhosocial.activerecord.backend.expression.query_sources import CTEExpression, WithQueryExpression
from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    TableExpression,
    QueryExpression,
    FunctionCall,
    GroupByHavingClause,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


@pytest.fixture
def backend():
    from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend

    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    backend.introspect_and_adapt()
    backend.execute(
        "CREATE TABLE items (id INTEGER PRIMARY KEY, cat TEXT, qty INTEGER)",
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )
    backend.execute_many(
        "INSERT INTO items (cat, qty) VALUES (?, ?)",
        [("a", 1), ("a", 2), ("b", 10)],
    )
    yield backend
    backend.disconnect()


class TestBasicCTEExecution:
    """Single non-recursive CTE."""

    def test_cat_totals(self, backend):
        dialect = backend.dialect
        cte = CTEExpression(
            dialect,
            name="cat_totals",
            query=QueryExpression(
                dialect,
                select=[Column(dialect, "cat"), FunctionCall(dialect, "SUM", Column(dialect, "qty"))],
                from_=TableExpression(dialect, "items"),
                group_by_having=GroupByHavingClause(dialect, group_by=[Column(dialect, "cat")]),
            ),
            columns=["cat", "total"],
        )
        main = QueryExpression(
            dialect,
            select=[Column(dialect, "cat"), Column(dialect, "total")],
            from_=TableExpression(dialect, "cat_totals"),
        )
        sql, params = WithQueryExpression(dialect, ctes=[cte], main_query=main).to_sql()
        rows = backend.fetch_all(sql, params=params)
        assert [(r["cat"], r["total"]) for r in rows] == [("a", 3), ("b", 10)]


class TestRecursiveCTEExecution:
    """Recursive CTE (1..5 counter)."""

    def test_counter(self, backend):
        dialect = backend.dialect
        cte = CTEExpression(
            dialect,
            name="cnt",
            query=("SELECT 1 AS x", ()),
        )
        # Build the recursive union by hand as raw SQL inside the CTE body.
        recursive_cte = CTEExpression(
            dialect,
            name="cnt",
            query=("SELECT 1 UNION ALL SELECT x+1 FROM cnt WHERE x < 5", ()),
            columns=["x"],
        )
        main = QueryExpression(dialect, select=[Column(dialect, "x")], from_=TableExpression(dialect, "cnt"))
        sql, params = WithQueryExpression(dialect, ctes=[recursive_cte], main_query=main, recursive=True).to_sql()
        rows = backend.fetch_all(sql, params=params)
        assert sorted(r["x"] for r in rows) == [1, 2, 3, 4, 5]


class TestMultipleCTEExecution:
    """Multiple CTEs with parameter passthrough."""

    def test_multi_with_params(self, backend):
        dialect = backend.dialect
        cte_a = CTEExpression(dialect, name="a", query=("SELECT ? AS v", (3,)))
        cte_b = CTEExpression(dialect, name="b", query=("SELECT ? AS w", (4,)))
        main = QueryExpression(
            dialect,
            select=[Column(dialect, "v"), Column(dialect, "w")],
            from_=[TableExpression(dialect, "a"), TableExpression(dialect, "b")],
        )
        sql, params = WithQueryExpression(dialect, ctes=[cte_a, cte_b], main_query=main).to_sql()
        rows = backend.fetch_all(sql, params=params)
        assert [(r["v"], r["w"]) for r in rows] == [(3, 4)]