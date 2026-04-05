# docs/examples/worker_pool/async_mode.py
"""
Async mode examples for WorkerPool.

This module demonstrates:
- Async hooks and tasks
- Single event loop per Worker lifetime
- Context data sharing in async mode
- Warning about sync tasks in async mode
"""

import asyncio
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


# ============= Async hooks =============

async def async_worker_init(ctx: WorkerContext):
    """Async hook for Worker initialization."""
    print(f"[Async Worker-{ctx.worker_id}] Initializing...")

    # Simulate async resource initialization
    await asyncio.sleep(0.01)

    # Store async resources in context
    ctx.data['async_resource'] = f"async_conn_{ctx.worker_id}"
    print(f"[Async Worker-{ctx.worker_id}] Initialized with {ctx.data['async_resource']}")


async def async_worker_cleanup(ctx: WorkerContext):
    """Async hook for Worker cleanup."""
    print(f"[Async Worker-{ctx.worker_id}] Cleaning up...")

    # Simulate async resource cleanup
    await asyncio.sleep(0.01)

    resource = ctx.data.get('async_resource')
    if resource:
        print(f"[Async Worker-{ctx.worker_id}] Released {resource}")


async def async_task_start(ctx: TaskContext):
    """Async hook before task execution."""
    await asyncio.sleep(0.001)  # Simulate async setup
    print(f"[Async Task-{ctx.task_id[:8]}] Starting: {ctx.fn_name}")


async def async_task_end(ctx: TaskContext):
    """Async hook after task execution."""
    await asyncio.sleep(0.001)  # Simulate async cleanup
    status = "SUCCESS" if ctx.success else "FAILED"
    print(f"[Async Task-{ctx.task_id[:8]}] {status}: {ctx.duration:.3f}s")


# ============= Async tasks =============

async def async_query_task(ctx: TaskContext, query_id: int) -> dict:
    """Async task using Worker-level async resource."""
    # Access Worker-level async resource
    resource = ctx.worker_ctx.data['async_resource']

    # Simulate async database query
    await asyncio.sleep(0.01)

    return {
        'query_id': query_id,
        'resource': resource,
        'worker_id': ctx.worker_ctx.worker_id,
    }


async def async_computation_task(ctx: TaskContext, value: int) -> dict:
    """Async task with computation."""
    # Simulate async computation
    await asyncio.sleep(0.02)

    result = value * 2

    # Store in task context
    ctx.data['computed'] = result

    return {
        'input': value,
        'output': result,
    }


# ============= Sync task in async mode (WARNING) =============

def sync_task_in_async_mode(ctx: TaskContext, value: int) -> int:
    """
    Synchronous task in async mode.

    WARNING: This will BLOCK the event loop!
    Use async tasks when all hooks are async.
    """
    import time
    time.sleep(0.01)  # This blocks the entire event loop!
    return value * 2


def main():
    """Run async mode examples."""
    print("=== Async Mode Examples ===\n")

    # Example 1: Basic async mode
    print("1. Basic async mode (all hooks are async):")
    with WorkerPool(
        n_workers=2,
        on_worker_start=async_worker_init,
        on_worker_stop=async_worker_cleanup,
    ) as pool:
        futures = [pool.submit(async_query_task, i) for i in range(4)]
        results = [f.result(timeout=10) for f in futures]
        for r in results:
            print(f"   Query {r['query_id']}: worker={r['worker_id']}, resource={r['resource']}")

    # Example 2: Async task-level hooks
    print("\n2. Async task-level hooks:")
    with WorkerPool(
        n_workers=2,
        on_task_start=async_task_start,
        on_task_end=async_task_end,
    ) as pool:
        futures = [pool.submit(async_computation_task, i) for i in range(3)]
        results = [f.result(timeout=10) for f in futures]
        for r in results:
            print(f"   Input={r['input']}, Output={r['output']}")

    # Example 3: Full async setup
    print("\n3. Full async setup (worker + task hooks):")
    with WorkerPool(
        n_workers=2,
        on_worker_start=async_worker_init,
        on_worker_stop=async_worker_cleanup,
        on_task_start=async_task_start,
        on_task_end=async_task_end,
    ) as pool:
        futures = [pool.submit(async_query_task, i) for i in range(3)]
        results = [f.result(timeout=10) for f in futures]

    # Example 4: Warning about sync tasks in async mode
    print("\n4. WARNING: Sync task in async mode blocks event loop!")
    print("   When all hooks are async, the Worker runs a single event loop.")
    print("   A synchronous task will BLOCK this event loop.")
    print("   Recommendation: Use async tasks when all hooks are async.")

    print("\n5. Mode selection rules:")
    print("   - Sync mode: All hooks are sync, no event loop created")
    print("   - Async mode: At least one hook is async, single event loop for Worker lifetime")
    print("   - Mixing sync/async hooks raises TypeError")

    print("\n=== All async mode examples completed ===")


if __name__ == '__main__':
    main()
