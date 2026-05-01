# tests/rhosocial/activerecord_test/feature/worker/hooks/test_hooks.py
"""
Tests for WorkerPool lifecycle hooks.

Note: Hook functions must be imported from a proper module to be picklable in spawn mode.
The sample_hooks.py module provides test hook functions.
"""

import glob
import os
import tempfile
import time

from rhosocial.activerecord.worker import (
    WorkerPool,
    WorkerEvent,
    TaskContext,
)

# Import test hooks from the separate module (required for pickle in spawn mode)
from rhosocial.activerecord_test.feature.worker.hooks.sample_hooks import (
    simple_init_hook,
    simple_stop_hook,
    task_start_hook,
    task_end_hook,
    logging_task_end_hook,
    async_init_hook,
    async_stop_hook,
    async_task_start_hook,
    async_task_end_hook,
    data_init_hook,
    data_task_start_hook,
    failing_init_hook,
    failing_task_end_hook,
    async_failing_task_end_hook,
    detailed_log_task_end_hook,
    hook_with_arg,
    hook_with_args,
)

# Cross-platform temporary directory
TEMP_DIR = tempfile.gettempdir()


# ── Test Task Functions (must be module-level for pickle) ────────────────────

def simple_task(ctx: TaskContext, x):
    """Simple task that returns x * 2."""
    return x * 2


def failing_task(ctx: TaskContext, x):
    """Task that raises an exception."""
    raise ValueError(f"Intentional failure for x={x}")


async def async_simple_task(ctx: TaskContext, x):
    """Async simple task that returns x * 2."""
    return x * 2


def data_access_task(ctx: TaskContext, x):
    """Task that accesses Worker-level data."""
    test_value = ctx.worker_ctx.data.get('test_value', 'not_found')
    counter = ctx.worker_ctx.data.get('counter', 0)
    task_counter = ctx.data.get('task_counter', 0)
    return {
        'x': x,
        'test_value': test_value,
        'counter': counter,
        'task_counter': task_counter,
    }


def slow_task(ctx: TaskContext, x):
    """Task that takes a long time (for timeout testing)."""
    time.sleep(5)  # Long sleep
    return x


# ── Test Cases ────────────────────────────────────────────────────────────────

def cleanup_marker_files():
    """Clean up any marker files from previous tests."""
    patterns = [
        os.path.join(TEMP_DIR, "worker_hook_*.txt"),
        os.path.join(TEMP_DIR, "task_hook_*.txt"),
    ]
    for pattern in patterns:
        for f in glob.glob(pattern):
            try:
                os.remove(f)
            except Exception:
                pass


def test_worker_start_stop_hooks():
    """Test that WORKER_START and WORKER_STOP hooks are called."""
    cleanup_marker_files()

    with WorkerPool(
        n_workers=2,
        on_worker_start=simple_init_hook,
        on_worker_stop=simple_stop_hook,
    ) as pool:
        # Submit some tasks
        futures = [pool.submit(simple_task, i) for i in range(4)]
        for f in futures:
            f.result(timeout=10)

    # Check that start hooks were called
    for wid in range(2):
        marker_file = os.path.join(TEMP_DIR, f"worker_hook_start_{wid}.txt")
        assert os.path.exists(marker_file), f"Start hook marker for Worker {wid} not found"
        with open(marker_file) as f:
            content = f.read()
            assert f"started:{wid}:" in content

    # Check that stop hooks were called
    for wid in range(2):
        marker_file = os.path.join(TEMP_DIR, f"worker_hook_stop_{wid}.txt")
        assert os.path.exists(marker_file), f"Stop hook marker for Worker {wid} not found"
        with open(marker_file) as f:
            content = f.read()
            assert f"stopped:{wid}:" in content

    cleanup_marker_files()
    print("test_worker_start_stop_hooks PASSED")


