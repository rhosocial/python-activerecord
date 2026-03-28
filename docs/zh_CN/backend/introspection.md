# 数据库内省 (Database Introspection)

数据库内省是一种在运行时查询数据库结构元数据的能力。rhosocial-activerecord 提供了完整的内省系统，支持查询数据库、表、列、索引、外键、视图、触发器等元数据。

## 概述

内省系统位于 `backend.introspector` 属性中，提供：

- **数据库信息**：名称、版本、编码、大小等
- **表信息**：表列表、表详情、表类型（基表、视图、系统表）
- **列信息**：列名、数据类型、是否可空、默认值、主键信息
- **索引信息**：索引名、列、唯一性、索引类型
- **外键信息**：引用表、列映射、更新/删除行为
- **视图信息**：视图定义 SQL
- **触发器信息**：触发事件、执行时机、触发器 SQL

## 架构设计

### 模块结构

```
backend/introspection/
├── __init__.py          # 模块导出
├── base.py              # 抽象基类
├── types.py             # 数据结构定义
├── errors.py            # 内省专用异常
├── executor.py          # 执行器抽象
└── backend_mixin.py     # Backend 混入类
```

### 同步与异步分离

内省系统遵循项目的同步/异步对等原则：

- `SyncAbstractIntrospector` — 同步内省器
- `AsyncAbstractIntrospector` — 异步内省器
- `IntrospectorMixin` — 共享的非 I/O 逻辑（缓存、SQL 生成、解析）

## 数据结构

### DatabaseInfo

数据库基本信息：

```python
@dataclass
class DatabaseInfo:
    name: str                      # 数据库名称
    version: str                   # 版本字符串
    version_tuple: Tuple[int, ...] # 版本元组
    vendor: str                    # 数据库厂商
    encoding: Optional[str]        # 编码
    collation: Optional[str]       # 排序规则
    timezone: Optional[str]        # 时区
    size_bytes: Optional[int]      # 数据库大小
    table_count: Optional[int]     # 表数量
    extra: Dict[str, Any]          # 额外信息
```

### TableInfo

表信息：

```python
@dataclass
class TableInfo:
    name: str                    # 表名
    schema: str                  # Schema 名称
    table_type: TableType        # 表类型
    comment: Optional[str]       # 表注释
    row_count: Optional[int]     # 行数估计
    size_bytes: Optional[int]    # 表大小
    extra: Dict[str, Any]        # 额外信息
```

### ColumnInfo

列信息：

```python
@dataclass
class ColumnInfo:
    name: str                         # 列名
    table_name: str                   # 所属表名
    data_type: str                    # 数据类型
    nullable: ColumnNullable          # 是否可空
    default_value: Optional[str]      # 默认值
    is_primary_key: bool              # 是否主键
    ordinal_position: int             # 列位置
    comment: Optional[str]            # 列注释
    character_set: Optional[str]      # 字符集
    collation: Optional[str]          # 排序规则
    extra: Dict[str, Any]             # 额外信息
```

### IndexInfo

索引信息：

```python
@dataclass
class IndexInfo:
    name: str                      # 索引名
    table_name: str                # 所属表名
    columns: List[IndexColumnInfo] # 索引列
    is_unique: bool                # 是否唯一
    is_primary: bool               # 是否主键
    index_type: IndexType          # 索引类型
    comment: Optional[str]         # 索引注释
    extra: Dict[str, Any]          # 额外信息
```

### ForeignKeyInfo

外键信息：

```python
@dataclass
class ForeignKeyInfo:
    name: str                           # 外键名
    table_name: str                     # 所属表名
    columns: List[str]                  # 外键列
    referenced_table: str               # 引用表名
    referenced_columns: List[str]       # 引用列
    on_update: ReferentialAction        # 更新行为
    on_delete: ReferentialAction        # 删除行为
    match_option: Optional[str]         # 匹配选项
    extra: Dict[str, Any]               # 额外信息
```

### ViewInfo

视图信息：

```python
@dataclass
class ViewInfo:
    name: str                    # 视图名
    schema: str                  # Schema 名称
    definition: str              # 视图定义 SQL
    is_updatable: Optional[bool] # 是否可更新
    comment: Optional[str]       # 视图注释
    extra: Dict[str, Any]        # 额外信息
```

### TriggerInfo

触发器信息：

```python
@dataclass
class TriggerInfo:
    name: str                    # 触发器名
    table_name: str              # 关联表名
    event: TriggerEvent          # 触发事件
    timing: TriggerTiming        # 触发时机
    statement: str               # 触发器 SQL
    condition: Optional[str]     # 触发条件
    extra: Dict[str, Any]        # 额外信息
```

