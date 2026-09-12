# Parallel Worker Patterns

When your application needs to process large volumes of data — batch imports, periodic analytics, task queue consumers — running multiple workers in parallel is the natural approach. But rhosocial-activerecord's connection model creates a constraint that most developers encounter too late: a single ActiveRecord class holds a single connection, and that connection is not safe to share across threads or coroutines.

This document explains why that constraint exists, what the correct patterns are, and how to handle the database-specific details that differ between backends.

## Why One Connection Per Class

Every call to `MyModel.configure(config, Backend)` writes the backend instance to a class-level attribute (`MyModel.__backend__`). This is a deliberate design choice — it keeps the API simple and avoids hidden state. But it means that all instances of `MyModel` share the same underlying database connection.

In a multi-threaded environment, two threads calling `MyModel.find()` simultaneously will interleave their operations on the same connection. Most database drivers do not support this: cursors get corrupted, queries fail with cryptic errors, and connections leak. The `mysql-connector-python` documentation states this explicitly, and `psycopg` does as well.

The same problem exists with async code, but in a subtler way. An event loop is single-threaded, so two coroutines cannot truly run concurrently — but they can interleave at every `await` point. If one coroutine is in the middle of a query when another starts, the connection state is corrupted.

The solution in both cases is the same: **do not share a connection**. Each independent unit of work needs its own backend instance.

## Multi-Process: The Correct Approach

Multi-processing gives each worker its own memory space, its own Python interpreter, and its own database connection. The `configure()` call happens after the process starts, so each child process establishes an independent connection — no sharing, no conflicts.

The pattern is straightforward:

```python
import multiprocessing
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, MySQLConnectionConfig
from models import Post

def worker(post_ids: list[int]):
    # Configure inside the child process — each process gets its own connection
    config = MySQLConnectionConfig(
        host="localhost", port=3306,
        database="mydb", username="app", password="secret",
    )
    User.configure(config, MySQLBackend)
    Post.__backend__ = User.backend()

    try:
        for post_id in post_ids:
            post = Post.find_one(post_id)
            if post is None:
                continue
            post.view_count += 1
            post.save()
    finally:
        User.backend().disconnect()

if __name__ == "__main__":
    post_ids = list(range(1, 101))
    chunk_size = 25
    with multiprocessing.Pool(processes=4) as pool:
        chunks = [post_ids[i:i+chunk_size] for i in range(0, len(post_ids), chunk_size)]
        pool.map(worker, chunks)
```

The critical detail is that `configure()` runs inside the child process, not before `fork`. If you configure the backend in the parent process and then fork, the child inherits the parent's file descriptors — and for TCP connections, this means two processes trying to read from the same socket, which corrupts the protocol stream.

## Async Behavior: Sequential Within a Process

Within a single process, async code using a single-connection backend executes sequentially. You cannot use `asyncio.gather()` to run multiple queries concurrently on the same connection — the second query will fail because the first one is still in progress.

```python
# This will raise RuntimeError
async def wrong(post_ids: list[int]):
    await asyncio.gather(*[update_one(pid) for pid in post_ids])

# This works — sequential execution
async def correct(post_ids: list[int]):
    for pid in post_ids:
        await update_one(pid)
```

The advantage of async is not concurrency within a process, but efficiency at the I/O boundary. When a coroutine sends a query and awaits the response, the event loop can handle other work — reading from a queue, processing an HTTP request, writing logs. The database query itself still executes one at a time.

True concurrency comes from running multiple processes, each with its own connection and event loop.

## Deadlock Prevention

When multiple processes write to the same table, they can deadlock if they lock rows in inconsistent order. The universal principles apply regardless of which database you use:

**Consistent lock order.** If two transactions need to lock rows A and B, always lock them in the same order (e.g., by ascending primary key). This eliminates the circular-wait condition that causes deadlocks.

**Short transactions.** Keep transactions as brief as possible. Every `await` inside a transaction is an opportunity for another process to acquire a lock and create a deadlock.

**Atomic claim.** Instead of reading a row and then updating it in two separate operations, combine them into a single transaction. This reduces the window during which locks are held.

**Data partitioning.** If you can assign each worker a disjoint set of data (by ID range, by hash, by status), there is no lock contention at all.

**Deadlock retry.** All major databases detect deadlocks automatically and roll back one of the transactions. Catching the error and retrying is often simpler than trying to prevent deadlocks through lock ordering.

The specific error codes and detection mechanisms differ between databases — see each backend's `scenarios/parallel_workers.md` for details.

## When to Separate Applications

In production systems, web request handling and batch processing usually have very different resource profiles. Web requests are short, latency-sensitive, and benefit from connection pooling. Batch jobs are long-running, throughput-oriented, and benefit from dedicated connections that do not compete with request traffic.

The practical recommendation is to deploy them as separate processes: the web application handles HTTP requests with its own connection management, and a separate worker pool processes batch tasks with its own connections. They may share the same database, but they do not share connections.

## See Also

- [Worker Pool Module](../worker_pool/README.md) — managed multi-process task execution with lifecycle hooks
- [Connection Management](../connection/README.md) — BackendGroup and BackendManager for connection organization
- [MySQL Parallel Workers](../../../python-activerecord-mysql/docs/en_US/scenarios/parallel_workers.md) — MySQL-specific deadlock codes, test results, FastAPI patterns
- [PostgreSQL Parallel Workers](../../../python-activerecord-postgres/docs/en_US/scenarios/parallel_workers.md) — PostgreSQL-specific details, BackendPool usage
