# FastAPI 集成

FastAPI 是一个现代、高性能的 Python Web 框架，与 `rhosocial-activerecord` 有着天然的契合度——因为 `ActiveRecord` 模型本质上就是 `Pydantic` 模型，这意味着你可以直接将它们用作 FastAPI 的请求体和响应模型，无需任何额外的序列化层。

本章将带你从零开始，构建一个完整的**博客系统 REST API**，包含用户管理、文章发布、关联查询等功能。我们将展示 **异步** 实现方式（FastAPI 的推荐模式），并重点讲解**并行请求的连接隔离**、**推导 DDL**、**日志**与 **Prometheus 指标**。

> 完整的可运行示例代码位于 `docs/examples/chapter_14_scenarios/fastapi_blog/`，其中的测试已全部通过。

## 目录

1. [项目结构](#1-项目结构)
2. [环境准备](#2-环境准备)
3. [定义模型](#3-定义模型)
4. [连接池与推导 DDL](#4-连接池与推导-ddl)
5. [创建 FastAPI 应用](#5-创建-fastapi-应用)
6. [实现 API 路由](#6-实现-api-路由)
7. [日志配置](#7-日志配置)
8. [集成 Prometheus 指标](#8-集成-prometheus-指标)
9. [运行与测试](#9-运行与测试)
10. [并行请求的连接隔离](#10-并行请求的连接隔离)
11. [常见错误用法](#11-常见错误用法)
12. [最佳实践](#12-最佳实践)

## 1. 项目结构

```
fastapi_blog/
├── app/
│   ├── __init__.py
│   ├── models.py          # AsyncActiveRecord 数据模型
│   ├── database.py        # 连接池 + 推导 DDL + 依赖注入
│   ├── logging_conf.py    # 日志配置
│   ├── routes.py          # API 路由
│   └── main.py            # FastAPI 应用入口
├── tests/
│   └── test_api.py        # 集成测试（httpx ASGITransport）
└── requirements.txt
```

## 2. 环境准备

```txt
fastapi>=0.110.0
uvicorn[standard]>=0.30.0
rhosocial-activerecord[async]>=1.0.0.dev
prometheus-client>=0.20.0
prometheus-fastapi-instrumentator>=7.0.0
pytest>=8.0.0
httpx>=0.27.0
```

> `rhosocial-activerecord[async]` 会安装 `aiosqlite`——异步 SQLite 后端所必需的驱动。**同步**使用 `SQLiteBackend` 则无需该 extra。

## 3. 定义模型

我们定义 `User` 和 `Post` 两个模型，展示一对多关系（一个用户可以有多篇文章）。

> **⚠️ 注意**：本章使用异步模型 (`AsyncActiveRecord`)，这是 FastAPI 的推荐模式。所有数据库操作都需要使用 `await`。

```python
# app/models.py
import uuid
from typing import Annotated, ClassVar, Optional

from rhosocial.activerecord.base import FieldProxy, UseColumn, UseSqlType
from rhosocial.activerecord.backend.expression.types import (
    BooleanType, DateTimeType, TextType, VarCharType,
)
from rhosocial.activerecord.field import DefaultTimestampMixin, UUIDMixin
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.relation import AsyncBelongsTo, AsyncHasMany


class User(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    __table_name__ = "users"

    username: Annotated[str, UseSqlType(VarCharType(length=50))]
    email: Annotated[str, UseSqlType(VarCharType(length=120))]
    bio: Annotated[Optional[str], UseSqlType(TextType())] = None
    is_active: Annotated[bool, UseSqlType(BooleanType())] = True

    c: ClassVar[FieldProxy] = FieldProxy()
    posts: ClassVar[AsyncHasMany["Post"]] = AsyncHasMany(
        foreign_key="user_id", inverse_of="author"
    )


class Post(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    __table_name__ = "posts"

    title: Annotated[str, UseSqlType(VarCharType(length=200))]
    content: Annotated[str, UseSqlType(TextType())]
    is_published: Annotated[bool, UseSqlType(BooleanType())] = False
    user_id: Annotated[uuid.UUID, UseColumn("user_id")]
    published_at: Annotated[Optional[object], UseSqlType(DateTimeType())] = None

    c: ClassVar[FieldProxy] = FieldProxy()
    author: ClassVar[AsyncBelongsTo["User"]] = AsyncBelongsTo(
        foreign_key="user_id", inverse_of="posts"
    )
```

要点：

- **`UseSqlType`**：显式声明 SQL 列类型（`VARCHAR(50)`、`TEXT`、`BOOLEAN`…），推导 DDL 会据此生成建表语句；不声明时框架按 Python 类型自动推断。
- **`UseColumn`**：控制 Python 属性名与数据库列名的映射。
- 关系字段必须是 `ClassVar`，避免被 Pydantic 当作普通字段。

## 4. 连接池与推导 DDL

这是本场景的核心部分，参考真实项目（如 webcrawler）的实践：

- 应用启动时创建 **`AsyncBackendPool`**（异步连接池）
- 所有模型共享同一份后端类与连接配置
- **`generate_create_table()`** 由模型推导 DDL——不再手写建表 SQL

```python
# app/database.py
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Type

from fastapi import Request
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.connection.pool import AsyncBackendPool, PoolConfig
from rhosocial.activerecord.interface.model import IAsyncActiveRecord


def make_connection_config(database: str = "blog.db") -> SQLiteConnectionConfig:
    return SQLiteConnectionConfig(database=database)


def configure_models(models: List[Type[IAsyncActiveRecord]], config: SQLiteConnectionConfig) -> None:
    """为所有模型配置后端类与连接配置。

    模型不持有固定后端实例；在 ``pool.connection()`` 上下文中，
    ``Model.backend()`` 会优先解析到当前请求借出的连接。
    """
    for model in models:
        model.__backend_class__ = AsyncSQLiteBackend
        model.__connection_config__ = config


async def create_schema(models: List[Type[IAsyncActiveRecord]]) -> None:
    """推导 DDL：由模型定义自动生成并执行 CREATE TABLE。"""
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    for model in models:
        expr = model.generate_create_table(if_not_exists=True)
        sql, params = expr.to_sql()
        await model.backend().execute(sql, params, options=options)


async def create_pool(config: SQLiteConnectionConfig) -> AsyncBackendPool:
    pool_config = PoolConfig(
        min_size=2,
        max_size=10,
        connection_mode="auto",
        backend_factory=lambda: AsyncSQLiteBackend(connection_config=config),
    )
    return await AsyncBackendPool.create(pool_config)


async def get_db_context(request: Request) -> AsyncGenerator[None, None]:
    """FastAPI 依赖：为当前请求借出一个独立连接。

    这是一个原生 async generator 依赖（FastAPI 的 yield 依赖约定）。
    在 ``async with pool.connection():`` 内部，contextvars 会设置当前
    异步连接后端，使 ``User.query()`` 等调用自动使用该请求专属的连接。
    """
    pool: AsyncBackendPool = request.app.state.pool
    async with pool.connection():
        yield
```

> **重要**：`get_db_context` 必须写成**原生 async generator**（`async def ... yield`），不要用 `@asynccontextmanager` 装饰。FastAPI 依赖注入通过 `inspect.isasyncgenfunction` 识别 yield 依赖；用装饰器包装后返回的是 context manager 对象而非 async generator，会导致 `TypeError`。

## 5. 创建 FastAPI 应用

```python
# app/main.py
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from .database import (
    configure_models, create_pool, create_schema, make_connection_config,
)
from .logging_conf import setup_logging
from .models import Post, User
from .routes import router

logger = logging.getLogger("blog")
ALL_MODELS = [User, Post]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 日志
    setup_logging()
    logger.info("日志已初始化")

    # 2. 连接池
    config = make_connection_config(database="blog.db")
    configure_models(ALL_MODELS, config)
    pool = await create_pool(config)
    app.state.pool = pool

    # 3. 推导 DDL 建表 + 种子数据
    async with pool.connection():
        await create_schema(ALL_MODELS)
        if await User.query().count() == 0:
            alice = User(username="alice", email="alice@example.com")
            await alice.save()
            await Post(user_id=alice.id, title="Hello FastAPI", content="First post").save()

    yield
    await pool.close()  # 优雅关闭


app = FastAPI(
    title="博客系统 API",
    description="rhosocial-activerecord + FastAPI 博客示例",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
```

> 使用 **`lifespan`**（`@asynccontextmanager`）而非已弃用的 `@app.on_event("startup")`。

## 6. 实现 API 路由

路由统一挂载 `get_db_context` 依赖，因此每个请求都自动获得独立连接：

```python
# app/routes.py
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .database import get_db_context
from .models import Post, User

router = APIRouter(prefix="/api", dependencies=[Depends(get_db_context)])


@router.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(username: str, email: str, bio: Optional[str] = None):
    if await User.query().where(User.c.username == username).one():
        raise HTTPException(status_code=409, detail="用户名已存在")
    user = User(username=username, email=email, bio=bio)
    await user.save()
    return user


@router.get("/users/")
async def list_users(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100),
                     is_active: Optional[bool] = Query(None)):
    query = User.query()
    if is_active is not None:
        query = query.where(User.c.is_active == is_active)
    return await query.order_by((User.c.created_at, "DESC")).limit(limit).offset(skip).all()


@router.get("/users/{user_id}")
async def get_user(user_id: uuid.UUID):
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("/posts/", status_code=status.HTTP_201_CREATED)
async def create_post(title: str, content: str, user_id: uuid.UUID):
    if not await User.find_one(user_id):
        raise HTTPException(status_code=404, detail="作者不存在")
    post = Post(title=title, content=content, user_id=user_id)
    await post.save()
    return post


@router.post("/posts/{post_id}/publish")
async def publish_post(post_id: uuid.UUID):
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    post.is_published = True
    post.published_at = datetime.now(timezone.utc)
    await post.save()
    return post


@router.get("/users/{user_id}/posts")
async def get_user_posts(user_id: uuid.UUID, skip: int = Query(0, ge=0),
                         limit: int = Query(10, ge=1, le=100)):
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return await user.posts_query().limit(limit).offset(skip).all()
```

要点：

- **`User.c.username`**：`FieldProxy` 提供类型安全的查询构建。
- **`user.posts_query()`**：关系查询方法，返回可继续链式调用的 `ActiveQuery`。
- 查询统一使用 `order_by(...).limit(...).offset(...)`。

## 7. 日志配置

框架提供 `ActiveRecordFormatter`，可为 ORM 内部日志（模块:行号）与应用日志提供统一格式。参考真实项目实践：**文件轮转 + 控制台双输出**，并让 uvicorn 访问日志共享同一格式。

```python
# app/logging_conf.py
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from rhosocial.activerecord.logging import ActiveRecordFormatter


def setup_logging(log_dir: str = "logs", log_filename: str = "blog",
                  level: str = "INFO", when: str = "d", backup_count: int = 7) -> None:
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    formatter = ActiveRecordFormatter()

    file_handler = TimedRotatingFileHandler(
        filename=str(log_path / f"{log_filename}.log"),
        when=when, backupCount=backup_count, encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # uvicorn 访问日志转发到 root，与 ORM 日志格式统一
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv = logging.getLogger(name)
        uv.handlers.clear()
        uv.propagate = True
```

`ActiveRecordFormatter` 的默认格式为：

```
2024-01-15 10:30:45,123 - DEBUG - [rhosocial.activerecord.backend.base:42] - Executing query: SELECT * FROM users
```

> 框架的 ORM 内部日志默认 `propagate=False`，且使用自己的 `LoggingConfig`。如需在应用日志中看到 ORM 的 SQL 追踪，可在 `logging_conf` 中显式调整对应 logger 的 `propagate`。

## 8. 集成 Prometheus 指标

使用 `prometheus-fastapi-instrumentator` 自动采集 HTTP 指标并暴露 `/metrics` 端点：

```python
# app/main.py（追加）

# Prometheus 指标收集与暴露
_instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/metrics", "/health"],
)
_instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health")
async def health():
    """存活探针。"""
    return {"status": "healthy", "version": "1.0.0"}
```

启动后访问 `http://localhost:8000/metrics` 可看到：

```
# HELP http_requests_total Total number of requests by method, status and handler.
# TYPE http_requests_total counter
http_requests_total{handler="/api/users/",method="GET",status="200"} 3.0

# HELP http_request_duration_seconds Latency with only few buckets by handler.
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{handler="/api/users/",le="0.05"} 1.0
...
```

**Prometheus 抓取配置**（`prometheus.yml`）：

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "blog-api"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: /metrics
```

**业务指标**：除 HTTP 指标外，你还可以用 `prometheus_client` 定义自定义 Counter/Histogram/Gauge（如 `blog_posts_published_total`、`blog_query_duration_seconds`），并在路由或服务层 `inc()` / `observe()`。真实项目中可借鉴的做法：

- 用装饰器统一记录「服务调用次数 + 耗时」直方图（成功/失败打标签）
- 用后台定时任务把数据库统计（如活跃用户数）刷新到 Gauge
- 用 `app.middleware("http")` 捕获未处理异常并计数

**Grafana 可视化**：可将 Prometheus 接入 Grafana 面板；生产环境可参考 webcrawler 项目的 `docker-compose.monitoring.yml`（Prometheus + Grafana）。

## 9. 运行与测试

### 启动应用

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000/docs`（Swagger UI）、`http://localhost:8000/metrics`（Prometheus 指标）。

### 集成测试

示例附带 `tests/test_api.py`，使用 `httpx.ASGITransport` 在进程内驱动应用，无需真实端口。核心测试用例：

```python
async def test_parallel_requests_use_isolated_connections(client):
    """并发请求各自使用独立连接（AsyncBackendPool + contextvar 隔离）。"""
    async def hit():
        resp = await client.get("/api/users/")
        assert resp.status_code == 200
        return resp.json()

    results = await asyncio.gather(*[hit() for _ in range(20)])
    assert len(results) == 20
```

```bash
PYTHONPATH=docs/examples/chapter_14_scenarios/fastapi_blog \
    pytest -o asyncio_mode=auto docs/examples/chapter_14_scenarios/fastapi_blog/tests/
```

> 测试将整个生命周期（建池 → 推导 DDL → 种子 → 请求 → 关池）放在**同一个** `asyncio.run()` 事件循环中，避免跨事件循环使用连接池。

## 10. 并行请求的连接隔离

这是 FastAPI 异步并发场景最关键的一点，也是本场景采用连接池的核心动机。

### 问题：共享单个连接的危险

如果所有模型共享**同一个后端实例**（即同一 SQLite 连接），那么：

- 并发请求会**交叉读写**同一个连接，产生不可预测的结果
- 一个请求的事务可能被另一个请求干扰
- SQLite 在跨线程使用时还受 `check_same_thread` 限制

```python
# ❌ 反例：所有模型共享同一连接（仅适合单线程 CLI 场景）
backend = AsyncSQLiteBackend(connection_config=config)
User.__backend__ = backend
Post.__backend__ = backend  # 并发请求将共享此连接
```

### 方案：AsyncBackendPool + contextvar 隔离

`rhosocial-activerecord` 提供 `AsyncBackendPool`，配合 **contextvars** 实现请求级连接隔离：

1. **lifespan 创建连接池**：池中维护 `min_size`~`max_size` 个独立连接（SQLite 文件数据库，每个连接共享同一份数据）。
2. **每个请求借出独立连接**：`get_db_context` 依赖调用 `pool.connection()`，借出**该请求专属**的连接，并通过 `contextvars` 绑定到当前请求的 async 上下文。
3. **模型感知当前连接**：`Model.backend()` 优先返回 contextvar 中的连接（而非类级后端），因此 `await User.query()` 等调用自动落到当前请求的连接上。
4. **请求结束归还**：依赖的 `yield` teardown 阶段自动 `pool.release()`。

由于每个请求运行在独立的 asyncio task 中，其 contextvar 互不可见——**并发的请求各自使用独立连接，互不干扰**，同时事件循环单线程上 `check_same_thread=True` 也永不违反。

```python
async with pool.connection():          # 请求依赖中
    users = await User.query().all()   # 使用当前请求的连接
```

### 与「单例后端」的取舍

| 方式 | 并发安全 | 适用场景 |
|------|----------|----------|
| 单例后端（共享连接） | ❌ | 单线程 CLI、脚本、测试 |
| `AsyncBackendPool` + 依赖注入 | ✅ | FastAPI 等异步 Web 服务 |

> 对 `:memory:` 数据库的提醒：连接池中**每个连接都有独立的 `:memory:` 数据库**，彼此看不到对方的数据。因此连接池场景必须使用**文件数据库**（或共享缓存模式），让所有连接指向同一份数据。

## 11. 常见错误用法

本节展示在 FastAPI 异步并发场景中最容易踩的坑，并附上真实实验结果。

### 错误用法 A：多个模型直接共享同一个后端实例

```python
# ❌ 反例：所有模型共享同一个后端实例（同一连接）
backend = AsyncSQLiteBackend(connection_config=config)   # 或 AsyncMySQLBackend
User.__backend__ = backend
Post.__backend__ = backend      # Post 直接复用 User 的连接
```

这会让并发请求**同时读写同一连接**。在 SQLite 下问题可能不明显——`aiosqlite` 把所有操作排队到**单个后台线程**，意外地串行化了并发，看起来「碰巧能跑」：

```python
# 实测：SQLite + 共享单连接 + 20 并发写入
# 结果：20/20 "成功" —— 但这是因为 aiosqlite 内部串行化，掩盖了真实风险
```

但在 MySQL / PostgreSQL 等**每个连接可被并发使用**的数据库中，问题立刻暴露。本机 MySQL 8.0.46 实测（`docs/examples/chapter_14_scenarios/fastapi_blog/tests/manual_mysql_pool_compare.py`）：

```
[反例] 多个模型共享同一后端实例（不隔离连接）
  30 路并发写入: 成功 1 / 失败 29
  错误类型: {'DatabaseError': 29}
  示例: DatabaseError: read() called while another coroutine is
        already waiting for incoming data

[正确] AsyncBackendPool + 每请求独立连接
  30 路并发写入: 成功 30 / 失败 0
```

`read() called while another coroutine is already waiting for incoming data` 是 mysql-connector 异步连接**被多协程同时使用**的典型错误：一个请求的读取尚未完成，另一个请求又尝试在**同一连接**上读写。

> 复现：`python-activerecord-mysql` 仓库有测试连接可用时，运行
> ```bash
> MYSQL_HOST=... MYSQL_PORT=... MYSQL_USER=root MYSQL_PASSWORD=... \
>     python docs/examples/chapter_14_scenarios/fastapi_blog/tests/manual_mysql_pool_compare.py
> ```

### 错误用法 B：绕过 `configure()`，直接手工设置 `__backend__`

```python
# ❌ 反例：不调用 configure()，直接赋值后端实例
backend = AsyncSQLiteBackend(connection_config=config)
User.__backend__ = backend
# 结果：缺少 introspect_and_adapt()（方言适配），首次操作即抛错
# DatabaseError: 'SQLite' dialect has not been adapted.
#   Call backend.introspect_and_adapt() or use backend.context() ...
```

`configure()` 会执行方言适配（`introspect_and_adapt`）等必要初始化。手工赋值绕过了它，导致模型无法正确生成/执行 SQL。**初始化一律走 `Model.configure(config, BackendClass)`**。

### 错误用法 C：依赖注入不是原生 async generator

```python
# ❌ 反例：用 @asynccontextmanager 装饰依赖
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_context(request: Request):
    async with pool.connection():
        yield

# 结果：FastAPI 抛 TypeError
# '_AsyncGeneratorContextManager' object is not an async iterator
```

FastAPI 通过 `inspect.isasyncgenfunction` 识别 yield 依赖。`@asynccontextmanager` 会把函数变成返回 context manager 的普通函数，FastAPI 便不再把它当作 yield 依赖。**必须写成原生 async generator**：

```python
# ✅ 正确
async def get_db_context(request: Request):
    async with pool.connection():
        yield
```

### 错误用法 D：每个模型各自 `configure()` 出独立连接

```python
# ❌ 反例：每个模型单独 configure，得到不同的后端实例/连接
await User.configure(config, AsyncSQLiteBackend)
await Post.configure(config, AsyncSQLiteBackend)
# User.__backend__ 与 Post.__backend__ 是不同的连接
```

这破坏了「模型共享同一份数据/事务」的语义：`await User.query()` 和 `await Post.save()` 落在**不同连接**上，无法参与同一事务，跨模型关联操作也会失效。正确做法是所有模型共享**同一份连接配置**，通过连接池为每个请求统一借出连接（见[第 4 节](#4-连接池与推导-ddl)的 `configure_models`）。

### 小结

| 场景 | 做法 | 结果 |
|------|------|------|
| 单线程 CLI / 脚本 | `configure()` 单例后端 | ✅ |
| FastAPI 并发请求 | 共享后端实例 | ❌ MySQL 下 1/30 成功 |
| FastAPI 并发请求 | `AsyncBackendPool` + `get_db_context` 依赖 | ✅ 30/30 |

核心原则：**FastAPI 中永远不要共享后端实例**。通过 `AsyncBackendPool` 让每个请求借出独立连接，并用 `get_db_context` 依赖建立 contextvar 隔离。

## 12. 最佳实践

### 请求/响应模型分离

虽然 `ActiveRecord` 模型可直接用作请求体，复杂场景建议创建专门的 Pydantic 模型：

```python
from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    email: str
    bio: str | None = None


@app.post("/users/", response_model=UserCreate)
async def create_user(user_data: UserCreate):
    user = User(**user_data.model_dump())
    await user.save()
    return user
```

### 事务管理

需要事务时，在 `get_db_context` 基础上使用后端事务上下文：

```python
@router.post("/posts/batch", dependencies=[Depends(get_db_context)])
async def create_posts_batch(posts: list[Post]):
    async with Post.backend().transaction():
        for post in posts:
            await post.save()
    return {"created": len(posts)}
```

### 生产环境配置

```python
import os

app = FastAPI(
    docs_url="/docs" if os.getenv("DEBUG") else None,   # 生产关闭文档
    redoc_url="/redoc" if os.getenv("DEBUG") else None,
    lifespan=lifespan,
)
```

---

## 下一步

- **[GraphQL 集成](graphql.md)**：构建更灵活的 API 接口
- **[连接管理](../connection/README.md)**：连接池、连接组的完整说明
- **[日志系统](../logging/README.md)**：`LoggingConfig`、数据摘要与格式定制