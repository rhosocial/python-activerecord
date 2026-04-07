# API Reference

## WorkerPool

```python
class WorkerPool:
    """
    Spawn-mode Resident Worker Pool with Graceful Shutdown.

    Worker processes start once and stay resident.
    Tasks dispatched via Queue, results captured via Future.
    Worker crash triggers automatic restart.
    Three-phase shutdown: DRAINING → STOPPING → KILLING → STOPPED.
    Supports lifecycle hooks and resource monitoring.
    """

    def __init__(
        self,
        n_workers: int = 4,
        check_interval: float = 0.5,
        orphan_timeout: Optional[float] = None,
        on_worker_start: Optional[AnyWorkerHook] = None,
        on_worker_stop: Optional[AnyWorkerHook] = None,
        on_task_start: Optional[AnyTaskHook] = None,
        on_task_end: Optional[AnyTaskHook] = None,
    ):
        """
        Initialize WorkerPool.

        Args:
            n_workers: Number of worker processes
            check_interval: Interval for supervisor to check worker health
            orphan_timeout: Orphan task detection timeout
            on_worker_start: Worker startup hook
            on_worker_stop: Worker exit hook
            on_task_start: Task start hook
            on_task_end: Task end hook
        """

    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit a task, immediately return Future."""

    def map(self, fn: Callable, iterable, timeout: Optional[float] = None) -> list:
        """Batch submit, collect results in order."""

    def shutdown(
        self,
        graceful_timeout: float = 10.0,
        term_timeout: float = 3.0,
    ) -> ShutdownReport:
        """Three-phase graceful shutdown."""

    def register_hook(
        self,
        event: WorkerEvent,
        hook: Union[AnyWorkerHook, AnyTaskHook],
        name: Optional[str] = None,
    ) -> str:
        """Register lifecycle hook, returns hook name."""

    def unregister_hook(self, event: WorkerEvent, name: str) -> bool:
        """Unregister hook, returns whether successful."""

    def get_hooks(self, event: WorkerEvent) -> List[Tuple[str, Union[AnyWorkerHook, AnyTaskHook]]]:
        """Get all hooks for specified event."""

    def get_stats(self) -> PoolStats:
        """Get current statistics snapshot."""

    def health_check(self) -> Dict[str, Any]:
        """Perform health check, returns status dict."""

    def drain(self, timeout: Optional[float] = None) -> bool:
        """Wait for all tasks to complete."""

    # Status properties
    @property
    def state(self) -> PoolState:
        """Current Pool state"""

    @property
    def pool_id(self) -> str:
        """Pool unique identifier"""

    @property
    def n_workers(self) -> int:
        """Configured number of workers"""

    @property
    def alive_workers(self) -> int:
        """Number of alive workers"""

    @property
    def ready_workers(self) -> int:
        """Number of workers that completed initialization and are ready to process tasks.

        Unlike alive_workers, ready_workers only counts Workers that have sent the
        __worker_ready__ message. A Worker process must complete WORKER_START hooks
        before sending the ready signal. This helps distinguish between "process has
        started" and "process is ready to handle tasks".
        """

    @property
    def pending_tasks(self) -> int:
        """Tasks waiting in queue"""

    @property
    def in_flight_tasks(self) -> int:
        """Tasks currently executing"""

    @property
    def queued_futures(self) -> int:
        """Futures waiting for result"""
```

## PoolState

```python
class PoolState(Enum):
    """Pool state machine (shutdown flow)."""
    RUNNING = auto()   # Normal operation, accepting tasks
    DRAINING = auto()  # Rejecting new tasks, waiting for in-flight
    STOPPING = auto()  # SIGTERM sent
    KILLING = auto()   # SIGKILL being sent
    STOPPED = auto()   # All processes terminated
```

## WorkerEvent

```python
class WorkerEvent(Enum):
    """Worker lifecycle events."""
    WORKER_START = auto()  # Worker process starts
    WORKER_STOP = auto()   # Worker process exits
    TASK_START = auto()    # Before task execution
    TASK_END = auto()      # After task execution
```

## PoolStats

```python
@dataclass
class PoolStats:
    """Pool execution statistics snapshot."""
    # Worker statistics
    total_workers: int = 0
    alive_workers: int = 0
    worker_restarts: int = 0
    worker_crashes: int = 0

    # Task statistics
    tasks_submitted: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_orphaned: int = 0

    # Queue statistics
    tasks_pending: int = 0
    tasks_in_flight: int = 0

    # Time statistics
    uptime: float = 0.0
    total_task_duration: float = 0.0
    avg_task_duration: float = 0.0

    # Memory statistics
    total_memory_delta: int = 0
    avg_memory_delta_mb: float = 0.0
```

## WorkerContext

```python
@dataclass
class WorkerContext:
    """Context passed to worker-level hooks."""
    worker_id: int        # Worker index
    pid: int              # Process ID
    pool_id: str          # Pool instance identifier
    start_time: float     # Worker start time
    task_count: int       # Tasks executed
```

## TaskContext

```python
@dataclass
class TaskContext:
    """Context passed to task-level hooks."""
    task_id: str
    worker_ctx: WorkerContext
    fn_name: str
    args: Tuple
    kwargs: Dict[str, Any]
    start_time: float
    end_time: float
    success: bool
    result: Any
    error: Optional[Exception]
    memory_start: int
    memory_end: int

    @property
    def duration(self) -> float:
        """Task duration in seconds"""

    @property
    def memory_delta(self) -> int:
        """Memory delta in bytes"""

    @property
    def memory_delta_mb(self) -> float:
        """Memory delta in MB"""

    def log_summary(self, logger, level=logging.INFO) -> None:
        """Log task execution summary"""
```

## ShutdownReport

```python
@dataclass
class ShutdownReport:
    """Return value of shutdown(), describes shutdown process."""
    duration: float          # Total shutdown time in seconds
    final_phase: str         # Phase where shutdown completed
    tasks_in_flight: int     # Tasks in progress when shutdown started
    tasks_killed: int        # Workers with tasks when SIGKILL sent
    workers_killed: int      # Workers killed by SIGKILL
```

## Exceptions

```python
class PoolDrainingError(RuntimeError):
    """Pool is in shutdown flow, no new tasks accepted."""

class TaskTimeoutError(TimeoutError):
    """Task execution timed out."""

class WorkerCrashedError(RuntimeError):
    """Worker process crashed, task could not complete."""
```

## Future

```python
class Future:
    """Async result handle with execution metadata."""

    def result(self, timeout: Optional[float] = None) -> Any:
        """Block and wait for result."""

    @property
    def done(self) -> bool:
        """Whether task has completed"""

    @property
    def succeeded(self) -> bool:
        """Whether task succeeded"""

    @property
    def failed(self) -> bool:
        """Whether task failed"""

    @property
    def traceback(self) -> Optional[str]:
        """Traceback string when task failed"""

    # Execution metadata
    @property
    def worker_id(self) -> Optional[int]:
        """Worker ID that executed the task"""

    @property
    def start_time(self) -> Optional[float]:
        """Task start timestamp"""

    @property
    def end_time(self) -> Optional[float]:
        """Task end timestamp"""

    @property
    def duration(self) -> float:
        """Task duration in seconds"""

    @property
    def memory_start(self) -> int:
        """Memory at task start in bytes"""

    @property
    def memory_end(self) -> int:
        """Memory at task end in bytes"""

    @property
    def memory_delta(self) -> int:
        """Memory delta in bytes"""

    @property
    def memory_delta_mb(self) -> float:
        """Memory delta in MB"""
```
