# FastAPI Integration

FastAPI is a modern, high-performance Python web framework with a natural fit for `rhosocial-activerecord` — because `ActiveRecord` models are essentially `Pydantic` models, you can use them directly as FastAPI request bodies and response models without any extra serialization layer.

This chapter walks through building a complete **blog REST API** with user management, post publishing, and relational queries. We use the **async** approach (FastAPI's recommended mode) and focus on **connection isolation for parallel requests**, **derived DDL**, **logging**, and **Prometheus metrics**.

> The complete runnable example lives in `docs/examples/chapter_14_scenarios/fastapi_blog/`; its tests all pass.

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Environment Setup](#2-environment-setup)
3. [Defining Models](#3-defining-models)
4. [Connection Pool & Derived DDL](#4-connection-pool--derived-ddl)
5. [Creating the FastAPI Application](#5-creating-the-fastapi-application)
6. [Implementing API Routes](#6-implementing-api-routes)
7. [Logging Configuration](#7-logging-configuration)
8. [Prometheus Metrics](#8-prometheus-metrics)
9. [Running and Testing](#9-running-and-testing)
10. [Connection Isolation for Parallel Requests](#10-connection-isolation-for-parallel-requests)
11. [Common Anti-Patterns](#11-common-anti-patterns)
12. [Best Practices](#12-best-practices)

## 1. Project Structure

```
fastapi_blog/
├── app/
│   ├── __init__.py
│   ├── models.py          # AsyncActiveRecord data models
│   ├── database.py        # connection pool + derived DDL + DI
│   ├── logging_conf.py    # logging configuration
│   ├── routes.py          # API routes
│   └── main.py            # FastAPI application entry
├── tests/
│   └── test_api.py        # integration tests (httpx ASGITransport)
└── requirements.txt
```

## 2. Environment Setup

```txt
fastapi>=0.110.0
uvicorn[standard]>=0.30.0
rhosocial-activerecord[async]>=1.0.0.dev
prometheus-client>=0.20.0
prometheus-fastapi-instrumentator>=7.0.0
pytest>=8.0.0
httpx>=0.27.0
```

> `rhosocial-activerecord[async]` installs `aiosqlite` — the driver required by the async SQLite backend. For **sync** use with `SQLiteBackend`, no extra is needed.

## 3. Defining Models

We define `User` and `Post` models to demonstrate a one-to-many relationship (one user has many posts).

> **⚠️ Note**: this chapter uses async models (`AsyncActiveRecord`), FastAPI's recommended mode. All database operations require `await`.

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

Key points:

- **`UseSqlType`**: explicitly declares the SQL column type (`VARCHAR(50)`, `TEXT`, `BOOLEAN`, ...); derived DDL uses it to build `CREATE TABLE`. Without it, the framework infers the type from the Python type.
- **`UseColumn`**: maps a Python attribute name to a database column name.
- Relationship fields must be `ClassVar` so Pydantic does not treat them as fields.

## 4. Connection Pool & Derived DDL

This is the core of the scenario, following real-world practice (e.g. the webcrawler project):

- The application creates an **`AsyncBackendPool`** (async connection pool) at startup
- All models share the same backend class and connection config
- **`generate_create_table()`** derives the DDL from the model — no handwritten SQL

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


def make_connection_config(database: str = "blog.db") -> SQLiteConnectionConfig:
    return SQLiteConnectionConfig(database=database)


def configure_models(models: List[Type[IAsyncActiveRecord]], config: SQLiteConnectionConfig) -> None:
    """Configure backend class and connection config for all models.

    Models do not hold a fixed backend instance; inside ``pool.connection()``,
    ``Model.backend()`` resolves to the connection borrowed by the current request.
    """
    for model in models:
        model.__backend_class__ = AsyncSQLiteBackend
        model.__connection_config__ = config


async def create_schema(models: List[Type[IAsyncActiveRecord]]) -> None:
    """Derived DDL: generate and execute CREATE TABLE from the model definitions."""
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
    """FastAPI dependency: borrow a dedicated connection for the current request.

    This is a native async generator dependency (FastAPI's yield-dependency
    convention). Inside ``async with pool.connection():``, contextvars set the
    current async connection backend, so calls like ``User.query()`` use the
    request-dedicated connection.
    """
    pool: AsyncBackendPool = request.app.state.pool
    async with pool.connection():
        yield
```

> **Important**: `get_db_context` must be a **native async generator** (`async def ... yield`), not decorated with `@asynccontextmanager`. FastAPI identifies yield dependencies via `inspect.isasyncgenfunction`; wrapping with the decorator returns a context-manager object instead of an async generator, causing a `TypeError`.

## 5. Creating the FastAPI Application

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
    # 1. Logging
    setup_logging()
    logger.info("logging initialized")

    # 2. Connection pool
    config = make_connection_config(database="blog.db")
    configure_models(ALL_MODELS, config)
    pool = await create_pool(config)
    app.state.pool = pool

    # 3. Derived DDL + seed data
    async with pool.connection():
        await create_schema(ALL_MODELS)
        if await User.query().count() == 0:
            alice = User(username="alice", email="alice@example.com")
            await alice.save()
            await Post(user_id=alice.id, title="Hello FastAPI", content="First post").save()

    yield
    await pool.close()  # graceful shutdown


app = FastAPI(
    title="Blog API",
    description="rhosocial-activerecord + FastAPI blog example",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
```

> Use **`lifespan`** (`@asynccontextmanager`) instead of the deprecated `@app.on_event("startup")`.

## 6. Implementing API Routes

The router mounts the `get_db_context` dependency, so every request automatically gets a dedicated connection:

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
        raise HTTPException(status_code=409, detail="username already exists")
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
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.post("/posts/", status_code=status.HTTP_201_CREATED)
async def create_post(title: str, content: str, user_id: uuid.UUID):
    if not await User.find_one(user_id):
        raise HTTPException(status_code=404, detail="author not found")
    post = Post(title=title, content=content, user_id=user_id)
    await post.save()
    return post


@router.post("/posts/{post_id}/publish")
async def publish_post(post_id: uuid.UUID):
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="post not found")
    post.is_published = True
    post.published_at = datetime.now(timezone.utc)
    await post.save()
    return post


@router.get("/users/{user_id}/posts")
async def get_user_posts(user_id: uuid.UUID, skip: int = Query(0, ge=0),
                         limit: int = Query(10, ge=1, le=100)):
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return await user.posts_query().limit(limit).offset(skip).all()
```

Key points:

- **`User.c.username`**: `FieldProxy` provides type-safe query building.
- **`user.posts_query()`**: relation query method returning a chainable `ActiveQuery`.
- Queries uniformly use `order_by(...).limit(...).offset(...)`.

## 7. Logging Configuration

The framework provides `ActiveRecordFormatter` for a unified format (module:line) across ORM internal logs and application logs. Following real-world practice: **file rotation + console dual output**, and route uvicorn access logs to the same format.

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

    # route uvicorn access/error logs to root for unified formatting
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv = logging.getLogger(name)
        uv.handlers.clear()
        uv.propagate = True
```

The default `ActiveRecordFormatter` format:

```
2024-01-15 10:30:45,123 - DEBUG - [rhosocial.activerecord.backend.base:42] - Executing query: SELECT * FROM users
```

> The framework's internal ORM loggers default to `propagate=False` and use their own `LoggingConfig`. To see ORM SQL traces in application logs, explicitly adjust the corresponding logger's `propagate` in `logging_conf`.

## 8. Prometheus Metrics

Use `prometheus-fastapi-instrumentator` to collect HTTP metrics automatically and expose a `/metrics` endpoint:

```python
# app/main.py (append)

# Prometheus metrics collection & exposure
_instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    excluded_handlers=["/metrics", "/health"],
)
_instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


@app.get("/health")
async def health():
    """Liveness probe."""
    return {"status": "healthy", "version": "1.0.0"}
```

After startup, visit `http://localhost:8000/metrics`:

```
# HELP http_requests_total Total number of requests by method, status and handler.
# TYPE http_requests_total counter
http_requests_total{handler="/api/users/",method="GET",status="200"} 3.0

# HELP http_request_duration_seconds Latency with only few buckets by handler.
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{handler="/api/users/",le="0.05"} 1.0
...
```

**Prometheus scrape config** (`prometheus.yml`):

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "blog-api"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: /metrics
```

**Business metrics**: beyond HTTP metrics, you can define custom Counter/Histogram/Gauge with `prometheus_client` (e.g. `blog_posts_published_total`, `blog_query_duration_seconds`) and call `inc()` / `observe()` in routes or services. Patterns seen in real projects:

- A decorator that records "service call count + duration" histograms (tagged success/failure)
- A background task that refreshes DB stats (e.g. active user count) into Gauges
- An `app.middleware("http")` that counts unhandled exceptions

**Grafana**: wire Prometheus into Grafana dashboards; for production, refer to the webcrawler project's `docker-compose.monitoring.yml` (Prometheus + Grafana).

## 9. Running and Testing

### Start the Application

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/docs` (Swagger UI) and `http://localhost:8000/metrics` (Prometheus metrics).

### Integration Tests

The example ships `tests/test_api.py`, driving the app in-process with `httpx.ASGITransport` (no real port). A key test case:

```python
async def test_parallel_requests_use_isolated_connections(client):
    """Concurrent requests each use an isolated connection (AsyncBackendPool + contextvar)."""
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

> The tests run the whole lifecycle (pool → derived DDL → seed → requests → close) inside a **single** `asyncio.run()` event loop to avoid using the pool across event loops.

## 10. Connection Isolation for Parallel Requests

This is the most important point for FastAPI async concurrency and the core motivation for using a connection pool.

### The Problem: Sharing a Single Connection

If all models share one backend instance (i.e. one SQLite connection):

- Concurrent requests **interleave** reads/writes on the same connection, producing unpredictable results
- One request's transaction can interfere with another's
- SQLite is also restricted by `check_same_thread` across threads

```python
# ❌ Anti-pattern: all models share one connection (only for single-threaded CLI)
backend = AsyncSQLiteBackend(connection_config=config)
User.__backend__ = backend
Post.__backend__ = backend  # concurrent requests will share this connection
```

### Solution: AsyncBackendPool + contextvar Isolation

`rhosocial-activerecord` provides `AsyncBackendPool`, combined with **contextvars** for request-level connection isolation:

1. **Create the pool in lifespan**: the pool maintains `min_size`–`max_size` independent connections (file-backed SQLite, all pointing to the same data).
2. **Each request borrows a dedicated connection**: the `get_db_context` dependency calls `pool.connection()`, borrowing a request-dedicated connection, bound to the request's async context via `contextvars`.
3. **Models sense the current connection**: `Model.backend()` prefers the contextvar connection (over the class-level backend), so calls like `await User.query()` land on the current request's connection.
4. **Return on request end**: the dependency's `yield` teardown calls `pool.release()` automatically.

Since each request runs in its own asyncio task, its contextvar is invisible to other requests — **concurrent requests each use an independent connection without interference**, while on the single-threaded event loop `check_same_thread=True` is never violated.

```python
async with pool.connection():          # inside a request dependency
    users = await User.query().all()   # uses the current request's connection
```

### Trade-off with a Singleton Backend

| Approach | Concurrency-safe | Use case |
|----------|------------------|----------|
| Singleton backend (shared connection) | ❌ | single-threaded CLI, scripts, tests |
| `AsyncBackendPool` + dependency injection | ✅ | async web services like FastAPI |

> Reminder about `:memory:`: **each connection in the pool has its own independent `:memory:` database** — they cannot see each other's data. Connection-pool scenarios must use a **file database** (or shared-cache mode) so all connections point to the same data.

## 11. Common Anti-Patterns

This section covers the most common pitfalls in FastAPI async concurrency, with real measured results.

### Anti-pattern A: Multiple Models Share One Backend Instance

```python
# ❌ Anti-pattern: all models share the same backend instance (one connection)
backend = AsyncSQLiteBackend(connection_config=config)   # or AsyncMySQLBackend
User.__backend__ = backend
Post.__backend__ = backend      # Post reuses User's connection
```

This makes concurrent requests read/write **the same connection simultaneously**. Under SQLite the problem may be invisible — `aiosqlite` queues every operation onto a **single background thread**, accidentally serializing concurrency so it looks like it "just works":

```python
# Measured: SQLite + shared single connection + 20 concurrent writes
# Result: 20/20 "succeeded" — but only because aiosqlite serializes internally,
# masking the real risk
```

On databases where **each connection can be used concurrently** (MySQL, PostgreSQL), the problem appears immediately. Measured on MySQL 8.0.46 (`docs/examples/chapter_14_scenarios/fastapi_blog/tests/manual_mysql_pool_compare.py`):

```
[Anti-pattern] Models share one backend instance (no connection isolation)
  30 concurrent writes: 1 succeeded / 29 failed
  error type: {'DatabaseError': 29}
  example: DatabaseError: read() called while another coroutine is
           already waiting for incoming data

[Correct] AsyncBackendPool + dedicated connection per request
  30 concurrent writes: 30 succeeded / 0 failed
```

`read() called while another coroutine is already waiting for incoming data` is the classic symptom of a mysql-connector async connection **used by multiple coroutines at once**: one request's read is still in flight while another tries to read/write on the **same connection**.

> Reproduce (when a MySQL test connection is available):
> ```bash
> MYSQL_HOST=... MYSQL_PORT=... MYSQL_USER=root MYSQL_PASSWORD=... \
>     python docs/examples/chapter_14_scenarios/fastapi_blog/tests/manual_mysql_pool_compare.py
> ```

### Anti-pattern B: Assigning `__backend__` Manually, Bypassing `configure()`

```python
# ❌ Anti-pattern: assign the backend instance directly without configure()
backend = AsyncSQLiteBackend(connection_config=config)
User.__backend__ = backend
# Result: missing introspect_and_adapt() (dialect adaptation), first op raises
# DatabaseError: 'SQLite' dialect has not been adapted.
#   Call backend.introspect_and_adapt() or use backend.context() ...
```

`configure()` performs the necessary initialization (dialect adaptation). Manual assignment bypasses it, so the model cannot generate/execute SQL correctly. **Always initialize via `Model.configure(config, BackendClass)`**.

### Anti-pattern C: Dependency Not a Native Async Generator

```python
# ❌ Anti-pattern: decorating the dependency with @asynccontextmanager
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_context(request: Request):
    async with pool.connection():
        yield

# Result: FastAPI raises TypeError
# '_AsyncGeneratorContextManager' object is not an async iterator
```

FastAPI detects yield dependencies via `inspect.isasyncgenfunction`. `@asynccontextmanager` turns the function into an ordinary function returning a context manager, so FastAPI no longer treats it as a yield dependency. **Write it as a native async generator**:

```python
# ✅ Correct
async def get_db_context(request: Request):
    async with pool.connection():
        yield
```

### Anti-pattern D: Each Model `configure()`d with Its Own Connection

```python
# ❌ Anti-pattern: configuring each model separately yields distinct backends/connections
await User.configure(config, AsyncSQLiteBackend)
await Post.configure(config, AsyncSQLiteBackend)
# User.__backend__ and Post.__backend__ are different connections
```

This breaks the semantics of "models share the same data/transactions": `await User.query()` and `await Post.save()` land on **different connections**, so they cannot join the same transaction, and cross-model relational operations break. The correct approach is for all models to share **one connection config** and let the pool hand out a connection per request (see `configure_models` in [Section 4](#4-connection-pool--derived-ddl)).

### Summary

| Scenario | Approach | Result |
|----------|----------|--------|
| Single-threaded CLI / script | `configure()` singleton backend | ✅ |
| FastAPI concurrent requests | Shared backend instance | ❌ MySQL: 1/30 succeeded |
| FastAPI concurrent requests | `AsyncBackendPool` + `get_db_context` dependency | ✅ 30/30 |

Core principle: **never share a backend instance in FastAPI**. Let `AsyncBackendPool` lend an independent connection to each request, isolated via the `get_db_context` dependency + contextvars.

## 12. Best Practices

### Request/Response Model Separation

Although `ActiveRecord` models work directly as request bodies, create dedicated Pydantic models in complex scenarios:

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

### Transaction Management

When you need transactions, use the backend transaction context on top of `get_db_context`:

```python
@router.post("/posts/batch", dependencies=[Depends(get_db_context)])
async def create_posts_batch(posts: list[Post]):
    async with Post.backend().transaction():
        for post in posts:
            await post.save()
    return {"created": len(posts)}
```

### Production Configuration

```python
import os

app = FastAPI(
    docs_url="/docs" if os.getenv("DEBUG") else None,   # disable docs in production
    redoc_url="/redoc" if os.getenv("DEBUG") else None,
    lifespan=lifespan,
)
```

---

## Next Steps

- **[GraphQL Integration](graphql.md)**: building more flexible APIs
- **[Connection Management](../connection/README.md)**: full connection pool & group documentation
- **[Logging](../logging/README.md)**: `LoggingConfig`, data summarization, and formatting