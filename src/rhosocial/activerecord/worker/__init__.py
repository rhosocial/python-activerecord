# src/rhosocial/activerecord/worker/__init__.py
"""
Multiprocessing Worker Pool Module.

Resident Worker Pool based on spawn mode:
- Worker processes start once and stay resident (no repeated spawn/release overhead)
- Tasks are dispatched via Queue, results captured via Future
- Worker crash triggers automatic restart, crashed task is marked as error
- Three-phase graceful shutdown: DRAINING → STOPPING → KILLING → STOPPED
- Lifecycle hooks for Worker and Task events

Lifecycle Hooks:
- WORKER_START: Called when a Worker process starts (for resource initialization)
- WORKER_STOP: Called when a Worker process stops (for resource cleanup)
- TASK_START: Called before each task execution (for per-task setup)
- TASK_END: Called after each task execution (for per-task cleanup/monitoring)

Hook Format:
    Hooks can be specified in several formats:
    - Single callable: on_worker_start=my_hook
    - List of callables: on_worker_start=[hook1, hook2]
    - Tuple with args: on_worker_start=(my_hook, arg1, arg2)  # Called as my_hook(ctx, arg1, arg2)
    - String path: on_worker_start="mymodule.hooks.my_hook"
    - List with string paths: on_worker_start=["mymodule.hooks.hook1", hook2]

    Note: Local functions and lambdas cannot be pickled in spawn mode.
    Define hooks in a proper module for multiprocessing compatibility.

Mode Selection:
- Sync mode: All hooks are synchronous, no event loop created
- Async mode: At least one hook is async, single event loop for Worker lifetime
- Mixing sync and async hooks raises TypeError

Task Function Signature:
- Task functions must accept ctx: TaskContext as the first argument
- The framework injects ctx automatically before other arguments

Context Data Sharing:
- WorkerContext.data: Worker-level shared data (persisted across tasks)
- TaskContext.data: Task-level data (scoped to single task)
- TaskContext.worker_ctx: Access Worker context from task

Usage Example (Sync Mode):
    from rhosocial.activerecord.worker import WorkerPool, WorkerContext, TaskContext

    # Define task: first argument is always ctx
    def my_task(ctx: TaskContext, user_id: int) -> dict:
        from myapp.models import User
        # Access Worker-level data
        db = ctx.worker_ctx.data.get('db')
        user = db.query(User).filter(User.id == user_id).first()
        return {"id": user.id, "name": user.name}

    # Worker-level hooks
    def init_db(ctx: WorkerContext):
        from myapp.db import Database
        db = Database.connect()
        ctx.data['db'] = db  # Store for task access

    def cleanup_db(ctx: WorkerContext):
        db = ctx.data.get('db')
        if db:
            db.close()

    if __name__ == '__main__':
        with WorkerPool(
            n_workers=4,
            on_worker_start=init_db,
            on_worker_stop=cleanup_db,
        ) as pool:
            # Submit with task arguments (ctx injected automatically)
            futures = [pool.submit(my_task, user_id=i) for i in range(10)]
            for f in futures:
                try:
                    print(f.result(timeout=10))
                except Exception as e:
                    print(f"Error: {e}")
                    print(f.traceback)

Usage Example (Async Mode):
    from rhosocial.activerecord.worker import WorkerPool, WorkerContext, TaskContext

    async def init_db(ctx: WorkerContext):
        from myapp.db import AsyncDatabase
        db = await AsyncDatabase.connect()
        ctx.data['db'] = db

    async def cleanup_db(ctx: WorkerContext):
        db = ctx.data.get('db')
        if db:
            await db.close()

    async def my_task(ctx: TaskContext, user_id: int) -> dict:
        db = ctx.worker_ctx.data['db']
        user = await db.query_user(user_id)
        return {"id": user.id, "name": user.name}

    if __name__ == '__main__':
        with WorkerPool(
            n_workers=4,
            on_worker_start=init_db,
            on_worker_stop=cleanup_db,
        ) as pool:
            futures = [pool.submit(my_task, user_id=i) for i in range(10)]
            results = [f.result(timeout=10) for f in futures]

Usage Example (Hook with Arguments):
    # Hook that takes additional arguments
    def init_with_config(ctx: WorkerContext, db_name: str, pool_size: int):
        from myapp.db import Database
        db = Database.connect(db_name, pool_size=pool_size)
        ctx.data['db'] = db

    # Pass arguments via tuple format
    with WorkerPool(
        n_workers=4,
        on_worker_start=(init_with_config, "mydb", 10),
    ) as pool:
        # ... tasks ...
"""

from .pool import (
    # Core classes
    WorkerPool,
    Future,
    PoolState,
    PoolStats,
    ShutdownReport,
    # Exceptions
    PoolDrainingError,
    TaskTimeoutError,
    WorkerCrashedError,
    # Lifecycle hooks
    WorkerEvent,
    WorkerContext,
    TaskContext,
)

__all__ = [
    # Core classes
    "WorkerPool",
    "Future",
    "PoolState",
    "PoolStats",
    "ShutdownReport",
    # Exceptions
    "PoolDrainingError",
    "TaskTimeoutError",
    "WorkerCrashedError",
    # Lifecycle hooks
    "WorkerEvent",
    "WorkerContext",
    "TaskContext",
]
