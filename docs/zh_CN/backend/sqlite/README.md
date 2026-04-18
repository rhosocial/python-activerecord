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
- **数据库内省**：完整的数据库元数据查询能力

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

## 数据库内省

SQLite 后端提供完整的数据库内省功能，可以查询数据库结构元数据。详细的内省 API 文档请参考 [数据库内省](../introspection.md)。

### 数据库信息

```python
# 获取数据库基本信息
db_info = backend.introspector.get_database_info()
print(f"数据库名称: {db_info.name}")
print(f"SQLite 版本: {db_info.version}")
print(f"数据库大小: {db_info.size_bytes} bytes")
```

### 表内省

```python
# 列出所有用户表
tables = backend.introspector.list_tables()
for table in tables:
    print(f"表: {table.name}, 类型: {table.table_type.value}")

# 包含系统表
all_tables = backend.introspector.list_tables(include_system=True)
system_tables = [t for t in all_tables if t.table_type.value == "SYSTEM_TABLE"]
print(f"系统表数量: {len(system_tables)}")

# 过滤特定类型
base_tables = backend.introspector.list_tables(table_type="BASE TABLE")
views = backend.introspector.list_tables(table_type="VIEW")

# 检查表是否存在
if backend.introspector.table_exists("users"):
    print("users 表存在")

# 获取表详细信息
table_info = backend.introspector.get_table_info("users")
if table_info:
    print(f"表名: {table_info.name}")
    print(f"Schema: {table_info.schema}")
```

### 列和索引信息

```python
# 列出表的所有列
columns = backend.introspector.list_columns("users")
for col in columns:
    nullable = "NOT NULL" if col.nullable.value == "NOT_NULL" else "NULLABLE"
    pk = " [PK]" if col.is_primary_key else ""
    print(f"{col.name}: {col.data_type} {nullable}{pk}")

# 获取主键信息
pk = backend.introspector.get_primary_key("users")
if pk:
    print(f"主键: {[c.name for c in pk.columns]}")

# 列出所有索引
indexes = backend.introspector.list_indexes("users")
for idx in indexes:
    unique = "UNIQUE " if idx.is_unique else ""
    print(f"{unique}索引: {idx.name}")
    for col in idx.columns:
        print(f"  - {col.name}")
```

### 外键和视图

```python
# 列出外键
foreign_keys = backend.introspector.list_foreign_keys("posts")
for fk in foreign_keys:
    print(f"外键: {fk.name}")
    print(f"  列: {fk.columns} -> {fk.referenced_table}.{fk.referenced_columns}")
    print(f"  ON DELETE: {fk.on_delete.value}")
    print(f"  ON UPDATE: {fk.on_update.value}")

# 列出视图
views = backend.introspector.list_views()
for view in views:
    print(f"视图: {view.name}")

# 获取视图定义
view_info = backend.introspector.get_view_info("user_posts_summary")
if view_info:
    print(f"定义: {view_info.definition}")
```

### 触发器

```python
# 列出所有触发器
triggers = backend.introspector.list_triggers()
for trigger in triggers:
    print(f"触发器: {trigger.name} on {trigger.table_name}")

# 列出特定表的触发器
table_triggers = backend.introspector.list_triggers("users")
for trigger in table_triggers:
    print(f"触发器: {trigger.name}")
```

### 异步内省 API

异步后端提供相同的内省方法，方法名与同步版本相同：

```python
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

backend = AsyncSQLiteBackend(database=":memory:")
await backend.connect()

# 异步内省方法
db_info = await backend.introspector.get_database_info()
tables = await backend.introspector.list_tables()
table_info = await backend.introspector.get_table_info("users")
columns = await backend.introspector.list_columns("users")
indexes = await backend.introspector.list_indexes("users")
foreign_keys = await backend.introspector.list_foreign_keys("posts")
views = await backend.introspector.list_views()
triggers = await backend.introspector.list_triggers()
```

### 缓存管理

内省结果会被缓存以提高性能。您可以管理缓存：

```python
# 清除所有内省缓存
backend.introspector.clear_cache()

# 使特定作用域的缓存失效
from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

# 使所有表相关缓存失效
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE)

# 使特定表的缓存失效
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.TABLE,
    name="users"
)
```

