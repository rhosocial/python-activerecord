---
name: dev-sync-async-parity
description: Sync/async API parity rules for rhosocial-activerecord contributors - backend/transaction symmetry, naming conventions, docstrings, field ordering, and testing parity
license: MIT
compatibility: opencode
metadata:
  category: architecture
  level: intermediate
  audience: developers
  order: 2
  prerequisites:
    - dev-backend-development
---

# Sync/Async API Parity Rules

This guide covers the strict sync/async parity requirements for rhosocial-activerecord framework development, with emphasis on **backend and transaction symmetry** as the foundation of all parity.

## Core Philosophy

### Backend & Transaction: The True Foundation

**Backend 和 Transaction 才是同步异步对等的真正基础。**

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                          │
│     ActiveRecord / AsyncActiveRecord (依赖于 Backend)          │
│     ActiveQuery / AsyncActiveQuery (依赖于 Backend)           │
├─────────────────────────────────────────────────────────────┤
│                    Backend Layer                             │
│     StorageBackend / AsyncStorageBackend (核心对等)            │
│     Transaction / AsyncTransaction (核心对等)                  │
├─────────────────────────────────────────────────────────────┤
│                    Database Layer                            │
│            SQLite / PostgreSQL / MySQL / etc.               │
└─────────────────────────────────────────────────────────────┘
```

**关键理解：**
- `ActiveRecord` 依赖于 `StorageBackend`
- `AsyncActiveRecord` 依赖于 `AsyncStorageBackend`
- 如果只有同步 `StorageBackend`，那么 `AsyncActiveRecord` 无法真正工作
- **Backend/Transaction 的对等是整个框架同步异步对等的前提条件**

## Backend 实现状态

### 当前状态说明

**并非所有 Backend 都需要同时提供同步和异步版本：**

| Backend 位置 | 同步实现 | 异步实现 | 用途 |
|-------------|---------|---------|------|
| `src/rhosocial/activerecord/backend/impl/sqlite/` | ✅ 已实现 | ❌ 未实现 | 生产使用 |
| `tests/` (模拟) | ✅ 测试用 | ✅ 测试用 | 仅供测试 |

```python
# src/rhosocial/activerecord/backend/impl/sqlite/backend.py
# ✅ 同步 Backend 已实现，可用于生产
class SQLiteBackend(StorageBackend):
    def connect(self): ...
    def execute(self, sql: str, params=None): ...
    def begin_transaction(self): ...
    def commit(self): ...
    def rollback(self): ...

# tests/rhosocial/activerecord_test/.../async_sqlite_backend.py
# ⚠️ 异步 Backend 仅在 tests 目录中，用于测试异步 API
class AsyncSQLiteBackend(AsyncStorageBackend):
    async def connect(self): ...
    async def execute(self, sql: str, params=None): ...
```

### 为什么异步 Backend 可能不需要？

1. **纯同步应用场景**：许多应用不需要异步数据库访问
2. **测试覆盖**：测试目录中的异步实现主要用于验证异步 API 设计
3. **社区贡献**：异步实现可以由社区按需补充
4. **性能考量**：对于简单应用，同步版本已足够

## 两条对等链

### 第一条对等链：Backend 层（核心）

```
StorageBackend (同步基础)
    ↓ 依赖
BaseActiveRecord / ActiveQuery (同步 API)

AsyncStorageBackend (异步基础)
    ↓ 依赖
AsyncBaseActiveRecord / AsyncActiveQuery (异步 API)
```

### 第二条对等链：Transaction 层

```
Transaction (同步事务)
    ↓ 提供事务支持
BaseActiveRecord.save() / BaseActiveRecord.delete()

AsyncTransaction (异步事务)
    ↓ 提供事务支持
AsyncBaseActiveRecord.save() / AsyncBaseActiveRecord.delete()
```

## 六条核心规则

### 规则一：类命名

对等链上的每一层都需要添加 `Async` 前缀：

```python
# Backend 层
StorageBackend → AsyncStorageBackend

# Transaction 层
Transaction → AsyncTransaction

# ActiveRecord 层
BaseActiveRecord → AsyncBaseActiveRecord

# Query 层
ActiveQuery → AsyncActiveQuery
RelationQuery → AsyncRelationQuery
```

### 规则二：方法命名（关键）

**方法名必须完全相同** - 禁止使用 `_async` 后缀：

```python
# ✅ 正确 - 方法名相同
class StorageBackend:
    def execute(self, sql: str, params=None): ...