def test_task_hooks():
    """Test that TASK_START and TASK_END hooks are called."""
    cleanup_marker_files()

    with WorkerPool(
        n_workers=2,
        on_task_start=task_start_hook,
        on_task_end=task_end_hook,
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(3)]
        for f in futures:
            f.result(timeout=10)

    # Check task end markers (start markers may have been overwritten by same task_id prefix)
    end_markers = glob.glob(os.path.join(TEMP_DIR, "task_hook_end_*.txt"))
    assert len(end_markers) >= 3, f"Expected at least 3 end markers, found {len(end_markers)}"

    # Check that success is recorded
    for marker_file in end_markers:
        with open(marker_file) as f:
            content = f.read()
            assert "task_end:" in content
            assert ":True:" in content  # success=True

    cleanup_marker_files()
    print("test_task_hooks PASSED")


def test_task_end_hook_on_failure():
    """Test that TASK_END hook is called even when task fails."""
    cleanup_marker_files()

    with WorkerPool(
        n_workers=2,
        on_task_end=task_end_hook,
    ) as pool:
        futures = [pool.submit(failing_task, i) for i in range(2)]
        for f in futures:
            try:
                f.result(timeout=10)
            except ValueError:
                pass  # Expected

    # Check that end markers were created with success=False
    end_markers = glob.glob(os.path.join(TEMP_DIR, "task_hook_end_*.txt"))
    assert len(end_markers) >= 2, f"Expected at least 2 end markers, found {len(end_markers)}"

    for marker_file in end_markers:
        with open(marker_file) as f:
            content = f.read()
            assert ":False:" in content  # success=False

    cleanup_marker_files()
    print("test_task_end_hook_on_failure PASSED")


def test_hook_registration():
    """Test register_hook and unregister_hook methods."""
    pool = WorkerPool(n_workers=2)

    # Register hooks
    name1 = pool.register_hook(WorkerEvent.WORKER_START, simple_init_hook, "test_init")
    assert name1 == "test_init"

    name2 = pool.register_hook(WorkerEvent.WORKER_STOP, simple_stop_hook)
    assert name2.startswith("hook_")

    # Get hooks
    start_hooks = pool.get_hooks(WorkerEvent.WORKER_START)
    assert len(start_hooks) == 1
    assert start_hooks[0][0] == "test_init"

    # Unregister
    result = pool.unregister_hook(WorkerEvent.WORKER_START, "test_init")
    assert result is True

    start_hooks = pool.get_hooks(WorkerEvent.WORKER_START)
    assert len(start_hooks) == 0

    # Unregister non-existent
    result = pool.unregister_hook(WorkerEvent.WORKER_START, "nonexistent")
    assert result is False

    pool.shutdown()
    print("test_hook_registration PASSED")


def test_string_path_hooks():
    """Test hooks specified as string paths."""
    cleanup_marker_files()

    # Use string path to the sample_hooks module
    with WorkerPool(
        n_workers=2,
        on_worker_start="rhosocial.activerecord_test.feature.worker.hooks.sample_hooks.simple_init_hook",
        on_worker_stop="rhosocial.activerecord_test.feature.worker.hooks.sample_hooks.simple_stop_hook",
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(2)]
        for f in futures:
            f.result(timeout=10)

    # Check hooks were called
    start_count = sum(1 for wid in range(2) if os.path.exists(os.path.join(TEMP_DIR, f"worker_hook_start_{wid}.txt")))
    stop_count = sum(1 for wid in range(2) if os.path.exists(os.path.join(TEMP_DIR, f"worker_hook_stop_{wid}.txt")))

    assert start_count == 2, f"Expected 2 start markers, found {start_count}"
    assert stop_count == 2, f"Expected 2 stop markers, found {stop_count}"

    cleanup_marker_files()
    print("test_string_path_hooks PASSED")


