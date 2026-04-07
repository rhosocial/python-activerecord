# docs/examples/worker_pool/connection_management.py
"""
Connection management strategies for WorkerPool.

This module demonstrates:
- Worker-level connection management (high-frequency, short operations)
- Task-level connection management (low-frequency, long operations)
- Why mixing levels is wrong
"""

from typing import Optional
from rhosocial.activerecord.worker import (
    WorkerPool,
    WorkerContext,
    TaskContext,
)


# ============= Simulated Database =============

class SimulatedDatabase:
    """Simulated database for demonstration purposes."""

    _connections = {}

    @classmethod
    def connect(cls, db_name: str = "default"):
        """Simulate database connection."""
        import threading
        thread_id = threading.get_ident()
        conn_id = f"{thread_id}-{db_name}"
        cls._connections[conn_id] = True
        print(f"   [DB] Connected: {conn_id}")
        return conn_id

    @classmethod
    def disconnect(cls, conn_id: Optional[str] = None):
        """Simulate database disconnection."""
        if conn_id and conn_id in cls._connections:
            del cls._connections[conn_id]
            print(f"   [DB] Disconnected: {conn_id}")

    @classmethod
    def query(cls, conn_id: str, sql: str):
        """Simulate query execution."""
        if conn_id not in cls._connections:
            raise RuntimeError(f"Not connected: {conn_id}")
        return f"Result of: {sql}"


# ============= Worker-level connection management =============
# Best for: High-frequency, short operations
# Connection is established once per Worker and reused across all tasks

def worker_connect(ctx: WorkerContext):
    """Connect when Worker starts."""
    conn_id = SimulatedDatabase.connect("worker_pool")
    ctx.data['conn_id'] = conn_id
    ctx.data['query_count'] = 0


def worker_disconnect(ctx: WorkerContext):
    """Disconnect when Worker stops."""
    conn_id = ctx.data.get('conn_id')
    if conn_id:
        SimulatedDatabase.disconnect(conn_id)
        print(f"   [Worker-{ctx.worker_id}] Total queries: {ctx.data.get('query_count', 0)}")


def worker_level_task(ctx: TaskContext, query_id: int) -> dict:
    """Task using Worker-level connection."""
    conn_id = ctx.worker_ctx.data['conn_id']

    # Execute query using existing connection
    result = SimulatedDatabase.query(conn_id, f"SELECT * FROM data WHERE id={query_id}")

    # Increment query counter
    ctx.worker_ctx.data['query_count'] = ctx.worker_ctx.data.get('query_count', 0) + 1

    return {
        'query_id': query_id,
        'result': result,
        'worker_id': ctx.worker_ctx.worker_id,
    }


# ============= Task-level connection management =============
# Best for: Low-frequency, long operations
# Connection is established per task and released immediately after

def task_connect(ctx: TaskContext):
    """Connect before each task."""
    conn_id = SimulatedDatabase.connect("task_level")
    ctx.data['conn_id'] = conn_id


def task_disconnect(ctx: TaskContext):
    """Disconnect after each task."""
    conn_id = ctx.data.get('conn_id')
    if conn_id:
        SimulatedDatabase.disconnect(conn_id)


def task_level_task(ctx: TaskContext, query_id: int) -> dict:
    """Task using Task-level connection."""
    conn_id = ctx.data['conn_id']

    # Execute query
    result = SimulatedDatabase.query(conn_id, f"SELECT * FROM data WHERE id={query_id}")

    return {
        'query_id': query_id,
        'result': result,
        'worker_id': ctx.worker_ctx.worker_id,
    }


# ============= WRONG: Mixed levels =============
# This will cause connection leaks or errors

# NEVER DO THIS:
# def worker_connect(ctx: WorkerContext):
#     ctx.data['conn_id'] = SimulatedDatabase.connect()
#
# def task_disconnect(ctx: TaskContext):
#     # WRONG! Disconnecting at task level when connected at worker level
#     conn_id = ctx.worker_ctx.data.get('conn_id')  # Accessing worker data
#     SimulatedDatabase.disconnect(conn_id)  # Will disconnect connection still needed by other tasks!


def main():
    """Run connection management examples."""
    print("=== Connection Management Strategies ===\n")

    # Example 1: Worker-level connection (recommended for high-frequency tasks)
    print("1. Worker-level connection (high-frequency, short operations):")
    print("   Connection established once per Worker, reused across tasks\n")
    with WorkerPool(
        n_workers=2,
        on_worker_start=worker_connect,
        on_worker_stop=worker_disconnect,
    ) as pool:
        futures = [pool.submit(worker_level_task, i) for i in range(6)]
        results = [f.result(timeout=10) for f in futures]
        for r in results:
            print(f"   Task {r['query_id']}: worker={r['worker_id']}")

    # Example 2: Task-level connection (recommended for low-frequency tasks)
    print("\n2. Task-level connection (low-frequency, long operations):")
    print("   Connection established per task, released immediately after\n")
    with WorkerPool(
        n_workers=2,
        on_task_start=task_connect,
        on_task_end=task_disconnect,
    ) as pool:
        futures = [pool.submit(task_level_task, i) for i in range(4)]
        results = [f.result(timeout=10) for f in futures]
        for r in results:
            print(f"   Task {r['query_id']}: worker={r['worker_id']}")

    # Example 3: Decision guide
    print("\n3. Decision guide:")
    print("   Tasks per minute per worker:")
    print("   ├── > 100 tasks/min  → Worker-level (connection overhead negligible)")
    print("   ├── 10-100 tasks/min → Either works (consider connection pool limits)")
    print("   └── < 10 tasks/min   → Task-level (avoid holding connections idle)")

    print("\n4. Important rules:")
    print("   ✅ CORRECT: Both hooks at same level (worker+worker or task+task)")
    print("   ❌ WRONG: Mixed levels (worker connect + task disconnect)")

    print("\n=== All connection management examples completed ===")


if __name__ == '__main__':
    main()