class AsyncStorageBackend:
    async def execute(self, sql: str, params=None): ...

# ✅ 正确 - 事务方法
class Transaction:
    def commit(self): ...

class AsyncTransaction:
    async def commit(self): ...

# ❌ 错误 - 禁止使用 _async 后缀
class AsyncStorageBackend:
    async def execute_async(self, sql: str, params=None): ...
```

### 规则三：Docstring 要求

异步版本的首句必须包含 "asynchronously"：

```python
class StorageBackend:
    def execute(self, sql: str, params=None):
        """Execute a SQL query."""
        ...

class AsyncStorageBackend:
    async def execute(self, sql: str, params=None):
        """Execute a SQL query asynchronously."""
        ...

class Transaction:
    def commit(self):
        """Commit the current transaction."""
        ...

class AsyncTransaction:
    async def commit(self):
        """Commit the current transaction asynchronously."""
        ...
```

### 规则四：字段/属性声明顺序

同步和异步版本的属性声明顺序必须完全一致：

```python
# StorageBackend 的属性顺序
class StorageBackend:
    _connection: Optional[Connection]
    _dialect: Optional[SQLDialect]
    _transaction: Optional[Transaction]
    
    @property
    def dialect(self): ...

# AsyncStorageBackend 必须保持相同顺序
class AsyncStorageBackend:
    _connection: Optional[AsyncConnection]
    _dialect: Optional[SQLDialect]
    _transaction: Optional[AsyncTransaction]
    
    @property
    def dialect(self): ...  # 顺序一致
```

### 规则五：功能对等

如果同步版本有某个功能，异步版本必须提供对应功能：

```python
# ✅ 正确 - 功能对等
class StorageBackend:
    def execute(self, sql: str, params=None): ...
    def execute_many(self, sql: str, params_list): ...
    def begin_transaction(self): ...
    def commit(self): ...
    def rollback(self): ...

class AsyncStorageBackend:
    async def execute(self, sql: str, params=None): ...
    async def execute_many(self, sql: str, params_list): ...
    async def begin_transaction(self): ...
    async def commit(self): ...
    async def rollback(self): ...

# ❌ 错误 - 功能缺失
class AsyncStorageBackend:
    async def execute(self, sql: str, params=None): ...
    # 缺少 execute_many、事务方法
```

### 规则六：测试对等

测试必须遵循严格的同步/异步对等：

```python
# 夹具对等
@pytest.fixture
def backend(sqlite_provider): ...
@pytest.fixture
def async_backend(sqlite_provider): ...

# 测试类对等
class TestBackendExecute:
    def test_execute_basic(self, backend): ...

class TestAsyncBackendExecute:
    @pytest.mark.asyncio
    async def test_execute_basic(self, async_backend): ...  # 方法名相同

# 测试方法对等
class TestTransactionCommit:
    def test_commit_success(self, backend): ...
    def test_commit_failure(self, backend): ...

class TestAsyncTransactionCommit:
    @pytest.mark.asyncio
    async def test_commit_success(self, async_backend): ...  # 相同方法名
    @pytest.mark.asyncio
    async def test_commit_failure(self, async_backend): ...  # 相同方法名
```

## 实现异步 Backend 的指南

### 何时需要实现异步 Backend？

1. **生产环境需要**：如果应用使用 async/await 框架（如 FastAPI）
2. **性能需求**：高并发场景需要异步数据库访问
3. **社区请求**：用户明确需要异步支持

### 异步 Backend 的实现策略

#### 策略一：基于同步版本包装

```python
# src/rhosocial/activerecord/backend/impl/sqlite/async_backend.py
import asyncio
from typing import Optional, Tuple, Any


