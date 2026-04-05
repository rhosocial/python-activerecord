# src/rhosocial/activerecord/worker/pool.py
"""
Resident Worker Pool Implementation.

Based on spawn mode, Worker processes start once and stay resident,
receiving tasks via Queue. Features graceful shutdown with three phases:
DRAINING → STOPPING → KILLING → STOPPED.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
import multiprocessing as mp
import os
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple, Union

# Resource monitoring support
try:
    import resource
    _HAS_RESOURCE = True
except ImportError:
    _HAS_RESOURCE = False  # Windows doesn't have resource module

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


class WorkerEvent(Enum):
    """Worker lifecycle events for hook registration."""
    WORKER_START = auto()  # Worker process startup
    WORKER_STOP = auto()   # Worker process shutdown
    TASK_START = auto()    # Task execution start
    TASK_END = auto()      # Task execution end (success or failure)


# ── Statistics ────────────────────────────────────────────────────────────────

@dataclass
class PoolStats:
    """
    Pool execution statistics snapshot.

    All statistics are point-in-time snapshots and may be stale immediately
    after retrieval in a busy pool.
    """
    # Worker statistics
    total_workers: int = 0           # Configured number of workers
    alive_workers: int = 0           # Currently alive workers
    worker_restarts: int = 0         # Worker restart count (after crash recovery)
    worker_crashes: int = 0          # Worker crash count (unexpected termination)

    # Task statistics
    tasks_submitted: int = 0         # Total tasks submitted
    tasks_completed: int = 0         # Successfully completed tasks
    tasks_failed: int = 0            # Failed tasks (exception thrown)
    tasks_orphaned: int = 0          # Orphaned tasks (lost due to worker crash)

    # Queue statistics
    tasks_pending: int = 0           # Tasks waiting in queue
    tasks_in_flight: int = 0         # Tasks currently executing

    # Time statistics
    uptime: float = 0.0              # Pool uptime in seconds
    total_task_duration: float = 0.0 # Sum of all task durations
    avg_task_duration: float = 0.0   # Average task duration

    # Memory statistics
    total_memory_delta: int = 0      # Total memory delta in bytes
    avg_memory_delta_mb: float = 0.0 # Average memory delta in MB


# ── Hook Context Types ───────────────────────────────────────────────────────

@dataclass
class WorkerContext:
    """
    Context passed to Worker-level hooks (WORKER_START/WORKER_STOP).

    Attributes:
        worker_id: Worker index (0, 1, 2, ...)
        pid: Process ID
        pool_id: Pool instance identifier
        start_time: Worker startup timestamp (monotonic)
        task_count: Number of tasks executed (incremented during WORKER_STOP)
    """
    worker_id: int
    pid: int
    pool_id: str
    start_time: float = 0.0
    task_count: int = 0


@dataclass
class TaskContext:
    """
    Context passed to Task-level hooks (TASK_START/TASK_END).

    Attributes:
        task_id: Task identifier
        worker_ctx: Worker context
        fn_name: Task function name
        args: Task positional arguments
        kwargs: Task keyword arguments
        start_time: Task start timestamp (monotonic)
        end_time: Task end timestamp (monotonic, set in TASK_END)
        success: Whether task succeeded (set in TASK_END)
        result: Task result (set in TASK_END on success)
        error: Task exception (set in TASK_END on failure)
        memory_start: Memory usage at task start (bytes, RSS)
        memory_end: Memory usage at task end (bytes, RSS)
    """
    task_id: str
    worker_ctx: WorkerContext
    fn_name: str = ""
    args: Tuple = ()
    kwargs: Dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    end_time: float = 0.0
    success: bool = False
    result: Any = None
    error: Optional[Exception] = None
    # Resource monitoring
    memory_start: int = 0  # RSS in bytes at task start
    memory_end: int = 0    # RSS in bytes at task end

    @property
    def duration(self) -> float:
        """Task execution duration in seconds."""
        return self.end_time - self.start_time if self.end_time else 0.0

    @property
    def memory_delta(self) -> int:
        """Memory delta in bytes (end - start)."""
        return self.memory_end - self.memory_start

    @property
    def memory_delta_mb(self) -> float:
        """Memory delta in megabytes."""
        return self.memory_delta / (1024 * 1024)

    def log_summary(
        self,
        logger: Optional[logging.Logger] = None,
        level: int = logging.INFO
    ) -> None:
        """
        Log a summary of task execution.

        Args:
            logger: Logger to use (defaults to module logger)
            level: Log level (default: INFO)
        """
        if logger is None:
            logger = logging.getLogger(__name__)

        status = "SUCCESS" if self.success else "FAILED"
        msg = (
            f"Task[{self.task_id[:8]}] {status} | "
            f"fn={self.fn_name}, "
            f"duration={self.duration:.3f}s"
        )
        if self.memory_start > 0:
            msg += f", memory_delta={self.memory_delta_mb:+.2f}MB"
        if not self.success and self.error:
            msg += f", error={type(self.error).__name__}: {self.error}"

        logger.log(level, msg)


# ── Hook Type Aliases ────────────────────────────────────────────────────────

# Synchronous hook types
WorkerHook = Callable[[WorkerContext], None]
TaskHook = Callable[[TaskContext], None]

# Asynchronous hook types
AsyncWorkerHook = Callable[[WorkerContext], Awaitable[None]]
AsyncTaskHook = Callable[[TaskContext], Awaitable[None]]

# Union types supporting both function objects and string paths
AnyWorkerHook = Union[WorkerHook, AsyncWorkerHook, str]
AnyTaskHook = Union[TaskHook, AsyncTaskHook, str]


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

def _get_memory_usage() -> int:
    """
    Get current process memory usage (RSS) in bytes.

    Uses resource module on Unix systems.
    Returns 0 if memory info is unavailable (e.g., on Windows without psutil).

    Returns:
        Resident Set Size (RSS) in bytes
    """
    if _HAS_RESOURCE:
        # resource.getrusage returns values in kilobytes on most systems
        # RUSAGE_SELF = current process
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss is in kilobytes on Linux, bytes on macOS
        # We normalize to bytes
        if hasattr(os, 'uname') and os.uname().sysname == 'Darwin':
            # macOS: ru_maxrss is already in bytes
            return rusage.ru_maxrss
        else:
            # Linux and others: ru_maxrss is in kilobytes
            return rusage.ru_maxrss * 1024
    else:
        # Windows: try to use psutil if available, otherwise return 0
        try:
            import psutil
            return psutil.Process(os.getpid()).memory_info().rss
        except ImportError:
            return 0


def _import_hook(path: str) -> Callable:
    """
    Dynamically import a hook function by its module path.

    Args:
        path: Full path to the function, e.g., "mymodule.hooks.on_start"

    Returns:
        The imported callable function
    """
    module_path, fn_name = path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, fn_name)


def _resolve_hooks(
    hooks: Optional[Union[AnyWorkerHook, AnyTaskHook, List[Tuple[str, Any]]]]
) -> List[Callable]:
    """
    Resolve hook specifications to actual callable functions.

    Supports:
    - None: returns empty list
    - String path: imports the function
    - String path with commas: imports multiple functions
    - List of (name, hook) tuples: resolves each item
    - Single callable: returns list with that callable

    Args:
        hooks: Hook specification in any supported format

    Returns:
        List of resolved callable functions
    """
    if hooks is None:
        return []

    if isinstance(hooks, str):
        # String path(s) - support comma-separated multiple paths
        if ',' in hooks:
            paths = hooks.split(',')
            return [_import_hook(p.strip()) for p in paths]
        return [_import_hook(hooks)]

    if isinstance(hooks, list):
        # List format: [(name, hook), ...] or [hook, ...]
        result = []
        for item in hooks:
            if isinstance(item, tuple):
                _, hook = item
            else:
                hook = item
            if isinstance(hook, str):
                result.append(_import_hook(hook))
            else:
                result.append(hook)
        return result

    # Single callable object
    return [hooks]


def _execute_hooks(
    hooks: List[Callable],
    ctx: Union[WorkerContext, TaskContext],
) -> Optional[Tuple[str, str]]:
    """
    Execute a list of hooks with the given context.

    Args:
        hooks: List of callable hook functions (sync or async)
        ctx: Context to pass to hooks (WorkerContext or TaskContext)

    Returns:
        Tuple of (error_message, traceback) if any hook failed, None otherwise
    """
    for hook in hooks:
        try:
            if inspect.iscoroutinefunction(hook):
                asyncio.run(hook(ctx))
            else:
                hook(ctx)
        except Exception as e:
            # Return error info for first failure
            return (str(e), traceback.format_exc())
    return None


def _worker_entry(
    worker_id: int,
    task_q: mp.Queue,
    result_q: mp.Queue,
    pool_id: str,
    on_worker_start: Optional[AnyWorkerHook] = None,
    on_worker_stop: Optional[AnyWorkerHook] = None,
    on_task_start: Optional[AnyTaskHook] = None,
    on_task_end: Optional[AnyTaskHook] = None,
) -> None:  # pragma: no cover
    """
    Resident Worker main loop with lifecycle hooks.

    Task-level exceptions caught here; process-level crashes handled by Supervisor.

    Note: This function runs in a subprocess spawned by multiprocessing.
    Coverage cannot track code executed in subprocesses with spawn mode.
    The logic is tested indirectly through integration tests.

    Hook Execution:
        WORKER_START: Executed before the main loop, failure prevents Worker startup
        TASK_START: Executed before each task, failure is logged but doesn't affect task
        TASK_END: Executed after each task (success or failure), failure is logged
        WORKER_STOP: Executed in finally block, failure is logged

    Message sequence:
        1. __worker_ready__ / __worker_init_failed__ - After WORKER_START hooks
        2. __dequeued__ - Sent immediately after get(), enables crash attribution
        3. __started__  - Sent before fn(), enables timeout tracking
        4. ok/error     - Sent after fn() completes/fails

    Async Support:
        Both sync and async (coroutine) functions are supported as task functions.
        Async functions are automatically wrapped with asyncio.run().
    """
    pid = os.getpid()
    ctx = WorkerContext(
        worker_id=worker_id,
        pid=pid,
        pool_id=pool_id,
        start_time=time.monotonic(),
        task_count=0,
    )

    # Resolve hooks once at startup
    start_hooks = _resolve_hooks(on_worker_start)
    stop_hooks = _resolve_hooks(on_worker_stop)
    task_start_hooks = _resolve_hooks(on_task_start)
    task_end_hooks = _resolve_hooks(on_task_end)

    # Execute WORKER_START hooks
    if start_hooks:
        error_info = _execute_hooks(start_hooks, ctx)
        if error_info:
            error_msg, tb = error_info
            result_q.put(("__worker_init_failed__", worker_id, error_msg, tb))
            return  # Worker does not start
        result_q.put(("__worker_ready__", worker_id, pid))

    try:
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

            # Build task context with resource monitoring
            task_ctx = TaskContext(
                task_id=task_id,
                worker_ctx=ctx,
                fn_name=getattr(fn, '__qualname__', str(fn)),
                args=args,
                kwargs=kwargs,
                start_time=time.monotonic(),
                memory_start=_get_memory_usage(),
            )

            # Execute TASK_START hooks (failures logged but don't affect task)
            if task_start_hooks:
                _execute_hooks(task_start_hooks, task_ctx)

            # Execute the task
            exc = None
            tb_str = None
            try:
                # Support both sync and async task functions
                if inspect.iscoroutinefunction(fn):
                    value = asyncio.run(fn(*args, **kwargs))
                else:
                    value = fn(*args, **kwargs)
                task_ctx.success = True
                task_ctx.result = value
            except Exception as e:
                exc = e
                tb_str = traceback.format_exc()
                task_ctx.success = False
                task_ctx.error = exc

            # Record end time and memory BEFORE sending result
            ctx.task_count += 1
            task_ctx.end_time = time.monotonic()
            task_ctx.memory_end = _get_memory_usage()

            # Send result with metadata
            if exc is None:
                result_q.put((
                    "ok", task_id, value,
                    worker_id, task_ctx.start_time, task_ctx.end_time,
                    task_ctx.memory_start, task_ctx.memory_end
                ))
            else:
                result_q.put((
                    "error", task_id, exc, tb_str,
                    worker_id, task_ctx.start_time, task_ctx.end_time,
                    task_ctx.memory_start, task_ctx.memory_end
                ))

            # Execute TASK_END hooks (failures logged but don't affect next task)
            if task_end_hooks:
                _execute_hooks(task_end_hooks, task_ctx)

    finally:
        # Execute WORKER_STOP hooks (even on crash/exception)
        if stop_hooks:
            _execute_hooks(stop_hooks, ctx)


# ── Future ────────────────────────────────────────────────────────────────────

class Future:
    """
    Asynchronous result handle with execution metadata.

    Thread-safe, used to retrieve task execution results and metadata.

    Attributes:
        task_id: Task identifier
        worker_id: ID of Worker that executed the task (available after completion)
        start_time: Task start timestamp (monotonic, available after completion)
        end_time: Task end timestamp (monotonic, available after completion)
        memory_start: Memory at task start (bytes, available after completion)
        memory_end: Memory at task end (bytes, available after completion)
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self._event = threading.Event()
        self._value: Any = None
        self._exc: Optional[BaseException] = None
        self._tb: Optional[str] = None
        # Execution metadata (populated on completion)
        self._worker_id: Optional[int] = None
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._memory_start: int = 0
        self._memory_end: int = 0

    # ── Internal methods (called by Supervisor thread) ────────────────────────

    def _resolve(
        self,
        value: Any,
        worker_id: Optional[int] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        memory_start: int = 0,
        memory_end: int = 0,
    ) -> None:
        """Mark task as succeeded with optional metadata."""
        self._value = value
        self._worker_id = worker_id
        self._start_time = start_time
        self._end_time = end_time
        self._memory_start = memory_start
        self._memory_end = memory_end
        self._event.set()

    def _reject(
        self,
        exc: BaseException,
        tb: str = "",
        worker_id: Optional[int] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        memory_start: int = 0,
        memory_end: int = 0,
    ) -> None:
        """Mark task as failed with optional metadata."""
        self._exc = exc
        self._tb = tb
        self._worker_id = worker_id
        self._start_time = start_time
        self._end_time = end_time
        self._memory_start = memory_start
        self._memory_end = memory_end
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

    # ── Execution Metadata Properties ─────────────────────────────────────

    @property
    def worker_id(self) -> Optional[int]:
        """ID of Worker that executed the task (available after completion)"""
        return self._worker_id

    @property
    def start_time(self) -> Optional[float]:
        """Task start timestamp (monotonic, available after completion)"""
        return self._start_time

    @property
    def end_time(self) -> Optional[float]:
        """Task end timestamp (monotonic, available after completion)"""
        return self._end_time

    @property
    def duration(self) -> float:
        """Task execution duration in seconds (0 if not completed)"""
        if self._start_time and self._end_time:
            return self._end_time - self._start_time
        return 0.0

    @property
    def memory_start(self) -> int:
        """Memory usage at task start in bytes"""
        return self._memory_start

    @property
    def memory_end(self) -> int:
        """Memory usage at task end in bytes"""
        return self._memory_end

    @property
    def memory_delta(self) -> int:
        """Memory delta (end - start) in bytes"""
        return self._memory_end - self._memory_start

    @property
    def memory_delta_mb(self) -> float:
        """Memory delta in megabytes"""
        return self.memory_delta / (1024 * 1024)

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

    Lifecycle Hooks:
        WORKER_START: Called when a Worker process starts (for resource initialization)
        WORKER_STOP: Called when a Worker process stops (for resource cleanup)
        TASK_START: Called before each task execution (for per-task setup)
        TASK_END: Called after each task execution (for per-task cleanup/monitoring)

    Parameters
    ----------
    n_workers        : Number of Worker processes
    check_interval   : Interval in seconds for Supervisor to check Worker health (default 0.5s)
    on_worker_start  : Hook for Worker startup (function or "module.path" string)
    on_worker_stop   : Hook for Worker shutdown (function or "module.path" string)
    on_task_start    : Hook for task start (function or "module.path" string)
    on_task_end      : Hook for task end (function or "module.path" string)

    Usage Example
    -------------
    # Basic usage
    if __name__ == '__main__':
        with WorkerPool(n_workers=4) as pool:
            futures = [pool.submit(my_task, i) for i in range(10)]
            for f in futures:
                try:
                    print(f.result(timeout=10))
                except Exception as e:
                    print(f"Error: {e}")

    # With lifecycle hooks for database connections
    def init_db(ctx: WorkerContext):
        from myapp.db import Database
        Database.connect()

    def cleanup_db(ctx: WorkerContext):
        from myapp.db import Database
        Database.disconnect()

    with WorkerPool(
        n_workers=4,
        on_worker_start=init_db,
        on_worker_stop=cleanup_db,
    ) as pool:
        # Workers have database connections ready
        pool.submit(process_data, data)
    """

    def __init__(
        self,
        n_workers: int = 4,
        check_interval: float = 0.5,
        orphan_timeout: Optional[float] = None,
        # Lifecycle hooks
        on_worker_start: Optional[AnyWorkerHook] = None,
        on_worker_stop: Optional[AnyWorkerHook] = None,
        on_task_start: Optional[AnyTaskHook] = None,
        on_task_end: Optional[AnyTaskHook] = None,
    ):
        """
        Initialize WorkerPool.

        Args:
            n_workers: Number of Worker processes
            check_interval: Interval in seconds for Supervisor to check Worker health
            orphan_timeout: Max seconds a task can wait without being claimed before
                considered orphaned (default: max(2.0, check_interval * 4)).
                Should be much larger than normal scheduling delay (< 0.1s).
            on_worker_start: Hook called when Worker process starts (for initialization)
            on_worker_stop: Hook called when Worker process stops (for cleanup)
            on_task_start: Hook called before each task execution
            on_task_end: Hook called after each task execution (success or failure)
        """
        self._n = n_workers
        self._check_interval = check_interval
        self._orphan_timeout = orphan_timeout or max(2.0, check_interval * 4)
        self._ctx = mp.get_context("spawn")
        self._state = PoolState.RUNNING
        self._pool_id = str(uuid.uuid4())[:8]  # Short ID for logging

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

        # Hook storage: Dict[WorkerEvent, List[Tuple[name, hook]]]
        self._hooks: Dict[WorkerEvent, List[Tuple[str, Union[AnyWorkerHook, AnyTaskHook]]]] = {
            WorkerEvent.WORKER_START: [],
            WorkerEvent.WORKER_STOP: [],
            WorkerEvent.TASK_START: [],
            WorkerEvent.TASK_END: [],
        }

        # Statistics tracking
        self._stats_lock = threading.Lock()
        self._start_time: float = time.monotonic()
        self._worker_restarts: int = 0
        self._worker_crashes: int = 0
        self._tasks_submitted: int = 0
        self._tasks_completed: int = 0
        self._tasks_failed: int = 0
        self._tasks_orphaned: int = 0
        self._total_task_duration: float = 0.0
        self._total_memory_delta: int = 0

        # Register constructor-provided hooks
        if on_worker_start:
            self.register_hook(WorkerEvent.WORKER_START, on_worker_start)
        if on_worker_stop:
            self.register_hook(WorkerEvent.WORKER_STOP, on_worker_stop)
        if on_task_start:
            self.register_hook(WorkerEvent.TASK_START, on_task_start)
        if on_task_end:
            self.register_hook(WorkerEvent.TASK_END, on_task_end)

        logger.info(
            "WorkerPool initializing | pool_id=%s, n_workers=%d, check_interval=%.2fs, orphan_timeout=%.2fs",
            self._pool_id, n_workers, check_interval, self._orphan_timeout
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

    def _serialize_hooks(
        self,
        event: WorkerEvent
    ) -> Optional[Union[str, List[Tuple[str, Any]]]]:
        """
        Serialize hooks for passing to Worker process.

        For a single hook:
        - String path: returned as-is
        - Callable: returned directly (will be pickled)

        For multiple hooks:
        - Returns list of (name, hook) tuples

        Args:
            event: The WorkerEvent to serialize hooks for

        Returns:
            Serialized hook specification, or None if no hooks
        """
        hooks = self._hooks.get(event, [])
        if not hooks:
            return None

        if len(hooks) == 1:
            # Single hook: return string path or callable directly
            _, hook = hooks[0]
            if isinstance(hook, str):
                return hook
            return hook  # Let pickle handle the callable

        # Multiple hooks: return as list
        return hooks

    def _start_worker(self, wid: int) -> WorkerHandle:
        """
        Start a new Worker process and register it.
        Does not hold self._lock (registry.add uses its own lock).
        Passes lifecycle hooks to the Worker process.
        """
        # Serialize hooks for this Worker
        on_start = self._serialize_hooks(WorkerEvent.WORKER_START)
        on_stop = self._serialize_hooks(WorkerEvent.WORKER_STOP)
        on_task_start = self._serialize_hooks(WorkerEvent.TASK_START)
        on_task_end = self._serialize_hooks(WorkerEvent.TASK_END)

        p = self._ctx.Process(
            target=_worker_entry,
            args=(
                wid,
                self._task_q,
                self._result_q,
                self._pool_id,
                on_start,
                on_stop,
                on_task_start,
                on_task_end,
            ),
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

    # ── Public: Status Properties ───────────────────────────────────────────

    @property
    def state(self) -> PoolState:
        """Current pool state (RUNNING/DRAINING/STOPPING/KILLING/STOPPED)"""
        return self._state

    @property
    def pool_id(self) -> str:
        """Unique pool identifier"""
        return self._pool_id

    @property
    def n_workers(self) -> int:
        """Configured number of workers"""
        return self._n

    @property
    def alive_workers(self) -> int:
        """Number of currently alive workers"""
        return self._registry.alive_count()

    @property
    def pending_tasks(self) -> int:
        """Number of tasks waiting in queue (approximate, may not be available on all platforms)"""
        try:
            return self._task_q.qsize()
        except NotImplementedError:
            return -1  # Not available on some platforms (e.g., macOS)

    @property
    def in_flight_tasks(self) -> int:
        """Number of tasks currently being executed"""
        with self._lock:
            return len([t for t in self._worker_task.values() if t is not None])

    @property
    def queued_futures(self) -> int:
        """Number of futures waiting for result"""
        with self._lock:
            return len(self._futures)

    def get_stats(self) -> PoolStats:
        """
        Get current pool statistics snapshot.

        Returns:
            PoolStats with current worker, task, queue, time, and memory statistics.
            Note: This is a point-in-time snapshot and may be stale immediately
            after retrieval in a busy pool.
        """
        with self._stats_lock:
            completed = self._tasks_completed
            total_duration = self._total_task_duration
            total_memory = self._total_memory_delta

            return PoolStats(
                total_workers=self._n,
                alive_workers=self._registry.alive_count(),
                worker_restarts=self._worker_restarts,
                worker_crashes=self._worker_crashes,
                tasks_submitted=self._tasks_submitted,
                tasks_completed=completed,
                tasks_failed=self._tasks_failed,
                tasks_orphaned=self._tasks_orphaned,
                tasks_pending=self.pending_tasks,
                tasks_in_flight=self.in_flight_tasks,
                uptime=time.monotonic() - self._start_time,
                total_task_duration=total_duration,
                avg_task_duration=total_duration / completed if completed > 0 else 0.0,
                total_memory_delta=total_memory,
                avg_memory_delta_mb=(total_memory / (1024 * 1024) / completed) if completed > 0 else 0.0,
            )

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check and return status.

        Returns:
            Dictionary containing:
            - healthy: bool - True if pool is healthy
            - state: str - Current pool state
            - alive_workers: int - Number of alive workers
            - dead_workers: int - Number of dead workers
            - pending_tasks: int - Tasks waiting in queue
            - in_flight_tasks: int - Tasks currently executing
            - warnings: List[str] - Warning messages (if any)

        Warnings may include:
        - "High failure rate" - >10% tasks failing
        - "Worker crashes detected" - Workers have crashed
        - "Queue backlog" - Many tasks waiting
        - "Pool not running" - Pool is in shutdown state
        """
        warnings = []

        stats = self.get_stats()

        # Check for warning conditions
        if stats.tasks_submitted > 10:
            failure_rate = stats.tasks_failed / stats.tasks_submitted
            if failure_rate > 0.1:
                warnings.append(f"High failure rate: {failure_rate:.1%}")

        if stats.worker_crashes > 0:
            warnings.append(f"Worker crashes detected: {stats.worker_crashes}")

        if stats.tasks_pending > 100:
            warnings.append(f"Queue backlog: {stats.tasks_pending} tasks waiting")

        if self._state != PoolState.RUNNING:
            warnings.append(f"Pool not running: {self._state.name}")

        dead_workers = stats.total_workers - stats.alive_workers
        healthy = (
            self._state == PoolState.RUNNING
            and stats.alive_workers > 0
            and len(warnings) == 0
        )

        return {
            "healthy": healthy,
            "state": self._state.name,
            "alive_workers": stats.alive_workers,
            "dead_workers": dead_workers,
            "pending_tasks": stats.tasks_pending,
            "in_flight_tasks": stats.tasks_in_flight,
            "warnings": warnings,
        }

    def drain(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all pending and in-flight tasks to complete.

        This method blocks until all submitted tasks have completed
        (successfully or with error), or until timeout expires.

        Args:
            timeout: Maximum time to wait in seconds. None means wait forever.

        Returns:
            True if all tasks completed, False if timeout expired.

        Note:
            This method does NOT prevent new tasks from being submitted.
            For a clean shutdown, use shutdown() instead.
        """
        start = time.monotonic()
        while True:
            with self._lock:
                pending = len(self._futures)
            if pending == 0:
                return True
            if timeout is not None:
                elapsed = time.monotonic() - start
                if elapsed >= timeout:
                    return False
                time.sleep(min(0.1, timeout - elapsed))
            else:
                time.sleep(0.1)

    # ── Public: Hook Management ─────────────────────────────────────────────

    def register_hook(
        self,
        event: WorkerEvent,
        hook: Union[AnyWorkerHook, AnyTaskHook],
        name: Optional[str] = None,
    ) -> str:
        """
        Register a lifecycle hook.

        Hooks can be registered for the following events:
        - WORKER_START: Called when a Worker process starts
        - WORKER_STOP: Called when a Worker process stops
        - TASK_START: Called before each task execution
        - TASK_END: Called after each task execution

        Note: Hooks registered after Pool startup will only affect
        newly started Workers (e.g., after crash recovery).

        Args:
            event: The WorkerEvent to hook into
            hook: Hook function (sync/async) or string path "module.function"
            name: Optional name for the hook (for later unregistration)

        Returns:
            Hook name (generated if not provided)

        Example:
            pool.register_hook(WorkerEvent.WORKER_START, init_db, "db_init")
            pool.register_hook(WorkerEvent.TASK_END, log_task, "task_logger")
        """
        if name is None:
            name = f"hook_{len(self._hooks[event])}"

        self._hooks[event].append((name, hook))
        logger.debug(
            "Registered hook | event=%s, name=%s, hook_type=%s",
            event.name, name, type(hook).__name__
        )
        return name

    def unregister_hook(self, event: WorkerEvent, name: str) -> bool:
        """
        Unregister a lifecycle hook.

        Note: Unregistering hooks after Pool startup will only affect
        newly started Workers. Running Workers retain their original hooks.

        Args:
            event: The WorkerEvent the hook was registered for
            name: The hook name (returned by register_hook)

        Returns:
            True if hook was found and removed, False otherwise
        """
        hooks = self._hooks[event]
        for i, (hook_name, _) in enumerate(hooks):
            if hook_name == name:
                hooks.pop(i)
                logger.debug("Unregistered hook | event=%s, name=%s", event.name, name)
                return True
        logger.debug("Hook not found | event=%s, name=%s", event.name, name)
        return False

    def get_hooks(self, event: WorkerEvent) -> List[Tuple[str, Union[AnyWorkerHook, AnyTaskHook]]]:
        """
        Get all registered hooks for an event.

        Args:
            event: The WorkerEvent to get hooks for

        Returns:
            List of (name, hook) tuples
        """
        return list(self._hooks.get(event, []))

    # ── Internal: Worker Health Check ───────────────────────────────────────

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
                with self._stats_lock:
                    self._worker_crashes += 1
            else:
                logger.log(
                    log_level,
                    "Worker-%d (pid=%s) exited (exit=%s), no task was in progress",
                    wid, handle.pid, exit_reason
                )
                # Count as crash only if non-normal exit
                if exitcode != 0:
                    with self._stats_lock:
                        self._worker_crashes += 1

            # Restart only if RUNNING
            if self._state == PoolState.RUNNING:
                new_handle = self._start_worker(wid)
                with self._stats_lock:
                    self._worker_restarts += 1
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

        # Handle new Worker lifecycle messages
        if kind == "__worker_ready__":
            # Worker successfully initialized (WORKER_START hooks passed)
            _, wid, pid = msg
            logger.info(
                "Worker-%d ready (pid=%d) | hooks initialized successfully",
                wid, pid
            )
            return

        if kind == "__worker_init_failed__":
            # Worker initialization failed (WORKER_START hook threw exception)
            _, wid, error, tb = msg
            logger.error(
                "Worker-%d initialization failed | error=%s\n%s",
                wid, error, tb
            )
            # Worker will not start, no need to track it
            # _check_workers will detect it as dead and may attempt restart
            return

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
            _, task_id, value, worker_id, start_time, end_time, memory_start, memory_end = msg
            self._clear_worker_task(task_id)
            handle = self._registry.get(worker_id) if worker_id is not None else None
            pid = handle.pid if handle else None
            with self._lock:
                fut = self._futures.pop(task_id, None)
                self._task_enqueue_time.pop(task_id, None)  # Defensive cleanup
            if fut:  # pragma: no cover - Future may already be removed due to timeout
                fut._resolve(value, worker_id, start_time, end_time, memory_start, memory_end)
                duration = end_time - start_time if end_time and start_time else 0
                memory_delta = memory_end - memory_start if memory_end and memory_start else 0
                with self._stats_lock:
                    self._tasks_completed += 1
                    self._total_task_duration += duration
                    self._total_memory_delta += memory_delta
                logger.debug(
                    "Task[%s] completed | Worker-%d (pid=%s) | duration=%.3fs",
                    task_id[:8], worker_id, pid, duration
                )

        elif kind == "error":
            _, task_id, exc, tb, worker_id, start_time, end_time, memory_start, memory_end = msg
            self._clear_worker_task(task_id)
            handle = self._registry.get(worker_id) if worker_id is not None else None
            pid = handle.pid if handle else None
            with self._lock:
                fut = self._futures.pop(task_id, None)
                self._task_enqueue_time.pop(task_id, None)  # Defensive cleanup
            if fut:  # pragma: no cover - Future may already be removed due to timeout
                fut._reject(exc, tb, worker_id, start_time, end_time, memory_start, memory_end)
                with self._stats_lock:
                    self._tasks_failed += 1
                logger.warning(
                    "Task[%s] failed | Worker-%d (pid=%s) | error=%s: %s",
                    task_id[:8], worker_id, pid, type(exc).__name__, exc
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
                with self._stats_lock:
                    self._tasks_orphaned += 1

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
        with self._stats_lock:
            self._tasks_submitted += 1
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
    def active_workers(self) -> int:
        """Number of alive Worker processes"""
        return self._registry.alive_count()

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
