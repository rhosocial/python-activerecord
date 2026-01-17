# 11.2 GraphQL 集成 (GraphQL Integration)

GraphQL 是一种强大的 API 查询语言，允许客户端精确请求所需的数据。`rhosocial-activerecord` 可以与 Python 生态中的 GraphQL 库（如 `graphene`）无缝集成。

本章将演示如何构建一个包含 `User` (用户), `Post` (文章), `Comment` (评论) 的社交网络 API，并使用 FastAPI 作为 Web 服务器。

## 核心架构

*   **Web 框架**: FastAPI (支持异步)
*   **GraphQL 库**: Graphene (支持异步执行)
*   **ORM**: rhosocial-activerecord (同步 SQLite)
*   **并发模型**: 由于 ORM 是同步的，而 FastAPI 和 Graphene (v3+) 是异步的，我们将利用 `starlette.concurrency.run_in_threadpool` 在线程池中执行同步的数据库查询，避免阻塞主事件循环。
*   **N+1 优化**: 使用 `aiodataloader` 进行批量加载。

## 1. 模型定义 (Models)

首先定义三个关联模型，并启用 `FieldProxy` 以支持类型安全的查询构建：

```python
# models.py
import uuid
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import BelongsTo, HasMany

class User(UUIDMixin, TimestampMixin, ActiveRecord):
    username: str
    email: str
    
    # Field Proxy
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # Relations
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id')
    comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='user_id')

class Post(UUIDMixin, TimestampMixin, ActiveRecord):
    user_id: uuid.UUID
    title: str
    content: str
    
    # Field Proxy
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # Relations
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')
    comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='post_id')

class Comment(UUIDMixin, TimestampMixin, ActiveRecord):
    user_id: uuid.UUID
    post_id: uuid.UUID
    content: str
    
    # Field Proxy
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # Relations
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')
    post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id')
```

## 2. 解决 N+1 问题 (DataLoader)

GraphQL 最常见的性能陷阱是 N+1 问题。例如，查询 10 篇文章的作者，可能会触发 1 次查询文章 + 10 次查询用户。

我们使用 `aiodataloader` (异步 DataLoader) 来解决这个问题。由于 `rhosocial-activerecord` 是同步的，我们需要在 `batch_load_fn` 中使用 `run_in_threadpool` 来执行实际的数据库查询。

```python
# schema.py
from aiodataloader import DataLoader
from starlette.concurrency import run_in_threadpool
from models import User, Post, Comment

class UserLoader(DataLoader):
    async def batch_load_fn(self, keys):
        # 在线程池中执行同步查询
        def load_users():
            # 使用 FieldProxy 构建类型安全的 IN 查询
            users = User.query().where(User.c.id.in_(keys)).all()
            user_map = {str(u.id): u for u in users}
            return [user_map.get(str(k)) for k in keys]
            
        return await run_in_threadpool(load_users)

class CommentsByPostLoader(DataLoader):
    async def batch_load_fn(self, post_ids):
        def load_comments():
            comments = Comment.query().where(Comment.c.post_id.in_(post_ids)).all()
            
            from collections import defaultdict
            comments_by_post = defaultdict(list)
            for comment in comments:
                comments_by_post[str(comment.post_id)].append(comment)
                
            return [comments_by_post.get(str(pid), []) for pid in post_ids]
            
        return await run_in_threadpool(load_comments)
```

## 3. 定义 Schema

在 Graphene 类型定义中使用异步解析器 (Async Resolvers) 和 DataLoader：

```python
# schema.py
import graphene
from graphene import ObjectType, String, Field, List

class UserType(ObjectType):
    id = String()
    username = String()
    email = String()
    posts = List(lambda: PostType)
    
    async def resolve_posts(root, info):
        return await info.context['loaders'].posts_by_user_loader.load(root.id)

class PostType(ObjectType):
    id = String()
    title = String()
    content = String()
    user = Field(UserType)
    comments = List(lambda: CommentType)
    
    async def resolve_user(root, info):
        return await info.context['loaders'].user_loader.load(root.user_id)
        
    async def resolve_comments(root, info):
        return await info.context['loaders'].comments_by_post_loader.load(root.id)

class CommentType(ObjectType):
    id = String()
    content = String()
    user = Field(UserType)
    post = Field(PostType)
    
    async def resolve_user(root, info):
        return await info.context['loaders'].user_loader.load(root.user_id)

    async def resolve_post(root, info):
        return await info.context['loaders'].post_loader.load(root.post_id)

class Query(ObjectType):
    users = List(UserType)
    posts = List(PostType)

    async def resolve_users(root, info):
        return await run_in_threadpool(lambda: User.find_all())

    async def resolve_posts(root, info):
        return await run_in_threadpool(lambda: Post.find_all())

schema = graphene.Schema(query=Query)
```

## 4. FastAPI 集成

为了在异步的 FastAPI 中运行 GraphQL，我们需要：
1.  在每个请求中初始化 `Loaders`。
2.  使用 `schema.execute_async` 执行异步 GraphQL 查询。

```python
# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from schema import schema, UserLoader, CommentsByPostLoader

app = FastAPI()

class Loaders:
    def __init__(self):
        self.user_loader = UserLoader()
        self.comments_by_post_loader = CommentsByPostLoader()
        # ... 初始化其他 loaders

@app.post("/graphql")
async def graphql_server(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
        
    query = data.get("query")
    variables = data.get("variables")
    operation_name = data.get("operationName")
    
    if not query:
        return JSONResponse({"errors": ["No query provided"]}, status_code=400)

    # 1. 创建上下文，包含本次请求的 Loaders
    context = {"request": request, "loaders": Loaders()}
    
    # 2. 执行异步查询
    result = await schema.execute_async(
        query,
        variable_values=variables,
        context_value=context,
        operation_name=operation_name
    )
    
    response_data = {}
    if result.data:
        response_data["data"] = result.data
    if result.errors:
        response_data["errors"] = [{"message": str(e)} for e in result.errors]
        
    return JSONResponse(response_data)

# 集成 GraphiQL 界面
@app.get("/graphql")
async def graphiql_interface():
    # 返回 GraphiQL HTML 页面 (使用 React 构建)
    return HTMLResponse(...)
```

## 完整示例

完整的代码示例位于 `docs/examples/chapter_09_scenarios/graphql_fastapi` 目录中。

该示例包含：
*   完整的 `User`, `Post`, `Comment` 模型定义。
*   基于 `aiodataloader` 的 N+1 优化实现。
*   集成了 React 版 GraphiQL 界面，可直接在浏览器中测试查询。

### 运行示例

```bash
cd docs/examples/chapter_09_scenarios/graphql_fastapi
pip install -r requirements.txt
python main.py
```

访问 `http://localhost:8000/graphql` 即可使用 GraphiQL 界面。
