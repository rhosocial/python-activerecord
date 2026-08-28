# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_sqlite_dialect_values_lateral.py
"""
Tests for SQLiteDialect.format_values_expression and LATERAL join handling.

SQLite rejects the ``AS alias(col, ...)`` column-list form for VALUES derived
tables, so ``format_values_expression`` must omit it and let the engine use the
implicit ``column1``/``column2`` names.

SQLite has never implemented the LATERAL keyword, so support is probed at
runtime (and cached) and lateral expressions must raise
UnsupportedFeatureError instead of emitting invalid SQL.
"""

import sqlite3

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    Column,
    QueryExpression,
    Subquery,
    TableExpression,
)
from rhosocial.activerecord.backend.expression.query_sources import (
    LateralExpression,
    ValuesExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def _probe_engine_supports_lateral() -> bool:
    """Probe the linked SQLite library directly, mirroring the dialect probe."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("SELECT 1 FROM (SELECT 1) AS t CROSS JOIN LATERAL (SELECT 1) AS s")
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


SUPPORTS_LATERAL = _probe_engine_supports_lateral()


@pytest.fixture
def dialect() -> SQLiteDialect:
    return SQLiteDialect()


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    yield connection
    connection.close()


class TestFormatValuesExpression:
    """Tests for the SQLite VALUES derived-table formatting override."""

    def test_with_alias_omits_column_name_list(self, dialect: SQLiteDialect):
        sql, params = dialect.format_values_expression([(1, "a"), (2, "b")], "v", ["id", "n"])
        assert sql == '(VALUES (?, ?), (?, ?)) AS "v"'
        assert params == (1, "a", 2, "b")

    def test_with_alias_without_column_names(self, dialect: SQLiteDialect):
        sql, params = dialect.format_values_expression([(1, "a")], "v", None)
        assert sql == '(VALUES (?, ?)) AS "v"'
        assert params == (1, "a")

    def test_without_alias(self, dialect: SQLiteDialect):
        sql, params = dialect.format_values_expression([(1,), (2,)], None, None)
        assert sql == "VALUES (?), (?)"
        assert params == (1, 2)

    def test_column_names_ignored_when_no_alias(self, dialect: SQLiteDialect):
        # The base implementation would emit invalid ``VALUES (?)(...)`` here;
        # the SQLite override must not.
        sql, _params = dialect.format_values_expression([(1, "a")], None, ["id", "n"])
        assert sql == "VALUES (?, ?)"

    def test_generated_sql_executes(self, dialect: SQLiteDialect, conn):
        sql, params = dialect.format_values_expression([(1, "a"), (2, "b")], "v", ["id", "n"])
        rows = conn.execute(f"SELECT * FROM {sql}", list(params)).fetchall()
        assert sorted(rows) == [(1, "a"), (2, "b")]

    def test_columns_get_implicit_names(self, dialect: SQLiteDialect, conn):
        sql, params = dialect.format_values_expression([(1, "a")], "v", ["id", "n"])
        cur = conn.execute(f"SELECT * FROM {sql}", list(params))
        assert [d[0] for d in cur.description] == ["column1", "column2"]

    def test_values_expression_roundtrip(self, dialect: SQLiteDialect, conn):
        expr = ValuesExpression(dialect, values=[(1, "x"), (2, "y")], alias="data", column_names=["id", "name"])
        sql, params = expr.to_sql()
        rows = conn.execute(f"SELECT * FROM {sql}", list(params)).fetchall()
        assert sorted(rows) == [(1, "x"), (2, "y")]


class TestSupportsLateralJoin:
    """Tests for the runtime LATERAL support probe."""

    @pytest.fixture(autouse=True)
    def reset_probe_cache(self):
        saved = SQLiteDialect._lateral_support
        SQLiteDialect._lateral_support = None
        yield
        SQLiteDialect._lateral_support = saved

    def test_matches_actual_engine_behavior(self, dialect: SQLiteDialect):
        assert dialect.supports_lateral_join() is SUPPORTS_LATERAL

    def test_result_is_cached(self, dialect: SQLiteDialect):
        first = dialect.supports_lateral_join()
        assert SQLiteDialect._lateral_support is first
        assert dialect.supports_lateral_join() is first

    def test_probe_failure_reports_unsupported(self, monkeypatch):
        def raise_connect(*args, **kwargs):
            raise RuntimeError("engine unavailable")

        monkeypatch.setattr(sqlite3, "connect", raise_connect)
        assert SQLiteDialect().supports_lateral_join() is False


@pytest.mark.skipif(SUPPORTS_LATERAL, reason="linked SQLite build supports LATERAL")
class TestLateralJoinUnsupported:
    """Tests that lateral expressions are rejected with a clear error."""

    def test_format_lateral_expression_raises(self, dialect: SQLiteDialect):
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            dialect.format_lateral_expression("(SELECT 1)", (), "lat", "CROSS")
        assert "LATERAL join" in str(excinfo.value)
        assert dialect.name in str(excinfo.value)

    def test_lateral_subquery_to_sql_raises(self, dialect: SQLiteDialect):
        subquery = Subquery(
            dialect,
            QueryExpression(dialect, select=[Column(dialect, "id")], from_=TableExpression(dialect, "t")),
        )
        expr = LateralExpression(dialect, expression=subquery, alias="lat_data")
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_lateral_values_source_raises(self, dialect: SQLiteDialect):
        values = ValuesExpression(dialect, values=[(1, "a")], alias="v")
        expr = LateralExpression(dialect, expression=values, alias="lat_values")
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()
