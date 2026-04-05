# src/rhosocial/activerecord/worker/pool.py
"""
Resident Worker Pool Implementation.

Based on spawn mode, Worker processes start once and stay resident,
receiving tasks via Queue. Features graceful shutdown with three phases:
DRAINING → STOPPING → KILLING → STOPPED.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import multiprocessing as mp
import threading
import time
import traceback
import uuid
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

from ..logging.manager import get_logging_manager

# Use semantic logger naming: rhosocial.activerecord.worker
logger = get_logging_manager().get_logger(
    get_logging_manager().LOGGER_WORKER
)


# ── Sentinel ─────────────────────────────────────────────────────────────────

_STOP = "<<STOP>>"  # Worker exit sentinel (via mp.Queue, must be pickle-able)


# ── Enums ────────────────────────────────────────────────────────────────────

class PoolState(Enum):
    """Pool state machine for shutdown flow."""
    RUNNING = auto()   # Normal operation, accepting tasks
    DRAINING = auto()  # Rejecting new tasks, waiting for in-flight tasks (STOP sentinels sent)
    STOPPING = auto()  # graceful_timeout expired, SIGTERM sent
    KILLING = auto()   # term_timeout expired, sending SIGKILL
    STOPPED = auto()   # All workers terminated


class StopSignal(Enum):
    """Worker stop signal levels (from gentle to forced)."""
    SENTINEL = auto()   # STOP sentinel (queue-level): Worker exits after completing current task
    TERMINATE = auto()  # SIGTERM: Python default is immediate exit
    KILL = auto()       # SIGKILL: Cannot be caught, immediate termination


# ── Exceptions ───────────────────────────────────────────────────────────────

class PoolDrainingError(RuntimeError):
    """Pool is in shutdown flow, no longer accepting new tasks."""


class TaskTimeoutError(TimeoutError):
    """Task execution timeout (distinct from Future.result(timeout=...) wait timeout)."""


class WorkerCrashedError(RuntimeError):
    """Worker process crashed, task could not complete."""


# ── WorkerHandle ─────────────────────────────────────────────────────────────

class WorkerHandle:
    """
    Wrapper for mp.Process providing unified lifecycle operations.

    Only handles process-level operations (terminate / kill / join).
    Business state (current task ID, timeout timing) stays at Pool level.
    """

    def __init__(self, wid: int, proc: mp.Process) -> None:
        self.wid = wid
        self._proc = proc

    @property
    def pid(self) -> Optional[int]:
        return self._proc.pid

    @property
    def is_alive(self) -> bool:
        return self._proc.is_alive()

    @property
    def exitcode(self) -> Optional[int]:
        """
        None = still running; negative = killed by signal (e.g., -9 = SIGKILL);
        positive = normal exit code.
        """
        return self._proc.exitcode

    def terminate(self) -> None:
        """Send SIGTERM. Python default: immediate exit (no wait for current task)."""
        if self._proc.is_alive():
            self._proc.terminate()

    def kill(self) -> None:
        """Send SIGKILL. Cannot be caught or ignored, process dies immediately."""
        if self._proc.is_alive():
            self._proc.kill()

    def join(self, timeout: Optional[float] = None) -> bool:
        """Wait for process to exit. Returns True if exited within timeout."""
        self._proc.join(timeout=timeout)
        return not self._proc.is_alive()

    def stop(self, signal: StopSignal) -> None:
        """
        Unified stop entry. SENTINEL requires caller to send sentinel to queue;
        this method only handles process-level operations.
        """
        if signal == StopSignal.TERMINATE:
            self.terminate()
        elif signal == StopSignal.KILL:
            self.kill()
        # StopSignal.SENTINEL: caller is responsible for sending sentinel to task_q

    def __repr__(self) -> str:
        state = "alive" if self.is_alive else f"dead(exit={self.exitcode})"
        return f"<WorkerHandle wid={self.wid} pid={self.pid} {state}>"


# ── WorkerRegistry ───────────────────────────────────────────────────────────

class WorkerRegistry:
    """
    CRUD wrapper for WorkerHandle. Thread-safe (holds internal lock).

    Lock safety: WorkerRegistry._lock and ResidentWorkerPool._lock are never nested.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._handles: Dict[int, WorkerHandle] = {}

    # ── Create ────────────────────────────────────────────────────────────

    def add(self, wid: int, proc: mp.Process) -> WorkerHandle:
        """Register new Worker (replaces if wid exists, no stop signal to old proc)."""
        h = WorkerHandle(wid, proc)
        with self._lock:
            self._handles[wid] = h
        return h

    # ── Read ──────────────────────────────────────────────────────────────

    def get(self, wid: int) -> Optional[WorkerHandle]:
        with self._lock:
            return self._handles.get(wid)

    def all(self) -> List[WorkerHandle]:
        with self._lock:
            return list(self._handles.values())

    def alive(self) -> List[WorkerHandle]:
        with self._lock:
            return [h for h in self._handles.values() if h.is_alive]

    def dead(self) -> List[WorkerHandle]:
        with self._lock:
            return [h for h in self._handles.values() if not h.is_alive]

    def alive_count(self) -> int:
        with self._lock:
            return sum(1 for h in self._handles.values() if h.is_alive)

    def count(self) -> int:
        with self._lock:
            return len(self._handles)

    # ── Update ────────────────────────────────────────────────────────────

    def replace(self, wid: int, proc: mp.Process) -> WorkerHandle:
        """Replace old Handle on crash restart (no stop signal). Equivalent to add()."""
        return self.add(wid, proc)

    # ── Delete ────────────────────────────────────────────────────────────

    def remove(
        self,
        wid: int,
        signal: StopSignal = StopSignal.KILL,
    ) -> Optional[WorkerHandle]:
        """
        Remove Worker from registry and send stop signal.

        StopSignal.SENTINEL  only removes, caller sends sentinel to task_q.
        StopSignal.TERMINATE removes + SIGTERM.
        StopSignal.KILL      removes + SIGKILL (default).
        """
        with self._lock:
            h = self._handles.pop(wid, None)
        if h and signal != StopSignal.SENTINEL:
            h.stop(signal)
        return h

    def wids(self) -> List[int]:
        with self._lock:
            return list(self._handles.keys())