### SQLite 专属：PragmaIntrospector

SQLite 内省器提供直接访问 PRAGMA 指令的能力：

```python
# 访问 PragmaIntrospector
pragma = backend.introspector.pragma

# 使用 PRAGMA 指令
table_info = pragma.pragma_table_info("users")
index_list = pragma.pragma_index_list("users")
foreign_keys = pragma.pragma_foreign_key_list("posts")
```

## 版本差异

### 内省功能版本差异

SQLite 内省行为因版本而异：

| 功能 | SQLite < 3.37.0 | SQLite >= 3.37.0 |
|------|-----------------|------------------|
| 表列表查询方式 | `sqlite_master` 查询 | `PRAGMA table_list` |
| 系统表是否在查询结果中 | 手动检测添加 | 自动返回 (type='shadow') |
| 列隐藏信息 | `PRAGMA table_info` | `PRAGMA table_xinfo` |

**重要说明**：

- **SQLite < 3.37.0**：系统表（如 `sqlite_schema`）**不存储在 `sqlite_master` 中**。后端会在 `include_system=True` 时自动检测并添加已知的系统表。
- **SQLite >= 3.37.0**：`PRAGMA table_list` 会返回系统表（`type='shadow'`），自动映射为 `TableType.SYSTEM_TABLE`。

### 已知的 SQLite 系统表

| 系统表名 | 说明 | 存在条件 |
|---------|------|---------|
| `sqlite_schema` | 数据库 schema 信息 | 始终存在 |
| `sqlite_master` | `sqlite_schema` 的别名 | 始终存在 |
| `sqlite_stat1` | 索引统计信息 | 执行 ANALYZE 后 |
| `sqlite_stat2/3/4` | 扩展统计信息 | 特定版本 ANALYZE 后 |
| `sqlite_sequence` | AUTOINCREMENT 计数器 | 使用 AUTOINCREMENT 后 |

### 版本特性支持矩阵

| 特性 | 最低版本 | 推荐版本 |
|------|---------|---------|
| 基础 CTE | 3.8.3 | 3.8.3+ |
| 递归 CTE | 3.8.3 | 3.8.3+ |
| 窗口函数 | 3.25.0 | 3.25.0+ |
| RETURNING 子句 | 3.35.0 | 3.35.0+ |
| JSON 操作 | 3.38.0 | 3.38.0+ |
| 系统 PRAGMA table_list | 3.37.0 | 3.37.0+ |

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

## 内省功能

SQLite 后端提供完整的数据库内省支持，可以查询数据库结构元数据：

### 基本用法

```python
# 获取数据库信息
db_info = backend.get_database_info()
print(f"数据库名称: {db_info.name}")
print(f"SQLite 版本: {db_info.version}")

# 列出所有表
tables = backend.list_tables()
for table in tables:
    print(f"表: {table.name}, 类型: {table.table_type}")

# 检查表是否存在
if backend.table_exists("users"):
    print("users 表存在")

# 获取表的详细信息
table_info = backend.get_table_info("users")
if table_info:
    print(f"表名: {table_info.name}")
    for col in table_info.columns:
        print(f"  列: {col.name}, 类型: {col.data_type}")
    for idx in table_info.indexes:
        print(f"  索引: {idx.name}")
```

### 列出系统表

```python
# 包含系统表
all_tables = backend.list_tables(include_system=True)
system_tables = [t for t in all_tables if t.table_type.value == "SYSTEM_TABLE"]
for t in system_tables:
    print(f"系统表: {t.name}")
```

### 列和索引信息

```python
# 列出表的所有列
columns = backend.list_columns("users")
for col in columns:
    print(f"{col.name}: {col.data_type} {'NOT NULL' if col.nullable.value == 'NOT_NULL' else 'NULLABLE'}")

# 获取主键信息
pk = backend.get_primary_key("users")
if pk:
    print(f"主键: {[c.name for c in pk.columns]}")

# 列出所有索引
indexes = backend.list_indexes("users")
for idx in indexes:
    print(f"索引: {idx.name}, 唯一: {idx.is_unique}")
```

### 外键和视图

