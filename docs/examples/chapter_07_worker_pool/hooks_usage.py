# docs/examples/worker_pool/hooks_usage.py
"""
WorkerPool lifecycle hooks examples.

This module demonstrates:
- Worker-level hooks (WORKER_START, WORKER_STOP)
- Task-level hooks (TASK_START, TASK_END)
- Context data sharing between hooks and tasks
- Hook with additional arguments (tuple format)
"""

import os
import tempfile
import logging
from typing import Optional

from rhosocial.activerecord.worker import (
    WorkerPool,
    WorkerContext,
    TaskContext,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use tempfile for cross-platform marker files
TEMP_DIR = tempfile.gettempdir()


# ============= Simple hooks =============

def worker_init(ctx: WorkerContext):
    """Initialize resources when Worker starts."""
    marker_file = os.path.join(TEMP_DIR, f"worker_{ctx.worker_id}_init.txt")
    with open(marker_file, 'w') as f:
        f.write(f"Worker {ctx.worker_id} (pid={ctx.pid}) initialized")
    print(f"[Worker-{ctx.worker_id}] Initialized (pid={ctx.pid})")


def worker_cleanup(ctx: WorkerContext):
    """Cleanup resources when Worker stops."""
    print(f"[Worker-{ctx.worker_id}] Stopped after processing {ctx.task_count} tasks")
    # Cleanup marker file
    marker_file = os.path.join(TEMP_DIR, f"worker_{ctx.worker_id}_init.txt")
    if os.path.exists(marker_file):
        os.remove(marker_file)


def task_start(ctx: TaskContext):
    """Hook called before each task."""
    print(f"[Task-{ctx.task_id[:8]}] Starting: {ctx.fn_name}")


def task_end(ctx: TaskContext):
    """Hook called after each task completes."""
    status = "SUCCESS" if ctx.success else "FAILED"
    print(f"[Task-{ctx.task_id[:8]}] {status}: duration={ctx.duration:.3f}s")


# ============= Context data sharing hooks =============

def init_shared_data(ctx: WorkerContext):
    """Store shared data in Worker context."""
    ctx.data['counter'] = 0
    ctx.data['db_connection'] = "simulated_connection"  # In real use, this would be a real DB connection
    print(f"[Worker-{ctx.worker_id}] Shared data initialized")


def task_with_shared_data(ctx: TaskContext, value: int) -> dict:
    """Task that uses Worker-level shared data."""
    # Access and modify Worker-level data
    counter = ctx.worker_ctx.data.get('counter', 0)
    ctx.worker_ctx.data['counter'] = counter + 1

    # Store task-level data
    ctx.data['processed_value'] = value * 2

    return {
        'value': value,
        'doubled': value * 2,
        'worker_counter': ctx.worker_ctx.data['counter'],
    }


# ============= Hooks with arguments (tuple format) =============

def init_with_config(ctx: WorkerContext, db_name: str, pool_size: int):
    """Hook that accepts additional arguments."""
    print(f"[Worker-{ctx.worker_id}] Configured with db={db_name}, pool_size={pool_size}")
    ctx.data['db_name'] = db_name
    ctx.data['pool_size'] = pool_size


def task_with_config(ctx: TaskContext, value: int) -> dict:
    """Task that uses configuration from Worker context."""
    return {
        'value': value,
        'db_name': ctx.worker_ctx.data.get('db_name'),
        'pool_size': ctx.worker_ctx.data.get('pool_size'),
    }


# ============= Logging hook with log_summary =============

def log_task_summary(ctx: TaskContext):
    """Hook that logs detailed task summary using built-in method."""
    # Use the built-in log_summary method for consistent formatting
    ctx.log_summary(logger, level=logging.INFO)


# ============= Example tasks =============

def simple_task(ctx: TaskContext, n: int) -> int:
    """Simple task function."""
    return n * 2


def main():
    """Run hook examples."""
    print("=== WorkerPool Hooks Examples ===\n")

    # Example 1: Basic lifecycle hooks
    print("1. Basic lifecycle hooks:")
    with WorkerPool(
        n_workers=2,
        on_worker_start=worker_init,
        on_worker_stop=worker_cleanup,
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(5)]
        results = [f.result(timeout=10) for f in futures]
        print(f"   Results: {results}")

    # Example 2: Task-level hooks
    print("\n2. Task-level hooks:")
    with WorkerPool(
        n_workers=2,
        on_task_start=task_start,
        on_task_end=task_end,
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(3)]
        results = [f.result(timeout=10) for f in futures]

    # Example 3: Context data sharing
    print("\n3. Context data sharing:")
    with WorkerPool(
        n_workers=2,
        on_worker_start=init_shared_data,
    ) as pool:
        futures = [pool.submit(task_with_shared_data, i) for i in range(5)]
        results = [f.result(timeout=10) for f in futures]
        for r in results:
            print(f"   {r}")

    # Example 4: Hook with arguments (tuple format)
    print("\n4. Hook with arguments:")
    with WorkerPool(
        n_workers=2,
        on_worker_start=(init_with_config, "mydb", 10),  # tuple format: (callable, arg1, arg2)
    ) as pool:
        futures = [pool.submit(task_with_config, i) for i in range(3)]
        results = [f.result(timeout=10) for f in futures]
        for r in results:
            print(f"   {r}")

    # Example 5: Using log_summary for monitoring
    print("\n5. Task logging with log_summary:")
    with WorkerPool(
        n_workers=2,
        on_task_end=log_task_summary,
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(3)]
        results = [f.result(timeout=10) for f in futures]

    print("\n=== All hook examples completed ===")


if __name__ == '__main__':
    main()
