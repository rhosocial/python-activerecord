# WorkerPool Examples

This directory contains runnable examples demonstrating WorkerPool features.

## Files

| File | Description |
|------|-------------|
| [basic_usage.py](./basic_usage.py) | Basic task submission, batch processing, error handling |
| [hooks_usage.py](./hooks_usage.py) | Lifecycle hooks, context sharing, tuple format |
| [connection_management.py](./connection_management.py) | Worker-level vs Task-level connection strategies |
| [async_mode.py](./async_mode.py) | Async hooks and tasks, event loop management |

## Running Examples

```bash
# From python-activerecord root directory
python -m docs.examples.worker_pool.basic_usage
python -m docs.examples.worker_pool.hooks_usage
python -m docs.examples.worker_pool.connection_management
python -m docs.examples.worker_pool.async_mode
```

## Key Concepts

### Task Function Signature

**All task functions MUST accept `ctx: TaskContext` as the first argument.**

```python
# ✅ CORRECT
def my_task(ctx: TaskContext, user_id: int) -> dict:
    db = ctx.worker_ctx.data.get('db')
    return {'id': user_id}

# ❌ WRONG - missing ctx parameter
def my_task(user_id: int) -> dict:
    return {'id': user_id}
```

### Connection Management

Choose **either** Worker-level **or** Task-level — **never mix**.

| Strategy | Hooks | Use Case |
|----------|-------|----------|
| Worker-level | `WORKER_START` + `WORKER_STOP` | High-frequency, short operations |
| Task-level | `TASK_START` + `TASK_END` | Low-frequency, long operations |

### Sync vs Async Mode

- **Sync mode**: All hooks are sync, no event loop
- **Async mode**: At least one hook is async, single event loop per Worker
- **Mixing modes raises `TypeError`**