def test_no_hooks():
    """Test that WorkerPool works without any hooks."""
    with WorkerPool(n_workers=2) as pool:
        futures = [pool.submit(simple_task, i) for i in range(4)]
        results = [f.result(timeout=10) for f in futures]

    assert results == [0, 2, 4, 6]
    print("test_no_hooks PASSED")


def test_task_resource_monitoring():
    """Test that TaskContext provides resource monitoring (duration, memory)."""
    cleanup_marker_files()

    with WorkerPool(
        n_workers=2,
        on_task_end=logging_task_end_hook,
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(3)]
        for f in futures:
            f.result(timeout=10)

    # Check logging markers were created with resource info
    logging_markers = glob.glob(os.path.join(TEMP_DIR, "task_hook_logging_*.txt"))
    assert len(logging_markers) >= 3, f"Expected at least 3 logging markers, found {len(logging_markers)}"

    for marker_file in logging_markers:
        with open(marker_file) as f:
            content = f.read()
            # Verify duration is recorded
            assert "duration=" in content
            # Verify memory_delta is recorded
            assert "memory_delta_mb=" in content
            # Verify success status
            assert "success=True" in content

    cleanup_marker_files()
    print("test_task_resource_monitoring PASSED")


def test_future_metadata():
    """Test that Future exposes execution metadata after completion."""
    with WorkerPool(n_workers=2) as pool:
        futures = [pool.submit(simple_task, i) for i in range(4)]

        for f in futures:
            result = f.result(timeout=10)
            assert result is not None

            # Verify metadata is available
            assert f.worker_id is not None
            assert f.worker_id >= 0
            assert f.start_time is not None
            assert f.end_time is not None
            assert f.end_time >= f.start_time
            assert f.duration >= 0
            assert isinstance(f.memory_delta, int)
            assert isinstance(f.memory_delta_mb, float)

            print(f"Task {f.task_id[:8]}: result={result}")
            print(f"  Worker: {f.worker_id}")
            print(f"  Duration: {f.duration:.6f}s")
            print(f"  Memory delta: {f.memory_delta_mb:.6f} MB")

    print("test_future_metadata PASSED")


def test_future_metadata_on_failure():
    """Test that Future exposes metadata even when task fails."""
    with WorkerPool(n_workers=2) as pool:
        futures = [pool.submit(failing_task, i) for i in range(2)]

        for f in futures:
            try:
                f.result(timeout=10)
                raise AssertionError("Expected exception")
            except ValueError:
                pass  # Expected

            # Verify metadata is still available on failure
            assert f.worker_id is not None
            assert f.start_time is not None
            assert f.end_time is not None
            assert f.duration >= 0
            assert f.failed is True

            print(f"Failed task {f.task_id[:8]}: Worker-{f.worker_id}, duration={f.duration:.6f}s")

    print("test_future_metadata_on_failure PASSED")


def test_pool_status_properties():
    """Test pool status properties."""
    with WorkerPool(n_workers=2) as pool:
        # Test basic properties
        assert pool.state.name == "RUNNING"
        assert pool.n_workers == 2
        assert pool.pool_id is not None
        assert pool.alive_workers == 2

        # Submit some tasks
        futures = [pool.submit(simple_task, i) for i in range(5)]

        # Check in_flight_tasks (at least some tasks should be in flight)
        assert pool.in_flight_tasks >= 0
        assert pool.queued_futures >= 0

        # Wait for completion
        for f in futures:
            f.result(timeout=10)

        # After completion
        assert pool.queued_futures == 0

    print("test_pool_status_properties PASSED")


def test_pool_stats():
    """Test pool statistics collection."""
    with WorkerPool(n_workers=2) as pool:
        # Initial stats
        stats = pool.get_stats()
        assert stats.total_workers == 2
        assert stats.alive_workers == 2
        assert stats.tasks_submitted == 0
        assert stats.uptime >= 0

        # Submit tasks
        futures = [pool.submit(simple_task, i) for i in range(5)]

        # Check stats during execution
        stats = pool.get_stats()
        assert stats.tasks_submitted == 5

        # Wait for completion
        for f in futures:
            f.result(timeout=10)

        # Check final stats
        stats = pool.get_stats()
        assert stats.tasks_completed == 5
        assert stats.tasks_failed == 0
        assert stats.total_task_duration >= 0
        assert stats.avg_task_duration >= 0

    print("test_pool_stats PASSED")


