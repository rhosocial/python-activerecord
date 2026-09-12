# 安装与配置

## 安装

SQLite 后端包含在核心 `rhosocial-activerecord` 包中。无需单独的后端包。

```bash
pip install rhosocial-activerecord
```

如需异步支持，请安装 `aiosqlite`：

```bash
pip install aiosqlite
```

或一次性安装所有依赖：

```bash
pip install rhosocial-activerecord[all]
```

### 依赖项

| 组件 | 必需 | 包 |
|------|------|-----|
| SQLite 驱动 | 是 | `sqlite3`（Python 标准库） |
| 异步 SQLite 驱动 | 仅异步需要 | `aiosqlite` |
| 表达式系统 | 是 | `pydantic` 2.x |

无需 SSL 配置——SQLite 是基于文件的本地数据库，没有网络传输。

## 连接配置

### SQLiteConnectionConfig

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteConnectionConfig

# 内存数据库
config = SQLiteConnectionConfig(database=":memory:")

# 基于文件的数据库
config = SQLiteConnectionConfig(database="/path/to/database.db")
```

### 数据库路径

`database` 参数接受：

| 值 | 行为 |
|-----|------|
| `":memory:"` | 内存数据库（断开连接时丢失） |
| `"path/to/file.db"` | 创建或打开基于文件的数据库 |
| `"file::memory:"` | 替代的内存语法 |

### 连接

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database=":memory:")
backend.connect()

# 使用后端...

backend.disconnect()
```

### 异步连接

```python
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

backend = AsyncSQLiteBackend(database=":memory:")
await backend.connect()

# 使用后端...

await backend.disconnect()
```

### 内存数据库 vs 基于文件的数据库

| 特性 | 内存数据库 | 基于文件的数据库 |
|------|-----------|----------------|
| 持久性 | 否（断开连接时丢失） | 是 |
| 速度 | 更快（无磁盘 I/O） | 稍慢 |
| 并发性 | 仅单个连接 | 支持多个连接 |
| 用例 | 测试、原型设计 | 生产环境、开发 |

对于内存数据库，每个连接获得自己的独立数据库。两个连接到 `:memory:` 不能共享数据——如果需要多个连接访问相同数据，请使用基于文件的数据库。

## 另请参阅

- **[Pragma 系统](../pragma.md)**：配置 SQLite 运行时行为
- **[事务支持](../transaction_support/README.md)**：事务管理

💡 *AI 提示*："我应该在什么时候使用内存数据库，什么时候使用基于文件的数据库？"
