# 命名连接

> **本文档定位**: 面向应用开发者的实践指南,侧重「为什么用」和「怎么用」。

---

## 1. 概述

命名连接是**后端功能**,用于将数据库配置封装为可调用的 Python 对象,实现配置与代码的解耦。

```mermaid
flowchart LR
    A[命名连接函数] -->|调用| B[ConnectionConfig]
    B -->|创建| C[Backend 实例]
    C -->|连接| D[数据库]
```

| 特性 | 用途 | 典型场景 |
|------|------|---------|
| **命名连接** | 数据库配置外部化 | 环境切换、多租户 |

> **重要**: 这是**后端功能**,与 ActiveRecord 模型无关。

---

## 2. 目录

1. [为什么需要命名连接?](#为什么需要命名连接)
2. [核心概念](#核心概念)
3. [定义命名连接](#定义命名连接)
4. [调用方式](#调用方式)
5. [环境切换最佳实践](#环境切换最佳实践)
6. [CLI 完整参数](#cli-完整参数)
7. [API 参考](#api-参考)

---

## 为什么需要命名连接?

命名连接将**数据库配置封装为纯 Python 函数**,享受完整开发体验:

```python
# myapp/connections.py
def production_db():
    """生产环境数据库配置"""
    return MySQLConnectionConfig(
        host="prod.example.com",
        database="myapp",
        user="app_user",
        password=os.getenv("DB_PASSWORD"),
    )

def development_db():
    """开发环境数据库配置"""
    return MySQLConnectionConfig(
        host="localhost",
        database="myapp_dev",
        user="root",
    )
```

**解决的问题:**

| 问题 | 说明 |
|------|------|
| **配置分散** | 硬编码、.env、k8s configmap,难以统一管理 |
| **无法版本控制** | 配置改动的审计记录困难 |
| **无 IDE 支持** | 无法跳转、类型提示 |
| **难以测试** | 无法 dry-run 查看最终配置 |
| **环境切换困难** | dev/staging/prod 配置差异大 |

---

## 核心概念

### 什么是命名连接?

**命名连接**是一个可调用对象(函数或类),必须满足:

1. **可调用**: 函数或带有 `__call__` 方法的类实例
2. **返回配置**: 必须返回 `ConnectionConfig` 子类
3. **可选参数**: 可接受任意命名参数(用于参数化配置)

### 支持的连接类型

| 后端 | 配置类 | 说明 |
|------|-------|------|
| SQLite | `SQLiteConnectionConfig` | 文件型/内存型 |
| MySQL | `MySQLConnectionConfig` | 需要 mysql-connector-python |
| PostgreSQL | `PostgresConnectionConfig` | 需要 psycopg |

---

## 定义命名连接

```python
# myapp/connections.py
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig


def development_db():
    """开发环境使用内存 SQLite"""
    return SQLiteConnectionConfig(
        database=":memory:",
        pragmas={"foreign_keys": "ON"},
    )


def production_db(pool_size: int = 10):
    """生产环境使用 MySQL"""
    return MySQLConnectionConfig(
        host="prod.example.com",
        database="myapp",
        user="app_user",
        password=os.getenv("DB_PASSWORD"),
        pool_size=pool_size,
    )


def file_db(database: str = "mydb.sqlite", timeout: int = 5):
    """文件型 SQLite 数据库"""
    return SQLiteConnectionConfig(
        database=database,
        timeout=timeout,
    )
```

---

## 调用方式

### CLI 调用

```bash
# 列出模块中所有命名连接
python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
    --named-connection myapp.connections --list

# 查看具体连接配置
python -m rhosocial.activerecord.backend.impl.mysql named-connection \
    --named-connection myapp.connections.production_db --show

# Dry-run 解析连接配置
python -m rhosocial.activerecord.backend.impl.mysql named-connection \
    --named-connection myapp.connections.production_db \
    --describe --conn-param pool_size=20

# 解析带参数覆盖的连接
python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
    --named-connection myapp.connections.file_db \
    --describe \
    --conn-param database=custom.db \
    --conn-param timeout=10
```

### 在 query 中使用命名连接

```bash
# 使用命名连接替代 --db-file
python -m rhosocial.activerecord.backend.impl.sqlite query \
    --named-connection myapp.connections.production_db \
    "SELECT * FROM users LIMIT 10"

# 命名连接 + conn-param 覆盖
python -m rhosocial.activerecord.backend.impl.sqlite query \
    --named-connection myapp.connections.production_db \
    --conn-param database=override.db \
    "SELECT 1"
```

### Programmatic API

```python
from rhosocial.activerecord.backend.named_connection import resolve_named_connection
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

# 一步解析
config = resolve_named_connection(
    "myapp.connections.production_db",
    user_params={"pool_size": 20}
)

# 创建后端
backend = MySQLBackend(connection_config=config)
```

```python
# 分步控制
from rhosocial.activerecord.backend.named_connection import NamedConnectionResolver

# 1. 创建解析器
resolver = NamedConnectionResolver("myapp.connections.production_db")

# 2. 加载可调用对象
resolver.load()

# 3. 查看描述(不实际调用)
info = resolver.describe()
print(f"参数: {info['parameters']}")
print(f"签名: {info['signature']}")

# 4. 解析并获取配置(可选传参覆盖)
config = resolver.resolve(user_params={"pool_size": 20})
```

---

## 环境切换最佳实践

```python
# myapp/connections.py
import os
from functools import partial

from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.mysql.config import MySQLConnectionConfig


def development_db():
    """开发环境数据库配置(内存 SQLite)"""
    return SQLiteConnectionConfig(
        database=":memory:",
        pragmas={"foreign_keys": "ON"},
    )


def production_db(pool_size: int = 10):
    """生产环境数据库配置(MySQL)"""
    return MySQLConnectionConfig(
        host=os.getenv("PROD_HOST", "prod.example.com"),
        database=os.getenv("PROD_DATABASE", "myapp_prod"),
        pool_size=pool_size,
    )


# 根据环境选择连接
def get_current_db(**kwargs):
    env = os.getenv("APP_ENV", "development")
    connections = {"development": development_db, "production": production_db}
    conn_fn = connections.get(env)
    return conn_fn(**kwargs)
```

结合 ActiveRecord:

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
from rhosocial.activerecord.backend.named_connection import resolve_named_connection

env = os.getenv("APP_ENV", "development")
connection_name = f"myapp.connections.{env}_db"
config = resolve_named_connection(connection_name)
ActiveRecord.configure(config, MySQLBackend)
```

---

## CLI 完整参数

| 参数 | 说明 |
|------|------|
| `--named-connection QUALIFIED_NAME` | 命名连接完全限定名 |
| `--list` | 列出模块中所有连接 |
| `--show` | 显示连接详情(敏感字段会被过滤) |
| `--describe` | Dry-run 解析配置 |
| `--conn-param KEY=VALUE` | 覆盖连接参数(可重复) |

---

## API 参考

### 异常类

- `NamedConnectionError` - 基础异常
- `NamedConnectionModuleNotFoundError` - 找不到模块
- `NamedConnectionNotFoundError` - 找不到连接
- `NamedConnectionNotCallableError` - 不可调用
- `NamedConnectionInvalidReturnTypeError` - 无效返回类型
- `NamedConnectionInvalidParameterError` - 无效参数
- `NamedConnectionMissingParameterError` - 缺少参数

### 核心 API

| 函数/类 | 说明 |
|--------|------|
| `resolve_named_connection(name, user_params=None)` | 一步完成命名连接的解析和调用 |
| `NamedConnectionResolver(name)` | 命名连接解析器类,提供细粒度控制 |
| `list_named_connections_in_module(module_name)` | 列出模块中定义的所有命名连接 |

### NamedConnectionResolver 方法

| 方法 | 说明 |
|------|------|
| `load()` | 加载并验证 callable 对象 |
| `describe()` | 获取函数签名和参数信息(不实际调用) |
| `resolve(user_params=None)` | 执行 callable 并返回配置 |
| `get_callable()` | 获取加载的 callable 对象 |

---

## 完整示例

### Python 示例

| 示例 | 说明 |
|------|------|
| `named_connections/memory.py` | 内存数据库连接示例 |
| `named_connections/file.py` | 文件型数据库连接示例 |

### CLI 示例

| 示例 | 说明 |
|------|------|
| `cli/named_connection_demo.py` | 命名连接 CLI 完整演示 |

### 运行示例

```bash
# Python 示例: 使用命名连接
cd src/rhosocial/activerecord/backend/impl/sqlite/examples
PYTHONPATH=../../../../..:. python3 -c "
from rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory import memory_db
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

config = memory_db()
backend = SQLiteBackend(connection_config=config)
print(f'Connected to: {config}')
"

# CLI 示例
cd src/rhosocial/activerecord/backend/impl/sqlite/examples
PYTHONPATH=../../../../..:. python3 cli/named_connection_demo.py
```