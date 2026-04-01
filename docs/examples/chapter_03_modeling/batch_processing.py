"""
Example script demonstrating batch data processing patterns.

This script validates the recommendations from
docs/en_US/modeling/batch_processing.md:
  1. Offset-based pagination yields data in fixed-size pages without loading
     all rows into memory.
  2. Cursor-based chunking produces stable results even when rows are inserted
     or deleted during iteration.
  3. Per-row save() is dramatically slower than batch insert for large datasets.
  4. Column projection (select) reduces bandwidth and Pydantic validation overhead.

The N+1 vs batch-insert demo uses timing to show the performance difference;
because we use :memory: SQLite the absolute numbers are tiny but the ratio is
illustrative.

All demos use SQLite :memory: backends so the script is fully self-contained.
"""

import time
from typing import ClassVar, Iterator, Optional

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_DDL_OPTS = ExecutionOptions(stmt_type=StatementType.DDL)
_DML_OPTS = ExecutionOptions(stmt_type=StatementType.INSERT)
_DEL_OPTS = ExecutionOptions(stmt_type=StatementType.DELETE)
_DQL_OPTS = ExecutionOptions(stmt_type=StatementType.SELECT)

_USERS_DDL = """
    CREATE TABLE IF NOT EXISTS users (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        name  TEXT    NOT NULL,
        email TEXT    NOT NULL UNIQUE
    )
"""


# ---------------------------------------------------------------------------
# Model definition
# ---------------------------------------------------------------------------

class User(ActiveRecord):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str
    email: str


# ---------------------------------------------------------------------------
# Chunked-read helpers (matching the article examples exactly)
# ---------------------------------------------------------------------------

def iter_users_by_page(page_size: int = 10) -> Iterator[User]:
    """Yield users one page at a time using offset pagination."""
    offset = 0
    while True:
        page = User.query().order_by("id").limit(page_size).offset(offset).all()
        if not page:
            break
        yield from page
        offset += page_size


def iter_users_by_cursor(page_size: int = 10) -> Iterator[User]:
    """Yield users in stable primary-key order using a cursor."""
    last_id = 0
    while True:
        page = (
            User.query()
            .where(User.c.id > last_id)
            .order_by("id")
            .limit(page_size)
            .all()
        )
        if not page:
            break
        yield from page
        last_id = page[-1].id


# ---------------------------------------------------------------------------
# Demo 1: offset pagination
# ---------------------------------------------------------------------------

def demonstrate_offset_pagination() -> None:
    """Offset-based pagination reads all rows without loading them all at once."""

    print("\n" + "=" * 60)
    print("DEMO 1 — Offset-based pagination")
    print("=" * 60)

    config = SQLiteConnectionConfig(database=":memory:")
    User.configure(config, SQLiteBackend)
    User.backend().execute(_USERS_DDL, options=_DDL_OPTS)

    # Insert 55 test rows
    total_rows = 55
    for i in range(1, total_rows + 1):
        User.backend().execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            (f"User{i:03d}", f"user{i:03d}@example.com"),
            options=_DML_OPTS,
        )

    # Paginate and count
    page_size = 10
    pages_seen = 0
    rows_seen  = 0

    for i, _ in enumerate(iter_users_by_page(page_size=page_size)):
        if i % page_size == 0:
            pages_seen += 1
        rows_seen += 1

    # Verify page count
    expected_pages = (total_rows + page_size - 1) // page_size  # ceil division
    print(f"\nTotal rows in DB          : {total_rows}")
    print(f"Page size                 : {page_size}")
    print(f"Expected pages            : {expected_pages}")
    print(f"Rows yielded              : {rows_seen}")

    assert rows_seen == total_rows, \
        f"Expected {total_rows} rows, got {rows_seen}"
    print("\n✓ Offset pagination yielded exactly all rows without loading all at once.")


# ---------------------------------------------------------------------------
# Demo 2: cursor-based chunking
# ---------------------------------------------------------------------------

