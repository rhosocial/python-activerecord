# Parallel Workers: {database} Specific Notes

This document covers {database}-specific details for parallel worker scenarios. For general patterns (multi-process lifecycle, async behavior, deadlock prevention principles, application separation), see [Core Parallel Worker Patterns](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers.md).

## {database} Concurrency Characteristics

| Feature | {database} |
| --- | --- |
| Lock granularity | |
| Concurrent writes | |
| Deadlock detection | |
| Async driver | |
| threadsafety | |

## Deadlock Detection

{database} has automatic deadlock detection. When a deadlock occurs, it automatically rolls back one of the transactions.

### Deadlock Error Detection

```python
def _is_deadlock(exc: Exception) -> bool:
    """Check whether the exception is a {database} deadlock."""
    # TODO: Implement backend-specific detection
    msg = str(exc)
    return 'deadlock' in msg.lower()
```

### Deadlock Retry Pattern

```python
import time

def claim_posts_with_retry(batch_size: int = 5, max_retry: int = 3) -> list:
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
                time.sleep(0.05 * (attempt + 1))
                continue
            raise
    return []
```

## FastAPI Best Practices

### Request-level BackendGroup (MySQL)

For MySQL (threadsafety=1), use request-level BackendGroup:

```python
@asynccontextmanager
async def get_request_db():
    config = load_config()
    group = AsyncBackendGroup(
        name="request",
        models=[AsyncUser, AsyncPost],
        config=config,
        backend_class=AsyncMySQLBackend,
    )
    try:
        await group.configure()
        backend = group.get_backend()
        async with backend.context():
            yield backend
    finally:
        await group.disconnect()
```

### BackendPool (PostgreSQL)

For PostgreSQL (threadsafety=2), use BackendPool for connection pooling:

```python
from rhosocial.activerecord.connection.pool import PoolConfig, AsyncBackendPool

async def init_pool():
    pool_config = PoolConfig(
        min_size=2,
        max_size=10,
        backend_factory=lambda: AsyncPostgreSQLBackend(connection_config=config),
    )
    _pool = AsyncBackendPool(pool_config)
```

## Platform-Specific Notes

### Windows

On Windows, async workers may need `WindowsSelectorEventLoopPolicy`:

```python
import asyncio
import sys

def worker_async(post_ids: list) -> int:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(async_worker_main(post_ids))
```

### macOS / Linux

No special configuration needed; default event loop works correctly.

## See Also

- [Core Parallel Worker Patterns](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/scenarios/parallel_workers) — general patterns
- [Transaction Support](../transaction_support/deadlock.md) — deadlock handling