## 基本用法

### 访问内省器

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database=":memory:")
backend.connect()

# 通过 introspector 属性访问
introspector = backend.introspector
```

### 获取数据库信息

```python
# 同步 API
db_info = backend.introspector.get_database_info()
print(f"数据库名称: {db_info.name}")
print(f"版本: {db_info.version}")
print(f"厂商: {db_info.vendor}")

# 异步 API
db_info = await backend.introspector.get_database_info()
```

### 列出表

```python
# 列出所有用户表
tables = backend.introspector.list_tables()
for table in tables:
    print(f"表: {table.name}, 类型: {table.table_type.value}")

# 包含系统表
all_tables = backend.introspector.list_tables(include_system=True)

# 过滤特定类型
base_tables = backend.introspector.list_tables(table_type="BASE TABLE")
views = backend.introspector.list_tables(table_type="VIEW")

# 检查表是否存在
if backend.introspector.table_exists("users"):
    print("users 表存在")

# 获取表详情
table_info = backend.introspector.get_table_info("users")
```

### 查询列信息

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

# 获取单列信息
col_info = backend.introspector.get_column_info("users", "email")
```

### 查询索引

```python
# 列出表的所有索引
indexes = backend.introspector.list_indexes("users")
for idx in indexes:
    unique = "UNIQUE " if idx.is_unique else ""
    print(f"{unique}索引: {idx.name}")
    for col in idx.columns:
        desc = "DESC" if col.is_descending else "ASC"
        print(f"  - {col.name} ({desc})")

# 检查索引是否存在
if backend.introspector.index_exists("users", "idx_users_email"):
    print("email 索引存在")
```

### 查询外键

```python
# 列出表的外键
foreign_keys = backend.introspector.list_foreign_keys("posts")
for fk in foreign_keys:
    print(f"外键: {fk.name}")
    print(f"  列: {fk.columns} -> {fk.referenced_table}.{fk.referenced_columns}")
    print(f"  ON DELETE: {fk.on_delete.value}")
    print(f"  ON UPDATE: {fk.on_update.value}")
```

### 查询视图

```python
# 列出所有视图
views = backend.introspector.list_views()
for view in views:
    print(f"视图: {view.name}")

# 获取视图详情
view_info = backend.introspector.get_view_info("user_posts_summary")
if view_info:
    print(f"定义: {view_info.definition}")

# 检查视图是否存在
if backend.introspector.view_exists("user_posts_summary"):
    print("视图存在")
```

### 查询触发器

```python
# 列出所有触发器
triggers = backend.introspector.list_triggers()
for trigger in triggers:
    print(f"触发器: {trigger.name} on {trigger.table_name}")

# 列出特定表的触发器
table_triggers = backend.introspector.list_triggers("users")
for trigger in table_triggers:
    print(f"触发器: {trigger.name}")
    print(f"  事件: {trigger.event.value}")
    print(f"  时机: {trigger.timing.value}")

# 获取触发器详情
trigger_info = backend.introspector.get_trigger_info("users", "trg_users_audit")
```

## 异步 API

异步后端提供相同的内省方法，方法名不带 `_async` 后缀（与同步方法同名）：

```python
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

backend = AsyncSQLiteBackend(database=":memory:")
await backend.connect()

# 异步内省方法（方法名与同步版本相同）
db_info = await backend.introspector.get_database_info()
tables = await backend.introspector.list_tables()
table_info = await backend.introspector.get_table_info("users")
columns = await backend.introspector.list_columns("users")
indexes = await backend.introspector.list_indexes("users")
foreign_keys = await backend.introspector.list_foreign_keys("posts")
views = await backend.introspector.list_views()
triggers = await backend.introspector.list_triggers()
```

## 缓存机制

内省结果默认会被缓存以提高性能。

### 缓存配置

```python
# 默认 TTL 为 300 秒（5 分钟）
# 内省器初始化时自动设置
```

### 缓存管理

```python
# 清除所有缓存
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

# 使列相关缓存失效
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.COLUMN,
    table_name="users"
)

# 使索引相关缓存失效
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.INDEX,
    table_name="users",
    name="idx_users_email"
)
```

### 缓存作用域

| 作用域 | 说明 | 失效参数 |
|--------|------|----------|
| `DATABASE` | 数据库信息 | 无 |
| `SCHEMA` | Schema 信息 | `name` |
| `TABLE` | 表信息 | `name` |
| `COLUMN` | 列信息 | `table_name`, `name` |
| `INDEX` | 索引信息 | `table_name`, `name` |
| `FOREIGN_KEY` | 外键信息 | `table_name`, `name` |
| `VIEW` | 视图信息 | `name` |
| `TRIGGER` | 触发器信息 | `table_name`, `name` |

