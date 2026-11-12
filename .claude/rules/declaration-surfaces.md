# 声明面（Declaration Surfaces）

本文档定义模型可以声明什么、在哪里声明、以及框架如何消费。它是**唯一**的声明口径：
其他文档、示例、docstring 与本文件冲突时，以本文件为准。

## 1. 三条面

一个模型只有三种声明渠道，每种只承载一类事实：

| 面 | 形式 | 承载的事实 | 例子 |
|---|---|---|---|
| **表级面** | 覆盖 `DDLSource` 类方法 | 表名、schema、主键、分区键、索引、约束、表选项 | `table_name()`、`primary_key()`、`table_indexes()` |
| **字段级面** | 字段注记（`Annotated[T, Marker]`） | 列名、列类型、约束、索引、注释、分区键成员 | `UseColumn("id")`、`UseIndex("idx")`、`UsePartitionKey()` |
| **运行时面** | 框架管理的私有状态 | 连接、日志、追踪、缓存等运行时事实 | `_dummy_backend`、`_dirty_fields`、`_version_snapshot` |

**dunder 不再是声明面。** `__table_name__`、`__primary_key__`、`__read_only__` 等
一律不再声明任何东西；写它们不会生效，读它们属于框架内部实现细节。

## 2. 如何声明（速查）

### 2.1 表级事实：覆盖类方法

```python
class User(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "users"

    @classmethod
    def primary_key(cls):
        return "id"                      # 复合键返回 tuple，None 表示无键

    @classmethod
    def schema_name(cls):
        return "crm"                     # 不覆盖 = None，走连接默认 schema

    @classmethod
    def pk_auto_generated(cls):
        return False                     # 应用自备主键
```

默认值一览（不覆盖时的行为）：

| 方法 | 默认 | 说明 |
|---|---|---|
| `table_name()` | **无默认** | 未覆盖 → `NotImplementedError`，在第一次读取处响亮失败 |
| `schema_name()` | `None` | 由连接默认 schema / search_path 解析 |
| `primary_key()` | `"id"` | 单列；返回 tuple 即复合键；返回 `None` 即声明无键模型 |
| `pk_auto_generated()` | `True` | 单列代理键由数据库生成 |
| `partition_key_columns()` | `()` | 见 §3.2 |
| `natural_key()` | `()` | 见 §3.3 |
| `table_indexes()` / `table_constraints()` | `[]` | 由注记衍生的部分自动并入 |
| `object_type()` | `TABLE` | `VIEW` / `MATERIALIZED_VIEW` |
| `deleted_at_field()` 等定位符 | 约定名 | 见 §3.4 |

### 2.2 字段事实：注记

```python
from typing import Annotated

class User(ActiveRecord):
    user_id: Annotated[int, UseColumn("id")]
    email: Annotated[str, UseIndex("idx_email", unique=True)]
    status: Annotated[str, UseConstraint(ColumnCheckConstraint, condition=...)]
```

可用标记：`UseColumn`、`UseColumnType`、`UseSqlType`、`UseConstraint`、`UseIndex`、
`UseColumnAttributes`、`UseComment`、`UseGeneratedColumn`、`UsePartitionKey`、
`UseAdapter`、`DerivedField`。

多列索引/约束在**锚点字段**上声明，`columns` 是权威列表（`columns[0]` 必须是锚点列）：

```python
email: Annotated[str, UseIndex("idx_email_country", columns=["email", "country"])]
```

### 2.3 混入特性：覆盖定位符方法

```python
class Doc(DefaultSoftDeleteMixin, ActiveRecord):
    @classmethod
    def deleted_at_field(cls):
        return "removed_on"          # 默认 "deleted_at"

class Post(DefaultTimestampMixin, ActiveRecord):
    @classmethod
    def created_at_field(cls):
        return "published_at"
```

## 3. 专门面

### 3.1 分区键

两种声明面，**只能选一种**：

