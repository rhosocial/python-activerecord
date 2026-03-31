# 线程安全与并发配置 (Thread Safety and Concurrent Configuration)

在多线程环境下——Web 服务器、后台 Worker、异步框架——错误的连接管理是导致数据异常和难以
复现的 Bug 的最常见来源之一。本文介绍在并发场景中正确配置模型所需注意的事项。

> 💡 **AI 提示词：** "我的 Flask/FastAPI 应用在高并发下行为异常——查询偶尔返回错误结果或报错，
> 这有可能是连接问题吗？"

---

## 1. 在应用启动时集中调用 configure()

`configure()` 是**类级别**的操作，它将后端实例赋给模型类，并由该类的所有实例共享。
应在任何请求或 Worker 线程启动之前，恰好调用一次。

```python
# ✅ 正确：在应用启动时配置
# app.py / main.py
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from myapp.models import User, Order, Product

def create_app():
    config = SQLiteConnectionConfig(database="app.db")
    User.configure(config, SQLiteBackend)
    Order.configure(config, SQLiteBackend)   # 共享后端——同一连接池
    # ... 其他初始化 ...
    return app
```

```python
# ❌ 错误：在请求处理函数中调用 configure()
@app.get("/users")
def list_users():
    User.configure(config, SQLiteBackend)   # 每次请求都会重置后端！
    return User.query().all()
```

**为什么有问题**：在请求处理函数中调用 `configure()` 会在每次请求时替换共享后端。
并发负载下，一个请求可能在另一个请求执行查询的中途覆盖其后端，导致数据被读写到错误的数据库。

---

## 2. SQLite 与线程安全

SQLite 的默认连接模式（`check_same_thread=True`）只允许一个线程使用同一个连接。
内置的 `SQLiteBackend` 会处理这一约束，但需要注意以下几点。

### 单线程服务器（开发环境）

Flask 内置开发服务器等单线程服务器下，单个 `SQLiteBackend` 实例是安全的：

```python
# 单线程开发服务器——一个连接，一个线程
config = SQLiteConnectionConfig(database="dev.db")
User.configure(config, SQLiteBackend)
```

### 多线程服务器（生产环境）

对于多线程 WSGI 服务器（Gunicorn sync worker、uWSGI），每个线程必须拥有独立连接。
最简单的做法是在 post-fork 钩子中按进程配置：

```python
# gunicorn.conf.py
def post_fork(server, worker):
    """在 fork 后的每个 Worker 进程中调用。"""
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
    from myapp.models import Base  # 基础模型类或所有模型类

    config = SQLiteConnectionConfig(database="app.db")
    Base.configure(config, SQLiteBackend)
```

> ⚠️ **不要在 fork 前配置**：如果在主进程中调用 `configure()` 后再 fork，所有 Worker
> 会共享同一个连接对象。这是不安全的，会导致 `check_same_thread` 报错或静默的数据损坏。

### 异步服务器（ASGI）

对于运行协程的 ASGI 服务器（Uvicorn、Hypercorn），事件循环运行在单线程中，
因此单个后端实例通常是安全的：

```python
# FastAPI 启动事件
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时配置
    config = SQLiteConnectionConfig(database="app.db")
    User.configure(config, SQLiteBackend)
    yield
    # 关闭时清理（如需要）

app = FastAPI(lifespan=lifespan)
```

---

## 3. MySQL / PostgreSQL 后端

对于服务器型数据库，后端使用连接池。关键参数如下：

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, MySQLConnectionConfig

config = MySQLConnectionConfig(
    host="db.example.com",
    port=3306,
    database="myapp",
    user="app",
    password="...",
    pool_size=5,          # 每个 Worker 进程的连接数
    pool_timeout=30,      # 等待空闲连接的超时秒数
    pool_recycle=3600,    # 1 小时后回收连接
)
User.configure(config, MySQLBackend)
```

**连接池大小经验公式**：

```
pool_size = (每个 Worker 的 CPU 核数) × 2 + 1
```

对于运行 4 个 Gunicorn Worker 的 4 核机器，从每个 Worker `pool_size=9` 开始，
根据实际等待时间调整。

---

## 4. 启动时检测未配置的模型

在所有 `configure()` 调用完成后，立即添加显式检查，在服务任何请求之前捕获遗漏：

```python
REQUIRED_MODELS = [User, Order, Product, UserMetric]

def assert_all_configured():
    unconfigured = [
        cls.__name__
        for cls in REQUIRED_MODELS
        if "__backend__" not in cls.__dict__ or cls.__dict__["__backend__"] is None
    ]
    if unconfigured:
        raise RuntimeError(
            f"以下模型未配置：{', '.join(unconfigured)}。"
            "请在启动服务器前为每个模型调用 configure()。"
        )

# 在应用工厂中，返回 app 之前调用
assert_all_configured()
```

---

## 5. 线程安全检查清单

- [ ] `configure()` 在应用启动时调用一次，不在请求处理函数中调用
- [ ] 对于 fork 类服务器（Gunicorn sync worker）：在 `post_fork` 钩子中配置，不在 fork 前配置
- [ ] 对于异步服务器（Uvicorn）：在 `lifespan` 启动事件中配置
- [ ] SQLite：每个进程/线程使用独立后端，避免跨线程共享连接
- [ ] MySQL / PostgreSQL：`pool_size` 根据 Worker 并发数调整
- [ ] 启动时断言验证所有必需模型已配置

---

## 可运行示例

参见 [`docs/examples/chapter_03_modeling/concurrency.py`](../../../examples/chapter_03_modeling/concurrency.py)，
该脚本自包含，完整演示了上述四种模式。

---

## 另请参阅

- [多个独立连接](best_practices.md#8-多个独立连接-multiple-independent-connections) — 共享字段但使用不同数据库的两种模式
- [环境隔离配置](configuration_management.md) — dev / test / prod 配置管理
- [并发与乐观锁](../performance/concurrency.md) — 使用 `OptimisticLockMixin` 处理并发写入