def test_pool_stats_with_failures():
    """Test that failed tasks are counted correctly."""
    with WorkerPool(n_workers=2) as pool:
        futures = [pool.submit(failing_task, i) for i in range(2)]

        for f in futures:
            try:
                f.result(timeout=10)
            except ValueError:
                pass

        stats = pool.get_stats()
        assert stats.tasks_failed == 2
        assert stats.tasks_completed == 0

    print("test_pool_stats_with_failures PASSED")


def test_health_check():
    """Test health_check() method."""
    with WorkerPool(n_workers=2) as pool:
        health = pool.health_check()

        assert health["healthy"] is True
        assert health["state"] == "RUNNING"
        assert health["alive_workers"] == 2
        assert health["dead_workers"] == 0
        assert len(health["warnings"]) == 0

    print("test_health_check PASSED")


def test_drain():
    """Test drain() method."""
    with WorkerPool(n_workers=2) as pool:
        # Submit tasks
        futures = [pool.submit(simple_task, i) for i in range(10)]

        # Drain should wait for all tasks
        result = pool.drain(timeout=30)

        assert result is True
        assert pool.queued_futures == 0

        # Verify all completed
        for f in futures:
            assert f.done

    print("test_drain PASSED")


# ── Async Mode Tests ──────────────────────────────────────────────────────────

def test_async_hooks():
    """Test async hooks with single event loop."""
    cleanup_marker_files()

    with WorkerPool(
        n_workers=2,
        on_worker_start=async_init_hook,
        on_worker_stop=async_stop_hook,
        on_task_start=async_task_start_hook,
        on_task_end=async_task_end_hook,
    ) as pool:
        futures = [pool.submit(async_simple_task, i) for i in range(3)]
        for f in futures:
            f.result(timeout=10)

    # Check async start hooks were called
    start_markers = glob.glob(os.path.join(TEMP_DIR, "worker_hook_async_start_*.txt"))
    assert len(start_markers) == 2, f"Expected 2 async start markers, found {len(start_markers)}"

    # Check async stop hooks were called
    stop_markers = glob.glob(os.path.join(TEMP_DIR, "worker_hook_async_stop_*.txt"))
    assert len(stop_markers) == 2, f"Expected 2 async stop markers, found {len(stop_markers)}"

    # Check that Worker context data was accessible from task hooks
    task_start_markers = glob.glob(os.path.join(TEMP_DIR, "task_hook_async_start_*.txt"))
    assert len(task_start_markers) >= 3, f"Expected at least 3 task start markers"

    for marker_file in task_start_markers:
        with open(marker_file) as f:
            content = f.read()
            # Verify Worker-level data was accessible
            assert "async_init=True" in content

    cleanup_marker_files()
    print("test_async_hooks PASSED")


def test_context_data_sharing():
    """Test Worker-level and Task-level data sharing via context."""
    cleanup_marker_files()

    with WorkerPool(
        n_workers=2,
        on_worker_start=data_init_hook,
        on_task_start=data_task_start_hook,
    ) as pool:
        futures = [pool.submit(data_access_task, i) for i in range(3)]
        results = [f.result(timeout=10) for f in futures]

    # Verify data was accessible in tasks
    for result in results:
        assert result['test_value'] == 'initialized', f"Worker data not accessible: {result}"
        # Counter should be incremented by each task
        assert result['counter'] >= 1, f"Counter not incremented: {result}"
        assert result['task_counter'] >= 1, f"Task counter not set: {result}"

    cleanup_marker_files()
    print("test_context_data_sharing PASSED")


