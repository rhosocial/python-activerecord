# 快速开始 (Quick Start)

让我们构建一个简单的博客系统来体验 `rhosocial-activerecord` 的功能，展示同步和异步实现的**同步异步对等**。

## 1. 定义模型

我们将定义同步和异步的 `User` 和 `Post` 模型，以展示**同步异步对等**原则。

### 同步模型

```python
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(UUIDMixin, TimestampMixin, ActiveRecord):
    username: str = Field(..., max_length=50)
    email: str

    # 启用类型安全的查询构建
    c: ClassVar[FieldProxy] = FieldProxy()

    # 关联关系
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')

    @classmethod
    def table_name(cls) -> str:
        return 'users'

class Post(UUIDMixin, TimestampMixin, ActiveRecord):
    title: str
    content: str
    user_id: uuid.UUID  # 外键

    # 启用类型安全的查询构建
    c: ClassVar[FieldProxy] = FieldProxy()

    # 关联关系
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')

    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

### 异步模型

```python
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import AsyncHasMany, AsyncBelongsTo

class AsyncUser(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    username: str = Field(..., max_length=50)
    email: str

    # 启用类型安全的查询构建
    c: ClassVar[FieldProxy] = FieldProxy()

    # 关联关系
    posts: ClassVar[AsyncHasMany['AsyncPost']] = AsyncHasMany(foreign_key='user_id', inverse_of='author')

    @classmethod
    def table_name(cls) -> str:
        return 'users'

class AsyncPost(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    title: str
    content: str
    user_id: uuid.UUID  # 外键

    # 启用类型安全的查询构建
    c: ClassVar[FieldProxy] = FieldProxy()

    # 关联关系
    author: ClassVar[AsyncBelongsTo['AsyncUser']] = AsyncBelongsTo(foreign_key='user_id', inverse_of='posts')

    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

## 2. 设置数据库

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig, AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# 配置同步模型
sync_config = SQLiteConnectionConfig(database=':memory:')
User.configure(sync_config, SQLiteBackend)
Post.__backend__ = User.__backend__  # 共享连接

# 配置异步模型
async_config = SQLiteConnectionConfig(database=':memory:')
AsyncUser.configure(async_config, AsyncSQLiteBackend)
AsyncPost.__backend__ = AsyncUser.__backend__  # 共享连接

# 创建表
# 注意: 在生产环境中，请使用迁移工具。这里为简单起见使用原生 SQL。
schema_sql_users = """
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    username VARCHAR(50),
    email VARCHAR(100),
    created_at TEXT,
    updated_at TEXT,
    version INTEGER DEFAULT 1
);
"""
schema_sql_posts = """
CREATE TABLE posts (
    id TEXT PRIMARY KEY,
    title VARCHAR(200),
    content TEXT,
    user_id TEXT,
    created_at TEXT,
    updated_at TEXT,
    version INTEGER DEFAULT 1
);
"""
User.backend().execute(schema_sql_users, options=ExecutionOptions(stmt_type=StatementType.DDL))
User.backend().execute(schema_sql_posts, options=ExecutionOptions(stmt_type=StatementType.DDL))
```

## 3. CRUD 操作

### 同步操作

```python
# 创建 (Create)
alice = User(username="alice", email="alice@example.com")
alice.save()

# 创建关联数据
post = Post(title="Hello World", content="My first post", user_id=alice.id)
post.save()

# 读取 (Read)
user = User.find_one({'username': 'alice'})
print(f"Found user: {user.username}")

# 读取关联数据
# 注意: 使用方法调用语法访问关联关系
user_posts = user.posts()
print(f"User has {len(user_posts)} posts")

# 更新 (Update)
user.email = "new_email@example.com"
user.save()

# 删除 (Delete)
post.delete()
```

### 异步操作

```python
import asyncio

async def async_crud_operations():
    # 创建 (Create)
    bob = AsyncUser(username="bob", email="bob@example.com")
    await bob.save()

    # 创建关联数据
    post = AsyncPost(title="Async Hello World", content="My first async post", user_id=bob.id)
    await post.save()

    # 读取 (Read)
    user = await AsyncUser.find_one({'username': 'bob'})
    print(f"Found async user: {user.username}")

    # 读取关联数据
    # 注意: 使用方法调用语法访问关联关系
    user_posts = await user.posts()
    print(f"Async user has {len(user_posts)} posts")

    # 更新 (Update)
    user.email = "new_async_email@example.com"
    await user.save()

    # 删除 (Delete)
    await post.delete()

# 运行异步操作
# asyncio.run(async_crud_operations())
```

## 4. 同步异步对等实践

注意同步和异步实现是如何遵循相同模式的：

*   **方法签名**: `User.save()` 和 `AsyncUser.save()` 具有相同的参数和返回类型（除了 `async`/`await`）
*   **查询接口**: `User.find_one()` 和 `AsyncUser.find_one()` 接受相同的参数
*   **关联处理**: 同步和异步关联关系的工作方式类似
*   **功能**: 同步版本中可用的每个功能在异步版本中也可用

这种**同步异步对等**使您能够在同步和异步上下文之间无缝过渡，而无需学习不同的 API 或牺牲功能。

这个简单的例子展示了核心工作流：定义 -> 配置 -> 交互，同步和异步实现都展示了**同步异步对等**原则。