```python
# 注记面：成员按 model_fields 顺序提取
bucket: Annotated[str, UsePartitionKey()]
created_at: Annotated[str, UsePartitionKey()]

# 直写面：内省生成的模型走这条
__partition_key__ = ("bucket", "created_day")
```

- 两者同时声明 → 类创建期 `TypeError`（一个事实一个来源）；
- 直写面只接受**纯列名元组**，表达式键暂不支持；
- 分区键不在主键内 → `UserWarning`（ClickHouse/BigQuery 合法，只是提醒）。

### 3.2 分区范围提示

- 查询侧：模型有分区键而 WHERE 未引用任何分区列 → 日志 WARNING；
- CLI：`--where` 未含分区列 → stderr 一行提示（`--quiet` 抑制）。

这是**提示**不是错误：读全部月份是正当需求。

### 3.3 自然键

```python
@classmethod
def natural_key(cls):
    return ("tenant", "external_id")
```

声明后 `find_one_or_create(defaults={...})` 可以不带关键字用声明键取值；
显式关键字 lookup 仍然优先；未声明时行为与从前一致。

### 3.4 定位符

| 方法 | 默认 | 所属 |
|---|---|---|
| `deleted_at_field()` | `deleted_at` | 软删 |
| `created_at_field()` | `created_at` | 时间戳 |
| `updated_at_field()` | `updated_at` | 时间戳 |
| `version_field()` | `version` | 乐观锁 |
| `version_increment_by()` | `1` | 乐观锁 |
| `read_only()` | `True`（继承 ReadOnlyMixin 时） | 只读 |
| `logger_name()` | `None` | 日志 |
| `no_track_fields()` | MRO 并集 | 变更追踪 |
| `uuid_version()` | `"uuid4"` | UUID 主键 |

## 4. 活着的声明 dunder

以下 dunder **仍可作为声明**，其余一律不是：

| dunder | 原因 |
|---|---|
| `__partition_key__` | 内省生成模型与表达式键的入口（§3.1） |
| `__table_indexes__` / `__table_constraints__` | 未注记化的遗留直写面，逐步迁移中（见 §6） |
| `__annotations__` / `ClassVar` 字段 | Pydantic 与 Python 本身 |

## 5. 规则（R1–R5）

- **R1** 消费方只经类方法访问事实；框架内部**不得**直读声明 dunder。
- **R2** 用户覆盖永远赢：类体先于基类，方法覆盖优先级最高。
- **R3** 一个事实一个来源：两处同时声明即类创建期 `TypeError`
  （分区键 both-declared、索引同名冲突、复合声明锚点错位均属此类）。
- **R4** 逐字段的答案优先于类级标志：`IdentityAttribute` 胜过
  `pk_auto_generated()`，`UseColumn` 胜过字段名。
- **R5** 错误必须响亮：未声明 `table_name()` 报错而非返回 `None`；
  未消费的注记在访问器入口 `TypeError`，而非静默忽略。

## 6. 遗留与迁移

- `__table_indexes__` / `__table_constraints__` 直写面仍可读；同名单列/复合索引应改用
  `UseIndex` / `UseConstraint`，冲突检测已就位。
- 后端包与应用包在各自版本迁移；在迁移完成前，它们在新版 core 上会因
  `NotImplementedError` / `TypeError` 直接失败——这是有意的，避免静默漂移。
- 迁移工具：`scripts/d5_migrate_declarations.py`（AST 定位，改写类体 dunder 为方法覆盖）
  与 `scripts/d5_migrate_embedded.py`（改写字符串内嵌的模型源码）。

## 7. 反例（不要这样写）

```python
class Bad(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "bad"          # 不生效：改用 table_name()
    @classmethod
    def primary_key(cls):
        return ("a", "b")    # 不生效：改用 primary_key()
    @classmethod
    def read_only(cls):
        return True            # 不生效：改用 read_only()
    __partition_key__ = ("a",)      # 有效，但不能再同时用 UsePartitionKey
    a: Annotated[int, UsePartitionKey()]   # → TypeError：一个事实两个来源
```
