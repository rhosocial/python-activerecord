# SQLite 后端

SQLite 是 rhosocial-activerecord 核心库中包含的默认数据库后端。它是一个轻量级的嵌入式数据库，非常适合开发、测试和小型应用场景。

## 概述

SQLite 后端提供以下功能：

- **完整的 CRUD 操作支持**：创建、读取、更新、删除
- **同步和异步 API**：两种 API 完全对等
- **表达式系统**：支持复杂查询构建
- **关系支持**：一对一、一对多、多对多关系
- **事务管理**：支持嵌套事务和保存点
- **Pragma 系统**：完整的 SQLite PRAGMA 支持
- **扩展框架**：支持 FTS5、JSON1、R-Tree 等扩展

## 版本要求

- **最低版本**：SQLite 3.8.3（支持基础 CTE）
- **推荐版本**：SQLite 3.35.0+（支持大部分现代特性）

不同版本支持的特性有所差异，后端会根据实际版本自动调整功能支持。

## 同步与异步 API

SQLite 后端同时提供同步和异步实现：

```python
# 同步 API
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database=":memory:")
backend.connect()

# 异步 API
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

backend = AsyncSQLiteBackend(database=":memory:")
await backend.connect()
```

### 异步依赖

异步 SQLite 后端需要安装 `aiosqlite`：

```bash
pip install aiosqlite
```

或安装完整包：

```bash
pip install rhosocial-activerecord[all]
```

## 文档目录

- **[Pragma 系统](pragma.md)**：SQLite PRAGMA 配置和查询
- **[扩展框架](extension.md)**：扩展检测和管理
- **[全文搜索 (FTS5)](fts5.md)**：FTS5 全文搜索功能

## 快速开始

### 基本配置

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

# 内存数据库
backend = SQLiteBackend(database=":memory:")

# 文件数据库
backend = SQLiteBackend(database="/path/to/database.db")

# 连接
backend.connect()
```

### 检查版本和特性

```python
# 获取 SQLite 版本
version = backend.dialect.version
print(f"SQLite 版本: {version}")

# 检查特性支持
if backend.dialect.supports_window_functions():
    print("支持窗口函数")

if backend.dialect.supports_fts5():
    print("支持 FTS5 全文搜索")
```

### 使用 Pragma

```python
# 获取 Pragma 信息
info = backend.dialect.get_pragma_info('foreign_keys')
print(f"foreign_keys 信息: {info}")

# 生成 Pragma SQL
sql = backend.dialect.get_pragma_sql('journal_mode')
print(f"SQL: {sql}")  # PRAGMA journal_mode

# 设置 Pragma SQL
sql = backend.dialect.set_pragma_sql('foreign_keys', 1)
print(f"SQL: {sql}")  # PRAGMA foreign_keys = 1
```

### 检测扩展

```python
# 检测所有可用扩展
extensions = backend.dialect.detect_extensions()
for name, info in extensions.items():
    print(f"{name}: {'可用' if info.installed else '不可用'}")

# 检查特定扩展
if backend.dialect.is_extension_available('fts5'):
    print("FTS5 扩展可用")

# 检查扩展特性
if backend.dialect.check_extension_feature('fts5', 'trigram_tokenizer'):
    print("FTS5 trigram 分词器可用")
```

## 数据类型适配

SQLite 使用动态类型系统，后端自动处理类型转换：

| SQLite 类型 | Python 类型 |
|------------|------------|
| INTEGER | int |
| REAL | float |
| TEXT | str |
| BLOB | bytes |
| NULL | None |

此外，后端还支持以下特殊类型：

| Python 类型 | SQLite 存储 | 说明 |
|------------|------------|------|
| datetime.datetime | TEXT (ISO8601) | 自动序列化 |
| datetime.date | TEXT (ISO8601) | 自动序列化 |
| uuid.UUID | TEXT (36字符) | 自动序列化 |
| decimal.Decimal | TEXT | 精确数值 |
| dict/list | TEXT (JSON) | 需要 JSON1 扩展 |

## 事务支持

SQLite 后端支持完整的事务管理：

```python
# 手动事务
with backend.transaction():
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))

# 嵌套事务（保存点）
with backend.transaction():
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    with backend.transaction():  # 创建保存点
        backend.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))
```

## 限制和注意事项

1. **并发限制**：SQLite 使用文件锁，写入并发有限
2. **网络存储**：不建议在网络存储（如 NFS）上使用 SQLite 数据库文件
3. **RIGHT/FULL JOIN**：SQLite 不支持 RIGHT JOIN 和 FULL JOIN
4. **数据库大小**：SQLite 数据库文件最大支持 281 TB

## 命令行工具

SQLite 后端提供命令行工具用于快速测试和环境检测：

### 执行 SQL 查询

```bash
# 执行 SQL 查询（使用内存数据库）
python -m rhosocial.activerecord.backend.impl.sqlite "SELECT sqlite_version();"

# 使用数据库文件
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my.db "SELECT * FROM users;"

# 从文件执行 SQL 脚本
python -m rhosocial.activerecord.backend.impl.sqlite --file script.sql

# 执行多语句脚本
python -m rhosocial.activerecord.backend.impl.sqlite --executescript --file dump.sql
```

### 环境信息检测

使用 `--info` 选项可以查看当前环境的 SQLite 信息：

```bash
# 显示基本信息（协议族支持概览）
python -m rhosocial.activerecord.backend.impl.sqlite --info

# 显示详细信息（包含具体协议支持）
python -m rhosocial.activerecord.backend.impl.sqlite --info -v

# 显示完整详细信息（包含每个协议方法的支持状态）
python -m rhosocial.activerecord.backend.impl.sqlite --info -vv

# JSON 格式输出
python -m rhosocial.activerecord.backend.impl.sqlite --info --output json
```

`--info` 输出包含：

- **SQLite 版本**：当前环境的 SQLite 版本号
- **扩展支持**：FTS5、JSON1、R-Tree 等扩展的可用性
- **Pragma 系统**：各类别 Pragma 的数量统计
- **协议支持**：按功能分组显示后端实现的协议支持程度

### 输出格式

```bash
# 表格格式（默认，需要 rich 库）
python -m rhosocial.activerecord.backend.impl.sqlite --output table "SELECT 1;"

# JSON 格式
python -m rhosocial.activerecord.backend.impl.sqlite --output json "SELECT 1;"

# CSV 格式
python -m rhosocial.activerecord.backend.impl.sqlite --output csv "SELECT * FROM users;"

# TSV 格式
python -m rhosocial.activerecord.backend.impl.sqlite --output tsv "SELECT * FROM users;"
```

> **建议**：其他后端（如 MySQL、PostgreSQL）建议参照此模式实现类似的命令行工具，提供统一的用户体验。
