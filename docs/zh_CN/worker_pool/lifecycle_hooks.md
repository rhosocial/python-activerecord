# 生命周期钩子

WorkerPool 支持在 Worker 和任务的关键生命周期点执行自定义钩子函数。

## 钩子类型

| 事件 | 触发时机 | 典型用途 |
|------|----------|----------|
| `WORKER_START` | Worker 进程启动时 | 初始化数据库连接、加载配置 |
| `WORKER_STOP` | Worker 进程退出时 | 关闭连接池、释放资源 |
| `TASK_START` | 任务执行前 | 记录开始日志、建立任务级连接 |
| `TASK_END` | 任务执行后 | 记录执行日志、清理资源、统计监控 |

## 钩子格式

钩子可以以多种格式指定：

```python
# 单个可调用对象
on_worker_start=my_hook

# 可调用对象列表
on_worker_start=[hook1, hook2]

# 带参数的元组（调用方式：hook(ctx, arg1, arg2)）
on_worker_start=(my_hook, arg1, arg2)

# 字符串路径（用于配置驱动的方式）
on_worker_start="myapp.hooks.my_hook"

# 混合列表
on_worker_start=["myapp.hooks.hook1", hook2]
```

**重要提示**：在 spawn 模式下，局部函数和 lambda 无法被 pickle。必须在正确的模块中定义钩子以确保多进程兼容性。

## 任务函数签名

任务函数**必须**接受 `ctx: TaskContext` 作为第一个参数：

```python
def my_task(ctx: TaskContext, user_id: int) -> dict:
    """任务函数，上下文作为第一个参数。"""
    # 访问 Worker 级数据
    db = ctx.worker_ctx.data.get('db')
    # 存储任务级数据
    ctx.data['processed'] = True
    return {"id": user_id}

# 提交任务（ctx 自动注入）
pool.submit(my_task, user_id=123)
```

## 同步与异步模式

WorkerPool 同时支持同步和异步钩子：

- **同步模式**：所有钩子都是同步函数，不创建事件循环
- **异步模式**：至少有一个钩子是异步的，Worker 生命周期内运行单个事件循环
- **混合模式被拒绝**：混合同步和异步钩子会抛出 `TypeError`

```python
# 同步模式
def init_worker(ctx: WorkerContext):
    Database.connect()

# 异步模式
async def init_worker(ctx: WorkerContext):
    await AsyncDatabase.connect()
    ctx.data['db'] = db  # 存储供任务访问
```

**警告**：在异步模式下，同步任务会阻塞事件循环。当所有钩子都是异步时，请使用异步任务。

## 钩子使用示例

```python
from rhosocial.activerecord.worker import WorkerPool, WorkerContext, TaskContext

def init_worker(ctx: WorkerContext):
    """Worker 启动时初始化数据库连接"""
    from myapp.db import Database
    db = Database.connect()
    ctx.data['db'] = db  # 存储在 Worker 上下文中
    print(f"Worker-{ctx.worker_id} (pid={ctx.pid}) 已初始化")

def cleanup_worker(ctx: WorkerContext):
    """Worker 退出时清理资源"""
    db = ctx.data.get('db')
    if db:
        db.close()
    print(f"Worker-{ctx.worker_id} 处理了 {ctx.task_count} 个任务")

def log_task(ctx: TaskContext):
    """任务完成后记录日志"""
    import logging
    logger = logging.getLogger(__name__)
    status = "成功" if ctx.success else "失败"
    logger.info(
        f"任务 {ctx.task_id[:8]}: {ctx.fn_name} - "
        f"{status}, 耗时={ctx.duration:.3f}s, "
        f"内存增量={ctx.memory_delta_mb:.3f}MB"
    )

with WorkerPool(
    n_workers=4,
    on_worker_start=init_worker,
    on_worker_stop=cleanup_worker,
    on_task_end=log_task,
) as pool:
    futures = [pool.submit(process_data, i) for i in range(100)]
    for f in futures:
        f.result(timeout=30)
```

## 带参数的钩子

使用元组格式传递额外参数：

