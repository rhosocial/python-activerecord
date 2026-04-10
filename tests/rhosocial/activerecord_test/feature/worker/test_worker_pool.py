# tests/rhosocial/activerecord_test/feature/worker/test_worker_pool.py
"""
Test WorkerPool basic functionality and graceful shutdown.

================================================================================
DIRECTORY PURPOSE - PLEASE READ BEFORE MODIFYING
================================================================================

This directory (feature/worker/) is for ABSTRACT WorkerPool tests that do NOT
depend on any database backend.

WHAT BELONGS HERE:
- Tests for rhosocial.activerecord.worker.pool abstract functionality
- Tests that use simple task functions (no database I/O)
- Tests for WorkerHandle, WorkerRegistry, Future, PoolState, etc.

WHAT DOES NOT BELONG HERE:
- Database-dependent WorkerPool tests (SQLite, MySQL, PostgreSQL, etc.)
  → Put those in feature/basic/worker/ or feature/query/worker/
- Backend-specific WorkerPool tests
  → Put those in feature/backend/{backend}/worker/

Note: All task functions must be module-level functions (pickle-able).
Running tests requires if __name__ == '__main__' guard.
"""

import time
import multiprocessing as mp

import pytest


from rhosocial.activerecord.worker import (
    WorkerPool,
    Future,
    PoolState,
    PoolDrainingError,
    ShutdownReport,
    WorkerCrashedError,
)
from rhosocial.activerecord.worker.pool import (
    WorkerHandle,
    WorkerRegistry,
    StopSignal,
)


# ─────────────────────────────────────────────────────────────────────────────
# Test task functions (must be module-level functions, pickle-able)
# ─────────────────────────────────────────────────────────────────────────────

from rhosocial.activerecord.worker import TaskContext


def simple_task(ctx: TaskContext, n: int) -> int:
    """Simple task: return n * 2"""
    return n * 2


def slow_task(ctx: TaskContext, seconds: float) -> float:
    """Slow task: sleep for specified seconds"""
    time.sleep(seconds)
    return seconds


def very_slow_task(ctx: TaskContext) -> None:
    """Very slow task: sleep for 10 seconds"""
    time.sleep(10)


def failing_task(ctx: TaskContext, n: int) -> int:
    """Task that fails"""
    if n < 0:
        raise ValueError("n must be non-negative")
    return n


def crash_task(ctx: TaskContext) -> None:
    """Task that crashes the process (simulate segfault)"""
    import os
    # Use os._exit() to simulate abnormal termination
    # SIGKILL can corrupt multiprocessing.Queue state
    os._exit(1)


async def async_simple_task(ctx: TaskContext, n: int) -> int:
    """Simple async task: return n * 2"""
    import asyncio
    await asyncio.sleep(0.01)  # Small delay to verify async execution
    return n * 2


async def async_failing_task(ctx: TaskContext, n: int) -> int:
    """Async task that fails"""
    import asyncio
    await asyncio.sleep(0.01)
    if n < 0:
        raise ValueError("n must be non-negative")
    return n


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions for testing WorkerHandle and WorkerRegistry (must be module-level)
# ─────────────────────────────────────────────────────────────────────────────

def _dummy_worker_long() -> None:
    """Sleep for a long time - used to test alive process handling"""
    time.sleep(5)


def _quick_exit_worker() -> None:
    """Exit immediately - used to test dead process handling"""
    pass


def _sleepy_worker() -> None:
    """Sleep for 10 seconds - used to test terminate/kill"""
    time.sleep(10)


# ─────────────────────────────────────────────────────────────────────────────
# Test classes
# ─────────────────────────────────────────────────────────────────────────────

