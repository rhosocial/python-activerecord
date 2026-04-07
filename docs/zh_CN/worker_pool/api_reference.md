# API 参考

## WorkerPool

```python
class WorkerPool:
    """
    Spawn 模式驻留 Worker 进程池，支持优雅停机。

    Worker 进程启动后保持驻留。
    任务通过队列分发，结果通过 Future 收集。
    Worker 崩溃触发自动重启。
    三段式停机：DRAINING → STOPPING → KILLING → STOPPED。
    支持生命周期钩子和资源监控。
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
        初始化 WorkerPool。

        参数:
            n_workers: Worker 进程数量
            check_interval: 监督器检查 Worker 健康的间隔
            orphan_timeout: 孤儿任务检测超时
            on_worker_start: Worker 启动钩子
            on_worker_stop: Worker 退出钩子
            on_task_start: 任务开始钩子
            on_task_end: 任务结束钩子
        """

    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        """提交任务，立即返回 Future。"""

    def map(self, fn: Callable, iterable, timeout: Optional[float] = None) -> list:
        """批量提交，按顺序收集结果。"""

    def shutdown(
        self,
        graceful_timeout: float = 10.0,
        term_timeout: float = 3.0,
    ) -> ShutdownReport:
        """三段式优雅停机。"""

    def register_hook(
        self,
        event: WorkerEvent,
        hook: Union[AnyWorkerHook, AnyTaskHook],
        name: Optional[str] = None,
    ) -> str:
        """注册生命周期钩子，返回钩子名称。"""

    def unregister_hook(self, event: WorkerEvent, name: str) -> bool:
        """注销钩子，返回是否成功。"""

    def get_hooks(self, event: WorkerEvent) -> List[Tuple[str, Union[AnyWorkerHook, AnyTaskHook]]]:
        """获取指定事件的所有钩子。"""

    def get_stats(self) -> PoolStats:
        """获取当前统计快照。"""

    def health_check(self) -> Dict[str, Any]:
        """执行健康检查，返回状态字典。"""

    def drain(self, timeout: Optional[float] = None) -> bool:
        """等待所有任务完成。"""

    # 状态属性
    @property
    def state(self) -> PoolState:
        """当前进程池状态"""

    @property
    def pool_id(self) -> str:
        """进程池唯一标识"""

    @property
    def n_workers(self) -> int:
        """配置的 Worker 数量"""

    @property
    def alive_workers(self) -> int:
        """存活的 Worker 数量"""

    @property
    def ready_workers(self) -> int:
        """已完成初始化并准备好处理任务的 Worker 数量。

        与 alive_workers 不同，ready_workers 只计数已发送
        __worker_ready__ 消息的 Worker。Worker 进程必须完成 WORKER_START 钩子
        后才发送就绪信号。这有助于区分"进程已启动"和"进程已准备好处理任务"。
        """

    @property
    def pending_tasks(self) -> int:
        """队列中等待的任务"""

    @property
    def in_flight_tasks(self) -> int:
        """正在执行的任务"""

    @property
    def queued_futures(self) -> int:
        """等待结果的 Future"""
```

## PoolState

```python
class PoolState(Enum):
    """进程池状态机（停机流程）。"""
    RUNNING = auto()   # 正常运行，接受任务
    DRAINING = auto()  # 拒绝新任务，等待执行中的任务完成
    STOPPING = auto()  # 已发送 SIGTERM
    KILLING = auto()   # 正在发送 SIGKILL
    STOPPED = auto()   # 所有进程已终止
```

## WorkerEvent

```python
class WorkerEvent(Enum):
    """Worker 生命周期事件。"""
    WORKER_START = auto()  # Worker 进程启动
    WORKER_STOP = auto()   # Worker 进程退出
    TASK_START = auto()    # 任务执行前
    TASK_END = auto()      # 任务执行后
```

## PoolStats

```python
@dataclass
class PoolStats:
    """进程池执行统计快照。"""
    # Worker 统计
    total_workers: int = 0
    alive_workers: int = 0
    worker_restarts: int = 0
    worker_crashes: int = 0

    # 任务统计
    tasks_submitted: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    tasks_orphaned: int = 0

    # 队列统计
    tasks_pending: int = 0
    tasks_in_flight: int = 0

    # 时间统计
    uptime: float = 0.0
    total_task_duration: float = 0.0
    avg_task_duration: float = 0.0

    # 内存统计
    total_memory_delta: int = 0
    avg_memory_delta_mb: float = 0.0
```

## WorkerContext

```python
@dataclass
class WorkerContext:
    """传递给 Worker 级钩子的上下文。"""
    worker_id: int        # Worker 索引
    pid: int              # 进程 ID
    pool_id: str          # 进程池实例标识
    start_time: float     # Worker 启动时间
    task_count: int       # 已执行任务数
```

## TaskContext

```python
@dataclass
class TaskContext:
    """传递给任务级钩子的上下文。"""
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
        """任务耗时（秒）"""

    @property
    def memory_delta(self) -> int:
        """内存增量（字节）"""

    @property
    def memory_delta_mb(self) -> float:
        """内存增量（MB）"""

    def log_summary(self, logger, level=logging.INFO) -> None:
        """记录任务执行摘要"""
```

## ShutdownReport

```python
@dataclass
class ShutdownReport:
    """shutdown() 的返回值，描述停机过程。"""
    duration: float          # 总停机时间（秒）
    final_phase: str         # 停机完成的阶段
    tasks_in_flight: int     # 停机开始时执行中的任务
    tasks_killed: int        # 发送 SIGKILL 时有任务的 Worker
    workers_killed: int      # 被 SIGKILL 杀死的 Worker
```

## 异常

```python
class PoolDrainingError(RuntimeError):
    """进程池正在停机，不接受新任务。"""

class TaskTimeoutError(TimeoutError):
    """任务执行超时。"""

class WorkerCrashedError(RuntimeError):
    """Worker 进程崩溃，任务无法完成。"""
```

## Future

```python
class Future:
    """带执行元数据的异步结果句柄。"""

    def result(self, timeout: Optional[float] = None) -> Any:
        """阻塞等待结果。"""

    @property
    def done(self) -> bool:
        """任务是否已完成"""

    @property
    def succeeded(self) -> bool:
        """任务是否成功"""

    @property
    def failed(self) -> bool:
        """任务是否失败"""

    @property
    def traceback(self) -> Optional[str]:
        """任务失败时的堆栈追踪字符串"""

    # 执行元数据
    @property
    def worker_id(self) -> Optional[int]:
        """执行任务的 Worker ID"""

    @property
    def start_time(self) -> Optional[float]:
        """任务开始时间戳"""

    @property
    def end_time(self) -> Optional[float]:
        """任务结束时间戳"""

    @property
    def duration(self) -> float:
        """任务耗时（秒）"""

    @property
    def memory_start(self) -> int:
        """任务开始时内存（字节）"""

    @property
    def memory_end(self) -> int:
        """任务结束时内存（字节）"""

    @property
    def memory_delta(self) -> int:
        """内存增量（字节）"""

    @property
    def memory_delta_mb(self) -> float:
        """内存增量（MB）"""
```
