# 最佳实践与常见陷阱

## 最佳实践

### Worker 进程池生命周期

**不要频繁创建和销毁 WorkerPool 实例。**

进程管理开销很大。每次创建 WorkerPool 都涉及：
- 生成多个 Worker 进程
- 设置进程间队列
- 启动监督线程

```python
# 错误：为每批任务创建进程池
for batch in batches:
    with WorkerPool(n_workers=4) as pool:
        futures = [pool.submit(task, item) for item in batch]
        results = [f.result() for f in futures]
    # 进程池销毁，Worker 被杀死，资源释放
    # 然后为下一批重新创建 - 浪费！

# 正确：一个进程池处理所有工作
with WorkerPool(n_workers=4) as pool:
    for batch in batches:
        futures = [pool.submit(task, item) for item in batch]
        results = [f.result() for f in futures]
        # 进程池持久存在，Worker 保持存活
```

**建议**：在应用启动时创建一次进程池，复用处理所有任务，仅在应用退出时关闭。

### 连接管理策略

处理数据库连接时，选择 **Worker 级** 或 **任务级** 管理——**绝不要混用**。

| 策略 | 钩子对 | 适用场景 |
|------|--------|----------|
| **Worker 级** | `WORKER_START` + `WORKER_STOP` | 高频短操作 |
| **任务级** | `TASK_START` + `TASK_END` | 低频长操作 |

```python
# ✅ 正确：Worker 级连接（两个钩子都在 Worker 级）
with WorkerPool(
    on_worker_start=init_db,      # 连接一次
    on_worker_stop=cleanup_db,    # 断开一次
) as pool:
    # 所有任务共享同一个连接
    pass

# ✅ 正确：任务级连接（两个钩子都在任务级）
with WorkerPool(
    on_task_start=task_connect,    # 每个任务连接
    on_task_end=task_disconnect,   # 每个任务断开
) as pool:
    # 每个任务有自己的连接
    pass

# ❌ 错误：混合级别（Worker 级连接，任务级断开）
with WorkerPool(
    on_worker_start=init_db,       # Worker 启动时连接
    on_task_end=task_disconnect,   # 任务结束时断开 - 不匹配！
) as pool:
    # 这会导致连接泄漏或错误
    pass
```

### 选择连接策略

| 场景 | 建议 | 原因 |
|------|------|------|
| **高频短操作** | Worker 级 | 连接复用减少开销；开销分摊到多个任务 |
| **低频长操作** | 任务级 | 及时释放连接；无长期占用的空闲连接 |
| **混合负载** | 分离进程池 | 对不同任务类型使用不同策略的独立进程池 |

**决策指南**：

```
每个 Worker 每分钟任务数：
├── > 100 任务/分钟  → Worker 级（连接开销可忽略）
├── 10-100 任务/分钟 → 两者皆可（考虑连接池限制）
└── < 10 任务/分钟   → 任务级（避免连接空闲占用）
```

### 连接生命周期

在任务函数中始终遵循此模式：

```python
def task(params):
    # 1. 开始时配置
    Model.configure(config, Backend)

    try:
        # 2. 执行工作
        return result
    finally:
        # 3. 始终断开连接
        Model.backend().disconnect()
```

### 事务管理

保持事务简短和专注：

```python
# 正确：单一、专注的事务
with Model.transaction():
    record = Model.find_one(id)
    record.status = 'processed'
    record.save()

# 错误：多个事务，边界不清晰
with Model.transaction():
    record = Model.find_one(id)
# 事务已结束，但你还在工作...
record.status = 'processed'  # 不在事务中！
record.save()
```

### Worker 数量选择

| 场景 | 建议 |
|------|------|
| CPU 密集型任务 | `n_workers = cpu_count()` |
| I/O 密集型任务 | `n_workers = 2 * cpu_count()` |
| 数据库密集型 | `n_workers ≤ max_db_connections - 5`（保留管理连接） |
| 混合负载 | 从 `n_workers = cpu_count()` 开始，根据监控调整 |

### 优雅停机最佳实践

三段式停机确保任务优雅完成，同时防止无限等待：

```python
# 推荐：让上下文管理器处理停机
with WorkerPool(n_workers=4) as pool:
    futures = [pool.submit(task, i) for i in range(100)]
    results = [f.result() for f in futures]
# 上下文退出触发停机，使用默认超时

# 手动停机，自定义超时
pool = WorkerPool(n_workers=4)
# ... 提交任务 ...
report = pool.shutdown(graceful_timeout=30.0, term_timeout=5.0)
print(f"停机耗时 {report.duration:.2f}s，通过 {report.final_phase} 阶段完成")
```

**理解各阶段**：

| 阶段 | 信号 | 行为 | 用途 |
|------|------|------|------|
| DRAINING | STOP 哨兵 | Worker 完成当前任务后退出 | 正常停机 |
| STOPPING | SIGTERM | 立即终止（Python 默认） | 优雅超时已过 |
| KILLING | SIGKILL | 无法捕获，进程立即死亡 | TERM 超时已过 |

