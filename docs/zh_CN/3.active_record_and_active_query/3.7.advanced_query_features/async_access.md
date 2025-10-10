# 异步访问

> **❌ 未实现**：本文档中描述的异步访问功能**未实现**。此文档描述了计划中的功能，仅用于未来参考。当前用户应仅依赖同步操作。此功能可能会在未来版本中开发，但没有保证的时间表。本文档中描述的API可能与实际实现有显著差异。

> **⚠️ 非实现文档**：本文档描述了ActiveRecord的异步数据库操作，用于提高I/O绑定应用程序的性能。**注意：这是目前非实现的文档，不反映已实现的功能。**

本文档说明如何使用ActiveRecord的异步数据库操作来提高I/O绑定应用程序的性能。

## 介绍

异步编程允许您的应用程序在等待数据库操作完成的同时执行其他任务，这可以显著提高I/O绑定应用程序的性能和响应能力。ActiveRecord计划通过兼容的异步数据库驱动程序提供对异步数据库操作的支持。

## 何时使用异步访问

异步数据库访问在以下场景中特别有益：

1. **Web应用程序**：高效处理多个并发请求
2. **API服务器**：并行处理大量数据库操作
3. **数据处理**：处理可以并行化操作的大型数据集
4. **微服务**：管理与数据库的多个服务交互

## 设置异步数据库连接

要使用异步数据库访问，您需要使用异步兼容的数据库驱动程序配置ActiveRecord：

```python
from rhosocial.activerecord import ActiveRecord

# 使用异步驱动程序配置ActiveRecord
ActiveRecord.configure({
    'default': {
        'driver': 'pgsql',  # 使用asyncpg的PostgreSQL
        'driver_type': 'asyncpg',  # 指定异步驱动程序
        'host': 'localhost',
        'database': 'myapp',
        'username': 'user',
        'password': 'password',
        'async_mode': True  # 启用异步模式
    }
})
```

## 基本异步操作

配置完成后，您可以使用标准ActiveRecord方法的异步版本：

```python
import asyncio
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    __table_name__ = 'users'

async def get_users():
    # 异步查询执行
    users = await User.query().async_all()
    return users

async def create_user(data):
    user = User()
    user.attributes = data
    # 异步保存操作
    success = await user.async_save()
    return user if success else None

# 在异步上下文中运行
asyncio.run(get_users())
```

## 异步查询方法

ActiveRecord提供所有标准查询方法的异步版本：

```python
async def example_async_queries():
    # 通过主键查找
    user = await User.async_find(1)
    
    # 带条件查找
    active_users = await User.query().where('status = ?', 'active').async_all()
    
    # 查找第一条记录
    first_admin = await User.query().where('role = ?', 'admin').async_first()
    
    # 计数记录
    user_count = await User.query().async_count()
    
    # 聚合
    avg_age = await User.query().async_average('age')
```

## 异步事务

您也可以异步使用事务：

```python
async def transfer_funds(from_account_id, to_account_id, amount):
    async with Account.async_transaction() as transaction:
        try:
            from_account = await Account.async_find(from_account_id)
            to_account = await Account.async_find(to_account_id)
            
            from_account.balance -= amount
            to_account.balance += amount
            
            await from_account.async_save()
            await to_account.async_save()
            
            # 如果没有异常发生，提交会自动进行
        except Exception as e:
            # 异常时回滚会自动进行
            print(f"事务失败: {e}")
            raise
```

## 并行异步操作

异步访问的主要优势之一是能够并行执行多个数据库操作：

```python
async def process_data():
    # 并行执行多个查询
    users_task = User.query().async_all()
    products_task = Product.query().async_all()
    orders_task = Order.query().where('status = ?', 'pending').async_all()
    
    # 等待所有查询完成
    users, products, orders = await asyncio.gather(
        users_task, products_task, orders_task
    )
    
    # 现在处理结果
    return {
        'users': users,
        'products': products,
        'orders': orders
    }
```

## 异步关系

您也可以异步处理关系：

```python
async def get_user_with_orders(user_id):
    # 异步获取用户及相关订单
    user = await User.query().with_('orders').async_find(user_id)
    
    # 访问加载的关系
    for order in user.orders:
        print(f"订单 #{order.id}: {order.total}")
    
    return user
```

## 混合同步和异步代码

保持同步和异步代码之间的明确分离很重要：

```python
# 同步上下文
def sync_function():
    # 这是正确的 - 在同步上下文中使用同步方法
    users = User.query().all()
    
    # 这是不正确的 - 永远不要直接从同步代码调用异步方法
    # users = User.query().async_all()  # 这不会工作！
    
    # 相反，如果需要从同步调用异步，请使用异步运行器
    users = asyncio.run(User.query().async_all())
    return users

# 异步上下文
async def async_function():
    # 这是正确的 - 在异步上下文中使用异步方法
    users = await User.query().async_all()
    
    # 这是不正确的 - 用同步方法阻塞异步事件循环
    # users = User.query().all()  # 在异步代码中避免这样做
    
    return users
```

## 最佳实践

1. **一致的异步风格**：在异步上下文中一致使用异步方法，以避免阻塞事件循环。

2. **错误处理**：为异步操作实现适当的错误处理，因为异常的传播方式不同。

3. **连接管理**：执行多个并行操作时，注意连接池和限制。

4. **避免阻塞操作**：确保异步上下文中的所有I/O操作也是异步的，以防止阻塞事件循环。

5. **测试**：彻底测试异步代码，因为它可能引入不同的时序和并发问题。

## 限制

- 并非所有数据库驱动程序都支持异步操作
- 某些复杂功能可能对异步支持有限
- 调试异步代码可能更具挑战性

## 结论

ActiveRecord中的异步数据库访问提供了一种强大的方式来提高应用程序性能，允许并发数据库操作。通过利用异步功能，您可以构建更具响应性和效率的应用程序，特别是在高并发或I/O绑定工作负载的场景中。