class AsyncSQLiteBackend:
    """异步 SQLite Backend - 基于同步版本包装。"""
    
    def __init__(self, database: str = ":memory:"):
        """Initialize with same parameters as sync version."""
        self._sync_backend = SQLiteBackend(database)
        self._connected = False
    
    @property
    def dialect(self):
        """Delegate to sync dialect."""
        return self._sync_backend.dialect
    
    async def connect(self) -> None:
        """Connect asynchronously (delegates to sync)."""
        self._sync_backend.connect()
        self._connected = True
    
    async def disconnect(self) -> None:
        """Disconnect asynchronously."""
        self._sync_backend.disconnect()
        self._connected = False
    
    async def execute(
        self,
        sql: str,
        params: Optional[Tuple] = None
    ) -> Any:
        """Execute SQL asynchronously (runs sync in thread pool)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._sync_backend.execute(sql, params)
        )
    
    async def begin_transaction(self) -> None:
        """Begin transaction asynchronously."""
        await self.execute("BEGIN TRANSACTION")
    
    async def commit(self) -> None:
        """Commit transaction asynchronously."""
        await self.execute("COMMIT")
    
    async def rollback(self) -> None:
        """Rollback transaction asynchronously."""
        await self.execute("ROLLBACK")
```

#### 策略二：使用原生异步驱动

```python
# src/rhosocial/activerecord/backend/impl/postgresql/async_backend.py
# 使用 asyncpg 或其他原生异步驱动
import asyncpg


class AsyncPostgreSQLBackend:
    """使用原生异步驱动的 Backend。"""
    
    def __init__(self, dsn: str):
        """Initialize with connection string."""
        self._pool: Optional[asyncpg.Pool] = None
        self._dsn = dsn
    
    async def connect(self) -> None:
        """Create connection pool."""
        self._pool = await asyncpg.create_pool(self._dsn)
    
    async def execute(self, sql: str, params=None) -> Any:
        """Execute using async connection pool."""
        async with self._pool.acquire() as conn:
            if params:
                return await conn.fetch(sql, *params)
            return await conn.fetch(sql)
```

## 验证检查清单

实现或修改代码时，使用以下清单验证：

### Backend 层验证

- [ ] 同步 Backend 实现了 `StorageBackend` 协议
- [ ] 异步 Backend 实现了 `AsyncStorageBackend` 协议
- [ ] 同步/异步方法名完全相同
- [ ] 异步方法使用 `async def`
- [ ] 异步方法首句包含 "asynchronously"
- [ ] 属性声明顺序一致
- [ ] 事务方法完整对等

### 测试层验证

- [ ] 同步测试使用 `backend` 夹具
- [ ] 异步测试使用 `async_backend` 夹具
- [ ] 测试类名添加 `Async` 前缀
- [ ] 测试方法名完全相同
- [ ] 异步测试使用 `@pytest.mark.asyncio`
- [ ] 架构文件共享

### 文档层验证

- [ ] 同步 API 文档完整
- [ ] 异步 API 文档首句包含 "asynchronously"
- [ ] 说明了同步/异步 Backend 的可用状态

## 常见问题

### Q1: 什么时候可以只提供同步 Backend？

当：
- 应用场景明确是同步的
- 异步版本仅用于测试验证设计
- 社区尚未贡献异步实现

### Q2: 如何在只有同步 Backend 时使用异步 API？

**方案一：使用执行器包装**

```python
# 用户代码
async def some_async_function():
    loop = asyncio.get_event_loop()
    # 在线程池中执行同步 Backend 操作
    result = await loop.run_in_executor(
        None,
        lambda: User.find_one(User.c.id == 1)
    )
    return result
```

**方案二：使用模拟异步 Backend**

```python
# tests/conftest.py
@pytest.fixture
def async_backend(sqlite_provider):
    """测试用异步 Backend - 包装同步版本。"""
    return AsyncSQLiteBackend(":memory:")
```

### Q3: 如何验证异步 Backend 的正确性？

1. **复用同步测试**：基于相同逻辑编写异步版本测试
2. **对比执行结果**：确保同步/异步返回相同数据
3. **测试错误处理**：验证异步错误传播

```python
class TestAsyncBackendErrorHandling:
    @pytest.mark.asyncio
    async def test_invalid_sql_error(
        self,
        async_backend: AsyncSQLiteBackend
    ):
        """验证异步错误处理与同步一致。"""
        with pytest.raises(SyntaxError):
            await async_backend.execute("INVALID SQL")
```

## 快速参考

### 命名对照表

| 同步 | 异步 | 层级 |
|-----|------|-----|
| `StorageBackend` | `AsyncStorageBackend` | Backend |
| `Transaction` | `AsyncTransaction` | Transaction |
| `BaseActiveRecord` | `AsyncBaseActiveRecord` | ActiveRecord |
| `ActiveQuery` | `AsyncActiveQuery` | Query |

### 导入路径

```python
# 同步 Backend
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend

# 异步 Backend（仅测试目录）
from tests.async_backend import AsyncSQLiteBackend

# 同步/异步通用
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
```