# ── ShutdownReport ───────────────────────────────────────────────────────────

@dataclass
class ShutdownReport:
    """Return value of shutdown(), describing the shutdown process."""
    duration: float          # Total shutdown time (seconds)
    final_phase: str         # Phase where shutdown completed: "graceful" / "terminate" / "kill"
    tasks_in_flight: int     # Tasks executing when shutdown started (not including queued)
    tasks_killed: int        # Workers still holding tasks after SIGKILL (upper bound on lost tasks)
    workers_killed: int      # Workers with exitcode == -9 (SIGKILL'd)

    def __str__(self) -> str:
        return (
            f"ShutdownReport("
            f"phase={self.final_phase}, "
            f"duration={self.duration:.2f}s, "
            f"in_flight={self.tasks_in_flight}, "
            f"killed={self.tasks_killed}/{self.workers_killed}w)"
        )


# ── Worker Process Entry Point (must be top-level function, spawn requires pickle) ────

def _worker_entry(worker_id: int, task_q: mp.Queue, result_q: mp.Queue) -> None:  # pragma: no cover
    """
    Resident Worker main loop.

    Task-level exceptions caught here; process-level crashes handled by Supervisor.

    Note: This function runs in a subprocess spawned by multiprocessing.
    Coverage cannot track code executed in subprocesses with spawn mode.
    The logic is tested indirectly through integration tests.

    Message sequence:
        1. __dequeued__ - Sent immediately after get(), enables crash attribution
        2. __started__  - Sent before fn(), enables timeout tracking
        3. ok/error     - Sent after fn() completes/fails

    Async Support:
        Both sync and async (coroutine) functions are supported as task functions.
        Async functions are automatically wrapped with asyncio.run().
    """
    while True:
        try:
            msg = task_q.get()
        except (EOFError, OSError):
            break

        if msg == _STOP:
            break

        # ★ __dequeued__ sent immediately after get(), before unpacking.
        #   This enables crash attribution from the moment task leaves queue.
        #   If Worker dies between get() and this line, orphan scan catches it.
        task_id = msg[0]
        result_q.put(("__dequeued__", worker_id, task_id))

        task_id, fn, args, kwargs = msg

        # __started__ for timeout tracking (execution actually begins)
        result_q.put(("__started__", worker_id, task_id))

        try:
            # Support both sync and async task functions
            if inspect.iscoroutinefunction(fn):
                value = asyncio.run(fn(*args, **kwargs))
            else:
                value = fn(*args, **kwargs)
            result_q.put(("ok", task_id, value))
        except Exception as exc:
            result_q.put(("error", task_id, exc, traceback.format_exc()))
        # Note: Process-level crashes (SIGSEGV, etc.) don't reach here,
        # handled by Supervisor's is_alive() check.


