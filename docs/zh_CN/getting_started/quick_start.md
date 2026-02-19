# 快速开始 (Quick Start)

让我们构建一个简单的博客系统来体验 `rhosocial-activerecord` 的功能，展示同步和异步实现的**同步异步对等**。

> 💡 **AI提示词示例**: "我想快速了解如何使用rhosocial-activerecord构建一个博客系统，能给我一个完整的示例吗？"

## 1. 定义模型

在这一步中，我们将定义博客系统的核心模型：用户(User)和文章(Post)。我们将创建同步和异步两个版本的模型，以展示**同步异步对等**原则。

### 同步模型

同步模型使用 `ActiveRecord` 基类，适用于传统的同步编程场景。

> 💡 **AI提示词示例**: "我想创建一个带有用户和文章关联关系的博客系统，应该如何定义模型？"

```python
# 导入必要的模块
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

# User类代表博客系统的用户
# 继承UUIDMixin自动添加UUID主键，TimestampMixin自动添加创建和更新时间字段
# ActiveRecord是同步模型的基类
class User(UUIDMixin, TimestampMixin, ActiveRecord):
    # 用户名字段，最大长度50个字符，必需填写
    username: str = Field(..., max_length=50)
    # 邮箱字段，无长度限制
    email: str

    # FieldProxy允许类型安全的查询构建
    # 通过User.c.username可以进行类型安全的字段引用
    c: ClassVar[FieldProxy] = FieldProxy()

    # 定义用户与文章的一对多关系
    # 一个用户可以有多篇文章
    # ClassVar确保这个关系不会被Pydantic当作模型字段处理
    # foreign_key指定外键字段名，inverse_of指定反向关系名
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')

    # 返回数据库表名，如果不定义则默认为类名的小写复数形式
    @classmethod
    def table_name(cls) -> str:
        return 'users'

# Post类代表博客系统的文章
class Post(UUIDMixin, TimestampMixin, ActiveRecord):
    # 文章标题字段
    title: str
    # 文章内容字段
    content: str
    # 外键字段，关联到User表的id字段
    user_id: uuid.UUID

    # FieldProxy允许类型安全的查询构建
    c: ClassVar[FieldProxy] = FieldProxy()

    # 定义文章与用户的一对一关系（多对一）
    # 一篇文章属于一个用户
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')

    # 返回数据库表名
    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

> 💡 **AI提示词示例**: "为什么要在模型中使用ClassVar来定义关联关系？这样做的好处是什么？"

### 异步模型

异步模型使用 `AsyncActiveRecord` 基类，适用于需要高并发处理的异步编程场景。

> 💡 **AI提示词示例**: "同步模型和异步模型在定义上有什么区别？为什么要使用不同的关联关系类？"

```python
# 导入必要的模块
import uuid
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import AsyncHasMany, AsyncBelongsTo