```python
# 列出外键
foreign_keys = backend.list_foreign_keys("posts")
for fk in foreign_keys:
    print(f"外键: {fk.name} -> {fk.referenced_table}")

# 列出视图
views = backend.list_views()
for view in views:
    print(f"视图: {view.name}")

# 列出触发器
triggers = backend.list_triggers("users")
for trigger in triggers:
    print(f"触发器: {trigger.name}")
```

### 异步 API

```python
# 异步内省方法
db_info = await backend.get_database_info_async()
tables = await backend.list_tables_async()
table_info = await backend.get_table_info_async("users")
```

### 缓存管理

内省结果默认会被缓存以提高性能：

```python
# 清除所有内省缓存
backend.clear_introspection_cache()

# 使特定对象的缓存失效
from rhosocial.activerecord.backend.introspection.types import IntrospectionScope
backend.invalidate_introspection_cache(IntrospectionScope.TABLE, "users")
```

## 版本差异

SQLite 后端根据实际版本自动调整功能支持，不同版本间存在以下关键差异：

### 系统表识别（3.37.0+）

| SQLite 版本 | 系统表查询方式 | 系统表是否在 sqlite_master 中 |
|------------|--------------|---------------------------|
| < 3.37.0 | `sqlite_master` 查询 | ❌ 不包含，需手动识别 |
| >= 3.37.0 | `PRAGMA table_list` | ✅ 包含（type='shadow'） |

当调用 `list_tables(include_system=True)` 时：
- **SQLite >= 3.37.0**：使用 `PRAGMA table_list` 返回系统表（`sqlite_schema` 等）
- **SQLite < 3.37.0**：手动构建已知系统表信息（`sqlite_schema`、`sqlite_stat1`、`sqlite_sequence`）

### 特性支持矩阵

| 特性 | 最低版本 | 推荐版本 | 说明 |
|-----|---------|---------|------|
| 基础 CTE | 3.8.3 | 3.8.3+ | WITH 子句 |
| 递归 CTE | 3.8.3 | 3.8.3+ | WITH RECURSIVE |
| 窗口函数 | 3.25.0 | 3.25.0+ | OVER 子句 |
| RETURNING 子句 | 3.35.0 | 3.35.0+ | INSERT/UPDATE/DELETE 返回 |
| JSON 函数 | 3.38.0 | 3.38.0+ | 内置 JSON1 |
| 系统表识别 | 3.37.0 | 3.37.0+ | PRAGMA table_list |
| 扩展列信息 | 3.26.0 | 3.26.0+ | PRAGMA table_xinfo |

> **注意**：Python 3.8 自带的 SQLite 版本可能较低（如 3.35.5），部分功能可能受限。建议在生产环境中使用较新的 SQLite 版本或从源码编译 Python 以获得最新 SQLite 支持。

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

## 命令行内省命令

SQLite 后端提供命令行内省命令，无需编写代码即可查询数据库元数据。

### 基本用法

```bash
# 列出所有表
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db

# 列出所有视图
python -m rhosocial.activerecord.backend.impl.sqlite introspect views --db-file my.db

# 获取数据库信息
python -m rhosocial.activerecord.backend.impl.sqlite introspect database --db-file my.db

# 包含系统表
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db --include-system
```

### 查询表详情

```bash
# 获取表的完整信息（列、索引、外键）
python -m rhosocial.activerecord.backend.impl.sqlite introspect table users --db-file my.db

# 仅查询列信息
python -m rhosocial.activerecord.backend.impl.sqlite introspect columns users --db-file my.db

# 仅查询索引信息
python -m rhosocial.activerecord.backend.impl.sqlite introspect indexes users --db-file my.db

# 仅查询外键信息
python -m rhosocial.activerecord.backend.impl.sqlite introspect foreign-keys posts --db-file my.db

# 查询触发器
python -m rhosocial.activerecord.backend.impl.sqlite introspect triggers --db-file my.db

# 查询特定表的触发器
python -m rhosocial.activerecord.backend.impl.sqlite introspect triggers users --db-file my.db
```

### 内省类型