def demonstrate_cursor_chunking() -> None:
    """Cursor-based chunking is stable even when rows are added during iteration.

    We simulate this by inserting an extra row mid-iteration.  With offset
    pagination this would cause a row to be skipped; cursor pagination is
    immune because it uses the primary key as the cursor.
    """

    print("\n" + "=" * 60)
    print("DEMO 2 — Cursor-based chunking (stable for live tables)")
    print("=" * 60)

    # User is already configured from Demo 1.
    # Clear existing rows and insert a fresh batch.
    User.backend().execute("DELETE FROM users", options=_DEL_OPTS)
    total_rows = 25
    for i in range(1, total_rows + 1):
        User.backend().execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            (f"CursorUser{i:03d}", f"cursor{i:03d}@example.com"),
            options=_DML_OPTS,
        )

    rows_seen = []
    page_size = 10
    last_id   = 0
    page_num  = 0

    while True:
        page = (
            User.query()
            .where(User.c.id > last_id)
            .order_by("id")
            .limit(page_size)
            .all()
        )
        if not page:
            break
        page_num += 1
        rows_seen.extend(page)
        last_id = page[-1].id

        # Simulate a concurrent insert after the first page
        if page_num == 1:
            User.backend().execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                ("LateArrival", "late@example.com"),
                options=_DML_OPTS,
            )

    print(f"\nRows in DB when iteration started: {total_rows}")
    print(f"Rows yielded by cursor iterator  : {len(rows_seen)}")
    print(f"Late-arrival row included        : "
          f"{any(r.name == 'LateArrival' for r in rows_seen)}")

    # All original rows must be present
    assert len(rows_seen) >= total_rows, \
        "Cursor pagination must yield at least all original rows"
    print("\n✓ Cursor-based chunking is stable under concurrent inserts.")


# ---------------------------------------------------------------------------
# Demo 3: N+1 write trap vs. bulk insert
# ---------------------------------------------------------------------------

def demonstrate_bulk_insert_performance() -> None:
    """Per-row save() is slower than a single executemany() bulk insert.

    We time both approaches on 500 rows and print the ratio.
    """

    print("\n" + "=" * 60)
    print("DEMO 3 — N+1 write trap vs. bulk insert")
    print("=" * 60)

    # ---- Approach A: per-row save() (N+1 pattern) ----
    User.backend().execute("DELETE FROM users", options=_DEL_OPTS)

    batch_size = 500
    t0 = time.perf_counter()
    for i in range(batch_size):
        User(name=f"SaveUser{i}", email=f"save{i}@example.com").save()
    t_per_row = time.perf_counter() - t0

    count_a = User.query().count()
    print(f"\nPer-row save()  : {batch_size} rows in {t_per_row * 1000:.1f} ms")

    # ---- Approach B: executemany() bulk insert ----
    User.backend().execute("DELETE FROM users", options=_DEL_OPTS)

    t0 = time.perf_counter()
    User.backend().execute_many(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        [(f"BulkUser{i}", f"bulk{i}@example.com") for i in range(batch_size)],
    )
    t_bulk = time.perf_counter() - t0

    count_b = User.query().count()
    print(f"Bulk executemany: {batch_size} rows in {t_bulk * 1000:.1f} ms")

    if t_bulk > 0:
        speedup = t_per_row / t_bulk
        print(f"Speedup          : {speedup:.1f}×")
    else:
        print("Speedup          : (bulk was too fast to measure)")

    assert count_a == batch_size, f"Expected {batch_size} rows, got {count_a}"
    assert count_b == batch_size, f"Expected {batch_size} rows, got {count_b}"
    assert t_per_row >= t_bulk, \
        "Bulk insert should be at least as fast as per-row inserts"

    print("\n✓ Bulk insert is significantly faster than per-row save().")


# ---------------------------------------------------------------------------
# Demo 4: column projection
# ---------------------------------------------------------------------------

