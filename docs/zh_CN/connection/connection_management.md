# 连接管理 (Connection Management)

在 [数据库配置](configuration.md) 中，我们介绍了如何为单个模型或所有模型配置数据库连接。但在实际应用中，你可能需要管理多个模型共享同一个连接，或者连接多个不同的数据库。`rhosocial.activerecord.connection` 模块提供了 `ConnectionGroup` 和 `ConnectionManager` 来简化这些场景。

> 💡 **AI 提示词示例**: "我有一个应用需要连接多个数据库（主库和统计库），如何优雅地管理这些连接？"

## 目录

1. [ConnectionGroup - 连接组](#1-connectiongroup---连接组)
2. [ConnectionManager - 多数据库管理](#2-connectionmanager---多数据库管理)
3. [异步支持](#3-异步支持)
4. [实战示例](#4-实战示例)

## 1. ConnectionGroup - 连接组

`ConnectionGroup` 用于管理一组模型的数据库连接。它提供了上下文管理器，自动处理连接的建立和断开。

### 基本用法

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.connection import ConnectionGroup

# 定义模型
class User(ActiveRecord):
    name: str
    email: str

class Post(ActiveRecord):
    title: str
    content: str
    user_id: int

# 创建连接组
with ConnectionGroup(
    name="main",
    models=[User, Post],
    config=SQLiteConnectionConfig(database="app.db"),
    backend_class=SQLiteBackend,
) as group:
    # 在上下文中，所有模型已配置好连接
    user = User(name="张三", email="zhangsan@example.com")
    user.save()

    post = Post(title="第一篇文章", content="Hello World!", user_id=user.id)
    post.save()

# 退出上下文后，连接自动断开
```

### 手动管理

如果需要更细粒度的控制，可以手动调用 `configure()` 和 `disconnect()`：

```python
# 创建连接组
group = ConnectionGroup(
    name="main",
    models=[User, Post],
    config=SQLiteConnectionConfig(database="app.db"),
    backend_class=SQLiteBackend,
)

# 手动配置连接
group.configure()

# 检查连接状态
print(group.is_configured())  # True
print(group.is_connected())   # True

# 使用模型进行操作
user = User.find_one(1)

# 手动断开连接
group.disconnect()
```

### 动态添加模型

```python
group = ConnectionGroup(
    name="main",
    config=SQLiteConnectionConfig(database="app.db"),
    backend_class=SQLiteBackend,
)

# 动态添加模型（必须在 configure 之前）
group.add_model(User).add_model(Post)

group.configure()
```

### 连接健康检查

```python
with ConnectionGroup(...) as group:
    # 检查整体连接状态
    if group.is_connected():
        print("所有连接正常")

    # 检查每个模型的连接状态
    status = group.ping()
    for model, is_connected in status.items():
        print(f"{model.__name__}: {'正常' if is_connected else '断开'}")
```

## 2. ConnectionManager - 多数据库管理

当你需要连接多个数据库（例如主库 + 统计库，或主从架构）时，可以使用 `ConnectionManager`。

### 基本用法

```python
from rhosocial.activerecord.connection import ConnectionManager
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

# 创建管理器
manager = ConnectionManager()

# 创建主库连接组
manager.create_group(
    name="main",
    config=SQLiteConnectionConfig(database="main.db"),
    backend_class=SQLiteBackend,
    models=[User, Post],
)

# 创建统计库连接组
manager.create_group(
    name="stats",
    config=SQLiteConnectionConfig(database="stats.db"),
    backend_class=SQLiteBackend,
    models=[Log, Metric],
)

# 配置所有连接
manager.configure_all()

# 使用模型
user = User.find_one(1)
log = Log.create(action="login", user_id=user.id)

# 断开所有连接
manager.disconnect_all()
```

### 作为上下文管理器

```python
with ConnectionManager() as manager:
    manager.create_group(
        name="main",
        config=SQLiteConnectionConfig(database="main.db"),
        backend_class=SQLiteBackend,
        models=[User, Post],
    )

    manager.create_group(
        name="stats",
        config=SQLiteConnectionConfig(database="stats.db"),
        backend_class=SQLiteBackend,
        models=[Log, Metric],
    )

    # 在上下文中，所有连接已配置好
    user = User.find_one(1)
    log = Log.create(action="login", user_id=user.id)

# 退出时自动断开所有连接
```

### 管理连接组

```python
manager = ConnectionManager()

# 创建连接组
manager.create_group("main", config=config, backend_class=SQLiteBackend, models=[User])

# 检查是否存在
print(manager.has_group("main"))  # True

# 获取连接组
group = manager.get_group("main")

# 获取所有组名
print(manager.get_group_names())  # ['main']

# 移除连接组（会自动断开连接）
manager.remove_group("main")

# 检查所有连接状态
print(manager.is_connected())  # True/False
```

## 3. 异步支持

`rhosocial.activerecord.connection` 提供完整的异步支持，遵循项目的同步异步对等原则。

### AsyncConnectionGroup

```python
from rhosocial.activerecord.connection import AsyncConnectionGroup
from rhosocial.activerecord.model import AsyncActiveRecord

class User(AsyncActiveRecord):
    name: str
    email: str

# 使用异步连接组
async with AsyncConnectionGroup(
    name="main",
    models=[User],
    config=SQLiteConnectionConfig(database="app.db"),
    backend_class=AsyncSQLiteBackend,  # 需要异步后端
) as group:
    user = await User.find_one(1)
    user.name = "新名字"
    await user.save()
```

### AsyncConnectionManager

```python
from rhosocial.activerecord.connection import AsyncConnectionManager

async with AsyncConnectionManager() as manager:
    manager.create_group(
        name="main",
        config=SQLiteConnectionConfig(database="main.db"),
        backend_class=AsyncSQLiteBackend,
        models=[User, Post],
    )

    manager.create_group(
        name="stats",
        config=SQLiteConnectionConfig(database="stats.db"),
        backend_class=AsyncSQLiteBackend,
        models=[Log, Metric],
    )

    # 使用模型
    user = await User.find_one(1)
    log = await Log.create(action="login", user_id=user.id)
```

## 4. 实战示例

### CLI 工具场景

在 CLI 工具中，使用 `ConnectionGroup` 可以确保脚本结束时正确关闭连接：

```python
# scripts/migrate_users.py
from rhosocial.activerecord.connection import ConnectionGroup
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from app.models import User, Post

def migrate_users():
    """迁移用户数据的脚本。"""
    with ConnectionGroup(
        name="migration",
        models=[User, Post],
        config=SQLiteConnectionConfig(database="production.db"),
        backend_class=SQLiteBackend,
    ):
        for user in User.query().all():
            # 执行迁移逻辑
            user.migrated = True
            user.save()
            print(f"已迁移用户: {user.name}")

if __name__ == "__main__":
    migrate_users()
```

### 定时任务场景

```python
# tasks/daily_report.py
from rhosocial.activerecord.connection import ConnectionManager
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from app.models import User, Order, Report

def generate_daily_report():
    """生成每日报告的定时任务。"""
    with ConnectionManager() as manager:
        # 主库：读取用户和订单数据
        manager.create_group(
            name="main",
            config=SQLiteConnectionConfig(database="main.db"),
            backend_class=SQLiteBackend,
            models=[User, Order],
        )

        # 统计库：写入报告
        manager.create_group(
            name="stats",
            config=SQLiteConnectionConfig(database="stats.db"),
            backend_class=SQLiteBackend,
            models=[Report],
        )

        # 统计今日订单
        today_orders = Order.query().where(
            Order.c.created_at >= today_start()
        ).all()

        # 生成报告
        report = Report(
            date=today(),
            order_count=len(today_orders),
            total_amount=sum(o.amount for o in today_orders),
        )
        report.save()
```

### Web 应用场景

在 FastAPI 等 Web 框架中，可以在应用生命周期中管理连接：

```python
# app/database.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from rhosocial.activerecord.connection import AsyncConnectionManager
from rhosocial.activerecord.backend.impl.sqlite import SQLiteConnectionConfig

manager = AsyncConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时配置连接
    manager.create_group(
        name="main",
        config=SQLiteConnectionConfig(database="app.db"),
        backend_class=AsyncSQLiteBackend,
        models=[User, Post],
    )
    await manager.configure_all()

    yield

    # 关闭时断开连接
    await manager.disconnect_all()

app = FastAPI(lifespan=lifespan)
```

### 多租户场景

```python
from rhosocial.activerecord.connection import ConnectionManager
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

class TenantManager:
    """多租户连接管理器。"""

    def __init__(self):
        self.manager = ConnectionManager()

    def setup_tenant(self, tenant_id: str, models: list):
        """为租户创建独立的数据库连接。"""
        db_path = f"tenants/{tenant_id}.db"
        self.manager.create_group(
            name=tenant_id,
            config=SQLiteConnectionConfig(database=db_path),
            backend_class=SQLiteBackend,
            models=models,
        )
        self.manager.configure_all()

    def get_tenant_backend(self, tenant_id: str, model):
        """获取租户的后端实例。"""
        group = self.manager.get_group(tenant_id)
        return group.get_backend(model) if group else None

    def remove_tenant(self, tenant_id: str):
        """移除租户连接。"""
        self.manager.remove_group(tenant_id)

# 使用示例
tenant_manager = TenantManager()
tenant_manager.setup_tenant("company_a", [User, Post])
tenant_manager.setup_tenant("company_b", [User, Post])
```

## API 速查

### ConnectionGroup

| 方法 | 说明 |
|------|------|
| `configure()` | 配置连接 |
| `disconnect()` | 断开连接 |
| `is_configured()` | 检查是否已配置 |
| `is_connected()` | 检查连接是否正常 |
| `ping()` | 检查每个模型的连接状态 |
| `add_model(model)` | 添加模型（需在 configure 前调用） |
| `get_backend(model)` | 获取模型的后端实例 |

### ConnectionManager

| 方法 | 说明 |
|------|------|
| `create_group(name, ...)` | 创建连接组 |
| `get_group(name)` | 获取连接组 |
| `has_group(name)` | 检查连接组是否存在 |
| `remove_group(name)` | 移除连接组 |
| `configure_all()` | 配置所有连接 |
| `disconnect_all()` | 断开所有连接 |
| `is_connected()` | 检查所有连接是否正常 |
| `get_group_names()` | 获取所有组名 |

---

## 下一步

你已经掌握了连接管理的基础知识！接下来可以探索：

- **[FastAPI 集成](../scenarios/fastapi.md)**：在 Web 应用中使用连接管理
- **[测试策略](../testing/strategies.md)**：如何在测试中管理连接
- **[自定义后端](../backend/custom_backend.md)**：为其他数据库实现后端
