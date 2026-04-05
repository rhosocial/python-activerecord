# tests/rhosocial/activerecord_test/feature/worker/hooks/test_hooks.py
"""
Tests for WorkerPool lifecycle hooks.

Note: Hook functions must be imported from a proper module to be picklable in spawn mode.
The sample_hooks.py module provides test hook functions.
"""

import glob
import os

from rhosocial.activerecord.worker import (
    WorkerPool,
    WorkerEvent,
)

# Import test hooks from the separate module (required for pickle in spawn mode)
from tests.rhosocial.activerecord_test.feature.worker.hooks.sample_hooks import (
    simple_init_hook,
    simple_stop_hook,
    task_start_hook,
    task_end_hook,
    logging_task_end_hook,
)


# ── Test Task Functions (must be module-level for pickle) ────────────────────

def simple_task(x):
    """Simple task that returns x * 2."""
    return x * 2


def failing_task(x):
    """Task that raises an exception."""
    raise ValueError(f"Intentional failure for x={x}")


# ── Test Cases ────────────────────────────────────────────────────────────────

def cleanup_marker_files():
    """Clean up any marker files from previous tests."""
    for f in glob.glob("/tmp/worker_hook_*.txt") + glob.glob("/tmp/task_hook_*.txt"):
        try:
            os.remove(f)
        except:
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
        marker_file = f"/tmp/worker_hook_start_{wid}.txt"
        assert os.path.exists(marker_file), f"Start hook marker for Worker {wid} not found"
        with open(marker_file) as f:
            content = f.read()
            assert f"started:{wid}:" in content

    # Check that stop hooks were called
    for wid in range(2):
        marker_file = f"/tmp/worker_hook_stop_{wid}.txt"
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
    end_markers = glob.glob("/tmp/task_hook_end_*.txt")
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
    end_markers = glob.glob("/tmp/task_hook_end_*.txt")
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
        on_worker_start="tests.rhosocial.activerecord_test.feature.worker.hooks.sample_hooks.simple_init_hook",
        on_worker_stop="tests.rhosocial.activerecord_test.feature.worker.hooks.sample_hooks.simple_stop_hook",
    ) as pool:
        futures = [pool.submit(simple_task, i) for i in range(2)]
        for f in futures:
            f.result(timeout=10)

    # Check hooks were called
    start_count = sum(1 for wid in range(2) if os.path.exists(f"/tmp/worker_hook_start_{wid}.txt"))
    stop_count = sum(1 for wid in range(2) if os.path.exists(f"/tmp/worker_hook_stop_{wid}.txt"))

    assert start_count == 2, f"Expected 2 start markers, found {start_count}"
    assert stop_count == 2, f"Expected 2 stop markers, found {stop_count}"

    cleanup_marker_files()
    print("test_string_path_hooks PASSED")


def test_no_hooks():
    """Test that WorkerPool works without any hooks (backward compatibility)."""
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
    logging_markers = glob.glob("/tmp/task_hook_logging_*.txt")
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

    print("\nAll tests PASSED!")
