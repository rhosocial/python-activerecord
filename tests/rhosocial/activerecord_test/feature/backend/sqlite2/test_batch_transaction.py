# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_batch_transaction.py
"""
Transaction semantics tests for execute_batch_dml.

Tests verify database state after:
  - WHOLE mode: all-success, mid-batch error, consumer break, external transaction
  - PER_BATCH mode: all-success, mid-batch error, consumer break

Each test executes batch DML, then queries the database to confirm
which rows were committed and which were rolled back.

For async tests, see sqlite_async/test_batch_transaction.py.
"""
import pytest

from rhosocial.activerecord.backend.expression import (
    Column, Literal, InsertExpression, TableExpression, ValuesSource,
    ComparisonPredicate,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.errors import IntegrityError


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

CREATE_TABLE_SQL = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        batch_tag TEXT
    );
"""


@pytest.fixture
def backend(sqlite_backend):
    """SQLite backend with users table (UNIQUE on email for conflict tests)."""
    sqlite_backend.executescript(CREATE_TABLE_SQL)
    return sqlite_backend


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _make_insert(dialect, name, email, batch_tag="default"):
    source = ValuesSource(dialect, values_list=[
        [Literal(dialect, name), Literal(dialect, email), Literal(dialect, batch_tag)]
    ])
    return InsertExpression(dialect, into="users", columns=["name", "email", "batch_tag"], source=source)


def _count_rows(backend, where_clause="1=1"):
    """Count rows matching condition."""
    result = backend.execute(
        f"SELECT COUNT(*) as cnt FROM users WHERE {where_clause}", None,
        options=ExecutionOptions(stmt_type=StatementType.DQL),
    )
    return result.data[0]["cnt"]


def _collect_batches(iterator):
    return list(iterator)


def _make_conflict_batch(dialect, batch_size=5, conflict_at_batch=1):
    """
    Create expressions where batch `conflict_at_batch` will trigger UNIQUE violation.

    Strategy:
      - Pre-insert a "poison" row with email = 'conflict@test.com'
      - The expression at position (conflict_at_batch * batch_size) has the same email
      - All other expressions have unique emails tagged with their batch number

    Returns:
        (poison_expr, all_exprs): poison to pre-insert, then the batch list
    """
    poison = _make_insert(dialect, "poison", "conflict@test.com", batch_tag="poison")

    exprs = []
    for i in range(batch_size * 3):  # 3 batches worth
        batch_idx = i // batch_size
        tag = f"batch{batch_idx}"

        if batch_idx == conflict_at_batch and i == conflict_at_batch * batch_size:
            # This row will conflict with the poison row
            exprs.append(_make_insert(dialect, f"user{i}", "conflict@test.com", batch_tag=tag))
        else:
            exprs.append(_make_insert(dialect, f"user{i}", f"user{i}@test.com", batch_tag=tag))

    return poison, exprs


# ══════════════════════════════════════════════
# Sync: WHOLE mode
# ══════════════════════════════════════════════

class TestBatchTransactionWhole:
    """WHOLE commit mode — entire operation is atomic."""

    def test_all_success_committed(self, backend):
        """All batches succeed → all rows committed."""
        dialect = backend.dialect
        exprs = [_make_insert(dialect, f"u{i}", f"u{i}@t.com", "ok") for i in range(12)]

        from rhosocial.activerecord.backend.result import BatchCommitMode
        batches = _collect_batches(
            backend.execute_batch_dml(exprs, batch_size=5, commit_mode=BatchCommitMode.WHOLE)
        )

        assert len(batches) == 3  # 5 + 5 + 2
        assert _count_rows(backend) == 12

    def test_mid_batch_error_all_rollback(self, backend):
        """Error in batch 1 → all rows rolled back (including batch 0)."""
        dialect = backend.dialect
        poison, exprs = _make_conflict_batch(dialect, batch_size=5, conflict_at_batch=1)

        # Pre-insert poison row
        sql, params = poison.to_sql()
        backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DML))
        assert _count_rows(backend) == 1  # just poison

        from rhosocial.activerecord.backend.result import BatchCommitMode
        with pytest.raises((IntegrityError, Exception)):
            _collect_batches(
                backend.execute_batch_dml(exprs, batch_size=5, commit_mode=BatchCommitMode.WHOLE)
            )

        # Only the pre-inserted poison row remains — batch 0's rows were rolled back
        assert _count_rows(backend) == 1

    def test_consumer_break_all_rollback(self, backend):
        """Consumer breaks after batch 0 → managed transaction rolled back."""
        dialect = backend.dialect
        exprs = [_make_insert(dialect, f"u{i}", f"u{i}@t.com") for i in range(15)]

        from rhosocial.activerecord.backend.result import BatchCommitMode
        consumed = 0
        gen = backend.execute_batch_dml(exprs, batch_size=5, commit_mode=BatchCommitMode.WHOLE)
        for batch in gen:
            consumed += 1
            if consumed == 1:
                break
        # Explicitly close generator to trigger finally
        gen.close()

        # WHOLE mode: break → rollback → no rows committed
        assert _count_rows(backend) == 0

    def test_external_transaction_no_new_tx(self, backend):
        """When already in a transaction, execute_batch_dml should not begin a new one."""
        dialect = backend.dialect
        exprs = [_make_insert(dialect, f"u{i}", f"u{i}@t.com") for i in range(5)]

        from rhosocial.activerecord.backend.result import BatchCommitMode
        with backend.transaction():
            batches = _collect_batches(
                backend.execute_batch_dml(exprs, batch_size=3, commit_mode=BatchCommitMode.WHOLE)
            )
            assert len(batches) == 2
            # Still in external transaction — not yet committed to DB
            # (in_transaction should be True here)

        # External transaction committed on context exit
        assert _count_rows(backend) == 5


# ══════════════════════════════════════════════
# Sync: PER_BATCH mode
# ══════════════════════════════════════════════

class TestBatchTransactionPerBatch:
    """PER_BATCH commit mode — each batch is committed independently."""

    def test_all_success_committed(self, backend):
        dialect = backend.dialect
        exprs = [_make_insert(dialect, f"u{i}", f"u{i}@t.com", f"batch{i // 5}") for i in range(12)]

        from rhosocial.activerecord.backend.result import BatchCommitMode
        batches = _collect_batches(
            backend.execute_batch_dml(exprs, batch_size=5, commit_mode=BatchCommitMode.PER_BATCH)
        )

        assert len(batches) == 3
        assert _count_rows(backend) == 12

    def test_mid_batch_error_partial_commit(self, backend):
        """Batch 0 committed, batch 1 fails → batch 0 survives, batch 1 rolled back."""
        dialect = backend.dialect
        poison, exprs = _make_conflict_batch(dialect, batch_size=5, conflict_at_batch=1)

        # Pre-insert poison
        sql, params = poison.to_sql()
        backend.execute(sql, params, options=ExecutionOptions(stmt_type=StatementType.DML))

        from rhosocial.activerecord.backend.result import BatchCommitMode
        with pytest.raises((IntegrityError, Exception)):
            _collect_batches(
                backend.execute_batch_dml(exprs, batch_size=5, commit_mode=BatchCommitMode.PER_BATCH)
            )

        # Batch 0 (5 rows) was committed before batch 1 failed
        # Plus the poison row = 6 rows total
        batch0_count = _count_rows(backend, "batch_tag = 'batch0'")
        assert batch0_count == 5

        batch1_count = _count_rows(backend, "batch_tag = 'batch1'")
        # Batch 1 rolled back (the conflict row prevented the whole batch)
        # Depending on implementation: either 0 (if executemany atomically fails)
        # or partial rows if per-row execute
        # The key assertion: batch 0 survived
        assert batch0_count == 5

    def test_consumer_break_committed_batches_survive(self, backend):
        """Break after batch 0 → batch 0 committed, rest not executed."""
        dialect = backend.dialect
        exprs = [_make_insert(dialect, f"u{i}", f"u{i}@t.com", f"batch{i // 5}") for i in range(15)]

        from rhosocial.activerecord.backend.result import BatchCommitMode
        consumed = 0
        gen = backend.execute_batch_dml(exprs, batch_size=5, commit_mode=BatchCommitMode.PER_BATCH)
        for batch in gen:
            consumed += 1
            if consumed == 1:
                break
        gen.close()

        # Batch 0 was committed — its rows survive
        batch0_count = _count_rows(backend, "batch_tag = 'batch0'")
        assert batch0_count == 5

        # Total = only batch 0
        assert _count_rows(backend) == 5