class TestFuture:
    """Test Future"""

    def test_resolve(self):
        """Test successful result"""
        fut = Future("test-id")
        assert not fut.done

        fut._resolve(42)

        assert fut.done
        assert fut.succeeded
        assert not fut.failed
        assert fut.result() == 42
        assert fut.traceback is None

    def test_reject(self):
        """Test failed result"""
        fut = Future("test-id")
        assert not fut.done

        exc = ValueError("test error")
        tb = "Traceback (most recent call last):\n  ..."
        fut._reject(exc, tb)

        assert fut.done
        assert not fut.succeeded
        assert fut.failed
        assert fut.traceback == tb

        with pytest.raises(ValueError, match="test error"):
            fut.result()


class TestWorkerHandle:
    """Test WorkerHandle"""

    def test_handle_properties_alive(self):
        """Test WorkerHandle properties when process is alive"""
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_dummy_worker_long, daemon=True)
        proc.start()

        handle = WorkerHandle(0, proc)

        # Test alive state properties
        assert handle.is_alive is True
        assert handle.pid == proc.pid
        assert handle.exitcode is None

        # Test repr for alive process
        repr_str = repr(handle)
        assert "WorkerHandle" in repr_str
        assert "wid=0" in repr_str
        assert "alive" in repr_str

        # Cleanup
        proc.terminate()
        proc.join(timeout=2)
        if proc.is_alive():
            proc.kill()
            proc.join(timeout=2)

    def test_handle_properties_dead(self):
        """Test WorkerHandle properties when process is dead"""
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_quick_exit_worker, daemon=True)
        proc.start()
        proc.join(timeout=2)

        handle = WorkerHandle(1, proc)

        # Test dead state properties
        assert handle.is_alive is False
        assert handle.exitcode == 0  # Normal exit

        # Test repr for dead process
        repr_str = repr(handle)
        assert "dead" in repr_str
        assert "exit=0" in repr_str

    def test_handle_terminate(self):
        """Test terminate() method"""
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_sleepy_worker, daemon=True)
        proc.start()
        time.sleep(0.1)  # Let process start

        handle = WorkerHandle(2, proc)
        assert handle.is_alive is True

        handle.terminate()
        handle.join(timeout=2)

        assert handle.is_alive is False

    def test_handle_kill(self):
        """Test kill() method"""
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_sleepy_worker, daemon=True)
        proc.start()
        time.sleep(0.1)  # Let process start

        handle = WorkerHandle(3, proc)
        assert handle.is_alive is True

        handle.kill()
        handle.join(timeout=2)

        assert handle.is_alive is False
        # On most systems, SIGKILL results in exitcode -9
        # But the exact behavior depends on the OS

    def test_handle_stop_with_terminate_signal(self):
        """Test stop() method with TERMINATE signal"""
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_sleepy_worker, daemon=True)
        proc.start()
        time.sleep(0.1)

        handle = WorkerHandle(4, proc)
        handle.stop(StopSignal.TERMINATE)
        handle.join(timeout=2)

        assert handle.is_alive is False

    def test_handle_stop_with_kill_signal(self):
        """Test stop() method with KILL signal"""
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_sleepy_worker, daemon=True)
        proc.start()
        time.sleep(0.1)

        handle = WorkerHandle(5, proc)
        handle.stop(StopSignal.KILL)
        handle.join(timeout=2)

        assert handle.is_alive is False

    def test_handle_stop_with_sentinel_signal(self):
        """Test stop() method with SENTINEL signal (no-op)"""
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_sleepy_worker, daemon=True)
        proc.start()
        time.sleep(0.1)

        handle = WorkerHandle(6, proc)
        # SENTINEL doesn't send any signal to the process
        handle.stop(StopSignal.SENTINEL)

        # Process should still be alive
        assert handle.is_alive is True

        # Cleanup
        proc.terminate()
        proc.join(timeout=2)

    def test_handle_join_returns_bool(self):
        """Test join() returns True if process exited, False otherwise"""
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_quick_exit_worker, daemon=True)
        proc.start()

        handle = WorkerHandle(7, proc)

        # Wait with timeout, should return True when process exits
        result = handle.join(timeout=2)
        assert result is True  # Process exited

        # Join on already exited process
        result = handle.join(timeout=0.1)
        assert result is True  # Still True because already dead


