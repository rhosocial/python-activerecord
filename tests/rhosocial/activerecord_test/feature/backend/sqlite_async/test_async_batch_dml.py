# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_batch_dml.py
"""
Integration tests for execute_batch_dml with real async SQLite backend.

Tests cover:
  - INSERT / UPDATE / DELETE execution paths
  - executemany path (no RETURNING) and per-row execute path (with RETURNING)
  - batch_size boundary conditions
  - Parameter type conversion
  - Tier 2 (old SQLite version) RETURNING fast-fail
"""
import pytest
import pytest_asyncio
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


@pytest_asyncio.fixture
async def async_backend_with_users(async_sqlite_backend):
    """Async SQLite backend with users table created."""
    await async_sqlite_backend.executescript(CREATE_USERS_SQL)
    return async_sqlite_backend


@pytest_asyncio.fixture
async def async_backend_with_typed(async_sqlite_backend):
    """Async SQLite backend with typed_data table for type conversion tests."""
    await async_sqlite_backend.executescript(CREATE_TYPED_SQL)
    return async_sqlite_backend


@pytest_asyncio.fixture
async def async_backend_no_returning(tmp_path):
    """Async SQLite backend with dialect downgraded to 3.30.0 (no RETURNING)."""
    from rhosocial.activerecord.backend.impl.sqlite.backend import AsyncSQLiteBackend
    from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

    db_path = tmp_path / "tier2_async.db"
    config = SQLiteConnectionConfig(database=str(db_path))
    backend = AsyncSQLiteBackend(connection_config=config)
    backend._dialect = SQLiteDialect(version=(3, 30, 0))
    await backend.connect()
    await backend.executescript(CREATE_USERS_SQL)
    yield backend
    await backend.disconnect()


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


