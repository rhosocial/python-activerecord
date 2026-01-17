# 快速开始 (Quick Start)

让我们构建一个简单的博客系统来体验 `rhosocial-activerecord` 的功能。

## 1. 定义模型

我们将定义 `User` 和 `Post` 模型。

```python
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

## 2. 设置数据库

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# 配置
config = SQLiteConnectionConfig(database=':memory:')
User.configure(config, SQLiteBackend)
Post.__backend__ = User.__backend__  # 共享连接

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

这个简单的例子展示了核心工作流：定义 -> 配置 -> 交互。