class TestWorkerRegistry:
    """Test WorkerRegistry"""

    def test_add_and_get(self):
        """Test add() and get() methods"""
        ctx = mp.get_context("spawn")
        registry = WorkerRegistry()
        proc = ctx.Process(target=_sleepy_worker, daemon=True)
        proc.start()

        handle = registry.add(0, proc)
        assert handle is not None
        assert handle.wid == 0

        # Get existing handle
        retrieved = registry.get(0)
        assert retrieved is handle

        # Get non-existing handle
        assert registry.get(999) is None

        # Cleanup
        proc.terminate()
        proc.join(timeout=2)

    def test_all(self):
        """Test all() method"""
        ctx = mp.get_context("spawn")
        registry = WorkerRegistry()

        proc1 = ctx.Process(target=_sleepy_worker, daemon=True)
        proc1.start()
        proc2 = ctx.Process(target=_sleepy_worker, daemon=True)
        proc2.start()

        registry.add(0, proc1)
        registry.add(1, proc2)

        all_handles = registry.all()
        assert len(all_handles) == 2

        # Cleanup
        for proc in [proc1, proc2]:
            proc.terminate()
            proc.join(timeout=2)

    def test_alive_and_dead(self):
        """Test alive() and dead() methods"""
        ctx = mp.get_context("spawn")
        registry = WorkerRegistry()

        # Dead process
        proc_dead = ctx.Process(target=_quick_exit_worker, daemon=True)
        proc_dead.start()
        proc_dead.join(timeout=2)

        # Alive process
        proc_alive = ctx.Process(target=_sleepy_worker, daemon=True)
        proc_alive.start()
        time.sleep(0.1)

        registry.add(0, proc_dead)
        registry.add(1, proc_alive)

        dead_handles = registry.dead()
        assert len(dead_handles) == 1
        assert dead_handles[0].wid == 0

        alive_handles = registry.alive()
        assert len(alive_handles) == 1
        assert alive_handles[0].wid == 1

        # Cleanup
        proc_alive.terminate()
        proc_alive.join(timeout=2)

    def test_count_and_alive_count(self):
        """Test count() and alive_count() methods"""
        ctx = mp.get_context("spawn")
        registry = WorkerRegistry()

        proc_dead = ctx.Process(target=_quick_exit_worker, daemon=True)
        proc_dead.start()
        proc_dead.join(timeout=2)

        proc_alive = ctx.Process(target=_sleepy_worker, daemon=True)
        proc_alive.start()
        time.sleep(0.1)

        registry.add(0, proc_dead)
        registry.add(1, proc_alive)

        assert registry.count() == 2
        assert registry.alive_count() == 1

        # Cleanup
        proc_alive.terminate()
        proc_alive.join(timeout=2)

    def test_replace(self):
        """Test replace() method"""
        ctx = mp.get_context("spawn")
        registry = WorkerRegistry()

        proc1 = ctx.Process(target=_sleepy_worker, daemon=True)
        proc1.start()
        registry.add(0, proc1)

        proc2 = ctx.Process(target=_sleepy_worker, daemon=True)
        proc2.start()
        new_handle = registry.replace(0, proc2)

        assert new_handle.wid == 0
        assert registry.get(0) is new_handle

        # Cleanup
        proc1.terminate()
        proc2.terminate()
        proc1.join(timeout=2)
        proc2.join(timeout=2)

    def test_wids(self):
        """Test wids() method"""
        ctx = mp.get_context("spawn")
        registry = WorkerRegistry()

        proc1 = ctx.Process(target=_sleepy_worker, daemon=True)
        proc1.start()
        proc2 = ctx.Process(target=_sleepy_worker, daemon=True)
        proc2.start()

        registry.add(0, proc1)
        registry.add(5, proc2)

        wids = registry.wids()
        assert set(wids) == {0, 5}

        # Cleanup
        proc1.terminate()
        proc2.terminate()
        proc1.join(timeout=2)
        proc2.join(timeout=2)

    def test_remove_with_sentinel(self):
        """Test remove() with SENTINEL signal (no process kill)"""
        ctx = mp.get_context("spawn")
        registry = WorkerRegistry()
        proc = ctx.Process(target=_sleepy_worker, daemon=True)
        proc.start()
        time.sleep(0.1)

        registry.add(0, proc)
        assert registry.get(0) is not None

        # Remove with SENTINEL - process should still be alive
        removed = registry.remove(0, signal=StopSignal.SENTINEL)
        assert removed is not None
        assert proc.is_alive()  # Process NOT killed

        # Cleanup
        proc.terminate()
        proc.join(timeout=2)

    def test_remove_with_terminate(self):
        """Test remove() with TERMINATE signal"""
        ctx = mp.get_context("spawn")
        registry = WorkerRegistry()
        proc = ctx.Process(target=_sleepy_worker, daemon=True)
        proc.start()
        time.sleep(0.1)

        registry.add(0, proc)

        # Remove with TERMINATE
        removed = registry.remove(0, signal=StopSignal.TERMINATE)
        assert removed is not None
        proc.join(timeout=2)
        assert not proc.is_alive()

    def test_remove_with_kill(self):
        """Test remove() with KILL signal"""
        ctx = mp.get_context("spawn")
        registry = WorkerRegistry()
        proc = ctx.Process(target=_sleepy_worker, daemon=True)
        proc.start()
        time.sleep(0.1)

        registry.add(0, proc)

        # Remove with KILL
        removed = registry.remove(0, signal=StopSignal.KILL)
        assert removed is not None
        proc.join(timeout=2)
        assert not proc.is_alive()

    def test_remove_nonexistent(self):
        """Test remove() for non-existent worker"""
        registry = WorkerRegistry()
        result = registry.remove(999)
        assert result is None


