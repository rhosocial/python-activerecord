# 管理与统计

WorkerPool 提供丰富的运行时状态查询和统计功能，用于监控和调试。

## 状态属性

```python
with WorkerPool(n_workers=4) as pool:
    # 基本状态
    print(f"状态: {pool.state.name}")           # RUNNING
    print(f"进程池 ID: {pool.pool_id}")         # 唯一标识
    print(f"Worker 数: {pool.alive_workers}/{pool.n_workers}")

    # 任务状态
    print(f"待处理任务: {pool.pending_tasks}")      # 队列中等待
    print(f"执行中任务: {pool.in_flight_tasks}")    # 正在执行
    print(f"排队 Future: {pool.queued_futures}")    # 等待结果
```

| 属性 | 描述 |
|------|------|
| `state` | 进程池状态（RUNNING/DRAINING/STOPPING/KILLING/STOPPED） |
| `pool_id` | 进程池唯一标识 |
| `n_workers` | 配置的 Worker 数量 |
| `alive_workers` | 存活的 Worker 数量 |
| `pending_tasks` | 队列中等待的任务（近似值） |
| `in_flight_tasks` | 正在执行的任务 |
| `queued_futures` | 等待结果的 Future |

## 统计信息

```python
stats = pool.get_stats()

print(f"任务: {stats.tasks_submitted} 已提交, "
      f"{stats.tasks_completed} 已完成, "
      f"{stats.tasks_failed} 失败")

print(f"Worker: {stats.worker_crashes} 崩溃, "
      f"{stats.worker_restarts} 重启")

print(f"平均耗时: {stats.avg_task_duration:.3f}s")
print(f"平均内存: {stats.avg_memory_delta_mb:.3f}MB")
print(f"运行时间: {stats.uptime:.1f}s")
```

### PoolStats 字段

| 字段 | 描述 |
|------|------|
| `total_workers` | 配置的 Worker 数量 |
| `alive_workers` | 存活的 Worker 数量 |
| `worker_restarts` | Worker 重启次数 |
| `worker_crashes` | Worker 崩溃次数 |
| `tasks_submitted` | 提交的任务总数 |
| `tasks_completed` | 成功完成的任务数 |
| `tasks_failed` | 失败的任务数 |
| `tasks_orphaned` | 孤儿任务（因 Worker 崩溃丢失） |
| `tasks_pending` | 等待中的任务 |
| `tasks_in_flight` | 执行中的任务 |
| `uptime` | 进程池运行时间（秒） |
| `total_task_duration` | 所有任务耗时总和 |
| `avg_task_duration` | 平均任务耗时 |
| `total_memory_delta` | 总内存增量（字节） |
| `avg_memory_delta_mb` | 平均内存增量（MB） |

## 健康检查

```python
health = pool.health_check()

if not health["healthy"]:
    print(f"进程池不健康: {health['state']}")
    for warning in health["warnings"]:
        print(f"  - {warning}")
else:
    print(f"进程池健康: {health['alive_workers']} 个 Worker 活跃")
```

返回字段：

| 字段 | 描述 |
|------|------|
| `healthy` | 是否健康 |
| `state` | 当前状态 |
| `alive_workers` | 存活的 Worker 数量 |
| `dead_workers` | 已死亡的 Worker 数量 |
| `pending_tasks` | 待处理任务数 |
| `in_flight_tasks` | 执行中任务数 |
| `warnings` | 警告消息列表 |

**警告条件**：

- 高失败率（>10% 任务失败）
- 检测到 Worker 崩溃
- 队列积压（>100 任务等待）
- 进程池不在运行状态

## 等待完成

```python
# 提交所有任务
futures = [pool.submit(process, i) for i in range(1000)]

# 等待所有任务完成，最长 60 秒
if pool.drain(timeout=60):
    print("所有任务已完成")
else:
    print(f"超时，仍有 {pool.queued_futures} 个任务待处理")
```

## Future 执行元数据

任务完成后，`Future` 对象包含详细的执行元数据：

```python
future = pool.submit(process_data, data)
result = future.result(timeout=30)

# 执行元数据
print(f"Worker: {future.worker_id}")
print(f"耗时: {future.duration:.3f}s")
print(f"内存增量: {future.memory_delta_mb:.3f}MB")
print(f"开始时间: {future.start_time}")
print(f"结束时间: {future.end_time}")
```

| 属性 | 描述 |
|------|------|
| `worker_id` | 执行任务的 Worker ID |
| `start_time` | 任务开始时间戳 |
| `end_time` | 任务结束时间戳 |
| `duration` | 任务耗时（秒） |
| `memory_start` | 开始时内存（字节） |
| `memory_end` | 结束时内存（字节） |
| `memory_delta` | 内存增量（字节） |
| `memory_delta_mb` | 内存增量（MB） |
