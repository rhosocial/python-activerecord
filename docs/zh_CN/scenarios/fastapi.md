# FastAPI 集成

FastAPI 是一个现代、高性能的 Python Web 框架，与 `rhosocial-activerecord` 有着天然的契合度——因为 `ActiveRecord` 模型本质上就是 `Pydantic` 模型，这意味着你可以直接将它们用作 FastAPI 的请求体和响应模型，无需任何额外的序列化层。

本章将带你从零开始，构建一个完整的**博客系统 REST API**，包含用户管理、文章发布、关联查询等功能。我们将展示 **异步** 实现方式，这是 FastAPI 的推荐模式。

## 目录

1. [项目结构](#1-项目结构)
2. [环境准备](#2-环境准备)
3. [定义模型](#3-定义模型)
4. [数据库配置](#4-数据库配置)
5. [创建 FastAPI 应用](#5-创建-fastapi-应用)
6. [实现 API 路由](#6-实现-api-路由)
7. [运行与测试](#7-运行与测试)
8. [最佳实践](#8-最佳实践)

## 1. 项目结构

首先，让我们规划项目的目录结构：

```
my_blog_api/
├── app/
│   ├── __init__.py
│   ├── models.py          # 数据模型定义
│   ├── database.py        # 数据库配置
│   ├── schemas.py         # Pydantic 请求/响应模型（可选）
│   └── main.py            # FastAPI 应用入口
├── tests/
│   └── test_api.py        # API 测试
├── requirements.txt
└── README.md
```

## 2. 环境准备

### 2.1 安装依赖

创建 `requirements.txt`：

```txt
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
rhosocial-activerecord
aiosqlite>=0.19.0
```

安装依赖：

```bash
pip install -r requirements.txt
```

### 2.2 创建基础目录

```bash
mkdir -p app tests
touch app/__init__.py
```

## 3. 定义模型

我们将定义 `User` 和 `Post` 两个模型，展示一对多关系（一个用户可以有多篇文章）。

> **⚠️ 注意**
> 
> 本章使用异步模型 (`AsyncActiveRecord`)，这是 FastAPI 的推荐模式。所有数据库操作都需要使用 `await`。

创建 `app/models.py`：

```python
# app/models.py
import uuid
from datetime import datetime
from typing import ClassVar, Optional, List
from pydantic import Field
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import AsyncHasMany, AsyncBelongsTo


class User(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    """用户模型。"""
    
    username: str = Field(..., max_length=50, description="用户名")
    email: str = Field(..., max_length=100, description="邮箱地址")
    bio: Optional[str] = Field(default=None, max_length=500, description="个人简介")
    is_active: bool = Field(default=True, description="是否激活")
    
    # 启用类型安全的查询构建
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # 关联关系：一个用户有多篇文章
    posts: ClassVar[AsyncHasMany['Post']] = AsyncHasMany(
        foreign_key='user_id', 
        inverse_of='author'
    )
    
    @classmethod
    def table_name(cls) -> str:
        """返回表名。"""
        return 'users'
    
    class Config:
        # Pydantic V2 配置
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "bio": "Python 开发者",
                "is_active": True
            }
        }


class Post(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    """文章模型。"""
    
    title: str = Field(..., max_length=200, description="文章标题")
    content: str = Field(..., description="文章内容")
    summary: Optional[str] = Field(default=None, max_length=500, description="摘要")
    is_published: bool = Field(default=False, description="是否已发布")
    user_id: uuid.UUID = Field(..., description="作者ID")
    published_at: Optional[datetime] = Field(default=None, description="发布时间")
    
    # 启用类型安全的查询构建
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # 关联关系：文章属于一个用户
    author: ClassVar[AsyncBelongsTo['User']] = AsyncBelongsTo(
        foreign_key='user_id', 
        inverse_of='posts'
    )
    
    @classmethod
    def table_name(cls) -> str:
        """返回表名。"""
        return 'posts'
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Hello FastAPI",
                "content": "这是一篇关于 FastAPI 的文章...",
                "summary": "FastAPI 入门指南",
                "is_published": True,
                "user_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
```

## 4. 数据库配置

创建 `app/database.py` 来管理数据库连接：

```python
# app/database.py
import sys
from contextlib import asynccontextmanager
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# 从测试模块导入 AsyncSQLiteBackend
# 注意：这是用于测试的异步后端实现
sys.path.insert(0, 'tests')
from rhosocial.activerecord_test.feature.backend.sqlite.core.async_backend import AsyncSQLiteBackend


class Database:
    """数据库连接管理器。"""
    
    _config = None
    
    @classmethod
    def get_config(cls):
        """获取数据库配置（单例模式）。"""
        if cls._config is None:
            cls._config = SQLiteConnectionConfig(
                database='./blog.db',  # 使用文件数据库
                # database=':memory:'  # 使用内存数据库（测试时）
            )
        return cls._config
    
    @classmethod
    async def init_models(cls):
        """初始化模型（创建表）。"""
        from app.models import User, Post
        
        config = cls.get_config()
        
        # 配置模型（需要提供配置和后端类）
        User.configure(config, AsyncSQLiteBackend)
        Post.configure(config, AsyncSQLiteBackend)
        
        # 连接数据库
        backend = User.__backend__
        await backend.connect()
        
        # 创建表（如果不存在）
        # 注意：实际项目中应使用迁移工具
        await cls._create_tables(backend)
    
    @classmethod
    async def _create_tables(cls, backend):
        """创建数据库表。"""
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        
        # 创建 users 表
        await backend.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                bio TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """, options=options)
        
        # 创建 posts 表
        await backend.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                is_published INTEGER DEFAULT 0,
                user_id TEXT NOT NULL,
                published_at TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """, options=options)
    
    @classmethod
    async def close(cls):
        """关闭数据库连接。"""
        from app.models import User
        backend = User.__backend__
        if backend:
            await backend.disconnect()


@asynccontextmanager
async def get_db():
    """提供数据库会话的异步上下文管理器（用于依赖注入）。"""
    from app.models import User
    backend = User.__backend__
    try:
        yield backend
    except Exception:
        # 可以在这里添加回滚逻辑
        raise
```

## 5. 创建 FastAPI 应用

创建 `app/main.py` 作为应用入口：

```python
# app/main.py
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from typing import List, Optional
from contextlib import asynccontextmanager

from app.database import Database
from app.models import User, Post


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时初始化数据库
    await Database.init_models()
    print("数据库初始化完成")
    yield
    # 关闭时的清理逻辑
    await Database.close()
    print("应用关闭")


app = FastAPI(
    title="博客系统 API",
    description="使用 rhosocial-activerecord + FastAPI 构建的博客系统",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """API 根路径。"""
    return {
        "message": "欢迎使用博客系统 API",
        "docs": "/docs",
        "version": "1.0.0"
    }
```

## 6. 实现 API 路由

### 6.1 用户管理路由

```python
# app/main.py（追加到文件末尾）

@app.post("/users/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: User):
    """
    创建新用户。
    
    - **username**: 用户名（必填，最大50字符）
    - **email**: 邮箱地址（必填，最大100字符）
    - **bio**: 个人简介（可选，最大500字符）
    - **is_active**: 是否激活（可选，默认为 true）
    """
    # 检查用户名是否已存在
    existing = await User.query().where(User.c.username == user.username).one()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"用户名 '{user.username}' 已存在"
        )
    
    # 检查邮箱是否已存在
    existing = await User.query().where(User.c.email == user.email).one()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"邮箱 '{user.email}' 已被注册"
        )
    
    await user.save()
    return user


@app.get("/users/", response_model=List[User])
async def list_users(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(10, ge=1, le=100, description="返回的记录数"),
    is_active: Optional[bool] = Query(None, description="按激活状态筛选")
):
    """获取用户列表（支持分页和筛选）。"""
    query = User.query()
    
    if is_active is not None:
        query = query.where(User.c.is_active == is_active)
    
    # 对于 SQLite，我们需要确保正确使用 LIMIT 和 OFFSET
    # 按创建时间降序排序（最新的在前）
    users = await query.order_by((User.c.created_at, "DESC")).limit(limit).offset(skip).all()
    return users


@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    """根据 ID 获取用户详情。"""
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID '{user_id}' 不存在"
        )
    return user


@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_update: User):
    """更新用户信息。"""
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID '{user_id}' 不存在"
        )
    
    # 更新字段（排除主键和关系字段）
    update_data = user_update.model_dump(exclude={'id', 'posts'}, exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await user.save()
    return user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    """删除用户（及其所有文章）。"""
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID '{user_id}' 不存在"
        )
    
    # 删除用户（关联的文章会被外键约束处理，或手动删除）
    await user.delete()
    return None
```

### 6.2 文章管理路由

```python
# app/main.py（追加）

@app.post("/posts/", response_model=Post, status_code=status.HTTP_201_CREATED)
async def create_post(post: Post):
    """
    创建新文章。
    
    - **title**: 标题（必填，最大200字符）
    - **content**: 内容（必填）
    - **summary**: 摘要（可选）
    - **is_published**: 是否发布（可选，默认为 false）
    - **user_id**: 作者ID（必填）
    """
    # 验证作者是否存在
    author = await User.find_one(str(post.user_id))
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"作者 ID '{post.user_id}' 不存在"
        )
    
    await post.save()
    return post


@app.get("/posts/", response_model=List[Post])
async def list_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_published: Optional[bool] = Query(None),
    user_id: Optional[str] = Query(None, description="按作者筛选")
):
    """获取文章列表（支持分页和筛选）。"""
    query = Post.query()
    
    if is_published is not None:
        query = query.where(Post.c.is_published == is_published)
    
    if user_id:
        query = query.where(Post.c.user_id == user_id)
    
    # 对于 SQLite，我们需要确保正确使用 LIMIT 和 OFFSET
    # 按创建时间降序排序（最新的在前）
    posts = await query.order_by((Post.c.created_at, "DESC")).limit(limit).offset(skip).all()
    return posts


@app.get("/posts/{post_id}", response_model=Post)
async def get_post(post_id: str):
    """根据 ID 获取文章详情。"""
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文章 ID '{post_id}' 不存在"
        )
    return post


@app.put("/posts/{post_id}", response_model=Post)
async def update_post(post_id: str, post_update: Post):
    """更新文章信息。"""
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文章 ID '{post_id}' 不存在"
        )
    
    update_data = post_update.model_dump(exclude={'id', 'author'}, exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)
    
    await post.save()
    return post


@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: str):
    """删除文章。"""
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文章 ID '{post_id}' 不存在"
        )
    
    await post.delete()
    return None
```

### 6.3 关联查询路由

```python
# app/main.py（追加）

@app.get("/users/{user_id}/posts", response_model=List[Post])
async def get_user_posts(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """获取指定用户的所有文章。"""
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 ID '{user_id}' 不存在"
        )
    
    # 使用关系查询
    posts = await user.posts_query().limit(limit).offset(skip).all()
    return posts


@app.get("/posts/{post_id}/author", response_model=User)
async def get_post_author(post_id: str):
    """获取文章的作者信息。"""
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"文章 ID '{post_id}' 不存在"
        )
    
    author = await post.author_query().one()
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="作者信息不存在"
        )
    
    return author
```

> **🔍 提示词举例**
> 
> **场景**：你想让文章在发布时自动设置发布时间。
> 
> 可以添加一个自定义方法到 Post 模型：
> 
> ```python
> class Post(UUIDMixin, TimestampMixin, AsyncActiveRecord):
>     # ... 字段定义 ...
>     
>     async def publish(self) -> None:
>         """发布文章。"""
>         from datetime import datetime
>         self.is_published = True
>         self.published_at = datetime.now()
>         await self.save()
> 
> # 然后在 API 路由中使用
> @app.post("/posts/{post_id}/publish")
> async def publish_post(post_id: str):
>     post = await Post.find_one(post_id)
>     if not post:
>         raise HTTPException(status_code=404, detail="文章不存在")
>     await post.publish()
>     return {"message": "文章已发布", "published_at": post.published_at}
> ```

## 常见问题与解决方案

### 问题1："OFFSET 子句需要 LIMIT 子句"

**问题**：SQLite 使用 OFFSET 时需要配合 LIMIT。

**解决方案**：始终先使用 LIMIT 再使用 OFFSET：
```python
# 错误
users = await query.offset(skip).limit(limit).all()

# 正确
users = await query.limit(limit).offset(skip).all()
```

### 问题2：关系查询方法

**问题**：使用 `model.relation().query()` 导致 AttributeError。

**解决方案**：使用 `model.relation_query()`：
```python
# 错误
posts = await user.posts().query().limit(limit).offset(skip).all()

# 正确
posts = await user.posts_query().limit(limit).offset(skip).all()
```

### 问题3：查询方法名称

**问题**：使用 `query().first()` 导致 AttributeError。

**解决方案**：使用 `query().one()`：
```python
# 错误
existing = await User.query().where(User.c.username == user.username).first()

# 正确
existing = await User.query().where(User.c.username == user.username).one()
```

### 问题4：排序

**说明**：API现在通过查询参数支持灵活的排序选项。

**使用示例**：
```python
# 升序排序（默认）：
users = await query.order_by(User.c.created_at).limit(limit).offset(skip).all()

# 降序排序：
users = await query.order_by((User.c.created_at, "DESC")).limit(limit).offset(skip).all()

# 按不同字段排序：
users = await query.order_by(User.c.username).limit(limit).offset(skip).all()

# 混合排序：
users = await query.order_by((User.c.created_at, "DESC"), User.c.username).limit(limit).offset(skip).all()
```

实现的API端点接受`sort_by`和`sort_order`查询参数：
- `sort_by`：排序字段（例如"user.created_at"、"username"）
- `sort_order`：排序方向（"asc"或"desc"）

## 7. 运行与测试

### 7.1 启动应用

```bash
# 使用 uvicorn 启动（推荐用于开发）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用 python 直接运行
python -m uvicorn app.main:app --reload
```

### 7.2 访问文档

启动后，访问自动生成的 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 7.3 测试 API

使用 curl 或 httpie 测试：

```bash
# 1. 创建用户
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "bio": "Python 开发者"
  }'

# 2. 获取用户列表
curl "http://localhost:8000/users/"

# 3. 创建文章（假设用户ID是返回的UUID）
curl -X POST "http://localhost:8000/posts/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "我的第一篇文章",
    "content": "这是文章内容...",
    "user_id": "替换为实际的用户ID"
  }'

# 4. 获取用户的所有文章
curl "http://localhost:8000/users/用户ID/posts"
```

## 8. 最佳实践

### 8.1 请求/响应模型分离

虽然 `ActiveRecord` 模型可以直接用作请求体，但在复杂场景下，建议创建专门的 Pydantic 模型：

```python
# app/schemas.py
from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    """创建用户的请求模型。"""
    username: str
    email: str
    bio: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应模型。"""
    id: str
    username: str
    email: str
    bio: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True


# 在路由中使用
@app.post("/users/", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    user = User(**user_data.model_dump())
    await user.save()
    return user
```

### 8.2 错误处理

创建全局异常处理器：

```python
# app/main.py（追加）
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """处理请求验证错误。"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "请求数据验证失败",
            "errors": exc.errors()
        }
    )
```

### 8.3 依赖注入最佳实践

对于需要事务管理的场景：

```python
from fastapi import Depends
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_transaction():
    """提供事务上下文。"""
    backend = await Database.get_backend()
    try:
        await backend.transaction_manager.begin()
        yield backend
        await backend.transaction_manager.commit()
    except Exception:
        await backend.transaction_manager.rollback()
        raise

@app.post("/users/batch")
async def create_users_batch(users: List[User], tx=Depends(get_transaction)):
    """批量创建用户（事务保证）。"""
    for user in users:
        await user.save()
    return {"created": len(users)}
```

### 8.4 生产环境配置

```python
import os

# 生产环境建议使用更健壮的配置
app = FastAPI(
    title="博客系统 API",
    description="...",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEBUG") else None,  # 生产环境关闭文档
    redoc_url="/redoc" if os.getenv("DEBUG") else None,
    lifespan=lifespan
)
```

---

## 下一步

你已经完成了 FastAPI 与 rhosocial-activerecord 的集成！接下来可以探索：

- **[GraphQL 集成](graphql.md)**：构建更灵活的 API 接口
- **[高级查询技巧](../query_advanced/)**：使用窗口函数、CTE 等高级特性
- **[性能优化](../performance/)**：为你的 API 添加缓存和优化策略

> **💡 提示词举例**
> 
> **场景**：你希望为 API 添加认证和权限控制。
> 
> 可以使用 FastAPI 的依赖注入结合 `rhosocial-activerecord` 的查询能力：
> 
> ```python
> from fastapi.security import HTTPBearer
> 
> security = HTTPBearer()
> 
> async def get_current_user(token: str = Depends(security)) -> User:
>     """根据 Token 获取当前用户。"""
>     # 验证 token 并获取用户ID
>     user_id = verify_token(token.credentials)
>     user = await User.find_one(user_id)
>     if not user:
>         raise HTTPException(status_code=401, detail="无效的用户")
>     return user
> 
> @app.get("/users/me", response_model=User)
> async def get_me(current_user: User = Depends(get_current_user)):
>     """获取当前登录用户信息。"""
>     return current_user
> ```