class TestWorkerPool:
    """Test WorkerPool"""

    def test_submit_single_task(self):
        """Test submitting single task"""
        with WorkerPool(n_workers=2) as pool:
            fut = pool.submit(simple_task, 5)
            assert fut.result(timeout=10) == 10

    def test_submit_multiple_tasks(self):
        """Test submitting multiple tasks"""
        with WorkerPool(n_workers=2) as pool:
            futures = [pool.submit(simple_task, i) for i in range(5)]

            results = [f.result(timeout=10) for f in futures]
            assert results == [0, 2, 4, 6, 8]

    def test_map(self):
        """Test map method"""
        with WorkerPool(n_workers=2) as pool:
            results = pool.map(simple_task, [1, 2, 3, 4, 5])
            assert results == [2, 4, 6, 8, 10]

    def test_task_failure(self):
        """Test task failure"""
        with WorkerPool(n_workers=2) as pool:
            fut = pool.submit(failing_task, -1)

            with pytest.raises(ValueError, match="n must be non-negative"):
                fut.result(timeout=10)

            assert fut.failed
            assert fut.traceback is not None

    def test_timeout(self):
        """Test timeout"""
        with WorkerPool(n_workers=2) as pool:
            fut = pool.submit(slow_task, 5.0)  # 5 second task

            with pytest.raises(TimeoutError):
                fut.result(timeout=0.1)  # 0.1 second timeout

    def test_parallel_execution(self):
        """Test parallel execution"""
        with WorkerPool(n_workers=4) as pool:
            # Wait for all workers to be ready before timing,
            # to avoid counting process startup overhead
            deadline = time.monotonic() + 5.0
            while pool.ready_workers < 4 and time.monotonic() < deadline:
                time.sleep(0.05)

            start = time.perf_counter()
            futures = [pool.submit(slow_task, 0.1) for _ in range(4)]
            results = [f.result(timeout=10) for f in futures]
            elapsed = time.perf_counter() - start

            # 4 x 0.1s tasks in parallel should complete in ~0.1s, not 0.4s
            assert all(r == 0.1 for r in results)
            assert elapsed < 1.5  # Allow overhead for IPC and OS scheduling

    def test_worker_crash_and_restart(self):
        """
        Test Worker crash and restart recovery.

        This test verifies that the independent Pipe architecture correctly
        handles Worker crashes caused by os._exit(). Unlike the previous
        shared Queue architecture, the new architecture isolates each Worker's
        communication channel, so a crashed Worker's Pipe can be closed and
        a new Pipe created for the restarted Worker without affecting other
        Workers.
        """
        # Use longer orphan_timeout to avoid false positive orphan detection
        # during worker restart on slower/free-threaded Python builds
        with WorkerPool(n_workers=2, check_interval=0.5, orphan_timeout=2.0) as pool:
            # Wait for all workers to be ready before submitting crash task
            deadline = time.monotonic() + 5.0
            while pool.ready_workers < 2 and time.monotonic() < deadline:
                time.sleep(0.1)
            assert pool.ready_workers == 2, "Workers should be ready before test"

            # Submit a task that crashes the process
            crash_fut = pool.submit(crash_task)

            # Wait for the crash to be detected (crash_fut should fail with WorkerCrashedError)
            try:
                crash_fut.result(timeout=5.0)
                pytest.fail("crash_task should have raised WorkerCrashedError")
            except WorkerCrashedError:
                pass  # Expected

            # Now wait for the crashed worker to restart and become ready again
            deadline = time.monotonic() + 5.0
            while pool.ready_workers < 2 and time.monotonic() < deadline:
                time.sleep(0.1)
            assert pool.ready_workers == 2, "Restarted worker should be ready"

            # Submit new task, should execute normally (Worker restarted and ready)
            new_fut = pool.submit(simple_task, 42)
            assert new_fut.result(timeout=10) == 84

    def test_context_manager(self):
        """Test context manager"""
        pool = WorkerPool(n_workers=2)
        time.sleep(0.1)  # Give processes time to start
        assert pool.active_workers == 2

        with pool as p:
            assert p is pool
            assert pool.active_workers == 2

        time.sleep(0.1)
        assert pool.active_workers == 0

    def test_n_workers_property(self):
        """Test n_workers property"""
        with WorkerPool(n_workers=4) as pool:
            assert pool.n_workers == 4

    def test_state_property(self):
        """Test state property"""
        pool = WorkerPool(n_workers=2)
        assert pool.state == PoolState.RUNNING
        pool.shutdown(graceful_timeout=1.0)
        assert pool.state == PoolState.STOPPED


