# tests/rhosocial/activerecord_test/feature/worker/hooks/sample_hooks.py
"""
Sample hook functions for testing WorkerPool lifecycle hooks.

These functions must be in a proper Python module to be picklable in spawn mode.
"""

import logging
import tempfile
import os

# Set up a simple logger for testing
logger = logging.getLogger(__name__)

# Use tempfile for cross-platform temporary directory
TEMP_DIR = tempfile.gettempdir()


def simple_init_hook(ctx):
    """Simple hook that records Worker startup."""
    marker_file = os.path.join(TEMP_DIR, f"worker_hook_start_{ctx.worker_id}.txt")
    with open(marker_file, 'w') as f:
        f.write(f"started:{ctx.worker_id}:{ctx.pid}")


def simple_stop_hook(ctx):
    """Simple hook that records Worker shutdown."""
    marker_file = os.path.join(TEMP_DIR, f"worker_hook_stop_{ctx.worker_id}.txt")
    with open(marker_file, 'w') as f:
        f.write(f"stopped:{ctx.worker_id}:{ctx.task_count}")


def failing_init_hook(ctx):
    """Hook that raises an exception to test failure handling."""
    raise RuntimeError("Intentional init failure for testing")


def task_start_hook(ctx):
    """Hook that records task start."""
    marker_file = os.path.join(TEMP_DIR, f"task_hook_start_{ctx.task_id[:8]}.txt")
    with open(marker_file, 'w') as f:
        f.write(f"task_start:{ctx.task_id}:{ctx.fn_name}:{ctx.worker_ctx.worker_id}")


def task_end_hook(ctx):
    """Hook that records task end with result."""
    marker_file = os.path.join(TEMP_DIR, f"task_hook_end_{ctx.task_id[:8]}.txt")
    with open(marker_file, 'w') as f:
        f.write(f"task_end:{ctx.task_id}:{ctx.success}:{ctx.worker_ctx.task_count}")


def logging_task_end_hook(ctx):
    """
    Hook that logs task execution summary with resource usage.

    This hook demonstrates the recommended pattern for production use:
    - Logs duration, memory delta, and success/failure status
    - Uses the built-in log_summary() method for consistent formatting
    """
    # Use the built-in summary method
    ctx.log_summary(logger, level=logging.INFO)

    # Also write to marker file for testing
    marker_file = os.path.join(TEMP_DIR, f"task_hook_logging_{ctx.task_id[:8]}.txt")
    with open(marker_file, 'w') as f:
        f.write(
            f"task_id={ctx.task_id}:"
            f"fn={ctx.fn_name}:"
            f"duration={ctx.duration:.3f}:"
            f"memory_delta_mb={ctx.memory_delta_mb:.3f}:"
            f"success={ctx.success}"
        )


# ── Async hooks for testing async mode ────────────────────────────────────────

async def async_init_hook(ctx):
    """Async hook that records Worker startup."""
    marker_file = os.path.join(TEMP_DIR, f"worker_hook_async_start_{ctx.worker_id}.txt")
    with open(marker_file, 'w') as f:
        f.write(f"async_started:{ctx.worker_id}:{ctx.pid}")
    # Store data in Worker context for task access
    ctx.data['async_init_called'] = True


async def async_stop_hook(ctx):
    """Async hook that records Worker shutdown."""
    marker_file = os.path.join(TEMP_DIR, f"worker_hook_async_stop_{ctx.worker_id}.txt")
    with open(marker_file, 'w') as f:
        f.write(f"async_stopped:{ctx.worker_id}:{ctx.task_count}")


async def async_task_start_hook(ctx):
    """Async hook that records task start."""
    marker_file = os.path.join(TEMP_DIR, f"task_hook_async_start_{ctx.task_id[:8]}.txt")
    with open(marker_file, 'w') as f:
        # Access Worker-level data
        async_init = ctx.worker_ctx.data.get('async_init_called', False)
        f.write(f"async_task_start:{ctx.task_id}:async_init={async_init}")


async def async_task_end_hook(ctx):
    """Async hook that records task end."""
    marker_file = os.path.join(TEMP_DIR, f"task_hook_async_end_{ctx.task_id[:8]}.txt")
    with open(marker_file, 'w') as f:
        f.write(f"async_task_end:{ctx.task_id}:success={ctx.success}")


# ── Context data sharing hooks ────────────────────────────────────────────────

def data_init_hook(ctx):
    """Hook that stores data in Worker context."""
    ctx.data['test_value'] = 'initialized'
    ctx.data['counter'] = 0
    marker_file = os.path.join(TEMP_DIR, f"worker_hook_data_init_{ctx.worker_id}.txt")
    with open(marker_file, 'w') as f:
        f.write(f"data_init:{ctx.worker_id}")


def data_task_start_hook(ctx):
    """Hook that increments counter in Worker context."""
    counter = ctx.worker_ctx.data.get('counter', 0)
    ctx.worker_ctx.data['counter'] = counter + 1
    ctx.data['task_counter'] = counter + 1  # Task-level data


# ── Failing hooks for error handling tests ─────────────────────────────────────

def failing_task_end_hook(ctx):
    """Hook that raises an exception to test error handling in hooks."""
    raise RuntimeError("Intentional task_end hook failure for testing")


async def async_failing_task_end_hook(ctx):
    """Async hook that raises an exception to test error handling."""
    raise RuntimeError("Intentional async task_end hook failure for testing")


# ── Hooks for log_summary testing ──────────────────────────────────────────────

def detailed_log_task_end_hook(ctx):
    """
    Hook that tests log_summary with different scenarios.
    Writes detailed info to marker file for testing.
    """
    import logging
    test_logger = logging.getLogger("test_worker_hooks")

    # Test log_summary with explicit logger
    ctx.log_summary(test_logger, level=logging.INFO)

    # Also test with None (uses default logger)
    ctx.log_summary(None, level=logging.INFO)

    # Write marker with all details
    marker_file = os.path.join(TEMP_DIR, f"task_hook_detailed_{ctx.task_id[:8]}.txt")
    with open(marker_file, 'w') as f:
        f.write(
            f"success={ctx.success}:"
            f"memory_start={ctx.memory_start}:"
            f"memory_end={ctx.memory_end}:"
            f"error={type(ctx.error).__name__ if ctx.error else 'None'}"
        )


# ── Hooks with arguments for tuple format testing ──────────────────────────────

def hook_with_arg(ctx, message):
    """Hook that takes an additional argument."""
    marker_file = os.path.join(TEMP_DIR, f"worker_hook_args_{ctx.worker_id}.txt")
    with open(marker_file, 'w') as f:
        f.write(f"{message}:{ctx.worker_id}")


def hook_with_args(ctx, prefix, suffix):
    """Hook that takes multiple additional arguments."""
    marker_file = os.path.join(TEMP_DIR, f"worker_hook_multiargs_{ctx.worker_id}.txt")
    with open(marker_file, 'w') as f:
        f.write(f"{prefix}:{ctx.worker_id}:{suffix}")