# AsyncUser类是User的异步版本
# 继承相同的Mixin，但基类是AsyncActiveRecord
class AsyncUser(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    # 用户名字段，与同步版本相同
    username: str = Field(..., max_length=50)
    # 邮箱字段，与同步版本相同
    email: str

    # FieldProxy允许类型安全的查询构建，与同步版本相同
    c: ClassVar[FieldProxy] = FieldProxy()

    # 使用AsyncHasMany定义异步的一对多关系
    # 功能与HasMany相同，但适用于异步环境
    posts: ClassVar[AsyncHasMany['AsyncPost']] = AsyncHasMany(foreign_key='user_id', inverse_of='author')

    # 返回数据库表名，与同步版本相同
    @classmethod
    def table_name(cls) -> str:
        return 'users'

# AsyncPost类是Post的异步版本
class AsyncPost(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    # 文章标题字段，与同步版本相同
    title: str
    # 文章内容字段，与同步版本相同
    content: str
    # 外键字段，与同步版本相同
    user_id: uuid.UUID

    # FieldProxy允许类型安全的查询构建，与同步版本相同
    c: ClassVar[FieldProxy] = FieldProxy()

    # 使用AsyncBelongsTo定义异步的一对一关系
    # 功能与BelongsTo相同，但适用于异步环境
    author: ClassVar[AsyncBelongsTo['AsyncUser']] = AsyncBelongsTo(foreign_key='user_id', inverse_of='posts')

    # 返回数据库表名，与同步版本相同
    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

## 2. 设置数据库

在这一步中，我们将配置数据库连接并创建必要的表结构。我们将为同步和异步模型分别配置数据库后端。

> 💡 **AI提示词示例**: "我应该使用内存数据库还是文件数据库进行开发和测试？各有什么优缺点？"

```python
# 导入数据库后端相关模块
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig, AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# 配置同步模型的数据库连接
# 使用内存数据库(:memory:)，程序结束时数据会丢失，适合测试
sync_config = SQLiteConnectionConfig(database=':memory:')
# 为User模型配置SQLite后端，Post模型将共享相同的后端连接
User.configure(sync_config, SQLiteBackend)
Post.__backend__ = User.__backend__  # 共享连接以确保事务一致性

# 配置异步模型的数据库连接
# 同样使用内存数据库
async_config = SQLiteConnectionConfig(database=':memory:')
# 为AsyncUser模型配置异步SQLite后端，AsyncPost模型将共享相同的后端连接
AsyncUser.configure(async_config, AsyncSQLiteBackend)
AsyncPost.__backend__ = AsyncUser.__backend__  # 共享连接以确保事务一致性

# 创建数据库表结构
# 注意: 在生产环境中，请使用迁移工具。这里为简单起见使用原生 SQL。

> 💡 **AI提示词示例**: "在生产环境中应该如何管理数据库表结构变更？有推荐的迁移工具吗？"

# 定义users表的SQL结构
# 包含UUID主键、用户名、邮箱、创建时间、更新时间和版本号字段
schema_sql_users = """
CREATE TABLE users (
    id TEXT PRIMARY KEY,           -- UUID主键
    username VARCHAR(50),          -- 用户名，最大50字符
    email VARCHAR(100),            -- 邮箱，最大100字符
    created_at TEXT,               -- 创建时间
    updated_at TEXT,               -- 更新时间
    version INTEGER DEFAULT 1      -- 版本号，用于乐观锁
);
"""

# 定义posts表的SQL结构
# 包含UUID主键、标题、内容、外键、创建时间、更新时间和版本号字段
schema_sql_posts = """
CREATE TABLE posts (
    id TEXT PRIMARY KEY,           -- UUID主键
    title VARCHAR(200),            -- 标题，最大200字符
    content TEXT,                  -- 内容，文本类型
    user_id TEXT,                  -- 外键，关联users表的id字段
    created_at TEXT,               -- 创建时间
    updated_at TEXT,               -- 更新时间
    version INTEGER DEFAULT 1      -- 版本号，用于乐观锁
);
"""

# 执行SQL语句创建表
# 使用ExecutionOptions指定语句类型为DDL(数据定义语言)
User.backend().execute(schema_sql_users, options=ExecutionOptions(stmt_type=StatementType.DDL))
User.backend().execute(schema_sql_posts, options=ExecutionOptions(stmt_type=StatementType.DDL))
```

## 3. CRUD 操作

在这一步中，我们将演示基本的增删改查(CRUD)操作，包括同步和异步两种方式。

### 同步操作

同步操作使用传统的阻塞式调用方式，适用于简单的应用场景。

> 💡 **AI提示词示例**: "如何在rhosocial-activerecord中实现复杂的查询条件？比如查找某个时间段内发布的文章？"

```python
# 创建 (Create) - 创建新用户
# 实例化User对象并调用save()方法保存到数据库
alice = User(username="alice", email="alice@example.com")
# save()方法会执行INSERT操作并将数据持久化到数据库
alice.save()

# 创建关联数据 - 创建新文章并与用户关联
# 使用之前创建的用户ID作为外键
post = Post(title="Hello World", content="My first post", user_id=alice.id)
# save()方法会执行INSERT操作并将数据持久化到数据库
post.save()

# 读取 (Read) - 根据条件查找单个用户
# find_one()方法根据指定条件查找第一条匹配的记录
user = User.find_one({'username': 'alice'})
# 输出找到的用户名
print(f"Found user: {user.username}")

# 读取关联数据 - 获取用户的所有文章
# 注意: 使用方法调用语法()访问关联关系，这会触发数据库查询
# posts()方法会执行SELECT操作查询该用户的所有文章
user_posts = user.posts()
print(f"User has {len(user_posts)} posts")

# 更新 (Update) - 修改用户信息
# 直接修改模型属性
user.email = "new_email@example.com"
# 调用save()方法执行UPDATE操作将更改保存到数据库
user.save()

# 删除 (Delete) - 删除文章
# delete()方法会执行DELETE操作从数据库中移除记录
post.delete()
```

### 异步操作

异步操作使用非阻塞式调用方式，适用于需要高并发处理的应用场景。

> 💡 **AI提示词示例**: "异步操作和同步操作在使用上有什么区别？什么时候应该使用异步操作？"

```python
# 导入asyncio模块以支持异步操作
import asyncio

# 定义异步CRUD操作函数
async def async_crud_operations():
    # 创建 (Create) - 创建新用户
    # 使用AsyncUser类实例化对象
    bob = AsyncUser(username="bob", email="bob@example.com")
    # 使用await关键字等待save()操作完成
    # await确保异步操作在继续执行前完成
    await bob.save()

    # 创建关联数据 - 创建新文章并与用户关联
    post = AsyncPost(title="Async Hello World", content="My first async post", user_id=bob.id)
    # 使用await关键字等待save()操作完成
    await post.save()

    # 读取 (Read) - 根据条件查找单个用户
    # 使用await关键字等待find_one()操作完成
    user = await AsyncUser.find_one({'username': 'bob'})
    print(f"Found async user: {user.username}")

    # 读取关联数据 - 获取用户的所有文章
    # 使用await关键字等待posts()操作完成
    # posts()方法会执行异步SELECT操作查询该用户的所有文章
    user_posts = await user.posts()
    print(f"Async user has {len(user_posts)} posts")

    # 更新 (Update) - 修改用户信息
    # 直接修改模型属性（与同步操作相同）
    user.email = "new_async_email@example.com"
    # 使用await关键字等待save()操作完成
    await user.save()

    # 删除 (Delete) - 删除文章
    # 使用await关键字等待delete()操作完成
    await post.delete()

# 运行异步操作
# 在实际应用中取消注释下面的行来执行异步操作
# asyncio.run(async_crud_operations())
```

## 4. 同步异步对等实践

注意同步和异步实现是如何遵循相同模式的，这体现了**同步异步对等**原则：

> 💡 **AI提示词示例**: "什么是同步异步对等原则？为什么这个原则对开发很重要？"

*   **方法签名**: `User.save()` 和 `AsyncUser.save()` 具有相同的参数和返回类型（除了 `async`/`await`）
*   **查询接口**: `User.find_one()` 和 `AsyncUser.find_one()` 接受相同的参数
*   **关联处理**: 同步和异步关联关系的工作方式类似
*   **功能**: 同步版本中可用的每个功能在异步版本中也可用

这种**同步异步对等**使您能够在同步和异步上下文之间无缝过渡，而无需学习不同的 API 或牺牲功能。

这个简单的例子展示了核心工作流：定义 -> 配置 -> 交互，同步和异步实现都展示了**同步异步对等**原则。