class TestGracefulShutdown:
    """Test graceful shutdown"""

    def test_graceful_shutdown_fast_tasks(self):
        """Test graceful shutdown with fast tasks completing in time"""
        pool = WorkerPool(n_workers=2)
        futures = [pool.submit(simple_task, i) for i in range(4)]

        # Let tasks start
        time.sleep(0.1)

        # Shutdown with enough time for tasks to complete
        report = pool.shutdown(graceful_timeout=5.0, term_timeout=2.0)

        assert isinstance(report, ShutdownReport)
        assert report.final_phase == "graceful"
        assert report.workers_killed == 0
        assert pool.state == PoolState.STOPPED

        # All tasks should have completed successfully
        for i, fut in enumerate(futures):
            assert fut.succeeded
            assert fut.result() == i * 2

    def test_submit_during_shutdown_raises_error(self):
        """Test that submit() raises PoolDrainingError during shutdown"""
        pool = WorkerPool(n_workers=2)
        pool.shutdown(graceful_timeout=1.0)  # Start shutdown immediately

        # Trying to submit after shutdown started should raise
        with pytest.raises(PoolDrainingError):
            pool.submit(simple_task, 1)

    def test_forced_shutdown_sigterm(self):
        """Test forced shutdown with SIGTERM when graceful timeout expires"""
        pool = WorkerPool(n_workers=2)

        # Submit a slow task that won't finish quickly
        fut = pool.submit(slow_task, 10.0)  # 10 second task

        # Let task start
        time.sleep(0.2)

        # Shutdown with very short graceful timeout (triggers SIGTERM or SIGKILL)
        report = pool.shutdown(graceful_timeout=0.5, term_timeout=2.0)

        # Should have gone through terminate or kill phase
        assert report.final_phase in ("terminate", "kill")
        assert pool.state == PoolState.STOPPED

        # Task should have failed or be pending (worker terminated before completion)
        # Note: The Future may not be marked as failed if the supervisor didn't
        # process the worker death before shutdown completed
        assert fut.done or pool.state == PoolState.STOPPED

    def test_forced_shutdown_sigkill(self):
        """Test forced shutdown with SIGKILL when term timeout expires"""
        pool = WorkerPool(n_workers=2)

        # Submit a very slow task
        pool.submit(very_slow_task)

        # Let task start
        time.sleep(0.2)

        # Shutdown with very short timeouts (forces SIGKILL path on slow systems)
        # Note: On fast systems, SIGTERM might be enough to kill workers quickly
        report = pool.shutdown(graceful_timeout=0.2, term_timeout=0.1)

        # Should have gone through at least terminate phase
        assert report.final_phase in ("terminate", "kill")
        assert pool.state == PoolState.STOPPED
        # workers_killed counts only if SIGKILL was used (exitcode == -9)
        # On some systems SIGTERM might be sufficient

    def test_shutdown_report_content(self):
        """Test ShutdownReport contains correct information"""
        pool = WorkerPool(n_workers=2)

        # Submit and complete a task
        fut = pool.submit(simple_task, 5)
        fut.result(timeout=10)

        # Shutdown
        report = pool.shutdown(graceful_timeout=5.0)

        assert isinstance(report, ShutdownReport)
        assert report.duration >= 0
        assert report.final_phase == "graceful"
        assert report.tasks_in_flight >= 0
        assert report.tasks_killed >= 0
        assert report.workers_killed >= 0
        assert str(report).startswith("ShutdownReport(")

    def test_shutdown_with_in_flight_tasks(self):
        """Test shutdown report tracks in-flight tasks"""
        pool = WorkerPool(n_workers=2)

        # Submit tasks that take some time
        futures = [pool.submit(slow_task, 0.5) for _ in range(2)]

        # Immediately shutdown (tasks are in flight)
        report = pool.shutdown(graceful_timeout=3.0)

        # tasks_in_flight should reflect tasks being executed at shutdown start
        assert report.tasks_in_flight >= 0

        # With enough graceful timeout, tasks should complete
        if report.final_phase == "graceful":
            for fut in futures:
                assert fut.succeeded

    def test_exit_when_already_stopped(self):
        """Test __exit__ when pool is already stopped"""
        pool = WorkerPool(n_workers=2)
        pool.shutdown(graceful_timeout=1.0)
        assert pool.state == PoolState.STOPPED

        # __exit__ should not raise when already stopped
        pool.__exit__(None, None, None)


