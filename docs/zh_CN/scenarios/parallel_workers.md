# 并行 Worker 场景下的正确用法

在数据处理、任务队列、批量导入等场景中，开发者常常希望用多个 Worker 并行处理任务以提升吞吐量。本章将分析 ActiveRecord 在这类场景下的行为，指出常见陷阱，并给出经过验证的安全方案。

> **贯穿本章的设计原则**：`rhosocial-activerecord` 的同步类 `BaseActiveRecord` 与异步类 `AsyncBaseActiveRecord` 方法名**完全相同**——`configure()` / `backend()` / `transaction()` / `save()` 等均如此，异步版本只需加 `await` 或 `async with`。本章所有示例均提供两种版本。

## 目录

1. [ActiveRecord 的单连接模型](#1-activerecord-的单连接模型)
2. [多线程为什么危险](#2-多线程为什么危险)
3. [多进程：推荐方案](#3-多进程推荐方案)
4. [死锁：三种典型场景及预防](#4-死锁三种典型场景及预防)
5. [应用分离原则](#5-应用分离原则)
6. [asyncio 并发的特殊性](#6-asyncio-并发的特殊性)
7. [示例代码](#7-示例代码)

---

## 1. ActiveRecord 的单连接模型

`rhosocial-activerecord` 的核心设计原则是：**一个 ActiveRecord 类，绑定一条连接**。

- **同步**：`User.configure(config, SQLiteBackend)` → 写入 `User.__backend__`（`User` 继承自 `BaseActiveRecord`）
- **异步**：`await User.configure(config, AsyncSQLiteBackend)` → 写入 `User.__backend__`（`User` 继承自 `AsyncBaseActiveRecord`）

`configure()` 写入的是**类级别属性**，这意味着：

- 不论有多少个线程、多少个协程，它们引用的是同一个 `StorageBackend` 对象
- `StorageBackend` 内部封装着一条底层数据库连接（`sqlite3.Connection` / `mysql.connector.Connection` 等）
- 这些底层连接对象**不是线程安全的**

---

## 2. 多线程为什么危险

### 2.1 连接对象不线程安全

Python 的主流数据库驱动均明确说明连接对象不应在线程间共享：

| 驱动 | 官方说明 |
| --- | --- |
| `sqlite3` | "Connection 对象不是线程安全的" |
| `mysql-connector-python` | "Connection 不支持多线程并发使用" |
| `psycopg3` | "Connection 不是线程安全的" |

多线程共享 `__backend__` 会导致数据库游标混乱、数据损坏，甚至进程崩溃。

尤其是 SQLite 后端，`SQLiteConnectionConfig.check_same_thread` 默认为 `True`，一旦在非创建线程中访问连接，会直接抛出 `ProgrammingError`。

### 2.2 TransactionManager 没有锁

ActiveRecord 内部的 `TransactionManager` 使用普通 Python 整数和列表管理事务状态：

```python
class TransactionManagerBase:
    def __init__(self, ...):
        self._transaction_level = 0     # 普通 int，无锁
        self._state = TransactionState.INACTIVE
        self._active_savepoints = []    # 普通列表，无锁
```

线程 A 和线程 B 同时调用 `begin()` 时，会发生经典的**检查后修改**（Check-Then-Act）竞态：

```text
线程 A: if self._transaction_level == 0:  → 条件成立
线程 B: if self._transaction_level == 0:  → 条件成立（A 还没写入）
线程 A: self._do_begin(); self._transaction_level += 1  → level = 1
线程 B: self._do_begin(); self._transaction_level += 1  → BEGIN 再次执行！
```

结果：数据库收到两条 `BEGIN` 指令，事务状态损坏。同步和异步的 `TransactionManager` 均无锁，异步版本还因 `await` 存在额外的协程切换点，在同一进程内并发开启多事务时同样危险。

### 2.3 结论

> **不要将 ActiveRecord 配置在多个线程之间共享。** 多线程 + 共享 `__backend__` 是未定义行为。

可运行的演示代码见 [exp5_multithread_warning.py](../../examples/chapter_12_scenarios/parallel_workers/exp5_multithread_warning.py)，其中"场景 0"通过实验验证了 `check_same_thread=True` 默认值，"场景 1"展示共享连接的危险，"场景 2"展示每线程独立连接的局限性。

---

## 3. 多进程：推荐方案

多进程是并行 Worker 场景的推荐方案。每个进程拥有独立的内存空间，`configure()` 在进程内独立执行，连接完全隔离。

### 3.1 正确的生命周期

**同步（multiprocessing）**：

```python
import multiprocessing
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from models import Comment, Post, User  # User --has_many--> Post --has_many--> Comment

def worker(post_ids: list[int]):
    # 1. 进程启动后，在进程内配置连接——每个进程独立的连接，互不干扰
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
            # 通过 BelongsTo 关联获取作者
            author = post.author()
            # 通过 HasMany 关联统计已审核评论数
            approved = len([c for c in post.comments() if c.is_approved])
            post.view_count = 1 + approved
            post.save()
    finally:
        # 2. 进程退出前断开连接（可选，进程退出时会自动关闭）
        User.backend().disconnect()


if __name__ == "__main__":
    post_ids = list(range(1, 21))  # 20 篇文章
    chunk_size = 5

    with multiprocessing.Pool(processes=4) as pool:
        chunks = [post_ids[i:i+chunk_size] for i in range(0, len(post_ids), chunk_size)]
        pool.map(worker, chunks)
```

**异步（asyncio + 多进程）**：

asyncio 本身是单线程的，每个 `async def` 协程共享同一条连接（`AsyncBaseActiveRecord.__backend__`）。若要并行执行多个异步 Worker，正确的方式仍然是**多进程**：每个进程内部用 asyncio 驱动协程，进程间连接完全隔离。

```python
import asyncio
import multiprocessing
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from models import AsyncComment, AsyncPost, AsyncUser  # 异步版模型，方法名与同步版完全相同

async def async_worker_main(post_ids: list[int]):
    # 1. 在进程内配置异步连接（方法名与同步版本相同，加 await）
    config = SQLiteConnectionConfig(
        database="data.db",
        pragmas={"journal_mode": "WAL", "busy_timeout": "10000"},
    )
    await AsyncUser.configure(config, AsyncSQLiteBackend)
    AsyncPost.__backend__ = AsyncUser.backend()
    AsyncComment.__backend__ = AsyncUser.backend()

    try:
        # 同一进程内的协程共享这条连接，串行访问数据库，安全
        async def process_post(post_id: int):
            post = await AsyncPost.find_one(post_id)
            if post is None:
                return
            # 通过异步 BelongsTo 关联获取作者（加 await，方法名相同）
            author = await post.author()
            approved = len([c for c in await post.comments() if c.is_approved])
            post.view_count = 1 + approved
            await post.save()

        tasks = [process_post(pid) for pid in post_ids]
        await asyncio.gather(*tasks)
    finally:
        # 2. 进程退出前断开连接（与同步版本方法名相同，加 await）
        await AsyncUser.backend().disconnect()


def run_async_worker(post_ids: list[int]):
    # 每个进程有独立的 event loop 和独立的连接
    asyncio.run(async_worker_main(post_ids))


if __name__ == "__main__":
    post_ids = list(range(1, 21))
    chunk_size = 5

    with multiprocessing.Pool(processes=4) as pool:
        chunks = [post_ids[i:i+chunk_size] for i in range(0, len(post_ids), chunk_size)]
        pool.map(run_async_worker, chunks)
```

> **注意**：不要在多个进程间共享同一个 `asyncio.EventLoop` 或 `AsyncStorageBackend` 实例。`asyncio.run()` 会在每个进程内独立创建 event loop，符合"进程内独立连接"的原则。

**关键规则**：

- `configure()` 必须在子进程内调用，不能在父进程配置后 `fork`
- 每个进程的连接完全独立，不存在共享状态
- 异步场景下，同一进程内的协程天然串行访问数据库（event loop 单线程调度），无需额外锁

可运行的耗时对比演示见 [exp1_basic_multiprocess.py](../../examples/chapter_12_scenarios/parallel_workers/exp1_basic_multiprocess.py)。

### 3.2 为什么 fork 后的连接是危险的

如果在父进程 `configure()` 之后 `fork`，子进程会继承父进程的连接句柄。多个进程共用同一个文件描述符，会导致：

- 写入混乱（两个进程同时发送 SQL 命令）
- 连接提前关闭（一个进程关闭后，另一个进程的操作失败）

**正确模式**：先 `fork`（创建 Pool），再在子进程内调用 `configure()`。

---

## 4. 死锁：三种典型场景及预防

多进程并行写同一数据库时，仍然可能遇到死锁。以下是三种常见场景，每种均提供同步和异步两个版本的解决方案。

### 4.1 场景一：SQLite 写锁争用

SQLite 在写操作时对整个数据库文件加锁（默认 journal 模式）。多个进程同时尝试写入时，后来者必须等待锁释放。

**问题代码**（同步 / 异步同理）：

```python
# 同步版本
def worker(user_ids: list[int]):
    Post.configure(config, SQLiteBackend)
    # 进程 A 持有写锁，进程 B 在等待
    # 如果 B 的等待超时，会抛出 OperationalError: database is locked
    with Post.transaction():
        for uid in user_ids:
            posts = Post.query().where(Post.c.user_id == uid).all()
            for p in posts:
                p.view_count += 1
                p.save()

# 异步版本（问题相同；AsyncPost 继承自 AsyncBaseActiveRecord）
async def async_worker(user_ids: list[int]):
    await AsyncPost.configure(config, AsyncSQLiteBackend)
    async with AsyncPost.transaction():
        for uid in user_ids:
            posts = await AsyncPost.query().where(AsyncPost.c.user_id == uid).all()
            for p in posts:
                p.view_count += 1
                await p.save()
```

**解决方案**：通过 `SQLiteConnectionConfig` 的 `pragmas` 字典在连接时预设 WAL 模式，或连接后调用 `backend().set_pragma()`。

```python
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

# 方式一：通过 config 预设（推荐，连接时自动生效）
config = SQLiteConnectionConfig(
    database="data.db",
    pragmas={
        "journal_mode": "WAL",
        "busy_timeout": "5000",   # 等待最多 5000ms
    }
)

# 同步版本
def worker(user_ids: list[int]):
    Post.configure(config, SQLiteBackend)   # WAL 模式已在连接时自动设置
    with Post.transaction():
        for uid in user_ids:
            posts = Post.query().where(Post.c.user_id == uid).all()
            for p in posts:
                p.view_count += 1
                p.save()

# 异步版本（结构完全对称，方法名相同，加 await）
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
# 方式二：连接后动态设置（需要后端实例）
# 同步
def worker(user_ids: list[int]):
    Post.configure(config, SQLiteBackend)
    Post.backend().set_pragma("journal_mode", "WAL")
    Post.backend().set_pragma("busy_timeout", 5000)
    with Post.transaction():
        ...

# 异步（方法名相同，加 await）
async def async_worker(user_ids: list[int]):
    await AsyncPost.configure(config, AsyncSQLiteBackend)
    await AsyncPost.backend().set_pragma("journal_mode", "WAL")
    await AsyncPost.backend().set_pragma("busy_timeout", 5000)
    async with AsyncPost.transaction():
        ...
```

> **注意**：`set_pragma()` 是 **SQLite 后端专属**的便捷方法，MySQL、PostgreSQL 等后端没有此方法。其他数据库请通过各自的连接配置（如 `connect_args` 字典）或驱动级别设置来配置超时与隔离级别。

可运行的 WAL 模式并发写入性能对比见 [exp2_sqlite_wal_mode.py](../../examples/chapter_12_scenarios/parallel_workers/exp2_sqlite_wal_mode.py)。

### 4.2 场景二：MySQL/PostgreSQL 行锁顺序冲突

进程 A 先锁定记录 1，再请求锁定记录 2；进程 B 先锁定记录 2，再请求锁定记录 1。两者互相等待，产生死锁。

**解决方案**：**始终以相同的顺序锁定资源**（按主键排序）。

```python
# 同步版本
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

# 异步版本（结构完全对称，方法名相同，加 await）
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

### 4.3 场景三：重复处理（无原子领取）

多个 Worker 同时查询"待处理任务"，都读到同一批，都开始处理，导致任务被重复执行。

反面教材见 [exp3_deadlock_wrong.py](../../examples/chapter_12_scenarios/parallel_workers/exp3_deadlock_wrong.py)，可直观看到无原子领取时的重复处理现象。

**解决方案**：在事务内先查询待处理任务，再原子地将其状态更新为处理中。事务的隔离性保证同一批任务只有一个 Worker 能完成领取。

```python
# 同步版本
def claim_posts(batch_size: int = 5) -> list:
    """原子领取文章：事务内查询 + 更新，保证不重复"""
    with Post.transaction():
        # 查询待处理文章
        pending = (
            Post.query()
                .where(Post.c.status == "draft")
                .order_by(Post.c.id)
                .limit(batch_size)
                .all()
        )
        if not pending:
            return []
        # 在事务内原子更新状态
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
            # 统计已审核评论数（HasMany 关联）
            approved = len([c for c in post.comments() if c.is_approved])
            post.status = "published"
            post.view_count = 1 + approved
            post.save()
    Post.backend().disconnect()

# 异步版本（结构完全对称，方法名相同，加 await）
async def claim_posts_async(batch_size: int = 5) -> list:
    """异步原子领取"""
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

数据分区与原子领取的完整可运行实现见 [exp4_partition_correct.py](../../examples/chapter_12_scenarios/parallel_workers/exp4_partition_correct.py)，运行后可验证 100/100 个任务均无重复处理。

### 4.4 五条预防原则

| 原则 | 说明 |
| --- | --- |
| **数据分区** | 将数据集按 ID 范围或哈希分配给各 Worker，避免多进程操作同一行 |
| **一致的锁顺序** | 涉及多资源时，按固定顺序（如主键升序）请求锁 |
| **短事务** | 事务内只做必要操作，不跨越 I/O 等待或耗时计算 |
| **原子领取** | 在事务内查询并更新任务状态，而非先读后改 |
| **锁超时** | 通过 `pragmas={"busy_timeout": 5000}`（SQLite）或数据库驱动参数（MySQL/PostgreSQL）配置超时，避免永久等待 |

---

## 5. 应用分离原则

当你的系统同时包含两种截然不同的工作负载时，建议将它们部署为独立应用。

### 5.1 场景示例

| 工作负载类型 | 特征 | 合适部署 |
| --- | --- | --- |
| Web API 服务 | 短请求、高并发、响应时间敏感 | FastAPI / Django + asyncio |
| 数据分析批处理 | 长时间运行、大数据量、CPU 密集 | 独立脚本 + multiprocessing |
| 任务队列消费 | 定期轮询、任务间独立、易于水平扩展 | Celery / 自定义 + multiprocessing |

### 5.2 为什么不混在一起

把数据分析任务放在 Web 服务进程内运行，会产生以下问题：

- **阻塞 Web 响应**：长时间查询占用连接，用户请求排队
- **连接争用**：Web 请求和分析任务竞争同一条连接（或连接池槽位）
- **错误隔离差**：分析任务崩溃可能拖垮整个 Web 服务

**推荐架构**：

```text
用户请求 ──→ Web 应用（asyncio + 异步连接）
                │
                └──→ 任务队列（Redis / 数据库表）
                            │
                            └──→ 后台 Worker 进程池
                                  （每进程独立同步或异步连接）
```

Web 应用负责接收请求、写入任务队列；Worker 进程池负责执行耗时任务，互不干扰。

---

## 6. asyncio 并发的特殊性

asyncio 是**单线程协作式调度**，多个协程在同一线程内交替执行，不会有多线程的竞态条件。但事务仍然可能被"穿插"。

### 6.1 无事务操作：安全

```python
# 单条查询是原子的，多个协程并发调用不会互相干扰
async def handle_request(user_id: int):
    user = await User.find_one(user_id)
    return user
```

### 6.2 含 `await` 的事务：需要注意

```python
async def update_user(user_id: int):
    async with User.transaction():
        user = await User.find_one(user_id)
        # ← 此处 await 将控制权交还给 event loop
        #   其他协程可能在这里执行并写入数据库，导致事务语义损坏
        await asyncio.sleep(0)  # 模拟 I/O 等待
        user.name = "new name"
        await user.save()
```

### 6.3 asyncio 的安全用法

**避免**并发地对同一连接开启多个事务；**推荐**事务内操作紧凑，避免不必要的 `await`。

```python
# 正确：事务内操作紧凑，无额外 await
async with User.transaction():
    user = await User.find_one(user_id)
    user.name = "new name"
    await user.save()
# 事务结束，其他协程可以开始各自的事务
```

### 6.4 SQLite 异步的性能特殊性

使用 SQLite 时，你可能会观察到**异步版本比同步版本还慢**的情况。这不是代码问题，而是 SQLite 异步实现的固有特性。

**根本原因**：SQLite 异步后端（`aiosqlite`）并不是真正的异步 I/O。它将同步的 `sqlite3` 调用封装进线程池（`run_in_executor`），以模拟 `await` 语义。这意味着：

| 开销来源 | 说明 |
| --- | --- |
| 线程切换 | 每次数据库操作都要切换到线程池线程再切换回来 |
| 协程调度 | 每次 `await` 都涉及 event loop 的调度开销 |
| 写入仍串行 | SQLite 文件锁机制不变，`await` 无法带来并发加速 |

**对比 MySQL/PostgreSQL 异步**：

`aiomysql` / `asyncpg` 使用真正的**异步网络 I/O**。`await` 期间，CPU 可以真正切换处理其他协程，等待网络响应时不阻塞 event loop。这才是 asyncio 真正能提速的场景。

```text
SQLite async（aiosqlite）：
  协程 → 线程池 → sqlite3.execute() → 等待磁盘 → 线程回调 → 协程恢复
  （相比同步增加了线程调度开销，写入仍然串行）

MySQL/PostgreSQL async（aiomysql/asyncpg）：
  协程 → 发送 SQL → await 网络响应 → 期间可运行其他协程 → 响应到达 → 协程恢复
  （真正的 I/O 并发，网络等待期间不阻塞）
```

**实践建议**：

- SQLite 场景：同步版本往往足够，甚至更快；异步版本适合需要与其他 async 代码集成时
- MySQL/PostgreSQL 场景：高并发 Web 服务（如 FastAPI）中，异步版本能显著减少等待时间
- 在实验 `exp1` 和 `exp2` 中，若观察到异步比同步略慢，属于预期行为

---

## 7. 示例代码

本章的完整可运行示例位于 [`docs/examples/chapter_12_scenarios/parallel_workers/`](../../examples/chapter_12_scenarios/parallel_workers/)，包含以下实验：

| 文件 | 内容 | 对应章节 |
| --- | --- | --- |
| [`models.py`](../../examples/chapter_12_scenarios/parallel_workers/models.py) | 共享模型定义（`User`、`Post`、`Comment` 同步版 + 异步版） | — |
| [`setup_db.py`](../../examples/chapter_12_scenarios/parallel_workers/setup_db.py) | 数据库初始化脚本（同步/异步两种模式） | — |
| [`exp1_basic_multiprocess.py`](../../examples/chapter_12_scenarios/parallel_workers/exp1_basic_multiprocess.py) | 正确的多进程用法（含串行/同步多进程/异步多进程耗时对比） | §3.1 |
| [`exp2_sqlite_wal_mode.py`](../../examples/chapter_12_scenarios/parallel_workers/exp2_sqlite_wal_mode.py) | SQLite WAL 模式 vs 默认日志模式下的并发写入性能 | §4.1 |
| [`exp3_deadlock_wrong.py`](../../examples/chapter_12_scenarios/parallel_workers/exp3_deadlock_wrong.py) | 演示无原子领取导致重复处理（反面教材） | §4.3 |
| [`exp4_partition_correct.py`](../../examples/chapter_12_scenarios/parallel_workers/exp4_partition_correct.py) | 数据分区 + 原子领取的正确实现（同步/异步各两种方案） | §4.3、§4.4 |
| [`exp5_multithread_warning.py`](../../examples/chapter_12_scenarios/parallel_workers/exp5_multithread_warning.py) | 展示多线程共享连接的问题（反面教材） | §2 |

> **说明**：所有示例文件均直接使用 `rhosocial-activerecord` ORM，模型体系为 `User → Post → Comment`，并体现 `HasMany` / `BelongsTo` 关联关系的同步与异步对等用法。

运行前请先执行初始化脚本：

```bash
cd docs/examples/chapter_12_scenarios/parallel_workers
python setup_db.py
python exp1_basic_multiprocess.py   # 运行任意实验
```

详见该目录下的 `README.md` 了解各实验的完整说明和预期输出。