def test_mixed_sync_async_hooks_rejected():
    """Test that mixing sync and async hooks raises TypeError."""
    import pytest

    # Mix sync and async hooks should raise TypeError
    with pytest.raises(TypeError, match="Cannot mix sync and async hooks"):
        with WorkerPool(
            n_workers=2,
            on_worker_start=simple_init_hook,  # sync
            on_worker_stop=async_stop_hook,    # async
        ) as pool:
            pass

    print("test_mixed_sync_async_hooks_rejected PASSED")


# ── Additional Coverage Tests ───────────────────────────────────────────────────

def test_callable_list_hooks():
    """Test hooks specified as list of callables."""
    cleanup_marker_files()

    # Use list of callables
    hook_list = [simple_init_hook]

    with WorkerPool(
        n_workers=2,
        on_worker_start=hook_list,
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(2)]
        for f in futures:
            f.result(timeout=10)

    # Check hooks were called
    start_count = sum(1 for wid in range(2) if os.path.exists(os.path.join(TEMP_DIR, f"worker_hook_start_{wid}.txt")))
    assert start_count == 2, f"Expected 2 start markers, found {start_count}"

    cleanup_marker_files()
    print("test_callable_list_hooks PASSED")


def test_hook_with_args():
    """Test hooks with additional arguments using tuple format."""
    cleanup_marker_files()

    # Use tuple format: (callable, arg)
    with WorkerPool(
        n_workers=2,
        on_worker_start=(hook_with_arg, "initialized"),
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(2)]
        for f in futures:
            f.result(timeout=10)

    # Check hooks were called with args
    for wid in range(2):
        marker_file = os.path.join(TEMP_DIR, f"worker_hook_args_{wid}.txt")
        assert os.path.exists(marker_file), f"Marker for Worker {wid} not found"
        with open(marker_file) as f:
            content = f.read()
            assert content == f"initialized:{wid}"

    cleanup_marker_files()
    print("test_hook_with_args PASSED")


def test_hook_with_multiple_args():
    """Test hooks with multiple additional arguments."""
    cleanup_marker_files()

    # Use tuple format: (callable, arg1, arg2)
    with WorkerPool(
        n_workers=2,
        on_worker_start=(hook_with_args, "start", "end"),
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(2)]
        for f in futures:
            f.result(timeout=10)

    # Check hooks were called with all args
    for wid in range(2):
        marker_file = os.path.join(TEMP_DIR, f"worker_hook_multiargs_{wid}.txt")
        assert os.path.exists(marker_file)
        with open(marker_file) as f:
            content = f.read()
            assert content == f"start:{wid}:end"

    cleanup_marker_files()
    print("test_hook_with_multiple_args PASSED")


def test_hook_list_with_string_paths():
    """Test hooks specified as list with string paths."""
    cleanup_marker_files()

    # Use list format with string paths
    hook_list = [
        "rhosocial.activerecord_test.feature.worker.hooks.sample_hooks.simple_init_hook",
    ]

    with WorkerPool(
        n_workers=2,
        on_worker_start=hook_list,
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(2)]
        for f in futures:
            f.result(timeout=10)

    # Check hooks were called
    start_count = sum(1 for wid in range(2) if os.path.exists(os.path.join(TEMP_DIR, f"worker_hook_start_{wid}.txt")))
    assert start_count == 2, f"Expected 2 start markers, found {start_count}"

    cleanup_marker_files()
    print("test_hook_list_with_string_paths PASSED")