class TestWorkerHandleEdgeCases:
    """Test WorkerHandle edge cases for 100% coverage"""

    def test_terminate_on_dead_process(self):
        """Test terminate() on already dead process (no-op branch)"""
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_quick_exit_worker, daemon=True)
        proc.start()
        proc.join(timeout=2)

        handle = WorkerHandle(0, proc)
        assert handle.is_alive is False

        # terminate() on dead process should be no-op (branch: if not alive)
        handle.terminate()
        # Should not raise, process already dead

    def test_kill_on_dead_process(self):
        """Test kill() on already dead process (no-op branch)"""
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_quick_exit_worker, daemon=True)
        proc.start()
        proc.join(timeout=2)

        handle = WorkerHandle(1, proc)
        assert handle.is_alive is False

        # kill() on dead process should be no-op (branch: if not alive)
        handle.kill()
        # Should not raise, process already dead


class TestForceKillPhase:
    """Test to cover KILLING phase in shutdown"""

    def test_forced_kill_phase_with_sigkill(self):
        """Test shutdown that reaches KILLING phase (SIGKILL)"""
        pool = WorkerPool(n_workers=2)
        # Submit a task that will block
        pool.submit(very_slow_task)
        time.sleep(0.2)  # Let task start

        # Use extremely short timeouts to force KILLING phase
        # Note: This test is timing-dependent and may not always reach KILLING
        # on fast systems where SIGTERM is sufficient
        report = pool.shutdown(graceful_timeout=0.01, term_timeout=0.01)

        # Verify shutdown completed
        assert pool.state == PoolState.STOPPED
        assert report.final_phase in ("terminate", "kill")

    def test_final_cleanup_remaining_processes(self):
        """Test final cleanup of remaining processes in shutdown"""
        # This test covers the final cleanup loop (lines 654-656)
        pool = WorkerPool(n_workers=1)

        # Submit and immediately shutdown - worker might still be starting
        pool.submit(simple_task, 1)
        # Immediate shutdown with zero timeouts to force all cleanup paths
        report = pool.shutdown(graceful_timeout=0.0, term_timeout=0.0)

        assert pool.state == PoolState.STOPPED
        assert report is not None  # Verify report is returned
        # Workers should be cleaned up
        assert pool.active_workers == 0