| 类型 | 说明 | 是否需要表名 |
|------|------|-------------|
| `tables` | 列出所有表 | 否 |
| `views` | 列出所有视图 | 否 |
| `database` | 数据库信息 | 否 |
| `table` | 表完整详情（列、索引、外键） | 是 |
| `columns` | 列信息 | 是 |
| `indexes` | 索引信息 | 是 |
| `foreign-keys` | 外键信息 | 是 |
| `triggers` | 触发器信息 | 可选 |

### 输出格式

```bash
# 表格格式（默认，需要 rich 库）
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db

# JSON 格式
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db --output json

# CSV 格式
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db --output csv

# TSV 格式
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db --output tsv
```

### 使用内存数据库

```bash
# 不指定 --db-file 时使用内存数据库
python -m rhosocial.activerecord.backend.impl.sqlite introspect database
```

## 命名查询

命名查询提供了一种将可复用的 SQL 查询定义为 Python 可调用对象（函数或类）的方式，可以通过 CLI 执行。

### 概述

命名查询是返回 `BaseExpression` 对象的 Python 函数或类。它们使用后端表达式系统构建 SQL 查询，避免使用原始 SQL 字符串，提供类型安全。

### 定义命名查询

创建包含查询定义的 Python 模块：

```python
# myapp/queries.py
from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression
from rhosocial.activerecord.backend.expression.core import TableExpression, Column, Literal
from rhosocial.activerecord.backend.expression.query_parts import WhereClause, LimitOffsetClause

def orders_by_status(dialect, status: str, limit: int = 100):
    """按状态查询订单"""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "*")],
        from_=TableExpression(dialect, "orders"),
        where=WhereClause(dialect, Column(dialect, "status") == Literal(dialect, status)),
        limit_offset=LimitOffsetClause(dialect, limit=limit),
    )
```

关键点：
- 第一个参数必须是 `dialect`（由 CLI 注入）
- 返回类型必须是 `BaseExpression`（或其子类）
- 使用类型注解进行参数文档化
- 添加 docstring 用于描述

### 通过 CLI 使用命名查询

#### 执行命名查询

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.orders_by_status \
    --db-file mydb.sqlite \
    --param status=pending
```

#### 覆盖参数

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.orders_by_status \
    --db-file mydb.sqlite \
    --param status=completed \
    --param limit=50
```

#### 描述查询（显示签名）

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.orders_by_status \
    --describe
```

输出：
```
Query: myapp.queries.orders_by_status
Docstring: 按状态查询订单
Signature: (dialect, status: str, limit: int = 100)
Parameters (excluding 'dialect'):
  status <class 'str'>
  limit <class 'int'> default=100
```

#### 预览 SQL（Dry Run）

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.orders_by_status \
    --db-file mydb.sqlite \
    --param status=pending \
    --dry-run
```

输出：
```
[DRY RUN] SQL:
  SELECT * FROM "orders" WHERE "status" = ? LIMIT ?
Params: ('pending', 100)
```

#### 列出模块中的所有查询

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries \
    --list
```

输出：
```
Module: myapp.queries
  orders_by_status(dialect, status: str, limit: int = 100)
      按状态查询订单
  high_value_orders(dialect, threshold: float = 1000.0)
      高于阈值的订单
```

### 类形式查询

对于复杂的查询和元数据，可以使用类：

```python
class MonthlyRevenue:
    """月度营收报表"""
    def __call__(self, dialect, month: int, year: int):
        return QueryExpression(
            dialect,
            select=[Column(dialect, "SUM(amount) as total")],
            from_=TableExpression(dialect, "orders"),
            where=WhereClause(dialect, ...),
        )
```

执行：
```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.MonthlyRevenue \
    --param month=3 \
    --param year=2026
```

### 安全性

命名查询系统强制执行安全检查：

1. **返回类型验证**：仅允许 `BaseExpression`。拒绝原始 SQL 字符串以防止 SQL 注入。
2. **EXPLAIN 保护**：EXPLAIN 查询在实际执行时被阻止；使用 `--dry-run` 进行预览。
3. **非 SELECT 警告**：DML/DDL 语句会触发警告；使用 `--force` 强制执行。

### 配置

设置 PYTHONPATH 以包含查询模块：

```bash
PYTHONPATH=src:examples python -m rhosocial.activerecord.backend.impl.sqlite \
    named-query examples.named_queries.order_queries.orders_by_status \
    --param status=pending
```
