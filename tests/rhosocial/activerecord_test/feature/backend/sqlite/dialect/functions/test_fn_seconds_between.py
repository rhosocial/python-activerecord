# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/functions/test_fn_seconds_between.py
"""Signed seconds between two instants, executed on SQLite.

``seconds_between`` is a duration, so the cases that matter are the ones a
component sum gets wrong: the sign, the zero, the fraction and the boundaries
where a month or a year changes. Each assertion runs the rendered SQL against
an in-memory database rather than comparing SQL text alone.
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    QueryStatement,
    seconds_between,
)
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


@pytest.fixture
def backend():
    """An in-memory SQLite backend with no tables."""
    instance = SQLiteBackend(database=":memory:")
    instance.connect()
    instance.introspect_and_adapt()
    yield instance
    instance.disconnect()


def _elapsed(backend, start: str, end: str) -> float:
    """Run ``seconds_between(start, end)`` and return the scalar."""
    dialect = backend.dialect
    expr = seconds_between(dialect, Literal(dialect, start), Literal(dialect, end))
    query = QueryStatement(dialect, select=[expr.as_("seconds")])
    sql, params = query.to_sql()
    result = backend.execute(
        sql,
        params,
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    return result.data[0]["seconds"]


class TestSecondsBetweenExecution:
    """The value the SQLite spelling actually produces."""

    @pytest.mark.parametrize(
        "start,end,expected",
        [
            ("2026-06-04 10:00:00", "2026-06-04 10:00:00", 0.0),
            ("2026-06-04 10:00:00", "2026-06-04 11:00:00", 3600.0),
            ("2026-06-04 11:00:00", "2026-06-04 10:00:00", -3600.0),
            ("2026-01-31 23:59:59", "2026-02-01 00:00:00", 1.0),
            ("2025-12-31 12:00:00", "2026-01-01 12:00:00", 86400.0),
            ("2026-06-04 10:00:00.000", "2026-06-04 10:00:00.500", 0.5),
            ("2026-06-04 10:00:00.250", "2026-06-04 10:00:00.000", -0.25),
        ],
    )
    def test_interval(self, backend, start: str, end: str, expected: float):
        # ``julianday`` is a double holding days, so a second lands around
        # 1e-5 of a day; the fraction that survives is accurate to ~0.1 ms.
        assert _elapsed(backend, start, end) == pytest.approx(expected, abs=1e-4)

    def test_columns_in_a_row(self, backend):
        """The same question asked of two columns, not two literals."""
        backend.executescript(
            """
            CREATE TABLE spans (
                id INTEGER PRIMARY KEY,
                started_at TEXT,
                ended_at TEXT
            );
            INSERT INTO spans (started_at, ended_at) VALUES
                ('2026-03-01 00:00:00', '2026-03-02 00:00:00'),
                ('2026-03-02 00:00:00', '2026-03-01 00:00:00'),
                ('2026-03-01 00:00:00.750', '2026-03-01 00:00:01.000');
            """
        )

        dialect = backend.dialect
        expr = seconds_between(
            dialect,
            Column(dialect, "started_at"),
            Column(dialect, "ended_at"),
        )
        query = QueryStatement(
            dialect,
            select=[expr.as_("seconds"), Column(dialect, "id")],
            from_="spans",
        )
        sql, params = query.to_sql()
        result = backend.execute(
            sql,
            params,
            options=ExecutionOptions(stmt_type=StatementType.DQL),
        )

        rows = {row["id"]: row["seconds"] for row in result.data}
        assert rows[1] == pytest.approx(86400.0, abs=1e-4)
        assert rows[2] == pytest.approx(-86400.0, abs=1e-4)
        assert rows[3] == pytest.approx(0.25, abs=1e-4)