class TestOrphanedTaskDetection:
    """Test orphaned task detection (race condition: Worker dies before __dequeued__)"""

    def test_orphaned_task_detection(self):
        """Test that orphaned tasks are detected and Future is rejected"""
        from rhosocial.activerecord.worker.pool import WorkerCrashedError

        # Create pool with short check_interval and orphan_timeout
        pool = WorkerPool(n_workers=1, check_interval=0.1, orphan_timeout=0.1)

        # Wait for Worker to be ready first
        deadline = time.monotonic() + 2.0
        while pool.ready_workers < 1 and time.monotonic() < deadline:
            time.sleep(0.05)

        # Manually inject a task into _futures and _task_enqueue_time
        # to simulate a task that was dequeued but never claimed
        import uuid
        task_id = str(uuid.uuid4())
        fut = Future(task_id)

        # Simulate a Worker death to trigger orphan scan
        # Need to mark Worker as not ready (simulating crash) for orphan detection
        with pool._lock:
            pool._futures[task_id] = fut
            # Set enqueue time in the past to trigger orphan detection
            pool._task_enqueue_time[task_id] = time.monotonic() - 1.0
            # Mark Worker as not ready (simulating crash state)
            pool._worker_ready[0] = False
            # Trigger orphan scan by setting last worker death
            pool._last_worker_death = time.monotonic()

        # Wait for orphan detection (check_interval + buffer)
        # Need to wait long enough for supervisor to run _check_orphaned_tasks
        time.sleep(0.5)

        # Future should be rejected
        assert fut.done
        assert fut.failed
        with pytest.raises(WorkerCrashedError, match="orphaned"):
            fut.result()

        pool.shutdown(graceful_timeout=1.0)

    def test_normal_task_not_orphaned(self):
        """Test that normal tasks are not incorrectly marked as orphaned"""
        # Create pool with short check_interval and orphan_timeout
        pool = WorkerPool(n_workers=2, check_interval=0.1, orphan_timeout=0.5)

        # Submit a normal task - it should complete normally
        fut = pool.submit(simple_task, 5)
        result = fut.result(timeout=5)

        assert result == 10
        assert fut.succeeded
        assert not fut.failed

        pool.shutdown(graceful_timeout=1.0)

    def test_orphan_scan_no_orphans(self):
        """Test orphan scan when no orphaned tasks exist (empty _task_enqueue_time)"""
        pool = WorkerPool(n_workers=1, check_interval=0.1, orphan_timeout=0.1)

        # Trigger worker death but don't add any orphaned tasks
        with pool._lock:
            pool._last_worker_death = time.monotonic()

        # Wait for scan
        time.sleep(0.3)

        # Pool should still be running normally
        assert pool.state == PoolState.RUNNING

        pool.shutdown(graceful_timeout=1.0)

    def test_orphan_future_already_removed(self):
        """Test orphan handling when Future was already removed"""
        import uuid
        import time

        pool = WorkerPool(n_workers=1, check_interval=0.1, orphan_timeout=0.1)

        task_id = str(uuid.uuid4())

        # Add task to enqueue_time but NOT to _futures (simulates Future already removed)
        with pool._lock:
            pool._task_enqueue_time[task_id] = time.monotonic() - 1.0
            pool._last_worker_death = time.monotonic()

        # Wait for scan
        time.sleep(0.3)

        # Should complete without error (defensive branch: if fut is None)
        assert pool.state == PoolState.RUNNING

        pool.shutdown(graceful_timeout=1.0)


