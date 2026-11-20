# ActiveRecord 定义

> 本文是 `rhosocial-activerecord` 如何定义模型的**权威参考**：对声明面的完整、准确的能力矩阵。它**不是**教程——关于如何使用每项能力，请遵循[第 6 节](#6-where-to-go-next)中的指引。
>
> 范围与状态：本页反映代码的**当前状态**，包括尚未实现的边界与能力（见[第 4 节](#4-current-boundaries--not-yet-implemented)）。

---

## 0. 概览

模型分四层定义。每层各司其职，层与层之间从不交叉：

```text
1. Annotations (Annotated[T, ...])   — 声明模型「声明了什么」
        ↓
2. DDLSource                          — 读取「声明了什么」（24 个方法，与方言无关）
        ↓
3. derivation (build_*_statement)     — 把声明转换为通用语句表达式
        ↓
4. migration (MigrationMixin / @migration / Runner) — 执行或预览这些语句
```

**核心准则：** 声明只回答*「模型声明了什么？」*。它从不构建 SQL、从不绑定方言、从不执行任何操作。方言绑定与能力门控属于第 3、4 层的消费者。

行为 mixin（时间戳、软删除、乐观锁……）与这条流水线并列：它们改变模型的*行为*，并以 `Default*` 形式注入流水线所看到的列。

---

## 1. 能力矩阵

### 1.1 字段注解

声明写在 `typing.Annotated[T, ...]` 中。「是否进入 DDL？」表示该声明会影响生成的 DDL（列名、类型、约束、索引、注释）。标记为**否**的注解只影响运行时行为或查询表达式。

| 注解 | 声明内容 | 是否进入 DDL？ | 消费者 |
|---|---|---|---|
| `DDLAnnotation` | DDL 标记的共同基类；后端自有标记必须继承它并注册处理器 | 仅基类 | `DDLFieldMetadata` |
| `UseSqlType` | 用于**存储**的有序 SQL `DataType` 候选（第一个可渲染者胜出） | 是 | 存储类型推导 |
| `UseConstraint` | 一个列约束分支，或在给出 `columns=` 时的表级 UNIQUE/FOREIGN KEY | 是 | `column_constraints()` / `table_constraints()` |
| `UseIndex` | 锚定在字段上的索引（单个，或通过 `columns=` 组成的复合索引） | 是 | `column_indexes()` / `table_indexes()` |
| `UseColumnAttributes` | 与方言无关的 `IdentityAttribute` / `CollationAttribute` / `CharacterSetAttribute` | 是 | `column_attributes()` |
| `UseComment` | 列注释 | 是 | `column_comment()` / 注释语句 |
| `UseGeneratedColumn` | 数据库计算列表达式（或 `(dialect) -> constraint` 工厂） | 是 | `generated_column()` |
| `UsePartitionKey` | 把字段标记为分区键成员（感知列名） | 是（元数据） | `partition_key_columns()` |
| `UseColumn` | 把 Python 字段名映射为不同的数据库列名 | 是（名称） | `column_name()` |
| `UseFieldGenerator` | 按操作生成 Python 值（`before_insert`、`before_update`、`before_soft_delete`、`before_restore`、`on_all`） | 否 | 写入路径 |
| `UseAdapter` | 一个 `SQLTypeAdapter` 实例 + 目标驱动类型，用于值转换 | 否 | 运行时适配器 |
| `UseColumnType` | `Model.c.<field>` 操作所使用的列类 | 否 | `FieldProxy` / 表达式 |
| `DerivedField` | 查询时计算的、非列的只读字段 | 否（排除） | 派生字段处理器 |

通过 `UseColumnAttributes` 使用的关键值类：`IdentityAttribute`（生成方式必须是 `ALWAYS` 或 `BY DEFAULT`）、`CollationAttribute`、`CharacterSetAttribute`。`ObjectDeclaration`（`TABLE` / `VIEW` / `MATERIALIZED_VIEW`）是 `object_type()` 背后的值。

### 1.2 表级声明（`DDLSource` 方法）

| 方法 | 返回 | 产生方式 | 备注 |
|---|---|---|---|
| `table_options()` | `CreateTableOptions`（及后端子类） | classmethod 覆盖 | 仅通用选项（`or_replace`、注释） |
| `table_storage_options()` | `StorageOptionsExpression` | classmethod 覆盖 | 原样透传 |
| `table_partition()` | `PartitionClause` | classmethod 覆盖 | 与 `partition_key_columns()` 无关 |
| `table_indexes()` | `IndexDefinition` 序列 | `__table_indexes__` | 名称与字段的 `UseIndex` 交叉核对 |
| `table_constraints()` | `TableConstraint` 序列 | 字段 `UseConstraint` + `__table_constraints__` | 合成复合主键约束 |
| `table_inherits()` | 表名列表 | classmethod 覆盖 | PostgreSQL `INHERITS` |
| `table_tablespace()` | 字符串 | classmethod 覆盖 | — |
| `object_type()` | `ObjectDeclaration` | classmethod 覆盖 | 是一个声明，而非内省探测 |
| `schema_name()` | 字符串或 `None` | 模型接口 | 不由 `DDLSourceMixin` 实现 |

同一协议上的相关字段级事实：`table_name()`、`schema_name()`、`primary_key_columns()`、`partition_key_columns()`、`is_composite_pk()`、`ddl_field_names()`（排除派生字段）、`is_derived_field()`，以及第 1.1 节中的 `field_*` / `column_*` 访问器。

### 1.3 行为 mixin

需要了解两条约定：

- **语义基类 vs `Default*`**：纯语义 mixin（如 `TimestampMixin`）**不声明任何字段**；它通过覆盖钩子来维持行为，并通过一个 classmethod（`created_at_field()`）指向模型声明的字段。`Default*` 子类则添加约定字段。除非需要自定义字段名，否则应使用 `Default*`。
- **只有 `Default*` 变体和两个主键 mixin 会注入 DDL 列。** 纯语义 mixin 按名称引用列（通过 `UseColumn` 感知列重命名），不注入任何内容。

| Mixin（语义 / 默认） | 行为 | 注入的 DDL 列（仅 Default*） |
|---|---|---|
| `TimestampMixin` / `DefaultTimestampMixin` (+ `UtcTimestampMixin`) | 生成 `created_at` / `updated_at`；UTC 归一化 | `created_at`、`updated_at` |
| `OptimisticLockMixin` / `DefaultOptimisticLockMixin` | UPDATE 时带版本 WHERE 并自增；检测陈旧数据 | `version`（NOT NULL） |
| `SoftDeleteMixin` / `AsyncSoftDeleteMixin` / `Default*` | 标记删除、过滤查询、恢复 | `deleted_at` |
| `ReadOnlyMixin` | 拒绝所有框架写入路径 | 无 |
| `UUIDMixin` | 由 Python 生成 UUID 主键（uuid4 / uuid7） | `id` |
| `IntegerPKMixin` | 整数自增主键声明 | `id` |
| `CompositePKMixin` | 构造时校验所有主键成员都存在 | 无（校验已声明的列） |

行为 mixin 通过**继承**激活（混入模型类）——除了元类收集特性处理器与接口检查之外，不存在标记，也没有自动发现机制。

---

## 2. 三条设计边界

这些是当前定义中最常被误解的方面。

### 2.1 `UseSqlType` 与 `UseColumnType` 相互独立

| | `UseSqlType` | `UseColumnType` |
|---|---|---|
| 回答的问题 | 值如何**存储**（DDL `DataType`） | `Model.c.<field>` 提供哪些操作（列类） |
| 多个候选 | 允许，第一个可渲染者胜出 | 拒绝（必须恰好一个列类） |
| 是否交叉核对？ | **否** —— 字段可以只声明其一、两者都声明或都不声明；框架从不调和二者 | 同上 |

### 2.2 纯语义 mixin 不注入字段

`TimestampMixin`、`OptimisticLockMixin`、`SoftDeleteMixin`、`ReadOnlyMixin` 和 `CompositePKMixin` 不声明任何 Pydantic 字段。只有 `Default*` 变体以及 `UUIDMixin` / `IntegerPKMixin` 会向 DDL 注入列。通过 `UseColumn` 声明的自定义列名会被自动采纳。

### 2.3 声明、推导、执行三者分离

- `DDLSource` **读取**声明并呈现它们（与方言无关）。
- `base/derivation.py` 中的 `build_*` 函数**推导**通用语句表达式；推导器从不导入后端，也从不决定策略（例如内联索引与独立索引由显式的 `include_indexes` 参数决定，列顺序由调用方掌握并完全指定）。
- `MigrationMixin` 通过后端**执行**语句；函数式迁移（`@migration` + `MigrationContext.apply`）负责**编排**它们，处理依赖/版本/记录，并提供 `--dry-run` 预览。

---

## 3. 模型的生命周期

1. **类创建** —— Pydantic 收集 `model_fields`，然后元类运行特性处理器：校验 DDL 注解（`UseIndex` 锚点、`UseConstraint` 分支、`UsePartitionKey` 冲突），检查 mixin 字段配置，检查同步/异步关系描述符。
2. **实例化** —— Pydantic 校验类型；运行值生成器；`UUIDMixin` / `CompositePKMixin` 执行各自的检查。
3. **查询** —— 字段代理解析列类；派生字段被注入 `SELECT`；软删除谓词过滤结果。
4. **持久化** —— `save()` 先拒绝只读模型，然后调用 `validate_fields()`；DDL 由 `build_*_statement()` 根据声明生成，并由迁移机制执行或预览。

---

## 4. 当前边界 / 尚未实现

本节刻意写得明确——它记录当前定义**不做**什么。

- **不存在赋值时校验。** 模型没有启用 `validate_assignment`；对 `instance.status = "x"` 的赋值不会经过 Pydantic 校验。校验发生在构造时，以及 `save()` 中通过 `validate_fields()` / `validate_record()` 进行。
- **字段枚举范围（`UseEnumRange`）尚未实现。** 它已调研并列入计划；当前对取值集合的强制仅限于 Pydantic 对 `Enum` 注解字段的原生构造时检查，以及可选的 DDL `CHECK` 约束。
- **`object_type()` 在核心库中没有消费者。** 协议、mixin 和再导出都存在，但推导器只构建表语句，从不对 `VIEW` / `MATERIALIZED_VIEW` 做分支处理。
- **`schema_name()` 不是由 `DDLSourceMixin` 提供的**（它来自模型接口），而 `build_create_table_statement()` 构建的是未限定 schema 的 `Table(dialect, table_name())`。
- **`table_partition()` 与 `partition_key_columns()` 是两条独立的通道**；通用推导器从不会根据分区键合成 `PartitionClause`，并且一致性也未受检查。

---

## 5. 验证状态

- 共享契约测试套件 `feature/ddl/core` 覆盖了大多数 `DDLSource` 方法，但截至本文撰写时，它在**全部 11 个仓库中的桥接数为零**——该契约从未在后端的 CI 流水线中运行过。核心仓库有自己的内联 `feature/basic/ddl` 测试，覆盖了其中一部分。
- 有两个协议方法**共享契约中未提及**：`partition_key_columns()` 与 `object_type()`；不过 core 仓自身的内联测试已覆盖它们（分别为 partition-key 测试与只读/视图测试）。

---

## 6. 下一步去哪里

| 想了解…… | 参见 |
|---|---|
| 字段声明、列名、代理 | [字段与代理（Fields & Proxies）](fields.md) |
| `DDLSource` 协议详解 | [DDLSource 声明收集（DDLSource Declarations）](ddl_source.md) |
| DDL 声明示例 | [DDLSource 示例（DDLSource Examples）](ddl_source_examples.md) |
| 生成的 DDL 与语句 | [DDL](ddl.md) |
| 行为 mixin 及其字段 | [Mixin（Mixins）](mixins.md) |
| 派生字段 | [派生字段（Derived Fields）](derived_fields.md) |
| 验证与钩子 | [验证与钩子（Validation & Hooks）](validation.md) |
| 自定义类型与适配器 | [自定义类型（Custom Types）](custom_types.md) |
| 只读模型 / 无主键模型 | [只读模型（Read-Only Models）](readonly_models.md) / [无主键模型（Keyless Models）](keyless_models.md) |
| 并发与乐观锁 | [并发（Concurrency）](concurrency.md) |
