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

User responsibilities:
- Write Task functions (must be module-level functions, pickle-able)
- Plan which ORM models are needed
- Configure backend connections
- Handle CRUD operations and transactions

Usage Example:
    from rhosocial.activerecord.worker import WorkerPool, WorkerContext

    # Define task (user manages connections)
    def my_task(user_id: int) -> dict:
        from myapp.models import User
        from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
        from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

        # Configure connection inside Worker
        config = SQLiteConnectionConfig(database="app.db")
        User.configure(config, SQLiteBackend)

        # Execute business logic
        user = User.find_one(user_id)
        result = {"id": user.id, "name": user.name}

        # Cleanup
        User.backend().disconnect()
        return result

    # Use WorkerPool with lifecycle hooks
    def init_db(ctx: WorkerContext):
        # Initialize database connection for each Worker
        from myapp.db import Database
        Database.connect()

    def cleanup_db(ctx: WorkerContext):
        # Cleanup database connection for each Worker
        from myapp.db import Database
        Database.disconnect()

    if __name__ == '__main__':
        with WorkerPool(
            n_workers=4,
            on_worker_start=init_db,
            on_worker_stop=cleanup_db,
        ) as pool:
            futures = [pool.submit(my_task, i) for i in range(10)]
            for f in futures:
                try:
                    print(f.result(timeout=10))
                except Exception as e:
                    print(f"Error: {e}")
                    print(f.traceback)
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