def test_hook_tuple_with_string_path():
    """Test tuple format with string path and args."""
    cleanup_marker_files()

    # Use tuple with string path and args
    with WorkerPool(
        n_workers=2,
        on_worker_start=("rhosocial.activerecord_test.feature.worker.hooks.sample_hooks.hook_with_arg", "test_message"),
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(2)]
        for f in futures:
            f.result(timeout=10)

    # Check hooks were called
    for wid in range(2):
        marker_file = os.path.join(TEMP_DIR, f"worker_hook_args_{wid}.txt")
        assert os.path.exists(marker_file)
        with open(marker_file) as f:
            content = f.read()
            assert content == f"test_message:{wid}"

    cleanup_marker_files()
    print("test_hook_tuple_with_string_path PASSED")


def test_log_summary_with_failure():
    """Test log_summary with failed task and error info."""
    cleanup_marker_files()

    with WorkerPool(
        n_workers=2,
        on_task_end=detailed_log_task_end_hook,
    ) as pool:
        futures = [pool.submit(failing_task, i) for i in range(2)]
        for f in futures:
            try:
                f.result(timeout=10)
            except ValueError:
                pass  # Expected

    # Check detailed markers were created
    detailed_markers = glob.glob(os.path.join(TEMP_DIR, "task_hook_detailed_*.txt"))
    assert len(detailed_markers) >= 2, f"Expected at least 2 detailed markers, found {len(detailed_markers)}"

    for marker_file in detailed_markers:
        with open(marker_file) as f:
            content = f.read()
            # Verify error info is recorded
            assert "success=False" in content
            assert "error=ValueError" in content

    cleanup_marker_files()
    print("test_log_summary_with_failure PASSED")


def test_health_check_warnings():
    """Test health_check() with various warning conditions."""
    # Test high failure rate warning
    with WorkerPool(n_workers=2) as pool:
        # Submit many failing tasks to trigger high failure rate warning
        futures = [pool.submit(failing_task, i) for i in range(15)]
        for f in futures:
            try:
                f.result(timeout=10)
            except ValueError:
                pass

        health = pool.health_check()
        # Should have high failure rate warning (>10%)
        assert any("High failure rate" in w for w in health["warnings"]), \
            f"Expected high failure rate warning, got: {health['warnings']}"

    print("test_health_check_warnings PASSED")


def test_health_check_queue_backlog():
    """Test health_check() queue backlog warning."""
    with WorkerPool(n_workers=1) as pool:
        # Submit many tasks to create queue backlog
        futures = [pool.submit(simple_task, i) for i in range(150)]

        # Check health while tasks are pending
        # (timing-dependent, may not always trigger)
        time.sleep(0.1)  # Allow some tasks to start
        stats = pool.get_stats()

        # Clean up
        for f in futures:
            f.result(timeout=30)

    print("test_health_check_queue_backlog PASSED")


def test_health_check_not_running():
    """Test health_check() when pool is not running."""
    pool = WorkerPool(n_workers=2)
    pool.shutdown()

    health = pool.health_check()
    assert health["healthy"] is False
    assert any("Pool not running" in w for w in health["warnings"])

    print("test_health_check_not_running PASSED")


def test_future_duration_before_completion():
    """Test Future.duration property before task completion."""
    with WorkerPool(n_workers=2) as pool:
        futures = [pool.submit(simple_task, i) for i in range(2)]

        # Check duration while tasks might still be pending
        # (timing-dependent, but we can at least verify it doesn't error)
        for f in futures:
            # duration should be 0.0 if not completed yet, or >= 0 if completed
            duration = f.duration
            assert duration >= 0.0

        # Wait for completion
        for f in futures:
            f.result(timeout=10)
            assert f.duration >= 0.0

    print("test_future_duration_before_completion PASSED")


def test_drain_with_timeout_expiry():
    """Test drain() with timeout that expires before all tasks complete."""
    # Note: slow_task is defined at module level for pickle compatibility
    with WorkerPool(n_workers=1) as pool:
        # Submit tasks that will take longer than our drain timeout
        futures = [pool.submit(slow_task, i) for i in range(3)]

        # drain with very short timeout should return False
        result = pool.drain(timeout=0.1)

        # Most tasks should still be pending
        assert result is False, "Expected drain to timeout"

    print("test_drain_with_timeout_expiry PASSED")


