# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_batch_dml.py
"""
Integration tests for execute_batch_dml with real SQLite backend.

Tests cover:
  - INSERT / UPDATE / DELETE execution paths
  - executemany path (no RETURNING) and per-row execute path (with RETURNING)
  - batch_size boundary conditions
  - Parameter type conversion
  - Tier 2 (old SQLite version) RETURNING fast-fail

For async tests, see sqlite_async/test_batch_dml.py.
"""
import pytest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4, UUID

from rhosocial.activerecord.backend.expression import (
    Column, Literal, InsertExpression, UpdateExpression, DeleteExpression,
    TableExpression, ValuesSource, ComparisonPredicate,
    ReturningClause,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.result import QueryResult


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

CREATE_USERS_SQL = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TEXT
    );
"""

CREATE_TYPED_SQL = """
    CREATE TABLE typed_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uuid_col TEXT,
        dt_col TEXT,
        dec_col TEXT,
        bool_col INTEGER
    );
"""


@pytest.fixture
def backend_with_users(sqlite_backend):
    """SQLite backend with users table created."""
    sqlite_backend.executescript(CREATE_USERS_SQL)
    return sqlite_backend


@pytest.fixture
def backend_with_typed(sqlite_backend):
    """SQLite backend with typed_data table for type conversion tests."""
    sqlite_backend.executescript(CREATE_TYPED_SQL)
    return sqlite_backend


@pytest.fixture
def backend_no_returning(tmp_path):
    """SQLite backend with dialect downgraded to 3.30.0 (no RETURNING)."""
    from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
    backend = SQLiteBackend(database=str(tmp_path / "tier2.db"))
    backend._dialect = SQLiteDialect(version=(3, 30, 0))
    backend.connect()
    backend.executescript(CREATE_USERS_SQL)
    yield backend
    backend.disconnect()


# ──────────────────────────────────────────────
# Sync Fixtures
# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _make_insert_expr(dialect, name, email):
    """Build a single-row InsertExpression for users table."""
    source = ValuesSource(dialect, values_list=[
        [Literal(dialect, name), Literal(dialect, email)]
    ])
    return InsertExpression(dialect, into="users", columns=["name", "email"], source=source)


def _make_update_expr(dialect, pk_val, new_name):
    """Build an UpdateExpression: SET name=? WHERE id=?"""
    return UpdateExpression(
        dialect, table="users",
        assignments={"name": Literal(dialect, new_name)},
        where=ComparisonPredicate(dialect, "=", Column(dialect, "id"), Literal(dialect, pk_val)),
    )


def _make_delete_expr(dialect, pk_val):
    """Build a DeleteExpression: DELETE FROM users WHERE id=?"""
    return DeleteExpression(
        dialect, table="users",
        where=ComparisonPredicate(dialect, "=", Column(dialect, "id"), Literal(dialect, pk_val)),
    )


def _count_rows(backend, table="users"):
    """SELECT COUNT(*) helper."""
    from rhosocial.activerecord.backend.options import ExecutionOptions
    from rhosocial.activerecord.backend.schema import StatementType
    result = backend.execute(
        f"SELECT COUNT(*) as cnt FROM {table}", None,
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    return result.data[0]["cnt"]


def _collect_batches(iterator):
    """Consume an Iterator[BatchDMLResult] into a list."""
    return list(iterator)


# ══════════════════════════════════════════════
# Sync: INSERT
# ══════════════════════════════════════════════

class TestBatchDMLInsert:
    """Sync INSERT tests."""

    @pytest.mark.parametrize("row_count, batch_size, expected_batches", [
        pytest.param(10, 100, 1, id="all_in_one_batch"),
        pytest.param(10, 10, 1, id="exact_batch_boundary"),
        pytest.param(11, 5, 3, id="uneven_batches_5_5_1"),
        pytest.param(1, 100, 1, id="single_row"),
        pytest.param(3, 1, 3, id="batch_size_1"),
    ])
    def test_insert_batch_counts(self, backend_with_users, row_count, batch_size, expected_batches):
        dialect = backend_with_users.dialect
        exprs = [_make_insert_expr(dialect, f"user{i}", f"user{i}@test.com") for i in range(row_count)]

        batches = _collect_batches(
            backend_with_users.execute_batch_dml(exprs, batch_size=batch_size)
        )

        assert len(batches) == expected_batches
        total_affected = sum(b.total_affected_rows for b in batches)
        assert total_affected == row_count
        assert _count_rows(backend_with_users) == row_count

    def test_insert_batch_index_increments(self, backend_with_users):
        dialect = backend_with_users.dialect
        exprs = [_make_insert_expr(dialect, f"u{i}", f"u{i}@t.com") for i in range(7)]

        batches = _collect_batches(
            backend_with_users.execute_batch_dml(exprs, batch_size=3)
        )

        assert [b.batch_index for b in batches] == [0, 1, 2]
        assert [b.batch_size for b in batches] == [3, 3, 1]

    def test_insert_no_returning_results_empty(self, backend_with_users):
        dialect = backend_with_users.dialect
        exprs = [_make_insert_expr(dialect, f"u{i}", f"u{i}@t.com") for i in range(3)]

        batches = _collect_batches(
            backend_with_users.execute_batch_dml(exprs)
        )

        for b in batches:
            assert b.has_returning is False
            assert b.results == []

    def test_insert_with_returning(self, backend_with_users):
        dialect = backend_with_users.dialect
        exprs = [_make_insert_expr(dialect, f"u{i}", f"u{i}@t.com") for i in range(5)]

        batches = _collect_batches(
            backend_with_users.execute_batch_dml(
                exprs, batch_size=3, returning_columns=["id", "name"],
            )
        )

        assert len(batches) == 2  # 3 + 2
        for b in batches:
            assert b.has_returning is True
            assert len(b.results) == b.batch_size
            for r in b.results:
                assert r.data is not None
                assert len(r.data) == 1  # single row per INSERT
                assert "id" in r.data[0]
                assert "name" in r.data[0]

    def test_insert_returning_single_column(self, backend_with_users):
        dialect = backend_with_users.dialect
        exprs = [_make_insert_expr(dialect, f"u{i}", f"u{i}@t.com") for i in range(3)]

        batches = _collect_batches(
            backend_with_users.execute_batch_dml(exprs, returning_columns=["id"])
        )

        ids = [r.data[0]["id"] for b in batches for r in b.results]
        assert len(ids) == 3
        assert len(set(ids)) == 3  # all unique

    def test_empty_expressions(self, backend_with_users):
        batches = _collect_batches(
            backend_with_users.execute_batch_dml([])
        )
        assert batches == []


# ══════════════════════════════════════════════
# Sync: UPDATE
# ══════════════════════════════════════════════

class TestBatchDMLUpdate:
    """Sync UPDATE tests."""

    def _seed(self, backend, n=10):
        """Insert n rows as seed data, return list of ids."""
        dialect = backend.dialect
        for i in range(n):
            expr = _make_insert_expr(dialect, f"user{i}", f"user{i}@test.com")
            sql, params = expr.to_sql()
            from rhosocial.activerecord.backend.options import ExecutionOptions
            from rhosocial.activerecord.backend.schema import StatementType
            backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DML))
        return list(range(1, n + 1))

    def test_update_all_rows(self, backend_with_users):
        ids = self._seed(backend_with_users)
        dialect = backend_with_users.dialect
        exprs = [_make_update_expr(dialect, pk, f"updated{pk}") for pk in ids]

        batches = _collect_batches(
            backend_with_users.execute_batch_dml(exprs, batch_size=5)
        )

        total = sum(b.total_affected_rows for b in batches)
        assert total == 10
        assert len(batches) == 2  # 5 + 5

    def test_update_with_returning(self, backend_with_users):
        ids = self._seed(backend_with_users, n=3)
        dialect = backend_with_users.dialect
        exprs = [_make_update_expr(dialect, pk, f"new{pk}") for pk in ids]

        batches = _collect_batches(
            backend_with_users.execute_batch_dml(
                exprs, returning_columns=["id", "name"],
            )
        )

        for b in batches:
            assert b.has_returning is True
            for r in b.results:
                assert r.data is not None
                row = r.data[0]
                assert row["name"].startswith("new")


# ══════════════════════════════════════════════
# Sync: DELETE
# ══════════════════════════════════════════════

class TestBatchDMLDelete:
    """Sync DELETE tests."""

    def _seed(self, backend, n=10):
        dialect = backend.dialect
        for i in range(n):
            expr = _make_insert_expr(dialect, f"user{i}", f"user{i}@test.com")
            sql, params = expr.to_sql()
            from rhosocial.activerecord.backend.options import ExecutionOptions
            from rhosocial.activerecord.backend.schema import StatementType
            backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DML))
        return list(range(1, n + 1))

    def test_delete_all_rows(self, backend_with_users):
        ids = self._seed(backend_with_users)
        dialect = backend_with_users.dialect
        exprs = [_make_delete_expr(dialect, pk) for pk in ids]

        batches = _collect_batches(
            backend_with_users.execute_batch_dml(exprs, batch_size=4)
        )

        total = sum(b.total_affected_rows for b in batches)
        assert total == 10
        assert _count_rows(backend_with_users) == 0
        assert len(batches) == 3  # 4 + 4 + 2

    def test_delete_with_returning(self, backend_with_users):
        ids = self._seed(backend_with_users, n=3)
        dialect = backend_with_users.dialect
        exprs = [_make_delete_expr(dialect, pk) for pk in ids]

        batches = _collect_batches(
            backend_with_users.execute_batch_dml(
                exprs, returning_columns=["id", "name"],
            )
        )

        deleted_names = [r.data[0]["name"] for b in batches for r in b.results]
        assert set(deleted_names) == {"user0", "user1", "user2"}


# ══════════════════════════════════════════════
# Sync: Type conversion (executemany path)
# ══════════════════════════════════════════════

class TestBatchDMLTypeConversion:
    """Verify parameter type conversion works in the executemany path."""

    def test_uuid_and_datetime(self, backend_with_typed):
        dialect = backend_with_typed.dialect
        test_uuid = uuid4()
        test_dt = datetime(2025, 1, 15, 10, 30, 0)

        source = ValuesSource(dialect, values_list=[
            [Literal(dialect, str(test_uuid)), Literal(dialect, test_dt.isoformat()),
             Literal(dialect, "123.45"), Literal(dialect, 1)]
        ])
        exprs = [
            InsertExpression(dialect, into="typed_data",
                             columns=["uuid_col", "dt_col", "dec_col", "bool_col"], source=source)
        ]

        batches = _collect_batches(
            backend_with_typed.execute_batch_dml(exprs)
        )
        assert batches[0].total_affected_rows == 1


# ══════════════════════════════════════════════
# Sync: Tier 2 RETURNING fast-fail
# ══════════════════════════════════════════════

class TestBatchDMLTier2:
    """Tests with Tier 2 backend (SQLite < 3.35, no RETURNING)."""

    def test_insert_without_returning_succeeds(self, backend_no_returning):
        dialect = backend_no_returning.dialect
        exprs = [_make_insert_expr(dialect, f"u{i}", f"u{i}@t.com") for i in range(3)]

        batches = _collect_batches(
            backend_no_returning.execute_batch_dml(exprs)
        )
        assert sum(b.total_affected_rows for b in batches) == 3

    def test_insert_with_returning_raises(self, backend_no_returning):
        dialect = backend_no_returning.dialect
        exprs = [_make_insert_expr(dialect, "u0", "u0@t.com")]

        with pytest.raises(UnsupportedFeatureError):
            _collect_batches(
                backend_no_returning.execute_batch_dml(exprs, returning_columns=["id"])
            )
