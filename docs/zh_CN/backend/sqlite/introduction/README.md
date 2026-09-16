# 简介

## SQLite 后端概述

SQLite 后端包含在 `rhosocial-activerecord` 核心库中——无需单独安装包。SQLite 是一个轻量级的嵌入式数据库，无需服务器进程，非常适合开发、测试、移动应用和中小型工作负载。

### SQLite 后端提供的功能

- 使用 ActiveRecord 模式的完整 CRUD 操作
- 具有相同方法签名的同步和异步 API
- 用于复杂查询构建的表达式系统
- 关系（一对一、一对多、多对多）
- 带 savepoints 的事务管理
- 用于数据库配置的 PRAGMA 系统
- 扩展框架（FTS5、JSON1、R-Tree、Geopoly）
- 用于元数据查询的数据库自省

### 版本要求

| 要求 | 版本 |
|------|------|
| 最低 SQLite | 3.8.3（基本 CTE 支持） |
| 推荐 SQLite | 3.35.0+（RETURNING、DROP COLUMN、现代特性） |
| Python | 3.8+ |

功能可用性因 SQLite 版本而异。后端会自动检测运行时版本并相应调整功能。

## 同步与异步

SQLite 后端提供功能等效的同步和异步 API。本文档中的所有示例均使用同步 API——异步版本使用相同的方法名并加上 `await`。

### 命名约定

| 组件 | 同步 | 异步 |
|------|------|------|
| 后端类 | `SQLiteBackend` | `AsyncSQLiteBackend` |
| 事务管理器 | `SQLiteTransactionManager` | `AsyncSQLiteTransactionManager` |
| 连接配置 | `SQLiteConnectionConfig` | `SQLiteConnectionConfig`（共享） |
| 方言 | `SQLiteDialect` | `SQLiteDialect`（共享） |

连接配置和方言在同步和异步之间共享——它们是纯数据对象，不是活动连接。

### 模型层

| 操作 | `ActiveRecord`（同步） | `AsyncActiveRecord`（异步） |
|------|----------------------|----------------------------|
| 查找一个 | `find_one()` | `async find_one()` |
| 查找所有 | `find_all()` | `async find_all()` |
| 保存 | `save()` | `async save()` |
| 删除 | `delete()` | `async delete()` |

### 配置

```python
# 同步
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

class User(ActiveRecord):
    ...

User.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
user = User.find_one(1)

# 异步
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend, SQLiteConnectionConfig

class User(AsyncActiveRecord):
    ...

User.configure(SQLiteConnectionConfig(database=":memory:"), AsyncSQLiteBackend)
user = await User.find_one(1)
```

### 异步驱动要求

异步 SQLite 后端需要 `aiosqlite`：

```bash
pip install aiosqlite
```

或者安装包含所有可选依赖的完整包：

```bash
pip install rhosocial-activerecord[all]
```

如果您导入 `AsyncSQLiteBackend` 但未安装 `aiosqlite`，将在导入时收到 `ImportError`。

## 快速入门

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

# 内存数据库（非常适合测试）
backend = SQLiteBackend(database=":memory:")
backend.connect()

# 基于文件的数据库
backend = SQLiteBackend(database="/path/to/database.db")
backend.connect()

# 检查 SQLite 版本
version = backend.dialect.version
print(f"SQLite Version: {version}")

# 检查功能支持
if backend.dialect.supports_window_functions():
    print("Window functions supported")

backend.disconnect()
```

## 已知限制和怪癖

| 怪癖 | 描述 |
|------|------|
| 有限的 ALTER TABLE | 不能 ALTER COLUMN；RENAME COLUMN 需要 3.25.0+；DROP COLUMN 需要 3.35.0+ |
| 没有 DEFAULT 的 NOT NULL | 不能添加没有 DEFAULT 的 NOT NULL 列（除非 3.37.0+ 的 STRICT 表） |
| DELETE FROM 不回收空间 | 使用 VACUUM 回收空间；VACUUM 不能在事务内运行 |
| AUTOINCREMENT | 仅适用于 `INTEGER PRIMARY KEY`；防止 rowid 重用但增加存储 |
| 不支持 CASCADE/RESTRICT | DROP TABLE 不支持 CASCADE 或 RESTRICT 关键字 |
| 类型亲和性 | 所有字符串类型（CHAR/VARCHAR/TEXT）都具有 TEXT 亲和性 |
| 不支持 RIGHT/FULL JOIN | SQLite 不支持 RIGHT JOIN 和 FULL JOIN |
| 并发性 | 文件锁定限制写并发 |
| 网络存储 | 不建议用于 NFS 或类似的网络文件系统 |

💡 *AI 提示*："什么是 ActiveRecord 模式？它与 DataMapper 模式有什么区别？"
