# tests/rhosocial/activerecord_test/feature/backend/query/test_datetime_interval_explain_examples_async.py
"""Async twin of test_datetime_interval_explain_examples.py: EXPLAIN QUERY PLAN index-usage checks run on AsyncSQLiteBackend."""
import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonPredicate,
    Literal,
    LogicalPredicate,
    QueryExpression,
    TableExpression,
)
from rhosocial.activerecord.backend.expression.functions import date_add, date_diff, extract
from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
from rhosocial.activerecord.backend.expression.statements import ExplainOptions, ExplainType
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend, SQLiteExplainQueryPlanResult
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


_SETUP_STATEMENTS = [
    """CREATE TABLE temporal_events (
        id INTEGER PRIMARY KEY,
        category TEXT NOT NULL,
        created_at TEXT NOT NULL,
        started_at TEXT NOT NULL,
        ended_at TEXT NOT NULL
    )""",
    "CREATE INDEX idx_temporal_events_created_at ON temporal_events(created_at)",
    "CREATE INDEX idx_temporal_events_started_ended ON temporal_events(started_at, ended_at)",
    "CREATE INDEX idx_temporal_events_category_created ON temporal_events(category, created_at)",
    """INSERT INTO temporal_events (category, created_at, started_at, ended_at) VALUES
        ('deploy', '2026-06-01 09:00:00', '2026-06-01 09:10:00', '2026-06-01 09:40:00'),
        ('deploy', '2026-06-04 10:00:00', '2026-06-04 10:00:00', '2026-06-04 10:30:00'),
        ('deploy', '2026-06-05 11:00:00', '2026-06-05 11:15:00', '2026-06-05 11:45:00'),
        ('billing', '2026-01-10 08:00:00', '2026-01-10 08:00:00', '2026-01-10 08:20:00'),
        ('billing', '2026-02-12 13:00:00', '2026-02-12 13:05:00', '2026-02-12 13:35:00'),
        ('report', '2026-03-01 07:00:00', '2026-03-01 07:15:00', '2026-03-01 08:00:00'),
        ('report', '2026-04-15 18:00:00', '2026-04-15 18:30:00', '2026-04-15 19:00:00'),
        ('maintenance', '2025-12-31 23:00:00', '2025-12-31 23:00:00', '2025-12-31 23:30:00')
    """,
]


@pytest_asyncio.fixture()
async def temporal_backend():
    backend = AsyncSQLiteBackend(database=":memory:")
    await backend.connect()
    for statement in _SETUP_STATEMENTS:
        await backend.execute(statement, options=ExecutionOptions(stmt_type=StatementType.DDL))
    yield backend
    await backend.disconnect()


@pytest.fixture()
def query_plan_options():
    return ExplainOptions(type=ExplainType.QUERY_PLAN)


def _combined_plan_detail(result: SQLiteExplainQueryPlanResult) -> str:
    return " ".join(row.detail.upper() for row in result.rows)


def _range_filter(dialect, column_name: str, start: str, end: str):
    return LogicalPredicate(
        dialect,
        "AND",
        ComparisonPredicate(dialect, ">=", Column(dialect, column_name), Literal(dialect, start)),
        ComparisonPredicate(dialect, "<", Column(dialect, column_name), Literal(dialect, end)),
    )


def _category_created_filter(dialect):
    return LogicalPredicate(
        dialect,
        "AND",
        ComparisonPredicate(dialect, "=", Column(dialect, "category"), Literal(dialect, "deploy")),
        _range_filter(
            dialect,
            "created_at",
            "2026-06-01 00:00:00",
            "2026-07-01 00:00:00",
        ),
    )


@pytest.mark.asyncio
async def test_created_at_range_uses_datetime_index(temporal_backend, query_plan_options):
    dialect = temporal_backend.dialect
    query = QueryExpression(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "created_at")],
        from_=TableExpression(dialect, "temporal_events"),
        where=_range_filter(
            dialect,
            "created_at",
            "2026-06-01 00:00:00",
            "2026-07-01 00:00:00",
        ),
    )
    result = await temporal_backend.explain(query, query_plan_options)

    assert isinstance(result, SQLiteExplainQueryPlanResult)
    detail = _combined_plan_detail(result)
    assert "SEARCH" in detail
    assert "TEMPORAL_EVENTS" in detail
    assert "IDX_TEMPORAL_EVENTS_CREATED_AT" in detail
    assert result.is_index_used is True
    assert result.is_full_scan is False


@pytest.mark.asyncio
async def test_started_at_range_uses_composite_datetime_index(temporal_backend, query_plan_options):
    dialect = temporal_backend.dialect
    query = QueryExpression(
        dialect,
        select=[Column(dialect, "started_at"), Column(dialect, "ended_at")],
        from_=TableExpression(dialect, "temporal_events"),
        where=_range_filter(
            dialect,
            "started_at",
            "2026-06-04 00:00:00",
            "2026-06-06 00:00:00",
        ),
    )
    result = await temporal_backend.explain(query, query_plan_options)

    detail = _combined_plan_detail(result)
    assert "SEARCH" in detail
    assert "IDX_TEMPORAL_EVENTS_STARTED_ENDED" in detail
    assert result.is_index_used is True
    assert result.is_full_scan is False


@pytest.mark.asyncio
async def test_datetime_interval_expressions_work_with_indexed_filter(temporal_backend, query_plan_options):
    dialect = temporal_backend.dialect
    query = QueryExpression(
        dialect,
        select=[
            Column(dialect, "id"),
            extract(dialect, "year", Column(dialect, "created_at")).as_("created_year"),
            date_add(dialect, Column(dialect, "started_at"), 30, "minute").as_("starts_plus_30m"),
            date_diff(dialect, "minute", Column(dialect, "started_at"), Column(dialect, "ended_at")).as_(
                "duration_minutes"
            ),
        ],
        from_=TableExpression(dialect, "temporal_events"),
        where=_category_created_filter(dialect),
        order_by=OrderByClause(dialect, [(Column(dialect, "id"), "ASC")]),
    )

    explain_result = await temporal_backend.explain(query, query_plan_options)
    detail = _combined_plan_detail(explain_result)
    assert "SEARCH" in detail
    assert "IDX_TEMPORAL_EVENTS_CATEGORY_CREATED" in detail
    assert explain_result.is_index_used is True

    query_result = await temporal_backend.execute(
        *query.to_sql(),
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    rows = query_result.data

    assert rows is not None
    assert len(rows) == 3
    assert rows[0]["created_year"] == 2026
    assert rows[1]["starts_plus_30m"] == "2026-06-04 10:30:00"
    assert round(rows[1]["duration_minutes"]) == 30
