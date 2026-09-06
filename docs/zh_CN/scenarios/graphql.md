# GraphQL 集成

GraphQL 是一种强大的 API 查询语言，允许客户端精确请求所需的数据。`rhosocial-activerecord` 可以与 Python 生态中的 GraphQL 库（如 `graphene`）无缝集成。

本章将演示如何构建一个包含 `User` (用户), `Post` (文章), `Comment` (评论) 的社交网络 API，并使用 FastAPI 作为 Web 服务器。

> 完整的可运行示例代码位于 `docs/examples/chapter_14_scenarios/graphql_fastapi/`，其中的测试已全部通过。

## 核心架构

*   **Web 框架**: FastAPI (异步)
*   **GraphQL 库**: Graphene (异步执行)
*   **ORM**: rhosocial-activerecord (异步 SQLite，`AsyncActiveRecord`)
*   **并发模型**: 使用 `AsyncBackendPool` + 请求级 `contextvar` 隔离（与 [FastAPI 场景](fastapi.md) 相同）
*   **N+1 优化**: 使用 `aiodataloader` 进行批量加载
*   **建表**: 由模型推导 DDL（`generate_create_table()`），无需手写 SQL

## 目录

1. [理解 GraphQL Schema](#1-理解-graphql-schema)
2. [模型定义 (Models)](#2-模型定义-models)
3. [数据库：连接池 + 推导 DDL](#3-数据库连接池--推导-ddl)
4. [定义 Schema（Type + Resolver）](#4-定义-schema-type--resolver)
5. [解决 N+1 问题 (DataLoader)](#5-解决-n1-问题-dataloader)
6. [FastAPI 服务入口](#6-fastapi-服务入口)
7. [开发者如何使用 GraphQL](#7-开发者如何使用-graphql)
8. [在 Postman 中验证](#8-在-postman-中验证)
9. [运行与测试](#9-运行与测试)
10. [常见问题](#10-常见问题)

## 1. 理解 GraphQL Schema

**Schema（模式）是 GraphQL 的核心**，也是与 REST 最大的不同点。在 REST 中，每个端点（如 `GET /users/:id`）由服务端硬编码返回结构；而在 GraphQL 中，服务端通过一份 **Schema** 声明「客户端可以查询什么、每个对象有哪些字段」，客户端再按需挑选。

```
┌─────────────┐   Schema 声明类型与字段   ┌──────────────────┐
│  客户端/工具  │ ──────────────────────► │  Schema          │
│ (Postman等)  │ ◄────────────────────── │  query { users } │
└─────────────┘   introspection 发现能力   └──────────────────┘
```

### Schema 回答的三个问题

| 问题 | 对应 Schema 元素 | 本例 |
|------|------------------|------|
| 我能发起什么查询？ | `Query` 类型（根类型） | `users`、`posts`、`user(id)`、`post(id)` |
| 每个对象长什么样？ | `ObjectType`（对象类型） | `UserType`、`PostType`、`CommentType` |
| 字段是单个还是列表/是否必填？ | 字段类型 `String`/`[PostType]`、`!` 非空标记 | `id: String`、`posts: [PostType]` |

**模型 vs Schema 类型**：`ActiveRecord` 模型（`User`）描述**数据库表**；GraphQL 类型（`UserType`）描述**对外暴露的 API 形状**。二者可以不一致——Schema 只暴露你显式声明的字段，天然起到「接口白名单」作用。

### 让 Schema 可见：打印与 introspection

Schema 可打印为标准 Schema Definition Language (SDL)：

```python
from app.schema import schema

print(schema)
# 输出：
# type Query {
#   users: [UserType]
#   user(id: String!): UserType
#   ...
# }
# type UserType {
#   id: String
#   username: String
#   ...
# }
```

客户端（GraphiQL、Postman）通过标准的 **`__schema` introspection 查询** 自动发现你的 API 能力，无需额外文档：

```graphql
query IntrospectionQuery {
  __schema {
    queryType { name }
    types { name kind }
  }
}
```

> Schema 一旦定义，它就是**前后端之间的契约**：字段的增删改都反映在 Schema 上，客户端可据 introspection 自动补全。

## 2. 模型定义 (Models)

定义三个关联模型，启用 `FieldProxy`，并使用 `UseSqlType` 显式声明列类型：

```python
# app/models.py
import uuid
from typing import Annotated, ClassVar

from rhosocial.activerecord.base import FieldProxy, UseSqlType
from rhosocial.activerecord.backend.expression.types import TextType, VarCharType
from rhosocial.activerecord.field import DefaultTimestampMixin, UUIDMixin
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.relation import AsyncBelongsTo, AsyncHasMany


class User(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    __table_name__ = "users"

    username: Annotated[str, UseSqlType(VarCharType(length=50))]
    email: Annotated[str, UseSqlType(VarCharType(length=120))]

    c: ClassVar[FieldProxy] = FieldProxy()
    posts: ClassVar[AsyncHasMany["Post"]] = AsyncHasMany(foreign_key="user_id", inverse_of="user")
    comments: ClassVar[AsyncHasMany["Comment"]] = AsyncHasMany(foreign_key="user_id", inverse_of="user")


class Post(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    __table_name__ = "posts"

    user_id: uuid.UUID
    title: Annotated[str, UseSqlType(VarCharType(length=200))]
    content: Annotated[str, UseSqlType(TextType())]

    c: ClassVar[FieldProxy] = FieldProxy()
    user: ClassVar[AsyncBelongsTo["User"]] = AsyncBelongsTo(foreign_key="user_id", inverse_of="posts")
    comments: ClassVar[AsyncHasMany["Comment"]] = AsyncHasMany(foreign_key="post_id", inverse_of="post")


class Comment(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    __table_name__ = "comments"

    user_id: uuid.UUID
    post_id: uuid.UUID
    content: Annotated[str, UseSqlType(TextType())]

    c: ClassVar[FieldProxy] = FieldProxy()
    user: ClassVar[AsyncBelongsTo["User"]] = AsyncBelongsTo(foreign_key="user_id", inverse_of="comments")
    post: ClassVar[AsyncBelongsTo["Post"]] = AsyncBelongsTo(foreign_key="post_id", inverse_of="comments")
```

## 3. 数据库：连接池 + 推导 DDL

与 FastAPI 场景完全相同的连接池模式（详见 [FastAPI 集成 · 连接池与推导 DDL](fastapi.md#4-连接池与推导-ddl)）：

```python
# app/database.py
from typing import AsyncGenerator, List, Type

from fastapi import Request
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.connection.pool import AsyncBackendPool, PoolConfig
from rhosocial.activerecord.interface.model import IAsyncActiveRecord


async def create_pool(config: SQLiteConnectionConfig) -> AsyncBackendPool:
    pool_config = PoolConfig(
        min_size=2, max_size=10, connection_mode="auto",
        backend_factory=lambda: AsyncSQLiteBackend(connection_config=config),
    )
    return await AsyncBackendPool.create(pool_config)


async def create_schema(models: List[Type[IAsyncActiveRecord]]) -> None:
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    for model in models:
        expr = model.generate_create_table(if_not_exists=True)
        sql, params = expr.to_sql()
        await model.backend().execute(sql, params, options=options)


async def get_db_context(request: Request) -> AsyncGenerator[None, None]:
    """为当前请求借出一个独立连接（原生 async generator 依赖）。"""
    pool: AsyncBackendPool = request.app.state.pool
    async with pool.connection():
        yield
```

## 4. 定义 Schema（Type + Resolver）

定义 Schema 通常分三步：

1. 为每个模型定义一个 **`ObjectType`**（GraphQL 对象类型），声明暴露哪些字段；
2. 定义 **根 `Query` 类型**（入口查询），声明可用的查询及其参数；
3. 组装成 **`Schema`** 实例。

### 第 1 步：定义 ObjectType

每个 `ObjectType` 用 Graphene 的字段语法声明（`String`、`Int`、`Field(...)`、`List(...)`），并配上 `resolve_*` 方法作为 **resolver**——决定该字段的数据从哪来：

```python
# app/schema.py
from graphene import Field, List, ObjectType, Schema, String


class UserType(ObjectType):
    id = String()
    username = String()
    email = String()
    posts = List(lambda: PostType)          # 关联：User 的多篇文章

    async def resolve_posts(root, info):
        # root 是 User 模型实例；返回它的文章列表
        return await info.context["loaders"].posts_by_user_loader.load(root.id)


class PostType(ObjectType):
    id = String()
    title = String()
    content = String()
    user = Field(UserType)
    comments = List(lambda: CommentType)

    async def resolve_user(root, info):
        return await info.context["loaders"].user_loader.load(root.user_id)

    async def resolve_comments(root, info):
        return await info.context["loaders"].comments_by_post_loader.load(root.id)


class CommentType(ObjectType):
    id = String()
    content = String()
    user = Field(UserType)
    post = Field(PostType)

    async def resolve_user(root, info):
        return await info.context["loaders"].user_loader.load(root.user_id)

    async def resolve_post(root, info):
        return await info.context["loaders"].post_loader.load(root.post_id)
```

> `root`（resolver 的第一个参数）是父字段返回的对象。`info.context` 携带请求级上下文——这里我们把 `loaders`（DataLoader 集）放进 context，供 resolver 使用。

### 第 2 步：定义根 Query 类型

`Query` 是 GraphQL 查询的**入口**。`user(id: String!)` 声明了一个带必填参数 `id` 的查询字段：

```python
# app/schema.py（续）
class Query(ObjectType):
    users = List(UserType)
    posts = List(PostType)
    user = Field(UserType, id=String(required=True))
    post = Field(PostType, id=String(required=True))

    async def resolve_users(root, info):
        return await User.find_all()

    async def resolve_posts(root, info):
        return await Post.find_all()

    async def resolve_user(root, info, id):
        return await User.find_one(id)

    async def resolve_post(root, info, id):
        return await Post.find_one(id)
```

### 第 3 步：组装 Schema

```python
# app/schema.py（结尾）
schema = Schema(query=Query)
```

> 一个 Schema 只暴露 `Query` 表示它是「只读」API。若要支持写操作，需再定义 `Mutation` 类型并传给 `Schema(query=..., mutation=...)`——本例聚焦查询与 N+1 优化，故省略。

## 5. 解决 N+1 问题 (DataLoader)

GraphQL 最常见的性能陷阱是 N+1 问题。例如，查询 10 篇文章的作者，可能会触发 1 次查询文章 + 10 次查询用户。

我们使用 `aiodataloader` (异步 DataLoader) 来解决这个问题。**由于模型是异步的，`batch_load_fn` 直接 `await` 查询即可**——不再需要 `run_in_threadpool`。

```python
# app/schema.py
from aiodataloader import DataLoader
from .models import Comment, Post, User


class UserLoader(DataLoader):
    async def batch_load_fn(self, keys):
        users = await User.query().where(User.c.id.in_(keys)).all()
        user_map = {str(u.id): u for u in users}
        return [user_map.get(str(k)) for k in keys]


class PostsByUserLoader(DataLoader):
    async def batch_load_fn(self, user_ids):
        posts = await Post.query().where(Post.c.user_id.in_(user_ids)).all()
        from collections import defaultdict

        posts_by_user = defaultdict(list)
        for post in posts:
            posts_by_user[str(post.user_id)].append(post)
        return [posts_by_user.get(str(uid), []) for uid in user_ids]


class CommentsByPostLoader(DataLoader):
    async def batch_load_fn(self, post_ids):
        comments = await Comment.query().where(Comment.c.post_id.in_(post_ids)).all()
        from collections import defaultdict

        comments_by_post = defaultdict(list)
        for comment in comments:
            comments_by_post[str(comment.post_id)].append(comment)
        return [comments_by_post.get(str(pid), []) for pid in post_ids]


class Loaders:
    """每个请求独立创建一组 DataLoader，避免跨请求缓存串扰。"""

    def __init__(self):
        self.user_loader = UserLoader()
        self.post_loader = PostLoader()
        self.posts_by_user_loader = PostsByUserLoader()
        self.comments_by_post_loader = CommentsByPostLoader()
```

> **为什么每个请求新建 `Loaders`**：DataLoader 会缓存本批次已加载的 key。如果复用跨请求的 DataLoader，一个请求的缓存可能让另一个请求读到过期数据。每个请求创建新实例，保证数据新鲜。

## 6. FastAPI 服务入口

```python
# app/main.py
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .database import (configure_models, create_pool, create_schema,
                       get_db_context, make_connection_config)
from .models import Comment, Post, User
from .schema import Loaders, schema

ALL_MODELS = [User, Post, Comment]


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = make_connection_config(database="graphql.db")
    configure_models(ALL_MODELS, config)
    pool = await create_pool(config)
    app.state.pool = pool

    async with pool.connection():
        await create_schema(ALL_MODELS)
        if await User.query().count() == 0:
            alice = User(username="alice", email="alice@example.com")
            await alice.save()
            bob = User(username="bob", email="bob@example.com")
            await bob.save()
            p1 = Post(user_id=alice.id, title="Hello GraphQL", content="A post about GraphQL.")
            await p1.save()
            p2 = Post(user_id=alice.id, title="FastAPI Integration", content="FastAPI + Graphene.")
            await p2.save()
            await Comment(user_id=bob.id, post_id=p1.id, content="Great post!").save()
            await Comment(user_id=alice.id, post_id=p1.id, content="Thanks Bob!").save()

    yield
    await pool.close()


app = FastAPI(title="博客 GraphQL API",
              description="rhosocial-activerecord + Graphene + FastAPI",
              version="1.0.0", lifespan=lifespan)


@app.post("/graphql", dependencies=[Depends(get_db_context)])
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

    context = {"request": request, "loaders": Loaders()}
    result = await schema.execute_async(
        query,
        variable_values=variables,
        context_value=context,
        operation_name=operation_name,
    )

    response_data = {}
    if result.data:
        response_data["data"] = result.data
    if result.errors:
        response_data["errors"] = [{"message": str(e)} for e in result.errors]
    return JSONResponse(response_data)
```

要点：

- **`schema.execute_async`**：Graphene 的异步执行入口（resolver 是 coroutine，必须用异步执行）。
- **`get_db_context` 依赖**：挂在整个 `/graphql` 路由上，单个 GraphQL 查询内所有 resolver 共享同一个请求连接（因为依赖上下文在整个请求期间有效）。
- **`context`**：把 `loaders` 放进 GraphQL context，resolver 通过 `info.context["loaders"]` 访问。

### GraphiQL 交互界面

浏览器访问 `GET /graphql` 会返回一个可交互的 GraphiQL 页面，内置文档浏览器与自动补全：

```python
@app.get("/graphql")
async def graphiql_interface():
    html = """<!DOCTYPE html>
    <html><head>
      <link rel="stylesheet" href="https://unpkg.com/graphiql/graphiql.min.css" />
    </head><body>
      <div id="graphiql">Loading...</div>
      <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
      <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
      <script crossorigin src="https://unpkg.com/graphiql/graphiql.min.js"></script>
      <script>
        const root = ReactDOM.createRoot(document.getElementById('graphiql'));
        root.render(React.createElement(GraphiQL, {
          fetcher: GraphiQL.createFetcher({ url: '/graphql' })
        }));
      </script>
    </body></html>"""
    return HTMLResponse(html)
```

## 7. 开发者如何使用 GraphQL

对调用方（前端、Postman、脚本）来说，GraphQL 只有**一个端点**（`POST /graphql`），所有查询都通过请求体描述。

### 请求格式

客户端向 `POST /graphql` 发送 JSON，字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `query` | ✅ | GraphQL 查询字符串 |
| `variables` | 可选 | 变量字典（与查询中的 `$var` 对应） |
| `operationName` | 可选 | 当请求含多个操作时指定执行哪一个 |

```json
{
  "query": "query GetUser($id: String!) { user(id: $id) { id username email } }",
  "variables": { "id": "550e8400-e29b-41d4-a716-446655440000" }
}
```

### 基础查询：按需取字段

客户端**只取需要的字段**，这是 GraphQL 的核心优势：

```graphql
query {
  users {
    id
    username
  }
}
```

响应中**只包含**你请求的字段，不多不少：

```json
{
  "data": {
    "users": [
      { "id": "550e8400-...", "username": "alice" }
    ]
  }
}
```

### 嵌套查询与别名

可一次遍历多层关联（这正是 N+1 优化的用武之地）：

```graphql
query {
  users {
    username
    posts {
      title
      comments {
        content
      }
    }
  }
}
```

若需同字段多次查询且结果不同，用**别名**区分：

```graphql
query {
  firstUser: users { username }
  firstPost: posts { title }
}
```

### 带变量与必填参数

单个用户查询带必填 `id` 参数：

```graphql
query GetUser($id: String!) {
  user(id: $id) {
    id
    username
    email
  }
}
```

配合请求体的 `variables`：

```json
{ "query": "query GetUser($id: String!) { ... }", "variables": { "id": "..." } }
```

### Fragment 复用字段

用 fragment 复用公共字段集：

```graphql
query {
  users {
    ...UserSummary
    posts { title }
  }
  posts {
    user { ...UserSummary }
  }
}

fragment UserSummary on UserType {
  id
  username
}
```

### 错误响应

查询出错时返回 `errors`，不影响其他字段：

```json
{
  "errors": [{ "message": "Relation 'x' not found ..." }]
}
```

### 用 introspection 探索 API

无需文档，直接查 Schema 即可发现可用查询与字段：

```graphql
{
  __schema {
    queryType { name }
    types { name }
  }
}
```

## 8. 在 Postman 中验证

Postman 原生支持 GraphQL，可发请求、管理变量、看文档与自动补全。

### 方式 A：使用 Postman 的 GraphQL 请求类型（推荐）

1. **新建请求**：点击 `New` → `HTTP Request`。
2. **设置方法与 URL**：方法选 `POST`，URL 填 `http://localhost:8000/graphql`。
3. **切换请求类型为 GraphQL**：在 Body 一栏选择 `GraphQL`（而非 `raw`）。此时 Postman 自动读取服务端 introspection，右侧出现 **Docs** 与自动补全。
4. **在 Query 编辑器中输入**：

   ```graphql
   query {
     users {
       id
       username
       posts {
         title
       }
     }
   }
   ```

5. 点 **Send**，即可在下方看到返回的 JSON `data`。

### 方式 B：当作普通 JSON POST（等效）

GraphQL 端点本质就是一个 JSON POST。若不想用 GraphQL 类型，可手动构造：

1. 新建请求，方法 `POST`，URL `http://localhost:8000/graphql`。
2. Body 选 **raw**，类型选 **JSON**，输入：

   ```json
   {
     "query": "{ users { id username } }"
   }
   ```

3. Send，得到 `{"data":{"users":[...]}}`。

### 使用变量

1. 在 Query 中声明变量：`query GetUser($id: String!) { user(id: $id) { username } }`
2. 点 Query 下方的 **Variables** 标签（GraphQL 类型）或 body 中加入 `variables`（JSON 类型），输入：

   ```json
   { "id": "550e8400-e29b-41d4-a716-446655440000" }
   ```

### 查看请求历史与集合

- 每个请求都会出现在左侧 **History**。
- 把请求保存到 Collection，便于团队成员共享与运行。
- 可用 Postman **环境变量**（如 `{{graphql_url}}`）管理不同环境的 URL。

### 常用验证查询

| 目的 | 查询 |
|------|------|
| 列出所有用户 | `{ users { id username email } }` |
| 单用户及其文章 | `query($id: String!){ user(id:$id){ username posts{ title } } }` |
| 文章+作者+评论 | `{ posts { title user{username} comments{content} } }` |
| 发现 Schema | `{ __schema { types { name } } }` |

> **提示**：先启动服务（`uvicorn app.main:app --reload --port 8000`），Postman 的 GraphQL 类型会自动读取 introspection；若自动补全不出现，先执行一次 `{ __schema { types { name } } }` 触发 introspection 缓存。

## 9. 运行与测试

### 启动

```bash
uvicorn app.main:app --reload --port 8000
```

访问 `http://localhost:8000/graphql`（GraphiQL 交互界面）。

### 集成测试

示例附带 `tests/test_graphql.py`：

```bash
PYTHONPATH=docs/examples/chapter_14_scenarios/graphql_fastapi \
    pytest -o asyncio_mode=auto docs/examples/chapter_14_scenarios/graphql_fastapi/tests/
```

## 10. 常见问题

### 为什么 `schema.execute` 报 "can't be awaited"？

graphene 的 `Schema.execute` 是**同步**入口；当 resolver 是 `async` 时必须使用 **`schema.execute_async`**：

```python
# ❌
result = await schema.execute(query, ...)

# ✅
result = await schema.execute_async(query, ...)
```

### 为什么查询返回空数据？

若种子数据在**单独的事件循环**中插入，而请求运行在**另一个**事件循环，连接池会跨 loop 报错或读到空数据。务必把「建池 → 建表 → 种子 → 请求 → 关池」放在**同一个** `asyncio.run()` 内（示例测试即如此）。

### 为什么某个字段返回 null？

- 该字段的 resolver 抛错：看响应 `errors`。
- 关联数据未加载：确认 resolver 使用 DataLoader 且已传入 context。
- 模型实例上该属性确实为空（如用户无文章，`posts` 应为 `[]` 而非 `null`）。

### 如何增加写操作（Mutation）？

当前 Schema 只有 `Query`（只读）。添加写操作需定义 `Mutation`：

```python
from graphene import Mutation, String

class CreateUser(Mutation):
    class Arguments:
        username = String(required=True)
        email = String(required=True)

    user = Field(lambda: UserType)

    async def mutate(root, info, username, email):
        user = User(username=username, email=email)
        await user.save()
        return CreateUser(user=user)


class Mutation(ObjectType):
    create_user = CreateUser.Field()


schema = Schema(query=Query, mutation=Mutation)
```

客户端这样调用（返回的是 `CreateUser` 上的 `user` 字段，因此用嵌套选择）：

```graphql
mutation {
  createUser(username: "carol", email: "carol@example.com") {
    user {
      id
      username
    }
  }
}
```

### N+1 查询如何验证？

对比关闭/开启 DataLoader 的 SQL 数量。DataLoader 将 N 次子查询合并为 1 次 `IN` 查询——这正是 `User.c.id.in_(keys)` 的作用。

---

## 下一步

- **[FastAPI 集成](fastapi.md)**：REST API + 连接池 + Prometheus 指标
- **[查询接口](../querying/README.md)**：ActiveQuery / CTEQuery / SetOperationQuery