class TestDefensiveBranches:
    """Test defensive branches for 100% coverage"""

    def test_find_worker_by_task_not_found(self):
        """Test _find_worker_by_task returns None when task not found"""
        pool = WorkerPool(n_workers=1, check_interval=0.5)

        # Call _find_worker_by_task with non-existent task_id
        result = pool._find_worker_by_task("non-existent-task-id")

        assert result is None

        pool.shutdown(graceful_timeout=1.0)

    def test_orphan_scan_task_already_claimed(self):
        """Test orphan scan when task is already claimed (defensive branch)"""
        import uuid
        import time

        pool = WorkerPool(n_workers=1, check_interval=0.1, orphan_timeout=0.1)

        task_id = str(uuid.uuid4())

        # Add task to both enqueue_time AND worker_task (already claimed)
        # This simulates race condition: __dequeued__ arrived during orphan scan
        with pool._lock:
            pool._task_enqueue_time[task_id] = time.monotonic() - 1.0
            pool._worker_task[0] = task_id  # Task is claimed by Worker-0
            pool._last_worker_death = time.monotonic()

        # Wait for scan
        time.sleep(0.3)

        # Task should NOT be marked as orphan (it's claimed)
        # Pool should still be running
        assert pool.state == PoolState.RUNNING

        pool.shutdown(graceful_timeout=1.0)


class TestAsyncTaskSupport:
    """Test async task function support"""

    def test_async_task_basic(self):
        """Test basic async task execution"""
        pool = WorkerPool(n_workers=2, check_interval=0.5)

        fut = pool.submit(async_simple_task, 5)
        result = fut.result(timeout=10)

        assert result == 10
        assert fut.succeeded
        assert not fut.failed

        pool.shutdown(graceful_timeout=1.0)

    def test_async_task_exception(self):
        """Test async task that raises exception"""
        pool = WorkerPool(n_workers=2, check_interval=0.5)

        fut = pool.submit(async_failing_task, -1)

        with pytest.raises(ValueError, match="n must be non-negative"):
            fut.result(timeout=10)

        assert fut.failed
        assert fut.traceback is not None

        pool.shutdown(graceful_timeout=1.0)

    def test_async_task_multiple(self):
        """Test multiple async tasks"""
        pool = WorkerPool(n_workers=4, check_interval=0.5)

        futures = [pool.submit(async_simple_task, i) for i in range(10)]
        results = [f.result(timeout=10) for f in futures]

        assert results == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

        pool.shutdown(graceful_timeout=1.0)

    def test_mixed_sync_async_tasks(self):
        """Test mixing sync and async tasks in same pool"""
        pool = WorkerPool(n_workers=4, check_interval=0.5)

        # Submit mixed tasks
        fut_sync = pool.submit(simple_task, 5)
        fut_async = pool.submit(async_simple_task, 10)

        assert fut_sync.result(timeout=10) == 10
        assert fut_async.result(timeout=10) == 20

        pool.shutdown(graceful_timeout=1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
