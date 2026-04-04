# Parallel Workers: Using ActiveRecord Correctly

In data processing, task queues, and batch import scenarios, developers often want to run multiple Workers in parallel to improve throughput. This chapter analyzes how ActiveRecord behaves in these scenarios, identifies common pitfalls, and presents verified safe solutions.

> **Design principle throughout this chapter**: The synchronous class `BaseActiveRecord` and the asynchronous class `AsyncBaseActiveRecord` have **identical method names** — `configure()` / `backend()` / `transaction()` / `save()` and so on are the same; async versions simply require `await` or `async with`. All examples in this chapter are provided in both versions.

## Table of Contents

1. [ActiveRecord's Single-Connection Model](#1-activerecords-single-connection-model)
2. [Why Multi-Threading Is Dangerous](#2-why-multi-threading-is-dangerous)
3. [Multi-Process: The Recommended Approach](#3-multi-process-the-recommended-approach)
4. [Deadlocks: Three Typical Scenarios and Prevention](#4-deadlocks-three-typical-scenarios-and-prevention)
5. [Application Separation Principle](#5-application-separation-principle)
6. [Special Considerations for asyncio Concurrency](#6-special-considerations-for-asyncio-concurrency)
7. [Example Code](#7-example-code)

---

## 1. ActiveRecord's Single-Connection Model

The core design principle of `rhosocial-activerecord` is: **one ActiveRecord class, one connection**.

- **Sync**: `User.configure(config, SQLiteBackend)` → stored in `User.__backend__` (`User` inherits from `BaseActiveRecord`)
- **Async**: `await User.configure(config, AsyncSQLiteBackend)` → stored in `User.__backend__` (`User` inherits from `AsyncBaseActiveRecord`)

`configure()` writes to a **class-level attribute**, which means:

- No matter how many threads or coroutines exist, they all reference the same `StorageBackend` object
- `StorageBackend` internally wraps a single database connection (`sqlite3.Connection` / `mysql.connector.Connection`, etc.)
- These underlying connection objects **are not thread-safe**

---

## 2. Why Multi-Threading Is Dangerous

### 2.1 Connection Objects Are Not Thread-Safe

Major Python database drivers explicitly state that connection objects should not be shared between threads:

| Driver | Official Note |
| --- | --- |
| `sqlite3` | "Connection objects are not thread-safe" |
| `mysql-connector-python` | "Connections do not support concurrent use across threads" |
| `psycopg3` | "Connection is not thread-safe" |

Sharing `__backend__` across multiple threads leads to cursor corruption, data corruption, and even process crashes.

In particular, the SQLite backend has `SQLiteConnectionConfig.check_same_thread` defaulting to `True`. Using a connection in a thread other than the one that created it immediately raises `ProgrammingError`.

### 2.2 TransactionManager Has No Locks

ActiveRecord's internal `TransactionManager` uses plain Python integers and lists to manage transaction state:

```python
class TransactionManagerBase:
    def __init__(self, ...):
        self._transaction_level = 0     # plain int, no lock
        self._state = TransactionState.INACTIVE
        self._active_savepoints = []    # plain list, no lock
```

When Thread A and Thread B simultaneously call `begin()`, a classic **Check-Then-Act** race condition occurs:

```text
Thread A: if self._transaction_level == 0:  → condition met
Thread B: if self._transaction_level == 0:  → condition met (A hasn't written yet)
Thread A: self._do_begin(); self._transaction_level += 1  → level = 1
Thread B: self._do_begin(); self._transaction_level += 1  → BEGIN executed again!
```

Result: The database receives two `BEGIN` commands, and transaction state is corrupted. Both sync and async `TransactionManager` have no locks. The async version is equally dangerous when multiple transactions are concurrently opened within the same process, since `await` introduces additional coroutine switch points.

### 2.3 Conclusion

> **Do not share an ActiveRecord configuration across multiple threads.** Multi-threading + shared `__backend__` is undefined behavior.

See [exp5_multithread_warning.py](../../examples/chapter_12_scenarios/parallel_workers/exp5_multithread_warning.py) for a runnable demonstration — "Scenario 0" verifies the `check_same_thread=True` default, "Scenario 1" shows the danger of shared connections, and "Scenario 2" demonstrates the limitations of per-thread connections.

---

## 3. Multi-Process: The Recommended Approach

Multi-processing is the recommended solution for parallel Worker scenarios. Each process has its own independent memory space; `configure()` is called independently within each process, with fully isolated connections.

### 3.1 Correct Lifecycle

**Synchronous (multiprocessing)**:

```python
import multiprocessing
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from models import Comment, Post, User  # User --has_many--> Post --has_many--> Comment

def worker(post_ids: list[int]):
    # 1. After process starts, configure the connection within the process.
    #    Each process gets its own independent connection, no interference.
    config = SQLiteConnectionConfig(
        database="data.db",
        pragmas={"journal_mode": "WAL", "busy_timeout": "10000"},
    )
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()
    Comment.__backend__ = User.backend()

    try:
        for post_id in post_ids:
            post = Post.find_one(post_id)
            if post is None:
                continue
            # Traverse BelongsTo relationship to get author
            author = post.author()
            # Traverse HasMany relationship to count approved comments
            approved = len([c for c in post.comments() if c.is_approved])
            post.view_count = 1 + approved
            post.save()
    finally:
        # 2. Disconnect before process exits (optional; connection closes automatically on exit)
        User.backend().disconnect()


if __name__ == "__main__":
    post_ids = list(range(1, 21))  # 20 posts
    chunk_size = 5

    with multiprocessing.Pool(processes=4) as pool:
        chunks = [post_ids[i:i+chunk_size] for i in range(0, len(post_ids), chunk_size)]
        pool.map(worker, chunks)
```

**Asynchronous (asyncio + multi-process)**:

asyncio itself is single-threaded — all coroutines within a process share the same connection (`AsyncBaseActiveRecord.__backend__`). To run multiple async Workers in parallel, the correct approach is still **multi-process**: each process runs its own asyncio event loop internally, with fully isolated connections between processes.

```python
import asyncio
import multiprocessing
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from models import AsyncComment, AsyncPost, AsyncUser  # async models; same method names as sync

async def async_worker_main(post_ids: list[int]):
    # 1. Configure the async connection inside the process
    #    (same method name as sync version, add await)
    config = SQLiteConnectionConfig(
        database="data.db",
        pragmas={"journal_mode": "WAL", "busy_timeout": "10000"},
    )
    await AsyncUser.configure(config, AsyncSQLiteBackend)
    AsyncPost.__backend__ = AsyncUser.backend()
    AsyncComment.__backend__ = AsyncUser.backend()

    try:
        # Coroutines within the same process share this connection.
        # asyncio's single-threaded scheduling keeps database access serialized — safe.
        async def process_post(post_id: int):
            post = await AsyncPost.find_one(post_id)
            if post is None:
                return
            # AsyncBelongsTo: add await, same method name
            author = await post.author()
            # AsyncHasMany: add await, same method name
            approved = len([c for c in await post.comments() if c.is_approved])
            post.view_count = 1 + approved
            await post.save()

        tasks = [process_post(pid) for pid in post_ids]
        await asyncio.gather(*tasks)
    finally:
        # 2. Disconnect before process exits (same method name as sync, add await)
        await AsyncUser.backend().disconnect()


def run_async_worker(post_ids: list[int]):
    # Each process has its own event loop and its own connection
    asyncio.run(async_worker_main(post_ids))


if __name__ == "__main__":
    post_ids = list(range(1, 21))
    chunk_size = 5

    with multiprocessing.Pool(processes=4) as pool:
        chunks = [post_ids[i:i+chunk_size] for i in range(0, len(post_ids), chunk_size)]
        pool.map(run_async_worker, chunks)
```

> **Note**: Never share an `asyncio.EventLoop` or `AsyncStorageBackend` instance across processes. `asyncio.run()` creates an independent event loop within each process, satisfying the "independent connection per process" principle.

**Key Rules**:

- `configure()` must be called inside the child process — do not configure in the parent process before forking
- Each process's connection is completely independent, with no shared state
- In async scenarios, coroutines within the same process access the database serially (event loop is single-threaded), requiring no additional locking

See [exp1_basic_multiprocess.py](../../examples/chapter_12_scenarios/parallel_workers/exp1_basic_multiprocess.py) for a runnable timing comparison.

### 3.2 Why Post-Fork Connections Are Dangerous

If you call `configure()` in the parent process before forking, child processes inherit the parent's connection file descriptor. Multiple processes sharing the same file descriptor leads to:

- Write corruption (two processes sending SQL commands simultaneously)
- Premature connection closure (after one process closes, operations in other processes fail)

**Correct pattern**: Fork first (create Pool), then call `configure()` inside child processes.

---

## 4. Deadlocks: Three Typical Scenarios and Prevention

Even with multi-processing, deadlocks can occur when multiple processes write to the same database. Here are three common scenarios, each with both sync and async solutions.

### 4.1 Scenario 1: SQLite Write Lock Contention

SQLite locks the entire database file during write operations (default journal mode). When multiple processes attempt to write simultaneously, latecomers must wait for the lock to be released.

**Problematic code** (same issue for sync and async):

```python
# Synchronous version
def worker(user_ids: list[int]):
    Post.configure(config, SQLiteBackend)
    # Process A holds the write lock; Process B is waiting.
    # If B's wait times out, it throws OperationalError: database is locked
    with Post.transaction():
        for uid in user_ids:
            posts = Post.query().where(Post.c.user_id == uid).all()
            for p in posts:
                p.view_count += 1
                p.save()

# Asynchronous version (same problem; AsyncPost inherits from AsyncBaseActiveRecord)
async def async_worker(user_ids: list[int]):
    await AsyncPost.configure(config, AsyncSQLiteBackend)
    async with AsyncPost.transaction():
        for uid in user_ids:
            posts = await AsyncPost.query().where(AsyncPost.c.user_id == uid).all()
            for p in posts:
                p.view_count += 1
                await p.save()
```

**Solution**: Set WAL mode via the `pragmas` dict in `SQLiteConnectionConfig` (applied at connect time), or call `backend().set_pragma()` after connecting.

```python
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

# Option 1: via config (recommended — applied automatically at connect time)
config = SQLiteConnectionConfig(
    database="data.db",
    pragmas={
        "journal_mode": "WAL",
        "busy_timeout": "5000",   # wait up to 5000ms
    }
)

# Synchronous version
def worker(user_ids: list[int]):
    Post.configure(config, SQLiteBackend)   # WAL mode set automatically at connect
    with Post.transaction():
        for uid in user_ids:
            posts = Post.query().where(Post.c.user_id == uid).all()
            for p in posts:
                p.view_count += 1
                p.save()

# Asynchronous version (structurally symmetric, same method names, add await)
async def async_worker(user_ids: list[int]):
    await AsyncPost.configure(config, AsyncSQLiteBackend)
    async with AsyncPost.transaction():
        for uid in user_ids:
            posts = await AsyncPost.query().where(AsyncPost.c.user_id == uid).all()
            for p in posts:
                p.view_count += 1
                await p.save()
```

```python
# Option 2: set dynamically after connecting (requires a backend instance)
# Synchronous
def worker(user_ids: list[int]):
    Post.configure(config, SQLiteBackend)
    Post.backend().set_pragma("journal_mode", "WAL")
    Post.backend().set_pragma("busy_timeout", 5000)
    with Post.transaction():
        ...

# Asynchronous (same method names, add await)
async def async_worker(user_ids: list[int]):
    await AsyncPost.configure(config, AsyncSQLiteBackend)
    await AsyncPost.backend().set_pragma("journal_mode", "WAL")
    await AsyncPost.backend().set_pragma("busy_timeout", 5000)
    async with AsyncPost.transaction():
        ...
```

> **Note**: `set_pragma()` is a **SQLite-specific** convenience method and is not available on MySQL, PostgreSQL, or other backends. For other databases, configure timeouts and isolation levels through their respective connection config parameters (e.g., `connect_args` dict) or driver-level settings.

See [exp2_sqlite_wal_mode.py](../../examples/chapter_12_scenarios/parallel_workers/exp2_sqlite_wal_mode.py) for a runnable performance comparison of WAL mode vs. default journal mode under concurrent writes.

### 4.2 Scenario 2: MySQL/PostgreSQL Row Lock Order Conflict

Process A first locks record 1, then requests to lock record 2. Process B first locks record 2, then requests to lock record 1. They wait on each other — deadlock.

**Solution**: **Always lock resources in the same order** (sorted by primary key).

```python
# Synchronous version
def transfer_safe(from_id: int, to_id: int, amount: float):
    first_id, second_id = min(from_id, to_id), max(from_id, to_id)
    with Account.transaction():
        first  = Account.find_one(first_id)
        second = Account.find_one(second_id)
        debit, credit = (first, second) if from_id < to_id else (second, first)
        debit.balance  -= amount
        credit.balance += amount
        debit.save()
        credit.save()

# Asynchronous version (structurally symmetric, same method names, add await)
async def transfer_safe_async(from_id: int, to_id: int, amount: float):
    first_id, second_id = min(from_id, to_id), max(from_id, to_id)
    async with Account.transaction():
        first  = await Account.find_one(first_id)
        second = await Account.find_one(second_id)
        debit, credit = (first, second) if from_id < to_id else (second, first)
        debit.balance  -= amount
        credit.balance += amount
        await debit.save()
        await credit.save()
```

### 4.3 Scenario 3: Duplicate Processing (Without Atomic Claim)

Multiple Workers simultaneously query for "pending tasks," all retrieve the same batch, and all start processing — tasks get executed multiple times.

See [exp3_deadlock_wrong.py](../../examples/chapter_12_scenarios/parallel_workers/exp3_deadlock_wrong.py) for a runnable demonstration of this duplicate-processing race condition.

**Solution**: Query pending tasks and atomically update their status to "processing" inside a single transaction. Transaction isolation guarantees that only one Worker can complete the claim for the same batch.

```python
# Synchronous version
def claim_posts(batch_size: int = 5) -> list:
    """Atomic post claim: query + update inside a transaction, no duplicates"""
    with Post.transaction():
        # Query pending posts
        pending = (
            Post.query()
                .where(Post.c.status == "draft")
                .order_by(Post.c.id)
                .limit(batch_size)
                .all()
        )
        if not pending:
            return []
        # Atomically update status inside the transaction
        for post in pending:
            post.status = "processing"
            post.save()
        return pending

def worker(worker_id: int):
    config = SQLiteConnectionConfig(
        database="data.db",
        pragmas={"journal_mode": "WAL", "busy_timeout": "10000"},
    )
    Post.configure(config, SQLiteBackend)
    Comment.__backend__ = Post.backend()
    while True:
        posts = claim_posts()
        if not posts:
            break
        for post in posts:
            # Traverse HasMany relationship to count approved comments
            approved = len([c for c in post.comments() if c.is_approved])
            post.status = "published"
            post.view_count = 1 + approved
            post.save()
    Post.backend().disconnect()

# Asynchronous version (structurally symmetric, same method names, add await)
async def claim_posts_async(batch_size: int = 5) -> list:
    """Async atomic post claim"""
    async with AsyncPost.transaction():
        pending = await (
            AsyncPost.query()
                .where(AsyncPost.c.status == "draft")
                .order_by(AsyncPost.c.id)
                .limit(batch_size)
                .all()
        )
        if not pending:
            return []
        for post in pending:
            post.status = "processing"
            await post.save()
        return pending

async def async_worker(worker_id: int):
    config = SQLiteConnectionConfig(
        database="data.db",
        pragmas={"journal_mode": "WAL", "busy_timeout": "10000"},
    )
    await AsyncPost.configure(config, AsyncSQLiteBackend)
    AsyncComment.__backend__ = AsyncPost.backend()
    while True:
        posts = await claim_posts_async()
        if not posts:
            break
        for post in posts:
            approved = len([c for c in await post.comments() if c.is_approved])
            post.status = "published"
            post.view_count = 1 + approved
            await post.save()
    await AsyncPost.backend().disconnect()
```

See [exp4_partition_correct.py](../../examples/chapter_12_scenarios/parallel_workers/exp4_partition_correct.py) for a complete runnable implementation of both data partitioning and atomic claim strategies. Running it confirms 100/100 tasks processed with no duplicates.

### 4.4 Five Prevention Principles

| Principle | Description |
| --- | --- |
| **Data partitioning** | Distribute data by ID range or hash across Workers; avoid multiple processes touching the same rows |
| **Consistent lock ordering** | When multiple resources are involved, request locks in a fixed order (e.g., ascending primary key) |
| **Short transactions** | Keep only essential operations inside transactions; do not span I/O waits or expensive computation |
| **Atomic claim** | Query and update task status inside a transaction rather than read-then-modify |
| **Lock timeout** | Configure `pragmas={"busy_timeout": 5000}` (SQLite) or driver-level timeout parameters (MySQL/PostgreSQL) to avoid indefinite waits |

---

## 5. Application Separation Principle

When your system has two fundamentally different workloads, deploy them as separate applications.

### 5.1 Scenario Examples

| Workload Type | Characteristics | Suitable Deployment |
| --- | --- | --- |
| Web API service | Short requests, high concurrency, response-time sensitive | FastAPI / Django + asyncio |
| Data analytics batch processing | Long-running, large datasets, CPU-intensive | Standalone script + multiprocessing |
| Task queue consumer | Periodic polling, tasks are independent, easy to scale horizontally | Celery / custom + multiprocessing |

### 5.2 Why Not Mix Them

Running data analytics tasks inside the Web service process causes:

- **Web response blocking**: Long-running queries hold the connection, causing user requests to queue
- **Connection contention**: Web requests and analytics jobs compete for the same connection (or connection pool slots)
- **Poor error isolation**: An analytics task crash can bring down the entire Web service

**Recommended architecture**:

```text
User request ──→ Web app (asyncio + async connection)
                    │
                    └──→ Task queue (Redis / database table)
                                │
                                └──→ Background Worker process pool
                                      (each process: independent sync or async connection)
```

The Web application handles incoming requests and writes to the task queue. The Worker process pool executes long-running tasks — each side isolated from the other.

---

## 6. Special Considerations for asyncio Concurrency

asyncio is **single-threaded cooperative scheduling** — multiple coroutines take turns executing in the same thread. There are no multi-threading race conditions. However, transactions can still be "interleaved."

### 6.1 Operations Without Transactions: Safe

```python
# A single query is atomic; multiple coroutines calling concurrently do not interfere
async def handle_request(user_id: int):
    user = await User.find_one(user_id)
    return user
```

### 6.2 Transactions Containing `await`: Use Caution

```python
async def update_user(user_id: int):
    async with User.transaction():
        user = await User.find_one(user_id)
        # ← This await yields control back to the event loop.
        #   Other coroutines may execute and write to the database here,
        #   corrupting transaction semantics.
        await asyncio.sleep(0)  # simulates I/O wait
        user.name = "new name"
        await user.save()
```

### 6.3 Safe Usage with asyncio

**Avoid** concurrently opening multiple transactions on the same connection. **Prefer** keeping transactions compact with minimal `await` calls inside.

```python
# Correct: compact transaction, no unnecessary awaits
async with User.transaction():
    user = await User.find_one(user_id)
    user.name = "new name"
    await user.save()
# Transaction ends; other coroutines can start their own transactions
```

### 6.4 SQLite Async Performance Characteristics

When using SQLite, you may observe that **the async version is slower than the sync version**. This is not a code issue — it is an inherent characteristic of the SQLite async implementation.

**Root cause**: The SQLite async backend (`aiosqlite`) is not truly asynchronous I/O. It wraps synchronous `sqlite3` calls inside a thread pool (`run_in_executor`) to simulate `await` semantics. This means:

| Overhead source | Explanation |
| --- | --- |
| Thread switching | Every database operation requires switching to a thread pool thread and back |
| Coroutine scheduling | Every `await` involves event loop scheduling overhead |
| Writes remain serial | SQLite file-locking is unchanged; `await` brings no concurrency benefit |

**Comparison with MySQL/PostgreSQL async**:

`aiomysql` / `asyncpg` use true **async network I/O**. During `await`, the CPU can genuinely switch to handle other coroutines while waiting for a network response — the event loop is never blocked. This is where asyncio actually delivers performance gains.

```text
SQLite async (aiosqlite):
  coroutine → thread pool → sqlite3.execute() → wait for disk → thread callback → coroutine resumes
  (adds thread scheduling overhead compared to sync; writes remain serial)

MySQL/PostgreSQL async (aiomysql/asyncpg):
  coroutine → send SQL → await network response → other coroutines run meanwhile → response arrives → coroutine resumes
  (true I/O concurrency; network wait does not block the event loop)
```

**Practical guidelines**:

- SQLite workloads: The sync version is often sufficient and may even be faster. Use async only when you need to integrate with other async code.
- MySQL/PostgreSQL workloads: In high-concurrency web services (e.g., FastAPI), async significantly reduces wait time.
- In experiments `exp1` and `exp2`, observing async slightly slower than sync is expected behavior.

---

## 7. Example Code

The complete runnable examples for this chapter are in [`docs/examples/chapter_12_scenarios/parallel_workers/`](../../examples/chapter_12_scenarios/parallel_workers/):

| File | Contents | Section |
| --- | --- | --- |
| [`models.py`](../../examples/chapter_12_scenarios/parallel_workers/models.py) | Shared model definitions (`User`, `Post`, `Comment` — sync and async versions) | — |
| [`setup_db.py`](../../examples/chapter_12_scenarios/parallel_workers/setup_db.py) | Database initialization script (sync and async modes) | — |
| [`exp1_basic_multiprocess.py`](../../examples/chapter_12_scenarios/parallel_workers/exp1_basic_multiprocess.py) | Correct multi-process usage (serial / sync multi-process / async multi-process timing comparison) | §3.1 |
| [`exp2_sqlite_wal_mode.py`](../../examples/chapter_12_scenarios/parallel_workers/exp2_sqlite_wal_mode.py) | SQLite WAL mode vs. default journal mode concurrent write performance | §4.1 |
| [`exp3_deadlock_wrong.py`](../../examples/chapter_12_scenarios/parallel_workers/exp3_deadlock_wrong.py) | Demonstrates duplicate processing without atomic claim (anti-pattern) | §4.3 |
| [`exp4_partition_correct.py`](../../examples/chapter_12_scenarios/parallel_workers/exp4_partition_correct.py) | Correct implementation with data partitioning + atomic claim (sync and async, two strategies each) | §4.3, §4.4 |
| [`exp5_multithread_warning.py`](../../examples/chapter_12_scenarios/parallel_workers/exp5_multithread_warning.py) | Demonstrates the problem with multi-threaded shared connection (anti-pattern) | §2 |

> **Note**: All example files use the `rhosocial-activerecord` ORM directly. The model hierarchy is `User → Post → Comment`, demonstrating sync/async parity for `HasMany` and `BelongsTo` relationships.

Run the initialization script first, then any experiment:

```bash
cd docs/examples/chapter_12_scenarios/parallel_workers
python setup_db.py
python exp1_basic_multiprocess.py   # or any other experiment
```

See the `README.md` in that directory for full instructions and expected output for each experiment.
