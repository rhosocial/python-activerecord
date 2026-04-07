# 任务编写指南

## 任务函数规则

1. **必须是模块级函数**：嵌套/局部函数无法被 pickle
2. **必须可导入**：Worker 需要按名称导入函数
3. **第一个参数必须是 ctx: TaskContext**：框架自动注入上下文
4. **参数必须可 pickle**：基本类型、字典、列表均可
5. **返回值必须可 pickle**：与参数相同的约束
6. **支持异步函数**：`async def` 函数在同步和异步模式下都支持

## 任务函数签名

所有任务函数必须接受 `ctx: TaskContext` 作为第一个参数：

```python
def my_task(ctx: TaskContext, user_id: int) -> dict:
    """带上下文的任务函数模板。"""
    # 访问 Worker 级数据
    db = ctx.worker_ctx.data.get('db')

    # 存储任务级数据
    ctx.data['start_time'] = time.time()

    # 执行工作
    user = db.query(User).get(user_id)

    return {"id": user.id, "name": user.name}

# 提交：ctx 自动注入
pool.submit(my_task, user_id=123)
```

## 异步任务函数

WorkerPool 原生支持异步任务函数：

```python
# 同步模式进程池使用异步任务
async def async_query_task(ctx: TaskContext, params: dict) -> dict:
    """使用 AsyncActiveRecord 的异步任务"""
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

# 在同步和异步模式进程池中都能工作
with WorkerPool(n_workers=4) as pool:
    future = pool.submit(async_query_task, {'db_path': 'app.db', 'user_id': 123})
    result = future.result(timeout=30)
```

**异步模式（异步任务推荐）**：

当所有钩子都是异步的，进程池在异步模式下运行，每个 Worker 有一个事件循环：

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

## 任务函数模板

```python
# tasks.py - 专门存放任务函数的模块
from rhosocial.activerecord.worker import TaskContext

def my_task(ctx: TaskContext, params: dict) -> dict:
    """
    任务函数模板。

    参数:
        ctx: 任务上下文（自动注入）
        params: 任务参数（可序列化字典）

    返回:
        结果字典（可序列化）
    """
    # 1. 提取参数
    db_path = params['db_path']
    # ... 其他参数

    # 2. 配置连接（在 Worker 内）
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
    from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
    from myapp.models import MyModel

    config = SQLiteConnectionConfig(database=db_path)
    MyModel.configure(config, SQLiteBackend)

    try:
        # 3. 执行业务逻辑
        with MyModel.transaction():
            # ... 执行工作
            result = {'status': 'success', 'data': some_value}
            return result

    finally:
        # 4. 始终清理连接
        MyModel.backend().disconnect()
```

## 错误处理

```python
from rhosocial.activerecord.worker import TaskContext

def safe_task(ctx: TaskContext, params: dict) -> dict:
    """正确处理错误的任务 - ctx 始终是第一个参数"""
    try:
        # ... 执行工作
        return {'success': True, 'data': result}
    except ValueError as e:
        # 业务逻辑错误 - 作为结果的一部分返回
        return {'success': False, 'error': str(e)}
    except Exception as e:
        # 意外错误 - 让其传播
        raise RuntimeError(f"任务失败: {e}")
```

## 批量处理

对于简单批量操作，使用 `map()`：

```python
from rhosocial.activerecord.worker import TaskContext

def process_item(ctx: TaskContext, item_id: int) -> dict:
    """任务函数 - ctx 始终是第一个参数。"""
    # 处理单个项目
    return {'id': item_id, 'status': 'done'}

with WorkerPool(n_workers=4) as pool:
    # map() 自动为每个项目注入 ctx
    results = pool.map(process_item, range(100))
```

对于需要共享设置的复杂批量操作：

```python
def batch_task(ctx: TaskContext, params: dict) -> list:
    """在一个任务中处理多个项目"""
    db_path = params['db_path']
    item_ids = params['item_ids']

    # 为整个批次配置一次
    Model.configure(config, Backend)

    try:
        results = []
        with Model.transaction():
            for item_id in item_ids:
                item = Model.find_one(item_id)
                # ... 处理
                results.append(item.id)
        return results
    finally:
        Model.backend().disconnect()

# 提交批次
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