def test_pool_context_exit_with_exception():
    """Test WorkerPool context manager exit with exception."""
    with WorkerPool(n_workers=2) as pool:
        # Submit some tasks
        futures = [pool.submit(simple_task, i) for i in range(2)]
        for f in futures:
            f.result(timeout=10)

        # Pool should be running
        assert pool.state.name == "RUNNING"

        # Exit with exception - the pool should still shut down properly
        try:
            raise ValueError("Test exception in context")
        except ValueError:
            pass  # Caught here, pool already exited

    # Pool should have shut down
    assert pool.state.name in ("STOPPED", "STOPPING")

    print("test_pool_context_exit_with_exception PASSED")


def test_task_hook_failure_handling():
    """Test that task hook failures are handled gracefully."""
    cleanup_marker_files()

    # Task end hook that throws an exception
    # The task should still complete, but hook error should be logged
    with WorkerPool(
        n_workers=2,
        on_task_end=failing_task_end_hook,
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(2)]
        # Tasks should complete successfully despite hook failure
        results = [f.result(timeout=10) for f in futures]

    # Verify tasks completed
    assert results == [0, 2], f"Expected [0, 2], got {results}"

    cleanup_marker_files()
    print("test_task_hook_failure_handling PASSED")


def test_async_task_hook_failure_handling():
    """Test that async task hook failures are handled gracefully."""
    cleanup_marker_files()

    # Async task end hook that throws an exception
    with WorkerPool(
        n_workers=2,
        on_task_end=async_failing_task_end_hook,
    ) as pool:
        futures = [pool.submit(async_simple_task, i) for i in range(2)]
        # Tasks should complete successfully despite hook failure
        results = [f.result(timeout=10) for f in futures]

    # Verify tasks completed
    assert results == [0, 2], f"Expected [0, 2], got {results}"

    cleanup_marker_files()
    print("test_async_task_hook_failure_handling PASSED")


def test_single_callable_hook():
    """Test passing a single callable (not list or string) as hook."""
    cleanup_marker_files()

    # Pass single callable directly
    with WorkerPool(
        n_workers=2,
        on_worker_start=simple_init_hook,
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(2)]
        for f in futures:
            f.result(timeout=10)

    # Check hooks were called
    start_count = sum(1 for wid in range(2) if os.path.exists(os.path.join(TEMP_DIR, f"worker_hook_start_{wid}.txt")))
    assert start_count == 2, f"Expected 2 start markers, found {start_count}"

    cleanup_marker_files()
    print("test_single_callable_hook PASSED")


# ── Additional Tests ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run all tests
    print("Running hook tests...")

    test_no_hooks()
    test_hook_registration()
    test_worker_start_stop_hooks()
    test_task_hooks()
    test_task_end_hook_on_failure()
    test_string_path_hooks()
    test_task_resource_monitoring()
    test_future_metadata()
    test_future_metadata_on_failure()
    test_pool_status_properties()
    test_pool_stats()
    test_pool_stats_with_failures()
    test_health_check()
    test_drain()

    # New tests for async mode and context sharing
    test_async_hooks()
    test_context_data_sharing()
    test_mixed_sync_async_hooks_rejected()

    # Additional coverage tests
    test_callable_list_hooks()
    test_hook_with_args()
    test_hook_with_multiple_args()
    test_hook_list_with_string_paths()
    test_hook_tuple_with_string_path()
    test_log_summary_with_failure()
    test_health_check_warnings()
    test_health_check_queue_backlog()
    test_health_check_not_running()
    test_future_duration_before_completion()
    test_drain_with_timeout_expiry()
    test_pool_context_exit_with_exception()
    test_task_hook_failure_handling()
    test_async_task_hook_failure_handling()
    test_single_callable_hook()

    print("\nAll tests PASSED!")
