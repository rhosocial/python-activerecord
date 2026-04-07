# Best Practices & Common Pitfalls

## Best Practices

### Worker Pool Lifecycle

**Do NOT frequently create and destroy WorkerPool instances.**

The process management overhead is significant. Each WorkerPool creation involves:
- Spawning multiple worker processes
- Setting up inter-process queues
- Starting supervisor threads

```python
# BAD: Creating pool for each batch
for batch in batches:
    with WorkerPool(n_workers=4) as pool:
        futures = [pool.submit(task, item) for item in batch]
        results = [f.result() for f in futures]
    # Pool destroyed, workers killed, resources freed
    # Then recreated for next batch - wasteful!

# GOOD: One pool for all work
with WorkerPool(n_workers=4) as pool:
    for batch in batches:
        futures = [pool.submit(task, item) for item in batch]
        results = [f.result() for f in futures]
        # Pool persists, workers stay alive
```

**Recommendation**: Create the pool once at application startup, reuse it for all tasks, and shut it down only when the application exits.

### Connection Management Strategy

When working with database connections, choose **either** Worker-level **or** Task-level management — **never mix them**.

| Strategy | Hook Pair | Use Case |
|----------|-----------|----------|
| **Worker-level** | `WORKER_START` + `WORKER_STOP` | High-frequency, short operations |
| **Task-level** | `TASK_START` + `TASK_END` | Low-frequency, long operations |

```python
# ✅ CORRECT: Worker-level connection (both hooks at worker level)
with WorkerPool(
    on_worker_start=init_db,      # Connect once
    on_worker_stop=cleanup_db,    # Disconnect once
) as pool:
    # All tasks share the same connection
    pass

# ✅ CORRECT: Task-level connection (both hooks at task level)
with WorkerPool(
    on_task_start=task_connect,    # Connect per task
    on_task_end=task_disconnect,   # Disconnect per task
) as pool:
    # Each task has its own connection
    pass

# ❌ WRONG: Mixed levels (connect at worker, disconnect at task)
with WorkerPool(
    on_worker_start=init_db,       # Connect at worker start
    on_task_end=task_disconnect,   # Disconnect at task end - MISMATCH!
) as pool:
    # This will cause connection leaks or errors
    pass
```

### Choosing Connection Strategy

| Scenario | Recommendation | Rationale |
|----------|---------------|-----------|
| **High-frequency, short operations** | Worker-level | Connection reuse reduces overhead; overhead amortized across many tasks |
| **Low-frequency, long operations** | Task-level | Timely release of connections; no long-held idle connections |
| **Mixed workload** | Separate pools | Use different pools with different strategies for different task types |

**Decision guide**:

```
Tasks per minute per worker:
├── > 100 tasks/min  → Worker-level (connection overhead negligible)
├── 10-100 tasks/min → Either works (consider connection pool limits)
└── < 10 tasks/min   → Task-level (avoid holding connections idle)
```

### Connection Lifecycle

Always follow this pattern in task functions:

```python
def task(params):
    # 1. Configure at the start
    Model.configure(config, Backend)

    try:
        # 2. Do work
        return result
    finally:
        # 3. Always disconnect
        Model.backend().disconnect()
```

### Transaction Management

Keep transactions short and focused:

```python
# Good: Single, focused transaction
with Model.transaction():
    record = Model.find_one(id)
    record.status = 'processed'
    record.save()

# Bad: Multiple transactions, unclear boundaries
with Model.transaction():
    record = Model.find_one(id)
# Transaction ended, but you're still working...
record.status = 'processed'  # Not in transaction!
record.save()
```

### Worker Count Selection

| Scenario | Recommendation |
|----------|---------------|
| CPU-bound tasks | `n_workers = cpu_count()` |
| I/O-bound tasks | `n_workers = 2 * cpu_count()` |
| Database-heavy | `n_workers ≤ max_db_connections - 5` (reserve for admin) |
| Mixed workload | Start with `n_workers = cpu_count()`, tune based on monitoring |

### Graceful Shutdown Best Practices

The three-phase shutdown ensures tasks complete gracefully while preventing indefinite hangs:

```python
# Recommended: Let context manager handle shutdown
with WorkerPool(n_workers=4) as pool:
    futures = [pool.submit(task, i) for i in range(100)]
    results = [f.result() for f in futures]
# Context exit triggers shutdown with default timeouts

# Manual shutdown with custom timeouts
pool = WorkerPool(n_workers=4)
# ... submit tasks ...
report = pool.shutdown(graceful_timeout=30.0, term_timeout=5.0)
print(f"Shutdown took {report.duration:.2f}s via {report.final_phase}")
```

**Understanding the phases**:

| Phase | Signal | Behavior | Use Case |
|-------|--------|----------|----------|
| DRAINING | STOP sentinel | Workers complete current task, then exit | Normal shutdown |
| STOPPING | SIGTERM | Immediate termination (Python default) | Graceful timeout expired |
| KILLING | SIGKILL | Cannot be caught, process dies instantly | TERM timeout expired |

**Key difference between STOP sentinel and SIGTERM**:

- **STOP sentinel**: Queue-level polite request. Worker finishes current task, then reads sentinel and exits voluntarily.
- **SIGTERM**: OS-level signal. Python's default handler exits immediately, interrupting the current task.

```python
# Check if shutdown was clean
report = pool.shutdown()
if report.final_phase != "graceful":
    print(f"Warning: {report.tasks_killed} tasks were forcefully terminated")
```

---

## Common Pitfalls

### Pitfall 1: Local Function Definition

```python
# WRONG: Nested function cannot be pickled
def main():
    def my_task(ctx, n):  # Even with correct signature, local functions can't be pickled
        return n * 2

    with WorkerPool() as pool:
        pool.submit(my_task, 5)  # PicklingError!

# CORRECT: Module-level function
def my_task(ctx: TaskContext, n: int) -> int:
    return n * 2

def main():
    with WorkerPool() as pool:
        pool.submit(my_task, 5)  # OK
```

### Pitfall 2: Passing Model Instances

```python
# WRONG: Model instances may not serialize correctly
user = User.find_one(1)
pool.submit(process_user, user)  # May fail

# CORRECT: Pass IDs and let task fetch the record
pool.submit(process_user, user.id)

def process_user(ctx: TaskContext, user_id: int):
    User.configure(config, Backend)
    try:
        user = User.find_one(user_id)
        # ... process
    finally:
        User.backend().disconnect()
```

### Pitfall 3: Forgetting to Disconnect

```python
# WRONG: Connection leak
def my_task(ctx: TaskContext, params):
    Model.configure(config, Backend)
    return Model.find_one(params['id'])
    # Connection never closed!

# CORRECT: Always use try/finally
def my_task(ctx: TaskContext, params):
    Model.configure(config, Backend)
    try:
        return Model.find_one(params['id'])
    finally:
        Model.backend().disconnect()
```

### Pitfall 4: Configuring Outside Task

```python
# WRONG: Configure in main process, not in worker
Model.configure(config, Backend)

def my_task(ctx: TaskContext, params):
    # Worker doesn't have this configuration!
    return Model.find_one(params['id'])

# CORRECT: Configure inside task
def my_task(ctx: TaskContext, params):
    Model.configure(config, Backend)
    try:
        return Model.find_one(params['id'])
    finally:
        Model.backend().disconnect()
```

### Pitfall 5: Ignoring Worker Crashes

```python
# WRONG: Not handling crash
future = pool.submit(risky_task, params)
result = future.result()  # May raise RuntimeError if worker crashed

# CORRECT: Handle crash gracefully
future = pool.submit(risky_task, params)
try:
    result = future.result(timeout=30)
except RuntimeError as e:
    if "crashed" in str(e):
        print(f"Worker crashed: {e}")
        # Retry or handle appropriately
    else:
        raise
```

### Pitfall 6: Using os._exit() Causes Queue State Corruption

```python
# WRONG: Using os._exit() corrupts multiprocessing.Queue state
def crash_task(ctx: TaskContext):
    import os
    os._exit(1)  # Bypasses normal cleanup, may corrupt shared Queue

# Why is this a problem?
# os._exit() immediately terminates the process, bypassing Python's normal
# cleanup mechanisms. This can leave shared multiprocessing.Queue pipe
# state corrupted, preventing restarted Workers from communicating through
# that Queue.

# If you need to simulate a crash (e.g., for testing), be aware:
# 1. os._exit() corrupts Queue state
# 2. Signals (SIGKILL/SIGTERM) have similar issues
# 3. Actual segfaults typically don't corrupt Queue the same way

# CORRECT: Let tasks complete normally or raise exceptions
def task_with_error(ctx: TaskContext):
    raise RuntimeError("Task failed")  # Worker catches and handles normally
```

**Technical Details**:

WorkerPool's orphan task detection mechanism needs to distinguish between:

- Worker process has started but not yet completed initialization
- Worker is ready to process tasks

Newly started Workers are not counted in `ready_workers` until they send the `__worker_ready__` message. If `os._exit()` causes a Worker to terminate abnormally, the Queue pipe may be corrupted, and the restarted Worker won't be able to send the ready message, causing `ready_workers` count to never recover.

---

## Summary

The `WorkerPool` module provides a simple, reliable foundation for parallel task execution. By following these guidelines:

1. Write independent, module-level task functions
2. Manage connections inside each task
3. Use transactions appropriately
4. Always clean up connections in `finally`
5. Pass serializable data (IDs, not model instances)

You can build robust parallel processing workflows that integrate seamlessly with `rhosocial-activerecord`.
