# Task Writing Guide

## Rules for Task Functions

1. **Must be module-level functions**: Nested/local functions cannot be pickled
2. **Must be importable**: Workers need to import the function by name
3. **First argument must be ctx: TaskContext**: The framework injects context automatically
4. **Arguments must be pickle-able**: Basic types, dicts, lists work well
5. **Return pickle-able results**: Same constraint as arguments
6. **Support for async functions**: `async def` functions are supported in both sync and async modes

## Task Function Signature

All task functions must accept `ctx: TaskContext` as the first argument:

```python
def my_task(ctx: TaskContext, user_id: int) -> dict:
    """Task function template with context."""
    # Access Worker-level data
    db = ctx.worker_ctx.data.get('db')

    # Store task-level data
    ctx.data['start_time'] = time.time()

    # Do work
    user = db.query(User).get(user_id)

    return {"id": user.id, "name": user.name}

# Submit: ctx is injected automatically
pool.submit(my_task, user_id=123)
```

## Async Task Functions

WorkerPool natively supports async task functions:

```python
# Sync mode pool with async tasks
async def async_query_task(ctx: TaskContext, params: dict) -> dict:
    """Async task using AsyncActiveRecord"""
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
    from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
    from myapp.models import User

    config = SQLiteConnectionConfig(database=params['db_path'])
    await User.async_configure(config, SQLiteBackend)

    try:
        async with User.async_transaction():
            user = await User.find_one_async(params['user_id'])
            return {'status': 'success', 'user_id': user.id}
    finally:
        await User.async_backend().disconnect()

# Works in both sync and async mode pools
with WorkerPool(n_workers=4) as pool:
    future = pool.submit(async_query_task, {'db_path': 'app.db', 'user_id': 123})
    result = future.result(timeout=30)
```

**Async Mode (recommended for async tasks)**:

When all hooks are async, the pool runs in async mode with a single event loop per worker:

```python
async def init_db(ctx: WorkerContext):
    db = await AsyncDatabase.connect()
    ctx.data['db'] = db

async def cleanup_db(ctx: WorkerContext):
    db = ctx.data.get('db')
    if db:
        await db.close()

async def async_task(ctx: TaskContext, user_id: int):
    db = ctx.worker_ctx.data['db']
    return await db.query_user(user_id)

with WorkerPool(
    n_workers=4,
    on_worker_start=init_db,
    on_worker_stop=cleanup_db,
) as pool:
    futures = [pool.submit(async_task, user_id=i) for i in range(10)]
    results = [f.result(timeout=10) for f in futures]
```

## Task Function Template

```python
# tasks.py - Dedicated module for task functions
from rhosocial.activerecord.worker import TaskContext

def my_task(ctx: TaskContext, params: dict) -> dict:
    """
    Task function template.

    Args:
        ctx: Task context (injected automatically)
        params: Task parameters (serializable dict)

    Returns:
        Result dictionary (serializable)
    """
    # 1. Extract parameters
    db_path = params['db_path']
    # ... other parameters

    # 2. Configure connection (inside worker)
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
    from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
    from myapp.models import MyModel

    config = SQLiteConnectionConfig(database=db_path)
    MyModel.configure(config, SQLiteBackend)

    try:
        # 3. Execute business logic
        with MyModel.transaction():
            # ... do work
            result = {'status': 'success', 'data': some_value}
            return result

    finally:
        # 4. Always cleanup connection
        MyModel.backend().disconnect()
```

## Handling Errors

```python
from rhosocial.activerecord.worker import TaskContext

def safe_task(ctx: TaskContext, params: dict) -> dict:
    """Task with proper error handling - ctx is always first"""
    try:
        # ... do work
        return {'success': True, 'data': result}
    except ValueError as e:
        # Business logic error - return as part of result
        return {'success': False, 'error': str(e)}
    except Exception as e:
        # Unexpected error - let it propagate
        raise RuntimeError(f"Task failed: {e}")
```

## Batch Processing

Use `map()` for simple batch operations:

```python
from rhosocial.activerecord.worker import TaskContext

def process_item(ctx: TaskContext, item_id: int) -> dict:
    """Task function - ctx is always the first argument."""
    # Process single item
    return {'id': item_id, 'status': 'done'}

with WorkerPool(n_workers=4) as pool:
    # map() injects ctx automatically for each item
    results = pool.map(process_item, range(100))
```

For complex batch operations with shared setup:

```python
def batch_task(ctx: TaskContext, params: dict) -> list:
    """Process multiple items in one task"""
    db_path = params['db_path']
    item_ids = params['item_ids']

    # Configure once for entire batch
    Model.configure(config, Backend)

    try:
        results = []
        with Model.transaction():
            for item_id in item_ids:
                item = Model.find_one(item_id)
                # ... process
                results.append(item.id)
        return results
    finally:
        Model.backend().disconnect()

# Submit batches
batch_size = 10
with WorkerPool(n_workers=4) as pool:
    futures = []
    for i in range(0, 100, batch_size):
        batch = list(range(i, i + batch_size))
        futures.append(pool.submit(batch_task, {
            'db_path': 'app.db',
            'item_ids': batch
        }))
    results = [f.result() for f in futures]
```
