# tests/rhosocial/activerecord_test/feature/worker/hooks/sample_hooks.py
"""
Sample hook functions for testing WorkerPool lifecycle hooks.

These functions must be in a proper Python module to be picklable in spawn mode.
"""

import os


def simple_init_hook(ctx):
    """Simple hook that records Worker startup."""
    marker_file = f"/tmp/worker_hook_start_{ctx.worker_id}.txt"
    with open(marker_file, 'w') as f:
        f.write(f"started:{ctx.worker_id}:{ctx.pid}")


def simple_stop_hook(ctx):
    """Simple hook that records Worker shutdown."""
    marker_file = f"/tmp/worker_hook_stop_{ctx.worker_id}.txt"
    with open(marker_file, 'w') as f:
        f.write(f"stopped:{ctx.worker_id}:{ctx.task_count}")


def failing_init_hook(ctx):
    """Hook that raises an exception to test failure handling."""
    raise RuntimeError("Intentional init failure for testing")


def task_start_hook(ctx):
    """Hook that records task start."""
    marker_file = f"/tmp/task_hook_start_{ctx.task_id[:8]}.txt"
    with open(marker_file, 'w') as f:
        f.write(f"task_start:{ctx.task_id}:{ctx.fn_name}:{ctx.worker_ctx.worker_id}")


def task_end_hook(ctx):
    """Hook that records task end with result."""
    marker_file = f"/tmp/task_hook_end_{ctx.task_id[:8]}.txt"
    with open(marker_file, 'w') as f:
        f.write(f"task_end:{ctx.task_id}:{ctx.success}:{ctx.worker_ctx.task_count}")


def async_init_hook(ctx):
    """Async hook for testing async hook support."""
    # This is a sync wrapper - actual async hooks would use async def
    marker_file = f"/tmp/worker_hook_async_{ctx.worker_id}.txt"
    with open(marker_file, 'w') as f:
        f.write(f"async_started:{ctx.worker_id}")