async def _async_count_rows(backend, table="users"):
    """Async SELECT COUNT(*) helper."""
    from rhosocial.activerecord.backend.options import ExecutionOptions
    from rhosocial.activerecord.backend.schema import StatementType
    result = await backend.execute(
        f"SELECT COUNT(*) as cnt FROM {table}", None,
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    return result.data[0]["cnt"]


async def _async_collect_batches(async_iterator):
    """Consume an AsyncIterator[BatchDMLResult] into a list."""
    results = []
    async for batch in async_iterator:
        results.append(batch)
    return results


# ══════════════════════════════════════════════
# Async: INSERT
# ══════════════════════════════════════════════

@pytest.mark.asyncio
class TestAsyncBatchDMLInsert:
    """Async INSERT tests."""

    @pytest.mark.parametrize("row_count, batch_size, expected_batches", [
        pytest.param(10, 100, 1, id="all_in_one_batch"),
        pytest.param(10, 10, 1, id="exact_batch_boundary"),
        pytest.param(11, 5, 3, id="uneven_batches_5_5_1"),
        pytest.param(1, 100, 1, id="single_row"),
        pytest.param(3, 1, 3, id="batch_size_1"),
    ])
    async def test_insert_batch_counts(self, async_backend_with_users, row_count, batch_size, expected_batches):
        dialect = async_backend_with_users.dialect
        exprs = [_make_insert_expr(dialect, f"user{i}", f"user{i}@test.com") for i in range(row_count)]

        batches = await _async_collect_batches(
            async_backend_with_users.execute_batch_dml(exprs, batch_size=batch_size)
        )

        assert len(batches) == expected_batches
        total_affected = sum(b.total_affected_rows for b in batches)
        assert total_affected == row_count
        assert await _async_count_rows(async_backend_with_users) == row_count

    async def test_insert_batch_index_increments(self, async_backend_with_users):
        dialect = async_backend_with_users.dialect
        exprs = [_make_insert_expr(dialect, f"u{i}", f"u{i}@t.com") for i in range(7)]

        batches = await _async_collect_batches(
            async_backend_with_users.execute_batch_dml(exprs, batch_size=3)
        )

        assert [b.batch_index for b in batches] == [0, 1, 2]
        assert [b.batch_size for b in batches] == [3, 3, 1]

    async def test_insert_no_returning_results_empty(self, async_backend_with_users):
        dialect = async_backend_with_users.dialect
        exprs = [_make_insert_expr(dialect, f"u{i}", f"u{i}@t.com") for i in range(3)]

        batches = await _async_collect_batches(
            async_backend_with_users.execute_batch_dml(exprs)
        )

        for b in batches:
            assert b.has_returning is False
            assert b.results == []

    async def test_insert_with_returning(self, async_backend_with_users):
        dialect = async_backend_with_users.dialect
        exprs = [_make_insert_expr(dialect, f"u{i}", f"u{i}@t.com") for i in range(5)]

        batches = await _async_collect_batches(
            async_backend_with_users.execute_batch_dml(
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

    async def test_insert_returning_single_column(self, async_backend_with_users):
        dialect = async_backend_with_users.dialect
        exprs = [_make_insert_expr(dialect, f"u{i}", f"u{i}@t.com") for i in range(3)]

        batches = await _async_collect_batches(
            async_backend_with_users.execute_batch_dml(exprs, returning_columns=["id"])
        )

        ids = [r.data[0]["id"] for b in batches for r in b.results]
        assert len(ids) == 3
        assert len(set(ids)) == 3  # all unique

    async def test_empty_expressions(self, async_backend_with_users):
        batches = await _async_collect_batches(
            async_backend_with_users.execute_batch_dml([])
        )
        assert batches == []


# ══════════════════════════════════════════════
# Async: UPDATE
# ══════════════════════════════════════════════

@pytest.mark.asyncio
class TestAsyncBatchDMLUpdate:
    """Async UPDATE tests."""

    async def _seed(self, backend, n=10):
        """Insert n rows as seed data, return list of ids."""
        dialect = backend.dialect
        for i in range(n):
            expr = _make_insert_expr(dialect, f"user{i}", f"user{i}@test.com")
            sql, params = expr.to_sql()
            from rhosocial.activerecord.backend.options import ExecutionOptions
            from rhosocial.activerecord.backend.schema import StatementType
            await backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DML))
        return list(range(1, n + 1))

    async def test_update_all_rows(self, async_backend_with_users):
        ids = await self._seed(async_backend_with_users)
        dialect = async_backend_with_users.dialect
        exprs = [_make_update_expr(dialect, pk, f"updated{pk}") for pk in ids]

        batches = await _async_collect_batches(
            async_backend_with_users.execute_batch_dml(exprs, batch_size=5)
        )

        total = sum(b.total_affected_rows for b in batches)
        assert total == 10
        assert len(batches) == 2  # 5 + 5

    async def test_update_with_returning(self, async_backend_with_users):
        ids = await self._seed(async_backend_with_users, n=3)
        dialect = async_backend_with_users.dialect
        exprs = [_make_update_expr(dialect, pk, f"new{pk}") for pk in ids]

        batches = await _async_collect_batches(
            async_backend_with_users.execute_batch_dml(
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
# Async: DELETE
# ══════════════════════════════════════════════

@pytest.mark.asyncio
class TestAsyncBatchDMLDelete:
    """Async DELETE tests."""

    async def _seed(self, backend, n=10):
        dialect = backend.dialect
        for i in range(n):
            expr = _make_insert_expr(dialect, f"user{i}", f"user{i}@test.com")
            sql, params = expr.to_sql()
            from rhosocial.activerecord.backend.options import ExecutionOptions
            from rhosocial.activerecord.backend.schema import StatementType
            await backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DML))
        return list(range(1, n + 1))

    async def test_delete_all_rows(self, async_backend_with_users):
        ids = await self._seed(async_backend_with_users)
        dialect = async_backend_with_users.dialect
        exprs = [_make_delete_expr(dialect, pk) for pk in ids]

        batches = await _async_collect_batches(
            async_backend_with_users.execute_batch_dml(exprs, batch_size=4)
        )

        total = sum(b.total_affected_rows for b in batches)
        assert total == 10
        assert await _async_count_rows(async_backend_with_users) == 0
        assert len(batches) == 3  # 4 + 4 + 2

    async def test_delete_with_returning(self, async_backend_with_users):
        ids = await self._seed(async_backend_with_users, n=3)
        dialect = async_backend_with_users.dialect
        exprs = [_make_delete_expr(dialect, pk) for pk in ids]

        batches = await _async_collect_batches(
            async_backend_with_users.execute_batch_dml(
                exprs, returning_columns=["id", "name"],
            )
        )

        deleted_names = [r.data[0]["name"] for b in batches for r in b.results]
        assert set(deleted_names) == {"user0", "user1", "user2"}


# ══════════════════════════════════════════════
# Async: Type conversion (executemany path)
# ══════════════════════════════════════════════

@pytest.mark.asyncio
class TestAsyncBatchDMLTypeConversion:
    """Verify parameter type conversion works in the executemany path."""

    async def test_uuid_and_datetime(self, async_backend_with_typed):
        dialect = async_backend_with_typed.dialect
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

        batches = await _async_collect_batches(
            async_backend_with_typed.execute_batch_dml(exprs)
        )
        assert batches[0].total_affected_rows == 1


# ══════════════════════════════════════════════
# Async: Tier 2 RETURNING fast-fail
# ══════════════════════════════════════════════

@pytest.mark.asyncio
class TestAsyncBatchDMLTier2:
    """Tests with Tier 2 backend (SQLite < 3.35, no RETURNING)."""

    async def test_insert_without_returning_succeeds(self, async_backend_no_returning):
        dialect = async_backend_no_returning.dialect
        exprs = [_make_insert_expr(dialect, f"u{i}", f"u{i}@t.com") for i in range(3)]

        batches = await _async_collect_batches(
            async_backend_no_returning.execute_batch_dml(exprs)
        )
        assert sum(b.total_affected_rows for b in batches) == 3

    async def test_insert_with_returning_raises(self, async_backend_no_returning):
        dialect = async_backend_no_returning.dialect
        exprs = [_make_insert_expr(dialect, "u0", "u0@t.com")]

        with pytest.raises(UnsupportedFeatureError):
            await _async_collect_batches(
                async_backend_no_returning.execute_batch_dml(exprs, returning_columns=["id"])
            )