**STOP 哨兵与 SIGTERM 的关键区别**：

- **STOP 哨兵**：队列级别的礼貌请求。Worker 完成当前任务，然后读取哨兵并自愿退出。
- **SIGTERM**：操作系统级信号。Python 默认处理程序立即退出，中断当前任务。

```python
# 检查停机是否干净
report = pool.shutdown()
if report.final_phase != "graceful":
    print(f"警告: {report.tasks_killed} 个任务被强制终止")
```

---

## 常见陷阱

### 陷阱 1：局部函数定义

```python
# 错误：嵌套函数无法被 pickle
def main():
    def my_task(ctx, n):  # 即使签名正确，局部函数也无法 pickle
        return n * 2

    with WorkerPool() as pool:
        pool.submit(my_task, 5)  # PicklingError!

# 正确：模块级函数
def my_task(ctx: TaskContext, n: int) -> int:
    return n * 2

def main():
    with WorkerPool() as pool:
        pool.submit(my_task, 5)  # 正常
```

### 陷阱 2：传递模型实例

```python
# 错误：模型实例可能无法正确序列化
user = User.find_one(1)
pool.submit(process_user, user)  # 可能失败

# 正确：传递 ID，让任务获取记录
pool.submit(process_user, user.id)

def process_user(ctx: TaskContext, user_id: int):
    User.configure(config, Backend)
    try:
        user = User.find_one(user_id)
        # ... 处理
    finally:
        User.backend().disconnect()
```

### 陷阱 3：忘记断开连接

```python
# 错误：连接泄漏
def my_task(ctx: TaskContext, params):
    Model.configure(config, Backend)
    return Model.find_one(params['id'])
    # 连接从未关闭！

# 正确：始终使用 try/finally
def my_task(ctx: TaskContext, params):
    Model.configure(config, Backend)
    try:
        return Model.find_one(params['id'])
    finally:
        Model.backend().disconnect()
```

### 陷阱 4：在任务外部配置

```python
# 错误：在主进程配置，不在 Worker 中
Model.configure(config, Backend)

def my_task(ctx: TaskContext, params):
    # Worker 没有这个配置！
    return Model.find_one(params['id'])

# 正确：在任务内部配置
def my_task(ctx: TaskContext, params):
    Model.configure(config, Backend)
    try:
        return Model.find_one(params['id'])
    finally:
        Model.backend().disconnect()
```

### 陷阱 5：忽略 Worker 崩溃

```python
# 错误：不处理崩溃
future = pool.submit(risky_task, params)
result = future.result()  # Worker 崩溃时可能抛出 RuntimeError

# 正确：优雅处理崩溃
future = pool.submit(risky_task, params)
try:
    result = future.result(timeout=30)
except RuntimeError as e:
    if "crashed" in str(e):
        print(f"Worker 崩溃: {e}")
        # 重试或适当处理
    else:
        raise
```

### 陷阱 6：使用 os._exit() 导致队列状态损坏

```python
# 错误：使用 os._exit() 损坏 multiprocessing.Queue 状态
def crash_task(ctx: TaskContext):
    import os
    os._exit(1)  # 绕过正常清理，可能损坏共享队列

# 为什么这是问题？
# os._exit() 立即终止进程，绕过 Python 的正常清理机制。
# 这可能导致共享的 multiprocessing.Queue 管道状态损坏，
# 阻止重启的 Worker 通过该队列通信。

# 如果需要模拟崩溃（例如测试），请注意：
# 1. os._exit() 损坏队列状态
# 2. 信号（SIGKILL/SIGTERM）有类似问题
# 3. 实际的段错误通常不会以同样的方式损坏队列

# 正确：让任务正常完成或抛出异常
def task_with_error(ctx: TaskContext):
    raise RuntimeError("任务失败")  # Worker 正常捕获和处理
```

**技术细节**：

WorkerPool 的孤儿任务检测机制需要区分：

- Worker 进程已启动但尚未完成初始化
- Worker 已准备好处理任务

新启动的 Worker 在发送 `__worker_ready__` 消息之前不会计入 `ready_workers`。如果 `os._exit()` 导致 Worker 异常终止，队列管道可能损坏，重启的 Worker 无法发送就绪消息，导致 `ready_workers` 计数永远无法恢复。

---

## 总结

`WorkerPool` 模块为并行任务执行提供了简单、可靠的基础。遵循以下准则：

1. 编写独立的模块级任务函数
2. 在每个任务内管理连接
3. 合理使用事务
4. 始终在 `finally` 中清理连接
5. 传递可序列化数据（ID，而非模型实例）

您可以构建与 `rhosocial-activerecord` 无缝集成的健壮并行处理工作流。
