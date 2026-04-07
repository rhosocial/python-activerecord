# Lifecycle Hooks

WorkerPool supports custom hook functions at key lifecycle points for both workers and tasks.

## Hook Types

| Event | When Triggered | Typical Use |
|-------|----------------|-------------|
| `WORKER_START` | Worker process starts | Initialize database connections, load config |
| `WORKER_STOP` | Worker process exits | Close connection pools, release resources |
| `TASK_START` | Before task execution | Log start, establish task-level connection |
| `TASK_END` | After task execution | Log execution, cleanup, statistics monitoring |

## Hook Format

Hooks can be specified in several formats:

```python
# Single callable
on_worker_start=my_hook

# List of callables
on_worker_start=[hook1, hook2]

# Tuple with args (called as: hook(ctx, arg1, arg2))
on_worker_start=(my_hook, arg1, arg2)

# String path (for configuration-driven setups)
on_worker_start="myapp.hooks.my_hook"

# Mixed list
on_worker_start=["myapp.hooks.hook1", hook2]
```

**Important**: Local functions and lambdas cannot be pickled in spawn mode. Define hooks in a proper module for multiprocessing compatibility.

## Task Function Signature

Task functions **must** accept `ctx: TaskContext` as the first argument:

```python
def my_task(ctx: TaskContext, user_id: int) -> dict:
    """Task function with context as first argument."""
    # Access Worker-level data
    db = ctx.worker_ctx.data.get('db')
    # Store task-level data
    ctx.data['processed'] = True
    return {"id": user_id}

# Submit task (ctx is injected automatically)
pool.submit(my_task, user_id=123)
```

## Sync vs Async Mode

WorkerPool supports both synchronous and asynchronous hooks:

- **Sync mode**: All hooks are synchronous functions, no event loop created
- **Async mode**: At least one hook is async, a single event loop runs for Worker lifetime
- **Mixed mode is rejected**: Mixing sync and async hooks raises `TypeError`

```python
# Sync mode
def init_worker(ctx: WorkerContext):
    Database.connect()

# Async mode
async def init_worker(ctx: WorkerContext):
    await AsyncDatabase.connect()
    ctx.data['db'] = db  # Store for task access
```

**Warning**: In async mode, synchronous tasks will block the event loop. Use async tasks when all hooks are async.

## Hook Usage Example

```python
from rhosocial.activerecord.worker import WorkerPool, WorkerContext, TaskContext

def init_worker(ctx: WorkerContext):
    """Initialize database connection when worker starts"""
    from myapp.db import Database
    db = Database.connect()
    ctx.data['db'] = db  # Store in Worker context
    print(f"Worker-{ctx.worker_id} (pid={ctx.pid}) initialized")

def cleanup_worker(ctx: WorkerContext):
    """Cleanup resources when worker exits"""
    db = ctx.data.get('db')
    if db:
        db.close()
    print(f"Worker-{ctx.worker_id} processed {ctx.task_count} tasks")

def log_task(ctx: TaskContext):
    """Log after task completes"""
    import logging
    logger = logging.getLogger(__name__)
    status = "SUCCESS" if ctx.success else "FAILED"
    logger.info(
        f"Task {ctx.task_id[:8]}: {ctx.fn_name} - "
        f"{status}, duration={ctx.duration:.3f}s, "
        f"memory_delta={ctx.memory_delta_mb:.3f}MB"
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

## Hook with Arguments

Pass additional arguments using tuple format:

```python
def init_with_config(ctx: WorkerContext, db_name: str, pool_size: int):
    from myapp.db import Database
    db = Database.connect(db_name, pool_size=pool_size)
    ctx.data['db'] = db

# Tuple format: (callable, arg1, arg2, ...)
with WorkerPool(
    n_workers=4,
    on_worker_start=(init_with_config, "mydb", 10),
) as pool:
    # ...
```

## Connection Management Strategies

**Design Principle**: The framework doesn't make choices for users - let them decide when to manage connections based on their business scenarios.

| Strategy | Hook Location | Use Case | Characteristics |
|----------|---------------|----------|-----------------|
| **Worker-level connection** | WORKER_START/STOP | High-frequency short operations | Connection reuse, reduced overhead |
| **Task-level connection** | TASK_START/END | Low-frequency long operations | On-demand connection, timely release |

```python
# Scenario 1: High-frequency short operations → Worker-level connection
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
# Result: 4 workers, 4 connections, all tasks reuse them

# Scenario 2: Low-frequency long operations → Task-level connection
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
# Result: On-demand connections, released after task completion
```

## Context Objects

### WorkerContext

```python
@dataclass
class WorkerContext:
    worker_id: int        # Worker index (0, 1, 2, ...)
    pid: int              # Process ID
    pool_id: str          # Pool instance unique identifier
    start_time: float     # Worker start timestamp
    task_count: int       # Number of tasks executed
    data: Dict[str, Any]  # User data storage (persisted across tasks)
    event_loop: Optional[asyncio.AbstractEventLoop]  # Event loop (async mode)
```

### TaskContext

```python
@dataclass
class TaskContext:
    task_id: str                    # Task ID
    worker_ctx: WorkerContext       # Worker context (access Worker-level data)
    fn_name: str                    # Task function name
    args: Tuple                     # Positional arguments
    kwargs: Dict[str, Any]          # Keyword arguments
    start_time: float               # Task start time
    end_time: float                 # Task end time
    success: bool                   # Whether succeeded
    result: Any                     # Task result (on success)
    error: Optional[Exception]      # Task exception (on failure)
    memory_start: int               # Memory at task start (bytes)
    memory_end: int                 # Memory at task end (bytes)
    data: Dict[str, Any]            # Task-level data storage

    @property
    def duration(self) -> float:
        """Task duration in seconds"""

    @property
    def memory_delta(self) -> int:
        """Memory delta in bytes"""

    @property
    def memory_delta_mb(self) -> float:
        """Memory delta in MB"""

    def log_summary(self, logger, level=logging.INFO) -> None:
        """Log task execution summary"""
```

## Context Data Sharing

WorkerContext.data persists across tasks within the same worker. TaskContext.data is scoped to a single task.

```python
def init_db(ctx: WorkerContext):
    """Store connection in Worker context."""
    db = Database.connect()
    ctx.data['db'] = db

def my_task(ctx: TaskContext, user_id: int):
    """Access Worker-level data from task."""
    db = ctx.worker_ctx.data['db']  # Get connection
    user = db.query(User).get(user_id)
    ctx.data['processed'] = True    # Task-level data
    return user
```

## Dynamic Hook Registration

```python
from rhosocial.activerecord.worker import WorkerEvent

pool = WorkerPool(n_workers=4)

# Dynamic registration
name = pool.register_hook(WorkerEvent.TASK_END, log_task, "task_logger")

# Unregister hook
pool.unregister_hook(WorkerEvent.TASK_END, name)
```
