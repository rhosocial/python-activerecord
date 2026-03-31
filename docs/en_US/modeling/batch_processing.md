# Batch Data Processing

Loading a million rows into memory at once will exhaust your process's RAM and likely
crash your application.  This guide covers patterns for processing large datasets
efficiently -- whether you're running ETL pipelines, data migrations, or analytics jobs.

> 💡 **AI Prompt:** "I need to process all rows in a 10-million-row table without running
> out of memory.  What is the recommended approach with rhosocial-activerecord?"

---

## 1. The Core Problem: Memory

```python
# ❌ Loads the entire table into RAM -- dangerous for large tables
all_users = User.query().all()
for user in all_users:
    process(user)
```

For tables with millions of rows, `all()` will consume gigabytes of memory and likely
trigger an OOM kill.  The solution is to **process data in chunks**.

---

## 2. Chunk Reading with Offset Pagination

The simplest chunking strategy uses `limit` and `offset`:

```python
def iter_users_by_page(page_size: int = 500):
    """Yield users one page at a time."""
    offset = 0
    while True:
        page = User.query().order_by("id").limit(page_size).offset(offset).all()
        if not page:
            break
        yield from page
        offset += page_size

# Process every user without loading all rows into memory
for user in iter_users_by_page(page_size=500):
    process(user)
```

> ⚠️ **Stability requirement**: offset pagination only produces consistent results when
> the underlying data does not change during iteration.  For live tables, prefer
> cursor-based chunking (see below) or process from a snapshot.

---

## 3. Cursor-Based Chunking (Stable for Live Tables)

Use the last-seen primary key as a cursor instead of `offset`.  This avoids the
"shifting rows" problem when rows are inserted or deleted mid-iteration:

```python
def iter_users_by_cursor(page_size: int = 500):
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

for user in iter_users_by_cursor():
    process(user)
```

---

## 4. Framework Batch DQL

For large reads, the framework provides `execute_batch_dql` as a method on the backend
instance.  It handles pagination internally and yields one `BatchDQLResult` page at a time:

```python
from rhosocial.activerecord.backend.expression.statements import QueryExpression
from rhosocial.activerecord.backend.expression import WildcardExpression, TableExpression
from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
from rhosocial.activerecord.backend.expression import Column

# Build a SELECT * FROM users ORDER BY id expression
dialect = User.backend().dialect
query_expr = QueryExpression(
    dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, "users"),
    order_by=OrderByClause(dialect, expressions=[(Column(dialect, "id"), "ASC")]),
)

# execute_batch_dql is a method on the backend instance, not a free function
for page in User.backend().execute_batch_dql(query_expr, page_size=500):
    for row in page.data:   # page.data is a list of dicts
        process(row)
    if not page.has_more:
        break
```

See [Batch Operations](../performance/batch_operations.md) for full API documentation.

---

## 5. Bulk Inserts -- Avoid the N+1 Write Trap

### The trap

```python
# ❌ N+1 inserts -- one database round-trip per row
for row in source_data:
    User(name=row["name"], email=row["email"]).save()
```

For 10,000 rows, this issues 10,000 separate `INSERT` statements.  At 1 ms per round-
trip, that is 10 seconds -- for a dataset that a bulk insert could handle in under 100 ms.

### Correct approach: `execute_batch_dml`

```python
# ✅ Bulk insert via the backend's execute_batch_dml method
from rhosocial.activerecord.backend.expression import (
    InsertExpression, ValuesSource, Literal,
)
from rhosocial.activerecord.backend.result import BatchCommitMode

dialect = User.backend().dialect
exprs = [
    InsertExpression(
        dialect,
        into="users",
        columns=["name", "email"],
        source=ValuesSource(
            dialect,
            values_list=[[Literal(dialect, row["name"]), Literal(dialect, row["email"])]],
        ),
    )
    for row in source_data
]

# execute_batch_dml is a method on the backend instance, not a free function
for batch_result in User.backend().execute_batch_dml(exprs, batch_size=500):
    pass   # consume the generator; commit happens on exhaustion (WHOLE mode)
```

---

## 6. Transaction Strategy for Large Batches

### Full-transaction (all-or-nothing)

```python
from rhosocial.activerecord.backend.expression import (
    InsertExpression, ValuesSource, Literal,
)
from rhosocial.activerecord.backend.result import BatchCommitMode

dialect = User.backend().dialect
with User.transaction():
    for chunk in chunked(source_data, size=500):
        exprs = [
            InsertExpression(
                dialect, into="users", columns=["name", "email"],
                source=ValuesSource(dialect, values_list=[
                    [Literal(dialect, row["name"]), Literal(dialect, row["email"])]
                ]),
            )
            for row in chunk
        ]
        for _ in User.backend().execute_batch_dml(exprs, batch_size=500):
            pass
```

Use when: data integrity requires either complete success or complete rollback.

**Downside**: holds a write lock for the entire duration.  May block other writers.

### Per-batch commits (resumable)

```python
from rhosocial.activerecord.backend.result import BatchCommitMode

for _ in User.backend().execute_batch_dml(
    exprs,
    batch_size=500,
    commit_mode=BatchCommitMode.PER_BATCH,
):
    pass
```

Use when: the job may be interrupted and restarted (idempotent rows, or a progress
table tracks which batches succeeded).

**Downside**: a mid-job failure leaves partial data committed.  Design for idempotency.

---

## 7. Projecting Only the Columns You Need

Fetching wide rows when you only need two columns wastes bandwidth and Pydantic
validation time:

```python
# ❌ Fetches all columns, validates all fields
users = User.query().all()
emails = [u.email for u in users]

# ✅ Fetches only id and email
rows = User.query().select("id", "email").all()
emails = [r["email"] for r in rows]
```

---

## 8. Batch Processing Checklist

- [ ] Never call `.all()` on an unbounded query against a large table
- [ ] Use cursor-based chunking for live tables; offset pagination for static snapshots
- [ ] Use `execute_batch_dml` (or `insert_many`) instead of per-row `save()` for bulk writes
- [ ] Choose `WHOLE` transaction for integrity-critical jobs; `PER_BATCH` for resumable jobs
- [ ] Select only the columns you actually need (`query().select(...)`)
- [ ] Monitor memory usage during development with representative data volumes

---

## Runnable Example

See [`docs/examples/chapter_03_modeling/batch_processing.py`](../../../examples/chapter_03_modeling/batch_processing.py)
for a self-contained script that demonstrates all five patterns above.

---

## See Also

- [Batch Operations API](../performance/batch_operations.md) — `execute_batch_dml` and `execute_batch_dql` reference
- [Read-Only Analytics Models](readonly_models.md) — efficiently reading from analytics databases
- [Performance Modes](../performance/modes.md) — Raw mode for high-throughput aggregation queries