## 后端特定实现

### SQLite

SQLite 使用 `PRAGMA` 指令实现内省：

```python
# SQLite 专属：直接访问 PragmaIntrospector
pragma = backend.introspector.pragma

# 使用 PRAGMA 指令
table_info = pragma.pragma_table_info("users")
index_list = pragma.pragma_index_list("users")
foreign_keys = pragma.pragma_foreign_key_list("posts")
```

### MySQL

MySQL 使用 `information_schema` 和 `SHOW` 语句实现内省：

```python
# MySQL 专属：直接访问 ShowIntrospector
show = backend.introspector.show

# 使用 SHOW 语句
tables = show.show_tables()
columns = show.show_columns("users")
indexes = show.show_index("users")
create_table = show.show_create_table("users")
```

## 错误处理

内省系统定义了专用异常：

```python
from rhosocial.activerecord.backend.introspection.errors import (
    IntrospectionError,       # 内省基础异常
    TableNotFoundError,       # 表不存在
    ColumnNotFoundError,      # 列不存在
    IndexNotFoundError,       # 索引不存在
    ViewNotFoundError,        # 视图不存在
    TriggerNotFoundError,     # 触发器不存在
)

try:
    table_info = backend.introspector.get_table_info("nonexistent")
except TableNotFoundError as e:
    print(f"表不存在: {e}")
```

## 最佳实践

### 1. 使用缓存

内省操作通常涉及多次数据库查询，建议利用缓存：

```python
# 首次查询会缓存结果
tables = backend.introspector.list_tables()

# 后续查询直接从缓存返回
tables_again = backend.introspector.list_tables()

# 只有在表结构变更后才需要清除缓存
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE, name="users")
```

### 2. 批量操作

尽可能使用批量查询方法：

```python
# 好：一次查询获取所有列
columns = backend.introspector.list_columns("users")

# 避免：多次查询单列
for col_name in column_names:
    col = backend.introspector.get_column_info("users", col_name)  # 每次 I/O
```

### 3. 检查存在性

在执行依赖操作前检查对象是否存在：

```python
if backend.introspector.table_exists("users"):
    columns = backend.introspector.list_columns("users")
else:
    print("表不存在，跳过处理")
```

### 4. 异步环境中使用

```python
async def get_schema_info(backend):
    # 异步方法与同步方法同名
    tables = await backend.introspector.list_tables()

    # 并发获取多个表的列信息
    import asyncio
    tasks = [
        backend.introspector.list_columns(table.name)
        for table in tables
    ]
    all_columns = await asyncio.gather(*tasks)
    return dict(zip([t.name for t in tables], all_columns))
```

## 限制与注意事项

1. **权限要求**：内省功能需要数据库用户具有读取元数据的权限
2. **性能影响**：大规模数据库的内省可能较慢，建议启用缓存
3. **版本差异**：不同数据库版本的元数据可用性可能不同
4. **一致性**：内省结果反映查询时刻的数据库状态，非实时

## API 参考

### 核心方法

| 方法 | 说明 | 参数 |
|------|------|------|
| `get_database_info()` | 获取数据库信息 | 无 |
| `list_tables()` | 列出表 | `include_system`, `table_type`, `schema` |
| `get_table_info(name)` | 获取表详情 | `name`, `schema` |
| `table_exists(name)` | 检查表存在 | `name`, `schema` |
| `list_columns(table_name)` | 列出列 | `table_name`, `schema` |
| `get_column_info(table_name, column_name)` | 获取列详情 | `table_name`, `column_name`, `schema` |
| `get_primary_key(table_name)` | 获取主键 | `table_name`, `schema` |
| `list_indexes(table_name)` | 列出索引 | `table_name`, `schema` |
| `get_index_info(table_name, index_name)` | 获取索引详情 | `table_name`, `index_name`, `schema` |
| `index_exists(table_name, index_name)` | 检查索引存在 | `table_name`, `index_name`, `schema` |
| `list_foreign_keys(table_name)` | 列出外键 | `table_name`, `schema` |
| `list_views()` | 列出视图 | `schema` |
| `get_view_info(name)` | 获取视图详情 | `name`, `schema` |
| `view_exists(name)` | 检查视图存在 | `name`, `schema` |
| `list_triggers(table_name)` | 列出触发器 | `table_name`, `schema` |
| `get_trigger_info(table_name, trigger_name)` | 获取触发器详情 | `table_name`, `trigger_name`, `schema` |
| `clear_cache()` | 清除缓存 | 无 |
| `invalidate_cache(scope, ...)` | 使缓存失效 | `scope`, `name`, `table_name` |
