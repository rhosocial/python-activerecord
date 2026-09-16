# Deadlock Handling

## Overview

A deadlock occurs when two or more transactions are waiting for each other to release locks, creating a circular dependency. {database} automatically detects deadlocks and rolls back one of the transactions.

## {database} Deadlock Behavior

<!-- Document backend-specific deadlock detection. Examples:

### MySQL

MySQL InnoDB has a built-in deadlock detection algorithm. When a deadlock is detected, it automatically rolls back the transaction with lower cost.

- Error code: errno 1213
- Detection: Automatic via `innodb_deadlock_detect` (default enabled)
- Rollback: Cheaper transaction is rolled back

### PostgreSQL

PostgreSQL also has automatic deadlock detection.

- Error code: SQLSTATE 40P01
- Detection: Automatic
- Rollback: One transaction is rolled back

-->

## Detecting Deadlocks

<!-- Document how to detect deadlocks in Python. Examples:

### MySQL

```python
def _is_deadlock(exc: Exception) -> bool:
    """Check whether the exception is a MySQL deadlock."""
    msg = str(exc)
    return "1213" in msg or "deadlock" in msg.lower()
```

### PostgreSQL

```python
def _is_deadlock(exc: Exception) -> bool:
    """Check if exception is a PostgreSQL deadlock."""
    if hasattr(exc, 'sqlstate'):
        return exc.sqlstate == '40P01'
    msg = str(exc)
    return '40P01' in msg or 'deadlock' in msg.lower()
```

-->

## Retry Strategy

The recommended approach is to catch the deadlock error and retry with exponential back-off:

### Synchronous

```python
import time

def _is_deadlock(exc: Exception) -> bool:
    """Check whether the exception is a {database} deadlock."""
    # TODO: Implement backend-specific detection
    msg = str(exc)
    return 'deadlock' in msg.lower()


def claim_posts_with_retry(batch_size: int = 5, max_retry: int = 3) -> list:
    """Atomic claim with automatic deadlock retry."""
    for attempt in range(max_retry):
        try:
            with Post.transaction():
                pending = (
                    Post.query()
                        .where(Post.c.status == "draft")
                        .order_by(Post.c.id)
                        .limit(batch_size)
                        .all()
                )
                if not pending:
                    return []
                for post in pending:
                    post.status = "processing"
                    post.save()
                return pending
        except Exception as e:
            if _is_deadlock(e) and attempt < max_retry - 1:
                time.sleep(0.05 * (attempt + 1))  # exponential back-off
                continue
            raise
    return []
```

### Asynchronous

```python
import asyncio

async def claim_posts_with_retry(batch_size: int = 5, max_retry: int = 3) -> list:
    """Atomic claim with automatic deadlock retry (async version)."""
    for attempt in range(max_retry):
        try:
            async with Post.transaction():
                pending = (
                    await Post.query()
                        .where(Post.c.status == "draft")
                        .order_by(Post.c.id)
                        .limit(batch_size)
                        .all()
                )
                if not pending:
                    return []
                for post in pending:
                    post.status = "processing"
                    await post.save()
                return pending
        except Exception as e:
            if _is_deadlock(e) and attempt < max_retry - 1:
                await asyncio.sleep(0.05 * (attempt + 1))  # exponential back-off
                continue
            raise
    return []
```

## Best Practices

| Principle | Description |
|-----------|-------------|
| **Data partitioning** | Assign data by ID range or hash to each worker so they never touch the same rows |
| **Consistent lock order** | When locking multiple resources, always request them in a fixed order |
| **Short transactions** | Keep only necessary operations in a transaction |
| **Atomic claim** | Query and update task status inside one transaction |
| **Deadlock retry** | Catch deadlock errors and retry with back-off |

## See Also

- [Core: Parallel Worker Patterns](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers) — deadlock prevention principles