```python
def init_with_config(ctx: WorkerContext, db_name: str, pool_size: int):
    from myapp.db import Database
    db = Database.connect(db_name, pool_size=pool_size)
    ctx.data['db'] = db

# 元组格式：(可调用对象, 参数1, 参数2, ...)
with WorkerPool(
    n_workers=4,
    on_worker_start=(init_with_config, "mydb", 10),
) as pool:
    # ...
```

## 连接管理策略

**设计原则**：框架不替用户做选择——让用户根据业务场景决定何时管理连接。

| 策略 | 钩子位置 | 适用场景 | 特点 |
|------|----------|----------|------|
| **Worker 级连接** | WORKER_START/STOP | 高频短操作 | 连接复用，减少开销 |
| **任务级连接** | TASK_START/END | 低频长操作 | 按需连接，及时释放 |

```python
# 场景1：高频短操作 → Worker 级连接
def worker_connect(ctx: WorkerContext):
    from myapp.db import Database
    Database.connect()

def worker_disconnect(ctx: WorkerContext):
    from myapp.db import Database
    Database.disconnect()

pool = WorkerPool(
    n_workers=4,
    on_worker_start=worker_connect,
    on_worker_stop=worker_disconnect,
)
# 结果：4 个 Worker，4 个连接，所有任务复用它们

# 场景2：低频长操作 → 任务级连接
def task_connect(ctx: TaskContext):
    from myapp.db import Database
    Database.connect()

def task_disconnect(ctx: TaskContext):
    from myapp.db import Database
    Database.disconnect()

pool = WorkerPool(
    n_workers=4,
    on_task_start=task_connect,
    on_task_end=task_disconnect,
)
# 结果：按需连接，任务完成后释放
```

## 上下文对象

### WorkerContext

```python
@dataclass
class WorkerContext:
    worker_id: int        # Worker 索引（0, 1, 2, ...）
    pid: int              # 进程 ID
    pool_id: str          # 进程池实例唯一标识
    start_time: float     # Worker 启动时间戳
    task_count: int       # 已执行任务数
    data: Dict[str, Any]  # 用户数据存储（跨任务持久化）
    event_loop: Optional[asyncio.AbstractEventLoop]  # 事件循环（异步模式）
```

### TaskContext

```python
@dataclass
class TaskContext:
    task_id: str                    # 任务 ID
    worker_ctx: WorkerContext       # Worker 上下文（访问 Worker 级数据）
    fn_name: str                    # 任务函数名
    args: Tuple                     # 位置参数
    kwargs: Dict[str, Any]          # 关键字参数
    start_time: float               # 任务开始时间
    end_time: float                 # 任务结束时间
    success: bool                   # 是否成功
    result: Any                     # 任务结果（成功时）
    error: Optional[Exception]      # 任务异常（失败时）
    memory_start: int               # 任务开始时内存（字节）
    memory_end: int                 # 任务结束时内存（字节）
    data: Dict[str, Any]            # 任务级数据存储

    @property
    def duration(self) -> float:
        """任务耗时（秒）"""

    @property
    def memory_delta(self) -> int:
        """内存增量（字节）"""

    @property
    def memory_delta_mb(self) -> float:
        """内存增量（MB）"""

    def log_summary(self, logger, level=logging.INFO) -> None:
        """记录任务执行摘要"""
```

## 上下文数据共享

WorkerContext.data 在同一 Worker 内跨任务持久化。TaskContext.data 作用域为单个任务。

```python
def init_db(ctx: WorkerContext):
    """在 Worker 上下文中存储连接。"""
    db = Database.connect()
    ctx.data['db'] = db

def my_task(ctx: TaskContext, user_id: int):
    """从任务中访问 Worker 级数据。"""
    db = ctx.worker_ctx.data['db']  # 获取连接
    user = db.query(User).get(user_id)
    ctx.data['processed'] = True    # 任务级数据
    return user
```

## 动态钩子注册

```python
from rhosocial.activerecord.worker import WorkerEvent

pool = WorkerPool(n_workers=4)

# 动态注册
name = pool.register_hook(WorkerEvent.TASK_END, log_task, "task_logger")

# 注销钩子
pool.unregister_hook(WorkerEvent.TASK_END, name)
```
