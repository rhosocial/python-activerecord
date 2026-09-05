# tests/rhosocial/activerecord_test/feature/backend/query/test_cte_integration_async.py
"""Async twin of test_cte_integration.py: CTE execution on AsyncSQLiteBackend."""

import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.expression.query_sources import CTEExpression, WithQueryExpression
from rhosocial.activerecord.backend.expression import (
    Column,
    TableExpression,
    QueryExpression,
    FunctionCall,
    GroupByHavingClause,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


@pytest_asyncio.fixture
async def backend():
    from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

    backend = AsyncSQLiteBackend(database=":memory:")
    await backend.connect()
    await backend.introspect_and_adapt()
    await backend.execute(
        "CREATE TABLE items (id INTEGER PRIMARY KEY, cat TEXT, qty INTEGER)",
        options=ExecutionOptions(stmt_type=StatementType.DDL),
    )
    await backend.execute_many(
        "INSERT INTO items (cat, qty) VALUES (?, ?)",
        [("a", 1), ("a", 2), ("b", 10)],
    )
    yield backend
    await backend.disconnect()


class TestAsyncBasicCTEExecution:
    @pytest.mark.asyncio
    async def test_cat_totals(self, backend):
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
        rows = await backend.fetch_all(sql, params=params)
        assert [(r["cat"], r["total"]) for r in rows] == [("a", 3), ("b", 10)]


class TestAsyncRecursiveCTEExecution:
    @pytest.mark.asyncio
    async def test_counter(self, backend):
        dialect = backend.dialect
        recursive_cte = CTEExpression(
            dialect,
            name="cnt",
            query=("SELECT 1 UNION ALL SELECT x+1 FROM cnt WHERE x < 5", ()),
            columns=["x"],
        )
        main = QueryExpression(dialect, select=[Column(dialect, "x")], from_=TableExpression(dialect, "cnt"))
        sql, params = WithQueryExpression(dialect, ctes=[recursive_cte], main_query=main, recursive=True).to_sql()
        rows = await backend.fetch_all(sql, params=params)
        assert sorted(r["x"] for r in rows) == [1, 2, 3, 4, 5]


class TestAsyncMultipleCTEExecution:
    @pytest.mark.asyncio
    async def test_multi_with_params(self, backend):
        dialect = backend.dialect
        cte_a = CTEExpression(dialect, name="a", query=("SELECT ? AS v", (3,)))
        cte_b = CTEExpression(dialect, name="b", query=("SELECT ? AS w", (4,)))
        main = QueryExpression(
            dialect,
            select=[Column(dialect, "v"), Column(dialect, "w")],
            from_=[TableExpression(dialect, "a"), TableExpression(dialect, "b")],
        )
        sql, params = WithQueryExpression(dialect, ctes=[cte_a, cte_b], main_query=main).to_sql()
        rows = await backend.fetch_all(sql, params=params)
        assert [(r["v"], r["w"]) for r in rows] == [(3, 4)]