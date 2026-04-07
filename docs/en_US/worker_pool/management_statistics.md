# Management & Statistics

WorkerPool provides rich runtime status query and statistics capabilities for monitoring and debugging.

## Status Properties

```python
with WorkerPool(n_workers=4) as pool:
    # Basic status
    print(f"State: {pool.state.name}")           # RUNNING
    print(f"Pool ID: {pool.pool_id}")            # Unique identifier
    print(f"Workers: {pool.alive_workers}/{pool.n_workers}")

    # Task status
    print(f"Pending tasks: {pool.pending_tasks}")      # Waiting in queue
    print(f"In-flight tasks: {pool.in_flight_tasks}")  # Currently executing
    print(f"Queued futures: {pool.queued_futures}")    # Waiting for result
```

| Property | Description |
|----------|-------------|
| `state` | Pool state (RUNNING/DRAINING/STOPPING/KILLING/STOPPED) |
| `pool_id` | Pool unique identifier |
| `n_workers` | Configured number of workers |
| `alive_workers` | Number of alive workers |
| `pending_tasks` | Tasks waiting in queue (approximate) |
| `in_flight_tasks` | Tasks currently executing |
| `queued_futures` | Futures waiting for result |

## Statistics

```python
stats = pool.get_stats()

print(f"Tasks: {stats.tasks_submitted} submitted, "
      f"{stats.tasks_completed} completed, "
      f"{stats.tasks_failed} failed")

print(f"Workers: {stats.worker_crashes} crashes, "
      f"{stats.worker_restarts} restarts")

print(f"Avg duration: {stats.avg_task_duration:.3f}s")
print(f"Avg memory: {stats.avg_memory_delta_mb:.3f}MB")
print(f"Uptime: {stats.uptime:.1f}s")
```

### PoolStats Fields

| Field | Description |
|-------|-------------|
| `total_workers` | Configured number of workers |
| `alive_workers` | Number of alive workers |
| `worker_restarts` | Worker restart count |
| `worker_crashes` | Worker crash count |
| `tasks_submitted` | Total tasks submitted |
| `tasks_completed` | Successfully completed tasks |
| `tasks_failed` | Failed tasks |
| `tasks_orphaned` | Orphaned tasks (lost due to worker crash) |
| `tasks_pending` | Tasks waiting |
| `tasks_in_flight` | Tasks executing |
| `uptime` | Pool uptime in seconds |
| `total_task_duration` | Sum of all task durations |
| `avg_task_duration` | Average task duration |
| `total_memory_delta` | Total memory delta in bytes |
| `avg_memory_delta_mb` | Average memory delta in MB |

## Health Check

```python
health = pool.health_check()

if not health["healthy"]:
    print(f"Pool unhealthy: {health['state']}")
    for warning in health["warnings"]:
        print(f"  - {warning}")
else:
    print(f"Pool healthy: {health['alive_workers']} workers active")
```

Return fields:

| Field | Description |
|-------|-------------|
| `healthy` | Whether healthy |
| `state` | Current state |
| `alive_workers` | Alive worker count |
| `dead_workers` | Dead worker count |
| `pending_tasks` | Pending task count |
| `in_flight_tasks` | In-flight task count |
| `warnings` | Warning messages list |

**Warning conditions**:

- High failure rate (>10% tasks failing)
- Worker crashes detected
- Queue backlog (>100 tasks waiting)
- Pool not in running state

## Wait for Completion

```python
# Submit all tasks
futures = [pool.submit(process, i) for i in range(1000)]

# Wait for all tasks to complete, max 60 seconds
if pool.drain(timeout=60):
    print("All tasks completed")
else:
    print(f"Timeout, {pool.queued_futures} tasks still pending")
```

## Future Execution Metadata

After task completion, the `Future` object contains detailed execution metadata:

```python
future = pool.submit(process_data, data)
result = future.result(timeout=30)

# Execution metadata
print(f"Worker: {future.worker_id}")
print(f"Duration: {future.duration:.3f}s")
print(f"Memory delta: {future.memory_delta_mb:.3f}MB")
print(f"Start time: {future.start_time}")
print(f"End time: {future.end_time}")
```

| Property | Description |
|----------|-------------|
| `worker_id` | Worker ID that executed the task |
| `start_time` | Task start timestamp |
| `end_time` | Task end timestamp |
| `duration` | Task duration in seconds |
| `memory_start` | Memory at start in bytes |
| `memory_end` | Memory at end in bytes |
| `memory_delta` | Memory delta in bytes |
| `memory_delta_mb` | Memory delta in MB |