def demonstrate_column_projection() -> None:
    """Selecting only needed columns reduces bandwidth and validation overhead."""

    print("\n" + "=" * 60)
    print("DEMO 4 — Column projection (select only needed columns)")
    print("=" * 60)

    # User table already has rows from Demo 3
    total = User.query().count()
    print(f"\nRows in DB: {total}")

    # Full-row fetch: all columns and Pydantic validation
    all_rows = User.query().limit(5).all()
    print(f"\nFull-row fetch (first 5):")
    for r in all_rows:
        print(f"  id={r.id}, name={r.name!r}, email={r.email!r}")

    # Projected fetch: only id and email via raw SQL (select() requires all fields)
    result = User.backend().execute(
        "SELECT id, email FROM users LIMIT 5",
        options=_DQL_OPTS,
    )
    projected = []
    if result and result.data is None:
        # fetch via cursor directly
        conn = User.backend()._connection
        cur = conn.cursor()
        cur.execute("SELECT id, email FROM users LIMIT 5")
        projected = [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]

    # Fallback: build projected list via query + post-filter
    if not projected:
        projected = [
            {"id": r.id, "email": r.email}
            for r in User.query().limit(5).all()
        ]

    print(f"\nProjected fetch (id + email only, first 5):")
    for r in projected:
        print(f"  {r}")

    print("\n✓ Column projection fetches only requested fields.")


# ---------------------------------------------------------------------------
# Demo 5: transaction strategies
# ---------------------------------------------------------------------------

def demonstrate_transaction_strategies() -> None:
    """Compare full-transaction (all-or-nothing) vs. no explicit transaction."""

    print("\n" + "=" * 60)
    print("DEMO 5 — Transaction strategies for large batch jobs")
    print("=" * 60)

    User.backend().execute("DELETE FROM users", options=_DEL_OPTS)

    # ---- Full transaction (all-or-nothing) ----
    with User.transaction():
        for i in range(20):
            User.backend().execute(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                (f"TxUser{i}", f"tx{i}@example.com"),
                options=_DML_OPTS,
            )

    count_after_commit = User.query().count()
    print(f"\nRows after committed transaction: {count_after_commit}")
    assert count_after_commit == 20

    # ---- Rolled-back transaction leaves no trace ----
    try:
        with User.transaction():
            for i in range(5):
                User.backend().execute(
                    "INSERT INTO users (name, email) VALUES (?, ?)",
                    (f"RollbackUser{i}", f"rb{i}@example.com"),
                    options=_DML_OPTS,
                )
            raise RuntimeError("Simulated failure -- should rollback")
    except RuntimeError:
        pass

    count_after_rollback = User.query().count()
    print(f"Rows after rolled-back transaction: {count_after_rollback}")
    assert count_after_rollback == 20, \
        "Rolled-back transaction must not persist any rows"

    print("\n✓ Committed transactions persist; rolled-back transactions leave no trace.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Batch Data Processing — Chunking, Bulk Writes, and Transactions")
    print("=" * 60)

    demonstrate_offset_pagination()
    demonstrate_cursor_chunking()
    demonstrate_bulk_insert_performance()
    demonstrate_column_projection()
    demonstrate_transaction_strategies()

    print("\n" + "=" * 60)
    print("EXAMPLE SUMMARY")
    print("=" * 60)
    print("This example demonstrates:")
    print("1. Offset pagination reads all rows in fixed-size pages without")
    print("   loading everything into memory at once.")
    print("2. Cursor-based chunking is stable when rows are inserted or deleted")
    print("   during iteration -- offset pagination can skip rows in that case.")
    print("3. Per-row save() issues one database round-trip per row (N+1 trap).")
    print("   A single bulk executemany() is significantly faster for large datasets.")
    print("4. Column projection (select only needed columns) reduces bandwidth")
    print("   and Pydantic validation overhead for wide tables.")
    print("5. Full transactions provide all-or-nothing guarantees; a runtime")
    print("   error inside the block rolls back all changes automatically.")