# ── Future ────────────────────────────────────────────────────────────────────

class Future:
    """
    Asynchronous result handle.

    Thread-safe, used to retrieve task execution results.
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._event = threading.Event()
        self._value: Any = None
        self._exc: Optional[BaseException] = None
        self._tb: Optional[str] = None

    # ── Internal methods (called by Supervisor thread) ────────────────────────

    def _resolve(self, value: Any) -> None:
        """Mark task as succeeded"""
        self._value = value
        self._event.set()

    def _reject(self, exc: BaseException, tb: str = "") -> None:
        """Mark task as failed"""
        self._exc = exc
        self._tb = tb
        self._event.set()

    # ── Public API ──────────────────────────────────────────────────────────

    def result(self, timeout: Optional[float] = None) -> Any:
        """
        Block and wait for result.

        Args:
            timeout: Timeout in seconds, None means infinite wait

        Returns:
            Task return value

        Raises:
            TimeoutError: Timeout exceeded
            Exception: Original exception raised by task
        """
        if not self._event.wait(timeout):
            raise TimeoutError(f"Task {self.task_id!r} did not complete within {timeout}s")
        if self._exc is not None:
            raise self._exc
        return self._value

    @property
    def done(self) -> bool:
        """Whether task has completed (success or failure)"""
        return self._event.is_set()

    @property
    def succeeded(self) -> bool:
        """Whether task succeeded"""
        return self._event.is_set() and self._exc is None

    @property
    def failed(self) -> bool:
        """Whether task failed"""
        return self._event.is_set() and self._exc is not None

    @property
    def traceback(self) -> Optional[str]:
        """Return full traceback string when task failed"""
        return self._tb

    def __repr__(self) -> str:
        if not self.done:
            state = "pending"
        elif self.succeeded:
            state = f"ok={self._value!r}"
        else:
            state = f"err={self._exc!r}"
        return f"<Future {self.task_id[:8]}… {state}>"


# ── WorkerPool ────────────────────────────────────────────────────────────────

class WorkerPool:
    """
    Spawn-mode Resident Worker Pool with Graceful Shutdown.

    Worker processes start once and stay resident (no repeated spawn/release overhead).
    Tasks dispatched via Queue, results captured via Future.
    Worker crash triggers automatic restart, crashed task marked as error.
    Three-phase shutdown: DRAINING → STOPPING → KILLING → STOPPED.

    Parameters
    ----------
    n_workers      : Number of Worker processes
    check_interval : Interval in seconds for Supervisor to check Worker health (default 0.5s)

    Usage Example
    -------------
    if __name__ == '__main__':
        with WorkerPool(n_workers=4) as pool:
            futures = [pool.submit(my_task, i) for i in range(10)]
            for f in futures:
                try:
                    print(f.result(timeout=10))
                except Exception as e:
                    print(f"Error: {e}")
    """

    def __init__(
        self,
        n_workers: int = 4,
        check_interval: float = 0.5,
        orphan_timeout: Optional[float] = None,
    ):
        """
        Initialize WorkerPool.

        Args:
            n_workers: Number of Worker processes
            check_interval: Interval in seconds for Supervisor to check Worker health
            orphan_timeout: Max seconds a task can wait without being claimed before
                considered orphaned (default: max(2.0, check_interval * 4)).
                Should be much larger than normal scheduling delay (< 0.1s).
        """
        self._n = n_workers
        self._check_interval = check_interval
        self._orphan_timeout = orphan_timeout or max(2.0, check_interval * 4)
        self._ctx = mp.get_context("spawn")
        self._state = PoolState.RUNNING

        self._task_q: mp.Queue = self._ctx.Queue()
        self._result_q: mp.Queue = self._ctx.Queue()

        # self._lock protects the following fields (never call registry methods while holding)
        self._lock = threading.Lock()
        # wid → task_id, set by __dequeued__ (crash attribution from dequeue moment)
        self._worker_task: Dict[int, Optional[str]] = {}
        # wid → monotonic, set by __started__ (timeout tracking from execution start)
        self._worker_start_time: Dict[int, Optional[float]] = {}
        self._futures: Dict[str, Future] = {}
        # task_id → enqueue timestamp (for orphan detection)
        self._task_enqueue_time: Dict[str, float] = {}
        # ★ Last Worker death time, triggers orphan scan (avoid false positives on busy queues)
        self._last_worker_death: float = 0.0

        self._registry = WorkerRegistry()   # Independent lock, never nested with self._lock

        logger.info(
            "WorkerPool initializing | n_workers=%d, check_interval=%.2fs, orphan_timeout=%.2fs",
            n_workers, check_interval, self._orphan_timeout
        )

        # Start Worker processes
        for wid in range(n_workers):
            self._start_worker(wid)

        # Start Supervisor background thread
        self._sv_thread = threading.Thread(
            target=self._supervise, daemon=True, name="pool-supervisor"
        )
        self._sv_thread.start()
        logger.info(
            "WorkerPool started | %d workers ready, supervisor thread active",
            self._registry.alive_count()
        )

    # ── Internal: Process Management ────────────────────────────────────────

    def _start_worker(self, wid: int) -> WorkerHandle:
        """
        Start a new Worker process and register it.
        Does not hold self._lock (registry.add uses its own lock).
        """
        p = self._ctx.Process(
            target=_worker_entry,
            args=(wid, self._task_q, self._result_q),
            daemon=True,
            name=f"worker-{wid}",
        )
        p.start()
        handle = self._registry.add(wid, p)      # registry._lock only
        with self._lock:                          # self._lock only (no nesting)
            self._worker_task[wid] = None
            self._worker_start_time[wid] = None
        logger.debug("Started Worker-%d (pid=%d)", wid, p.pid)
        return handle

    def _check_workers(self) -> None:
        """
        Detect dead Workers, attribute failed tasks, restart processes.
        Lock safety: calls registry methods first, then acquires self._lock.
        """
        dead_handles = self._registry.dead()    # registry._lock, not holding self._lock

        if not dead_handles:
            return

        for handle in dead_handles:
            wid = handle.wid

            # Double-check: timeout path may have already put a new Worker in (new Worker is alive)
            # This race condition is rare and hard to trigger in tests
            current = self._registry.get(wid)   # registry._lock (not holding self._lock)
            if current and current.is_alive:
                continue  # pragma: no cover

            handle.join(timeout=1)

            # Attribute the task being executed
            with self._lock:                    # self._lock (no nesting)
                lost_task_id = self._worker_task.pop(wid, None)
                self._worker_start_time.pop(wid, None)
                # ★ Record death time to trigger orphan scan
                self._last_worker_death = time.monotonic()

            exitcode = handle.exitcode
            # Determine exit reason for logging
            if exitcode == 0:
                # Normal exit (STOP sentinel received during shutdown)
                exit_reason = "normal"
                log_level = logging.DEBUG
            elif exitcode and exitcode < 0:
                # Killed by signal (e.g., -9 = SIGKILL, -15 = SIGTERM)
                import signal
                sig_name = signal.Signals(-exitcode).name if hasattr(signal, 'Signals') else str(-exitcode)
                exit_reason = f"signal({sig_name})"
                log_level = logging.WARNING
            else:
                # Non-zero exit code (error)
                exit_reason = f"error(code={exitcode})"
                log_level = logging.WARNING

            if lost_task_id:
                logger.warning(
                    "Worker-%d (pid=%s) crashed while executing task %s (exit=%s)",
                    wid, handle.pid, lost_task_id[:8], exit_reason
                )
                with self._lock:
                    fut = self._futures.pop(lost_task_id, None)
                if fut:  # pragma: no cover - Future may already be removed due to timeout
                    fut._reject(
                        WorkerCrashedError(
                            f"Worker-{wid} (pid={handle.pid}) crashed "
                            f"while executing task {lost_task_id!r}"
                        ),
                        tb=f"Worker process terminated unexpectedly (exit={exit_reason})",
                    )
            else:
                logger.log(
                    log_level,
                    "Worker-%d (pid=%s) exited (exit=%s), no task was in progress",
                    wid, handle.pid, exit_reason
                )

            # Restart only if RUNNING
            if self._state == PoolState.RUNNING:
                new_handle = self._start_worker(wid)
                logger.info(
                    "Worker-%d restarted (old_pid=%s, new_pid=%s)",
                    wid, handle.pid, new_handle.pid
                )
            else:
                # During shutdown: don't restart, just clean registry
                logger.debug(
                    "Worker-%d removed from registry (pool state=%s)",
                    wid, self._state.name
                )
                self._registry.remove(wid, signal=StopSignal.SENTINEL)

    # ── Internal: Supervisor Thread ─────────────────────────────────────────

    def _supervise(self) -> None:
        """Supervisor main loop: consume result queue + periodically check Worker health"""
        last_check = time.monotonic()

        while self._state not in (PoolState.KILLING, PoolState.STOPPED):
            # Non-blocking consume result queue (small timeout to avoid busy-wait)
            try:
                msg = self._result_q.get(timeout=0.05)
                self._dispatch(msg)
            except Exception:
                pass  # queue.Empty or other noise

            # Periodically check Worker health and orphaned tasks
            now = time.monotonic()
            if now - last_check >= self._check_interval:
                last_check = now
                self._check_workers()
                self._check_orphaned_tasks()

    def _dispatch(self, msg: tuple) -> None:
        """Dispatch result message"""
        kind = msg[0]

        if kind == "__dequeued__":
            # ★ Task has left the queue, Worker now "owns" it.
            #   From this point, if Worker crashes, _check_workers can attribute
            #   the task via _worker_task[wid] and reject the Future.
            _, wid, task_id = msg
            with self._lock:
                self._worker_task[wid] = task_id
                self._task_enqueue_time.pop(task_id, None)  # No longer orphan-able
            handle = self._registry.get(wid)
            pid = handle.pid if handle else None
            logger.debug(
                "Task[%s] dequeued | Worker-%d (pid=%s)",
                task_id[:8], wid, pid
            )

        elif kind == "__started__":
            # Execution actually begins, record start time for timeout tracking.
            # Note: _worker_task[wid] already set by __dequeued__.
            _, wid, task_id = msg
            with self._lock:
                self._worker_start_time[wid] = time.monotonic()
            handle = self._registry.get(wid)
            pid = handle.pid if handle else None
            logger.debug(
                "Task[%s] started | Worker-%d (pid=%s)",
                task_id[:8], wid, pid
            )

        elif kind == "ok":
            _, task_id, value = msg
            # Find Worker ID before clearing
            wid = self._find_worker_by_task(task_id)
            handle = self._registry.get(wid) if wid is not None else None
            pid = handle.pid if handle else None
            self._clear_worker_task(task_id)
            with self._lock:
                fut = self._futures.pop(task_id, None)
                self._task_enqueue_time.pop(task_id, None)  # Defensive cleanup
            if fut:  # pragma: no cover - Future may already be removed due to timeout
                fut._resolve(value)
                logger.debug(
                    "Task[%s] completed | Worker-%d (pid=%s)",
                    task_id[:8], wid, pid
                )

        elif kind == "error":
            _, task_id, exc, tb = msg
            # Find Worker ID before clearing
            wid = self._find_worker_by_task(task_id)
            handle = self._registry.get(wid) if wid is not None else None
            pid = handle.pid if handle else None
            self._clear_worker_task(task_id)
            with self._lock:
                fut = self._futures.pop(task_id, None)
                self._task_enqueue_time.pop(task_id, None)  # Defensive cleanup
            if fut:  # pragma: no cover - Future may already be removed due to timeout
                fut._reject(exc, tb)
                logger.warning(
                    "Task[%s] failed | Worker-%d (pid=%s) | error=%s: %s",
                    task_id[:8], wid, pid, type(exc).__name__, exc
                )

    def _find_worker_by_task(self, task_id: str) -> Optional[int]:
        """Find Worker ID by task ID"""
        with self._lock:
            for wid, tid in self._worker_task.items():
                if tid == task_id:
                    return wid
        return None

    def _clear_worker_task(self, task_id: str) -> None:
        """Clear Worker's task binding"""
        with self._lock:
            for wid, tid in self._worker_task.items():  # pragma: no cover - defensive loop for task cleanup
                if tid == task_id:
                    self._worker_task[wid] = None
                    self._worker_start_time[wid] = None
                    break

    def _check_orphaned_tasks(self) -> None:
        """
        Detect tasks that were dequeued but never claimed by any Worker.

        This handles the race condition where a Worker dies between
        task_q.get() and result_q.put("__dequeued__", ...), leaving
        the task permanently pending.

        Trigger conditions (BOTH must be true to avoid false positives on busy queues):
          1. Recent Worker death (_last_worker_death within orphan_timeout * 3 seconds)
          2. Task has been enqueued > orphan_timeout seconds without being claimed

        Orphan cause:
          Worker died in the tiny window between get() and put(__dequeued__).
          Task left queue but no wid ever claimed it in _worker_task.

        False positive analysis:
          On busy pools, tasks may legitimately wait > orphan_timeout in queue.
          By requiring recent Worker death, we avoid triggering during normal operation.
          Default orphan_timeout=2s is much larger than normal dispatch delay (< 0.1s).
        """
        now = time.monotonic()

        # Only scan within the window after Worker death (3 × orphan_timeout)
        # This avoids false positives on busy queues where tasks legitimately wait
        if now - self._last_worker_death > self._orphan_timeout * 3:
            return

        # Collect claimed task IDs (set by __dequeued__)
        with self._lock:
            claimed = set(
                tid for tid in self._worker_task.values() if tid is not None
            )

            # Find orphaned tasks
            orphans = []
            for task_id, enqueue_time in list(self._task_enqueue_time.items()):
                if task_id not in claimed:
                    wait_time = now - enqueue_time
                    if wait_time > self._orphan_timeout:
                        orphans.append((task_id, wait_time))
                        self._task_enqueue_time.pop(task_id, None)

        # Handle orphaned tasks
        for task_id, wait_time in orphans:
            with self._lock:
                fut = self._futures.pop(task_id, None)
            if fut:
                logger.warning(
                    "Task[%s] orphaned (enqueued %.1fs ago, never claimed) | "
                    "Worker likely died in get()→__dequeued__ window",
                    task_id[:8], wait_time
                )
                fut._reject(
                    WorkerCrashedError(
                        f"Task {task_id!r} was dequeued by a Worker that crashed "
                        f"before sending __dequeued__ (waited {wait_time:.1f}s)"
                    ),
                    tb="Worker process terminated during task dispatch",
                )

    # ── Public API ──────────────────────────────────────────────────────────

    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        """
        Submit a task, immediately return Future.

        fn and all arguments must be pickle-able (spawn limitation).

        Args:
            fn: Task function (must be module-level function)
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Future: Asynchronous result handle

        Raises:
            PoolDrainingError: Pool is in shutdown flow
        """
        if self._state != PoolState.RUNNING:
            raise PoolDrainingError(
                f"Pool is {self._state.name} — no new tasks accepted. "
                f"shutdown() was already called."
            )
        task_id = str(uuid.uuid4())
        fut = Future(task_id)
        with self._lock:
            self._futures[task_id] = fut
            self._task_enqueue_time[task_id] = time.monotonic()
        self._task_q.put((task_id, fn, args, kwargs))
        logger.debug("Task[%s] submitted | fn=%s", task_id[:8], fn.__name__)
        return fut

    def map(self, fn: Callable, iterable, timeout: Optional[float] = None) -> list:
        """
        Batch submit, collect results in order.

        Args:
            fn: Task function
            iterable: Argument iterator
            timeout: Timeout in seconds for each task

        Returns:
            list: Result list (same order as input)

        Raises:
            Exception: Raised if any task fails
        """
        futs = [self.submit(fn, item) for item in iterable]
        return [f.result(timeout=timeout) for f in futs]

    def shutdown(
        self,
        graceful_timeout: float = 10.0,
        term_timeout: float = 3.0,
    ) -> ShutdownReport:
        """
        Three-phase graceful shutdown.

        Phase 1 · DRAINING (STOP sentinel, wait for natural exit)
        ─────────────────────────────────────────────────────────
        - Immediately reject new submit() (PoolDrainingError)
        - Inject N STOP sentinels into queue
        - Worker completes current task, reads sentinel, exits voluntarily
        - Wait for graceful_timeout seconds

        Phase 2 · STOPPING (SIGTERM)
        ─────────────────────────────────────────────────────────
        - graceful_timeout expired but workers still alive
        - proc.terminate() all alive Workers (Python default: immediate exit)
        - Wait for term_timeout seconds

        Phase 3 · KILLING (SIGKILL)
        ─────────────────────────────────────────────────────────
        - term_timeout expired but workers still alive
        - proc.kill(), cannot be caught, process dies immediately
        - Tasks being executed at this point are lost

        Args:
            graceful_timeout: Phase 1 wait time (default 10s)
            term_timeout: Phase 2 wait time (default 3s)

        Returns:
            ShutdownReport: Contains shutdown duration, completion phase, task loss info
        """
        start_time = time.monotonic()
        final_phase = "graceful"

        # ── Phase 1: DRAINING ─────────────────────────────────────────────
        self._state = PoolState.DRAINING

        # Snapshot in-flight tasks before shutdown
        with self._lock:
            tasks_in_flight = sum(1 for t in self._worker_task.values() if t is not None)

        # Inject sentinels into shared queue. Workers read sentinel after completing
        # current task and exit voluntarily.
        # Sentinel count = Worker count (FIFO queue guarantees each Worker gets one).
        for _ in range(self._n):
            self._task_q.put(_STOP)

        logger.info(
            "Shutdown initiated | DRAINING (graceful_timeout=%.1fs, in_flight=%d)",
            graceful_timeout, tasks_in_flight,
        )

        deadline = time.monotonic() + graceful_timeout
        while time.monotonic() < deadline:
            if self._registry.alive_count() == 0:
                logger.info(
                    "DRAINING complete | all workers exited gracefully (duration=%.2fs)",
                    time.monotonic() - start_time
                )
                break
            time.sleep(0.1)
        else:
            # ── Phase 2: STOPPING (SIGTERM) ────────────────────────────────
            self._state = PoolState.STOPPING
            final_phase = "terminate"
            alive = self._registry.alive()
            logger.warning(
                "DRAINING timeout | STOPPING (%d workers still alive, sending SIGTERM)",
                len(alive),
            )
            for h in alive:
                logger.debug("Sending SIGTERM to Worker-%d (pid=%d)", h.wid, h.pid)
                h.terminate()

            deadline2 = time.monotonic() + term_timeout
            while time.monotonic() < deadline2:
                if self._registry.alive_count() == 0:
                    logger.info(
                        "STOPPING complete | all workers terminated via SIGTERM (duration=%.2fs)",
                        time.monotonic() - start_time
                    )
                    break
                time.sleep(0.1)
            else:
                # ── Phase 3: KILLING (SIGKILL) ─────────────────────────────
                self._state = PoolState.KILLING
                final_phase = "kill"
                still_alive = self._registry.alive()
                logger.error(
                    "STOPPING timeout | KILLING (%d workers still alive, sending SIGKILL)",
                    len(still_alive),
                )
                for h in still_alive:
                    logger.debug("Sending SIGKILL to Worker-%d (pid=%d)", h.wid, h.pid)
                    h.kill()
                for h in still_alive:
                    h.join(timeout=2)

        # Final cleanup: ensure any remaining processes are terminated
        # This is defensive code for processes that survived SIGKILL (extremely rare)
        for h in self._registry.alive():  # pragma: no cover
            h.kill()
            h.join(timeout=2)

        # Count losses
        with self._lock:
            tasks_killed = sum(1 for t in self._worker_task.values() if t is not None)
        workers_killed = sum(1 for h in self._registry.all() if h.exitcode == -9)

        self._state = PoolState.STOPPED
        duration = time.monotonic() - start_time

        report = ShutdownReport(
            duration=duration,
            final_phase=final_phase,
            tasks_in_flight=tasks_in_flight,
            tasks_killed=tasks_killed,
            workers_killed=workers_killed,
        )
        logger.info("Shutdown complete | %s", report)
        return report

    @property
    def n_workers(self) -> int:
        """Number of Worker processes"""
        return self._n

    @property
    def active_workers(self) -> int:
        """Number of alive Worker processes"""
        return self._registry.alive_count()

    @property
    def state(self) -> PoolState:
        """Current pool state"""
        return self._state

    def __enter__(self) -> "WorkerPool":
        logger.debug("WorkerPool context entered | state=%s", self._state.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._state == PoolState.RUNNING:
            if exc_type is not None:
                logger.info(
                    "WorkerPool context exiting with exception | %s: %s",
                    exc_type.__name__, exc_val
                )
            else:
                logger.debug("WorkerPool context exiting normally")
            self.shutdown()
        else:
            logger.debug(
                "WorkerPool context exit | shutdown already in progress (state=%s)",
                self._state.name
            )
