# 数据库内省 (Database Introspection)

数据库内省是一种在运行时查询数据库结构元数据的能力。rhosocial-activerecord 提供了完整的内省系统，支持查询数据库、表、列、索引、外键、视图、触发器等元数据。

## 概述

内省系统位于 `backend.introspector` 属性中，提供：

- **数据库信息**：名称、版本、编码、大小等
- **表信息**：表列表、表详情、表类型（`BASE_TABLE`、`VIEW`、`MATERIALIZED_VIEW`、`FOREIGN_TABLE`、`PARTITIONED_TABLE`、`SYSTEM_TABLE`、`TEMPORARY`、`EXTERNAL`）
- **列信息**：列名、数据类型、是否可空、默认值、主键信息
- **索引信息**：索引名、列、唯一性、索引类型
- **外键信息**：引用表、列映射、更新/删除行为
- **视图信息**：视图定义 SQL
- **触发器信息**：触发事件、执行时机、触发器 SQL
- **对象状态**：表、分区、索引、约束、序列和引擎派生对象的中立快照，由核心数据类构成

## 可以问什么

内省回答四类问题，本页详述第一类：

- **声明层** —— 目录说对象是什么：数据库、表、列、索引、外键、视图和触发器。dialect 的能力探针说明某个引擎是否能回答其中每一类；见[能力探针](introspection/capabilities.md)。
- **运维层** —— 引擎运行中统计了什么：未使用索引、表与索引使用计数、运行时测量、对象依赖和 DDL 取回；见[运维家族](introspection/operations.md)。
- **数据层** —— 行实际持有什么，而不是模式承诺什么：列数据剖面、高频值和连接覆盖度；见[列数据剖面](introspection/data-profiles.md)。
- **对象状态层** —— 服务器此刻持有什么，形状由调用方拥有：表状态、分区状态、索引/约束/序列状态、引擎派生对象和共享对象存在性；见[中立对象状态](#中立对象状态)。

某类问题的能力探针返回 `False` 时，该引擎不提供这类回答；各后端自己的文档说明哪些探针返回 `True`，以及它的回答意味着什么。

## 架构设计

### 模块结构

```
backend/introspection/
├── __init__.py          # 模块导出
├── base.py              # 抽象内省器基类（同步 / 异步）
├── types.py             # 数据结构定义（TableType 等）
├── errors.py            # 内省专用异常
├── executor.py          # 执行器抽象
├── cache.py             # IntrospectionCache —— 可注入的结果缓存
├── backend_mixin.py     # Backend 混入类
└── status/              # 服务器状态概览（配置、性能、存储）
```

### 一个目录问题就是一个语句

内省不会就地拼接 SQL 文本。每个问题都是一个语句类（名为 `*Statement`，例如 `TableListQueryStatement`），由 dialect 的 `format_*_query_statement` 格式化；内省器持有使用它们的公开方法对（`list_tables()` / `parse_tables()` 等）。这带来两点对后端作者重要的后果：

- 表达式层不持有状态 —— 语句只包含渲染它所需要的全部信息；
- 后端回答一个目录问题的方式，是声明一个语句加一个格式化函数，而不是覆盖某个拼字符串的方法。

### 同步与异步分离

内省系统遵循项目的同步/异步对等原则：

- `AbstractIntrospector` — 同步内省器
- `AsyncAbstractIntrospector` — 异步内省器
- `IntrospectorMixin` — 共享的非 I/O 基类：它知道默认 schema，并暴露 `dialect` 与 `server_version` 快捷入口，但本身不持有状态、不做 I/O、也从不接触结果行。缓存与结果行解析属于继承它的管理器，SQL 由 dialect 的 `format_*` 方法从语句对象渲染。`server_version` 是内省器从服务器读到的版本，使能力判断不必再次询问服务器

## 能力协议

能力声明被拆成四个内省家族，而不是由单一协议承载。每个家族有一个同步协议、一个
成员相同的异步孪生，以及一个成员列表相同的方言混入：

| 家族 | 回答的问题 | 协议（同步 / 异步孪生） | 方言混入（同步 / 异步孪生） |
|------|------------|--------------------------|------------------------------|
| 结构 | 目录说对象是什么 | `StructureIntrospectionSupport` / `AsyncStructureIntrospectionSupport` | `StructureIntrospectionMixin` / `AsyncStructureIntrospectionMixin` |
| 运维统计 | 对象过去如何表现 | `OperationalStatsIntrospectionSupport` / `AsyncOperationalStatsIntrospectionSupport` | `OperationalStatsIntrospectionMixin` / `AsyncOperationalStatsIntrospectionMixin` |
| 数据剖面 | 一列的行长什么样 | `DataProfileIntrospectionSupport` / `AsyncDataProfileIntrospectionSupport` | `DataProfileIntrospectionMixin` / `AsyncDataProfileIntrospectionMixin` |
| DDL 取回 | 重建对象所需的文本 | `DdlExtractionIntrospectionSupport` / `AsyncDdlExtractionIntrospectionSupport` | `DdlExtractionIntrospectionMixin` / `AsyncDdlExtractionIntrospectionMixin` |

`IntrospectionMixin` 与 `AsyncIntrospectionMixin` 是四者的**纯组合聚合**：它们
自己不声明任何成员，所以组合了其中一个的 dialect 会继承每个家族的答案，方言中
任何位置的方法名覆盖也仍然生效。拆分为四族，是为了让 dialect 能回答一个问题
——声明、行为、数据、留存文本——而不声称其余三个。

一个家族**只有在至少一个探针回答 `True` 时才被声称**。组合聚合本身不构成声称：
一个组合了 `IntrospectionMixin`、但所有运维探针都回答 `False` 的 dialect，即使
方法存在于类上，也不算声称运维统计。每个后端的协议一致性测试都应用这条规则。

```python
from rhosocial.activerecord.backend.dialect.protocols import (
    StructureIntrospectionSupport,
    OperationalStatsIntrospectionSupport,
    DataProfileIntrospectionSupport,
    DdlExtractionIntrospectionSupport,
)

FAMILIES = (
    StructureIntrospectionSupport,
    OperationalStatsIntrospectionSupport,
    DataProfileIntrospectionSupport,
    DdlExtractionIntrospectionSupport,
)

dialect = backend.dialect
for family in FAMILIES:
    probes = [name for name in dir(family) if name.startswith("supports_")]
    claimed = any(getattr(dialect, name)() for name in probes)
    print(f"{family.__name__}: claimed={claimed}")
```

`True` 承诺这个引擎会回答；`False` 意味着不要问。每个回答承诺什么、不承诺什么，
见[能力探针](introspection/capabilities.md)。

[中立对象状态](#中立对象状态) 中的对象状态方法不是这些协议上的探针。它们是
管理器上的方法，回答不了一个方法的后端会按名字拒绝，而不是返回空值。

## 数据结构

### IntrospectionDatabaseInfo

数据库基本信息：

```python
@dataclass
class IntrospectionDatabaseInfo:
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

### IntrospectionTableInfo

表信息：

```python
@dataclass
class IntrospectionTableInfo:
    name: str                    # 表名
    schema: str                  # Schema 名称
    table_type: TableType        # 表类型（BASE_TABLE、VIEW、MATERIALIZED_VIEW、
                                 #  FOREIGN_TABLE、PARTITIONED_TABLE、SYSTEM_TABLE、
                                 #  TEMPORARY、EXTERNAL）
    comment: Optional[str]       # 表注释
    row_count: Optional[int]     # 行数估计
    size_bytes: Optional[int]    # 表大小
    extra: Dict[str, Any]        # 额外信息
```

`table_type` 保留目录实际做出的区分，而不是把所有关系都折叠成"表"。某个引擎如何归类一种关系，由该后端自己的文档说明。

### IntrospectionColumnInfo

列信息：

```python
@dataclass
class IntrospectionColumnInfo:
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

### IntrospectionForeignKeyInfo

外键信息：

```python
@dataclass
class IntrospectionForeignKeyInfo:
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

### IntrospectionViewInfo

视图信息：

```python
@dataclass
class IntrospectionViewInfo:
    name: str                    # 视图名
    schema: str                  # Schema 名称
    definition: str              # 视图定义 SQL
    is_updatable: Optional[bool] # 是否可更新
    comment: Optional[str]       # 视图注释
    extra: Dict[str, Any]        # 额外信息
```

### IntrospectionTriggerInfo

触发器信息：

```python
@dataclass
class IntrospectionTriggerInfo:
    name: str                    # 触发器名
    table_name: str              # 关联表名
    event: TriggerEvent          # 触发事件
    timing: TriggerTiming        # 触发时机
    statement: str               # 触发器 SQL
    condition: Optional[str]     # 触发条件
    extra: Dict[str, Any]        # 额外信息
```

## 中立对象状态

状态方法回答"服务器此刻持有什么"，并把答案放进中立的核心数据类。调用方永远看不到
后端特有的结果类型：每个后端把自己的目录映射成下面的形状。八个方法在同步与异步
内省器上同名存在；在异步类（`Async*Introspector`）上，每次调用都要 await。

| 方法 | 参数（含默认值） | 返回 |
|------|------------------|------|
| `get_table_state(table_name)` | `schema=None` | `TableState` |
| `get_partition_state(table_name)` | `schema=None, include_stats=False` | `PartitionState` |
| `list_index_states(table_name)` | `schema=None` | `List[IndexState]` |
| `list_constraint_states(table_name)` | `schema=None` | `List[ConstraintState]` |
| `list_sequence_states()` | `schema=None` | `List[SequenceState]` |
| `list_derived_objects(table_name)` | `schema=None` | `List[DerivedObjectState]` |
| `list_schemas()` | — | `List[str]` |
| `item_exists(kind, name)` | `schema=None` | `bool` |

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.introspection import TableState

backend = SQLiteBackend(database=":memory:")
backend.connect()
backend.executescript("""
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'open'
);
""")

state = backend.introspector.get_table_state("orders")
assert isinstance(state, TableState)
print(state.name, state.schema, state.kind, state.traits)
```

### 状态形状

所有状态类型都是
`rhosocial.activerecord.backend.introspection.types` 中的 frozen 数据类，并从
`rhosocial.activerecord.backend.introspection` 重新导出。

```python
@dataclass(frozen=True)
class TableState:
    name: str
    schema: Optional[str]
    kind: str                       # "regular" / "temporary" / "transient" / "unlogged"；
                                    #  后端可以增加自己的拼写
    traits: Tuple[str, ...]         # 复合特征，例如 "strict"、"without_rowid"
    storage: StorageOptionsState
    comment: Optional[str]
    partitioning: PartitionState        # 永不为 None；未分区时是空的 PartitionState
    raw: Dict[str, Any]            # 后端自己的槽位

@dataclass(frozen=True)
class StorageOptionsState:
    engine: Optional[str]           # None 表示引擎用了自己的默认值，
    charset: Optional[str]          #  而不是"未知"
    collation: Optional[str]
    compression: Optional[str]
    tablespace: Optional[str]
    raw: Dict[str, Any]

@dataclass(frozen=True)
class PartitionState:
    scheme: Optional[PartitionScheme]   # None 是"未分区"的唯一答案
    key_expression: str
    key_columns: Tuple[str, ...]
    has_default: bool
    auto_extend: bool
    bounds: Tuple[PartitionBound, ...]
    raw: Dict[str, Any]

@dataclass(frozen=True)
class PartitionBound:
    name: str
    lower: Optional[str]            # 服务器拼写的 RANGE/LIST 边界
    upper: Optional[str]
    values: Tuple[str, ...]
    modulus: Optional[int]          # HASH：键按 modulus 取模哈希到 remainder
    remainder: Optional[int]
    is_default: bool
    is_maxvalue: bool
    row_count: Optional[int]        # 只在请求了 include_stats 时填充
    size_bytes: Optional[int]       # 只在请求了 include_stats 时填充
    subpartition_count: int
    tablespace: Optional[str]

@dataclass(frozen=True)
class IndexState:
    name: str
    table: str
    schema: Optional[str]
    unique: bool
    method: Optional[str]
    predicate: Optional[str]
    visible: bool
    usable: bool                    # 引擎报告索引不可用/无效时为 False
    backs_constraint: Optional[str]
    raw: Dict[str, Any]

@dataclass(frozen=True)
class ConstraintState:
    name: str
    table: str
    kind: str                       # 例如 "primary_key"、"unique"、"check"、"foreign_key"
    schema: Optional[str]
    validated: bool
    enforced: bool
    deferred: bool
    disabled: bool
    backing_index: Optional[str]
    raw: Dict[str, Any]

@dataclass(frozen=True)
class SequenceState:
    name: str
    schema: Optional[str]
    owned_by: Optional[str]         # 拥有该序列的列（如果有）
    start: Optional[int]
    increment: Optional[int]
    raw: Dict[str, Any]

@dataclass(frozen=True)
class DerivedObjectState:
    kind: str                       # "backing_index" / "identity_sequence" / "history_table" /
                                    #  "named_default" / "autoindex"
    name: str
    owned_by: Optional[str]
    raw: Dict[str, Any]
```

两个枚举都是 `str` 枚举，所以值打印出来就是它的词：

| 枚举 | 值 |
|------|----|
| `PartitionScheme` | `range`、`list`、`hash`、`key`、`composite`、`interval`、`expression` |
| `ItemKind` | `schema`、`type`、`domain`、`function`、`sequence`、`table`、`index`、`extension`、`tablespace`、`partition_function`、`partition_scheme`、`fulltext_catalog` |

### scheme=None 是"未分区"的唯一答案

`PartitionState.scheme` 是"这张表是否分区"的唯一中立答案。无论后端怎样拼写或发现
分区（子表、系统分区、装饰过的表），它对每个后端都是 `None`。其他任何东西都不能
代替它：不是空的 `bounds`，不是编造出来的 scheme，也不是缺失的 `PartitionState`
—— `get_partition_state` 返回状态对象，并把 `None` 放进 `scheme`。`scheme` 为
`None` 时 `bounds` 为空，因为没有分区可描述。

```python
partition = backend.introspector.get_partition_state("orders")

assert partition.scheme is None      # 唯一的中立答案：未分区
assert partition.bounds == ()
print(partition.scheme, partition.key_columns)
```

`TableState.partitioning` 永不为 `None`。完全没有分区的引擎回答一个空的
`PartitionState`，其 `scheme` 为 `None` —— 与 `get_partition_state` 给出的是同一个
唯一中立答案。`None` 不是答案，调用方不得对它做判断。

### 统计是按需的，默认不得去查

`include_stats=False` 是默认值。这个选择发生在投影和查询层，而不是事后过滤值：默认
情况下后端必须完全不运行统计查询，所以 `PartitionBound.row_count` 与
`PartitionBound.size_bytes` 保持 `None`。`include_stats=True` 时后端才加上统计列
——例如目录里的行数估计和关系大小的查询——同样的 bounds 才携带这些数字。代价差别
就在那条查询上：靠遍历关系来计算大小的引擎，可能为每个分区付出一次扫描，而默认答案
只读一次目录。

```python
plain = backend.introspector.get_partition_state("orders")
assert all(bound.row_count is None and bound.size_bytes is None for bound in plain.bounds)

with_stats = backend.introspector.get_partition_state("orders", include_stats=True)
# 在分区引擎上，with_stats.bounds 现在携带 row_count / size_bytes。
print([(bound.name, bound.row_count, bound.size_bytes) for bound in with_stats.bounds])
```

在没有分区的引擎（SQLite）上，两次调用都回答 `PartitionState(scheme=None)`；没有
bounds 可比较，所以差别只有在存在 scheme 的地方才可观察。

### 拒绝要报出名字

后端没有实现的方法会抛出 `ProtocolNotImplementedError`，消息里指明 dialect、家族
和方法。空列表或 `None` 绝不能代替"无法回答"：它们意味着问题被问了、答案是"什么都
没有"，这是另一件事实。

```python
from types import SimpleNamespace

from rhosocial.activerecord.backend.dialect.exceptions import ProtocolNotImplementedError
from rhosocial.activerecord.backend.introspection.base import (
    AbstractIntrospector,
    IntrospectorMixin,
)


class UnimplementedIntrospector(IntrospectorMixin):
    def __init__(self):
        self._backend = SimpleNamespace(dialect=SimpleNamespace(name="Custom"))


try:
    AbstractIntrospector.get_table_state(UnimplementedIntrospector(), "orders")
except ProtocolNotImplementedError as exc:
    # 'Custom' dialect does not implement StructureIntrospectionSupport
    # protocol, which is required by get_table_state.
    print(exc.dialect_name, exc.protocol_name, exc.required_by)
```

异常把三个名字作为属性携带（`dialect_name`、`protocol_name`、`required_by`），
调用方不必解析消息就能据此反应。`None` 作为答案只保留给"问题已回答、但没有东西可
报告"的情况：`get_ddl_statement` 在引擎被问过、且没有文本时返回 `None`，绝不因为
引擎无法回答而返回。

### item_exists 回答三种情况

`item_exists(kind, name)` 问共享对象是否存在。共享对象比表活得更久：序列、类型、
域、函数、扩展、表空间、分区函数/方案、全文目录。一条规则覆盖所有类别：

1. 引擎根本没有这一类对象 → `False`，确定地表示"没有"，而不是"说不清"；
2. 引擎有这类对象，且目录查询已实现 → 查询并回答 `True` 或 `False`；
3. 引擎有这类对象，但这个后端没有该类别的查询 → 用
   `ProtocolNotImplementedError` 拒绝：这是实现缺口，这里的 `False` 会把它伪装成
   不存在。

```python
from rhosocial.activerecord.backend.introspection import ItemKind

introspector = backend.introspector

# 情况 2：SQLite 有表，且这个后端能查询它们
print(introspector.item_exists(ItemKind.TABLE, "orders"))      # True
print(introspector.item_exists(ItemKind.TABLE, "missing"))     # False：问过，没有

# 情况 1：SQLite 根本没有具名类型对象
print(introspector.item_exists(ItemKind.TYPE, "orders"))       # False：不存在
```

处于情况 3 的后端会抛出异常，而不是回答 `False`。

### 迁移说明：list_partitions 已被移除

`list_partitions` 已被移除，且没有兼容层。它的逻辑并入 `get_partition_state`：
scheme 和 bounds 现在一起放在一个 `PartitionState` 里，`scheme` 回答"这张表是否
分区"，`bounds` 描述各个分区。没有别名，也没有回退写法；唯一支持的拼写是
`get_partition_state`。

分区能力已移出内省家族：向
`PartitionSupport.supports_partition_metadata_introspection()` 询问后再向后端请求
分区元数据。见[能力探针](introspection/capabilities.md)。

## 基本用法

### 访问内省器

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend

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
if backend.introspector.get_index_info("users", "idx_users_email"):
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
trigger_info = backend.introspector.get_trigger_info("trg_users_audit")
```

## 异步 API

异步后端提供相同的内省方法，方法名不带 `_async` 后缀（与同步方法同名）：

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import AsyncSQLiteBackend

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

# 中立对象状态：同名方法，需要 await
state = await backend.introspector.get_table_state("users")
partition = await backend.introspector.get_partition_state("users")
```

## 缓存机制

内省结果默认会被缓存以提高性能。缓存是管理器的**组件**——管理器拥有它，调用者可以替换它——而不是隐藏属性：`backend.introspector.cache`。

### 缓存契约

`IntrospectionCache`（`rhosocial.activerecord.backend.introspection.cache`）是一个协议，因此后端可以把自有实现放进管理器后面，而不必继承本包的过期策略：

| 方法 | 用途 |
|------|------|
| `key(scope, name=None, schema=None, extra=None)` | 生成"问同一个问题"的两次调用共享的键 |
| `get(key)` | 返回缓存结果，或 `None` |
| `set(key, value)` | 存入结果 |
| `invalidate(scope=None, name=None)` | 从全体失效到单个对象失效 |
| `clear()` | 丢弃全部缓存结果 |

`InMemoryIntrospectionCache` 是默认实现：进程内、按 TTL 过期（默认 300 秒），过期项在有人查看时才被丢弃，而不是由后台清扫器处理。

```python
from rhosocial.activerecord.backend.introspection.cache import InMemoryIntrospectionCache

# 默认：进程内、300 秒 TTL
backend.introspector.cache = InMemoryIntrospectionCache(ttl=60)

# 或使用自己的缓存：只要满足该协议
class NoCache:
    def key(self, scope, name=None, schema=None, extra=None):
        return (scope, name, schema, extra)

    def get(self, key):
        return None

    def set(self, key, value):
        pass

    def invalidate(self, scope=None, name=None):
        pass

    def clear(self):
        pass

backend.introspector.cache = NoCache()
```

### 缓存管理

```python
# 清除所有缓存
backend.introspector.clear_cache()

# 使特定作用域的缓存失效
from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

# 使所有表相关缓存失效
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE)

# 使特定表、索引、列集合……的缓存失效
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.TABLE,
    name="users"
)
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.INDEX,
    name="idx_users_email"
)
```

### 缓存作用域

作用域说明一次失效波及哪些已缓存的答案，所以问题涉及的表由 `name` 携带（在 `key()` 中则由 `schema` / `extra` 携带）：

| 作用域 | 说明 |
|--------|------|
| `DATABASE` | 数据库信息 |
| `SCHEMA` | Schema 信息 |
| `TABLE` | 表信息 |
| `COLUMN` | 列信息 |
| `INDEX` | 索引信息 |
| `FOREIGN_KEY` | 外键信息 |
| `VIEW` | 视图信息 |
| `TRIGGER` | 触发器信息 |

## 后端特定实现

公共方法建立在后端提供的辅助内省器之上——内置 SQLite 后端的 `PragmaIntrospector` 与（例如）MySQL 的 `ShowIntrospector` 就是其中两种——各后端自己的文档说明它有哪些辅助内省器、它们回答什么，以及这些回答意味着什么。

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

三条事实能解释几乎每一个出人意料的内省回答：

1. **计数器是一个窗口，不是一生。** 运维家族报告的是引擎在*最后一次统计重置以来*数到了什么。零意味着"这个窗口里没有发生"，绝不意味着"从未发生过"。
2. **剖面可能描述一张更旧的表。** 从统计目录读到的数字可能和引擎最后一次刷新一样陈旧；`collected_at` 就在它们旁边，让读者知道它们描述的是哪个时刻。
3. **有些引擎回答不了有些问题。** 先问 dialect 的能力探针——见[能力探针](introspection/capabilities.md)。`False` 是确定的"这个引擎不回答这一类问题"，而各后端自己的文档说明哪些探针返回 `True`、它的回答意味着什么。

## API 参考

以下签名省略 `self`；同步与异步内省器的方法名和参数相同。

### 核心方法 —— 声明层

目录说对象是什么。每个结果都缓存在它所属的作用域下。

| 方法 | 参数（含默认值） | 说明 |
|------|------------------|------|
| `get_database_info()` | — | 数据库信息 |
| `list_tables()` | `schema=None, include_system=False, table_type=None` | 列出表（含视图） |
| `get_table_info(table_name)` | `schema=None` | 表详情，含列、索引和外键 |
| `table_exists(table_name)` | `schema=None` | 表是否存在 |
| `list_columns(table_name)` | `schema=None` | 列出列 |
| `get_column_info(table_name, column_name)` | `schema=None` | 列详情 |
| `column_exists(table_name, column_name)` | `schema=None` | 列是否存在 |
| `get_primary_key(table_name)` | `schema=None` | 主键索引 |
| `list_indexes(table_name)` | `schema=None` | 列出索引 |
| `get_index_info(table_name, index_name)` | `schema=None` | 索引详情 |
| `list_foreign_keys(table_name)` | `schema=None` | 列出外键 |
| `get_foreign_key_info(table_name, fk_name)` | `schema=None` | 外键详情 |
| `list_views()` | `schema=None, include_system=False` | 列出视图 |
| `get_view_info(view_name)` | `schema=None` | 视图详情 |
| `view_exists(view_name)` | `schema=None` | 视图是否存在 |
| `list_triggers()` | `table_name=None, schema=None` | 列出触发器，可按表过滤 |
| `get_trigger_info(trigger_name)` | `schema=None` | 触发器详情 |

### 核心方法 —— 中立对象状态

下面八个方法返回核心数据类，而不是后端特有的结果类型。它们不受四族探针把关：后端
没有实现其中某个方法时，会按名字拒绝（见[拒绝要报出名字](#拒绝要报出名字)）。同步
与异步内省器声明相同的名字；在异步类上，每次调用都要 await。

| 方法 | 参数（含默认值） | 说明 |
|------|------------------|------|
| `get_table_state(table_name)` | `schema=None` | 表的 kind、traits、存储选项、注释和分区状态 |
| `get_partition_state(table_name)` | `schema=None, include_stats=False` | 分区方案（未分区时为 `None`）及其 bounds；统计仅按需 |
| `list_index_states(table_name)` | `schema=None` | 每个索引，含方法、谓词、可见性和可用性 |
| `list_constraint_states(table_name)` | `schema=None` | 每个约束，含类别和验证/强制状态 |
| `list_sequence_states()` | `schema=None` | 一个 schema 的序列，及其拥有列 |
| `list_derived_objects(table_name)` | `schema=None` | 引擎为某个声明创建的对象（autoindex、identity sequence 等） |
| `list_schemas()` | — | 服务器暴露的 schema/命名空间名称 |
| `item_exists(kind, name)` | `schema=None` | 某个 `ItemKind` 的共享对象是否存在，按三种情况规则回答 |

### 核心方法 —— 运维层

这里的计数器是窗口，不是一生：零意味着"最后一次统计重置以来没有发生"（见[限制与注意事项](#限制与注意事项)）。调用前先看 dialect 的能力探针；`False` 表示该引擎不提供这一类回答。

| 方法 | 参数（含默认值） | 说明 |
|------|------------------|------|
| `list_unused_indexes()` | `schema=None` | 引擎报告从未服务过查询的索引 |
| `list_table_usage_stats()` | `schema=None` | 每张表的读/写计数，自最后一次统计重置起 |
| `list_runtime_metrics()` | `schema=None` | 实时运行时测量；每一项的 `source` 说明其窗口 |
| `list_index_usage_stats()` | `schema=None` | 每个索引的使用计数（"用了多少"，而非"是否用过"） |
| `list_object_dependencies()` | `object_name=None, schema=None` | 依赖图，或某个对象的依赖者 |
| `get_ddl_statement(object_name)` | `object_type=None, schema=None` | 重建某个对象的 DDL，或 `None` |

### 核心方法 —— 数据层

声明说一列*承诺*什么；这些方法说它*实际装*什么。`None` 表示未测量，绝不是零；剖面的 `source` 说明数字从哪来。

| 方法 | 参数（含默认值） | 说明 |
|------|------------------|------|
| `list_column_data_profiles(table_name)` | `schema=None` | 剖析一张表的每一列 |
| `sample_column_values(table_name, column_name)` | `limit=VALUE_SAMPLE_LIMIT, schema=None` | 一列最高频的值，最多 `limit` 个 |
| `estimate_join_coverage(left_table, left_column, right_table, right_column)` | `schema=None` | 两列值域的重叠程度；未测量时为 `None` |

`VALUE_SAMPLE_LIMIT` 只在 `backend/introspection/defaults.py` 中定义一次（当前为 100）；签名引用该常量，而不是重复它的值。

### 缓存与失效

缓存是每一层结果都会经过的组件；它本身不是一个层。

| 方法 | 参数（含默认值） | 说明 |
|------|------------------|------|
| `clear_cache()` | — | 丢弃全部缓存结果 |
| `invalidate_cache()` | `scope=None, name=None` | 使缓存失效，从全体一直到单个对象 |
