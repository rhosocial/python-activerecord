# DDLSource：从模型声明收集 DDL 定义

`DDLSource` 是 ActiveRecord 暴露 DDL 声明的结构化协议，`DDLSourceMixin` 是它在模型上的默认实现。它负责从模型类中收集 DDL 表达式和声明，并把结果呈现出来；它不选择后端、不生成 SQL、不创建语句计划，也不执行数据库操作。

```python
from rhosocial.activerecord.base import DDLSource
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    __table_name__ = "users"

    id: int
    name: str

assert isinstance(User, DDLSource)
```

同步模型 `ActiveRecord` 和异步模型 `AsyncActiveRecord` 使用同一个 `DDLSourceMixin`，因此 DDL 声明接口对两者保持一致。

## 边界：收集声明，而不是生成 DDL

一次 DDL 声明读取大致经过以下过程：

```text
模型类定义
  → ActiveRecordMetaclass
  → DDLAnnotationHandler.handle()
  → __table_ddl_fields__ 中的 DDLFieldMetadata
  → DDLSourceMixin 的各个接口
  → 调用方读取方言无关的声明
```

`DDLSourceMixin` 的返回值可能是 `UseSqlType`、`ColumnConstraint`、`IndexDefinition`、`TableConstraint` 或后端自己的表达式类实例。它们在收集阶段通常不绑定方言；后续如何选择候选类型、绑定方言、检查能力并构造可渲染表达式，属于外部 DDL 消费者和后端方言的职责。

当前实现不会根据普通 Python 类型自动生成 `DataType`。没有 `UseSqlType` 时，`column_type()` 返回 `None`；有 `UseSqlType` 时，它返回完整的 `UseSqlType` 标记，候选类型位于 `marker.data_types` 中，声明顺序保持不变。

## 声明如何进入收集器

### 模型级声明

| 声明 | 读取接口 | 说明 |
|------|----------|------|
| `__table_name__` | `table_name()` | 必须是字符串；未设置或类型错误会抛出 `ValueError`。 |
| `__schema_name__` | `schema_name()` | 原样返回；未设置时为 `None`。 |
| `__primary_key__` | `primary_key_columns()` | 字符串规范化为单元素 tuple，tuple 原样返回。 |
| `__primary_key__` | `is_composite_pk()` | 只有 tuple 才表示复合主键。 |
| `__table_indexes__` | `table_indexes()` | 返回列表的浅拷贝，索引对象本身不复制。 |
| `__table_constraints__` | `table_constraints()` | 返回列表的浅拷贝；复合主键会在没有匹配显式约束时补入表级主键。 |

`table_options()`、`table_storage_options()`、`table_partition()`、`table_inherits()` 和 `table_tablespace()` 默认返回 `None`。模型可以覆盖这些方法，mixin 会原样返回覆盖结果。

### 字段级声明

字段声明写在 `typing.Annotated` 中，收集器会同时读取 `Annotated` 元数据和 Pydantic `FieldInfo.metadata`。

| 标记 | 收集结果 | 顺序规则 |
|------|----------|----------|
| `UseSqlType(*types)` | `column_type()` 返回 `UseSqlType` 标记 | 标记内部候选类型按声明顺序保存并去重；多个标记只取第一个。 |
| `UseConstraint(...)` | `column_constraints()` 返回 `ColumnConstraint` 序列 | 所有标记按声明顺序展开。 |
| `UseIndex(...)` | `column_indexes()` 返回新建的 `IndexDefinition` 序列 | 每个标记生成一个定义，并把 Python 字段名换成物理列名。 |
| `UseColumnAttributes(...)` | `column_attributes()` 返回 `ColumnAttribute` 序列 | 标记按声明顺序展开；单个标记内部先去重。 |
| `UseComment(text)` | `column_comment()` 返回字符串 | 多个标记只取第一个。 |
| `UseGeneratedColumn(expr)` | `generated_column()` 返回表达式或工厂 | 多个标记只取第一个；工厂不在收集阶段调用。 |

`UseColumn` 负责 Python 字段名到数据库列名的映射，不属于 DDL 标记本身，但会影响 `column_name()`、主键判断和 `UseIndex` 生成的列名。

### 后端注解处理器

后端专属注解必须继承 `DDLAnnotation`，并由模型显式注册处理器。核心处理器只收集核心标记；它不会猜测某个后端注解应该如何转换。

```python
from rhosocial.activerecord.base import DDLAnnotation, DDLAnnotationHandler

class BackendSetting(DDLAnnotation):
    def __init__(self, option):
        self.option = option

class BackendSettingHandler(DDLAnnotationHandler):
    annotation_types = (BackendSetting,)

    @classmethod
    def apply(cls, new_class, field_name, annotation, metadata):
        metadata.add_column_options(annotation.option)

class Report(ActiveRecord):
    __table_name__ = "reports"
    _feature_handlers = [BackendSettingHandler]

    id: int
```

访问字段级 DDL 声明时，mixin 会检查所有 `DDLAnnotation` 是否已经被处理器消费。未处理的注解会抛出 `TypeError`，不会静默丢弃。

## 协议接口参考

下表中的“收集结果”描述的是 `DDLSourceMixin` 的默认实现；自定义 source 可以提供同样的结构化接口。

| 接口 | 返回值 | 如何收集及注意事项 |
|------|--------|------------------|
| `table_name()` | `str` | 读取并校验 `__table_name__`。 |
| `schema_name()` | `Optional[str]` | 读取 `__schema_name__`。 |
| `primary_key_columns()` | `Tuple[str, ...]` | 规范化 `__primary_key__`。 |
| `is_composite_pk()` | `bool` | 判断主键声明是否为 tuple。 |
| `ddl_field_names()` | `Tuple[str, ...]` | 按 `model_fields` 顺序返回普通字段，并排除 `__derived_fields__`；访问前会检查未处理注解。 |
| `is_derived_field(field)` | `bool` | 检查字段是否在 `__derived_fields__` 中。 |
| `field_python_type(field)` | `type` | 读取字段元数据；`Optional[T]` 解包为 `T`。未知字段抛出 `KeyError`。 |
| `field_is_optional(field)` | `bool` | `Optional[T]` 或默认值为 `None` 时为 `True`。 |
| `column_name(field)` | `str` | 使用 `ColumnNameMixin`；有 `UseColumn` 时返回物理列名，否则返回字段名。 |
| `column_type(field)` | `Optional[UseSqlType]` | 返回第一个 `UseSqlType` 标记；没有标记时为 `None`。不在此处选择候选类型。 |
| `column_constraints(field)` | `Sequence[ColumnConstraint]` | 先放显式约束，再应用主键和非空规则。 |
| `column_attributes(field)` | `Sequence[ColumnAttribute]` | 按标记顺序展开属性；不做方言筛选。 |
| `column_indexes(field)` | `Sequence[IndexDefinition]` | 为每个 `UseIndex` 建立定义，并使用物理列名。 |
| `column_comment(field)` | `Optional[str]` | 返回第一个 `UseComment` 的文本。 |
| `generated_column(field)` | `Optional[GeneratedColumnExpression or factory]` | 返回第一个 `UseGeneratedColumn` 的值；不调用工厂。 |
| `column_options(field)` | `None`、`ColumnOptions` 或其序列 | 返回处理器写入 `DDLFieldMetadata.column_options` 的值；一个选项返回对象，多个选项返回 list。 |
| `table_options()` | `None`、表达式或其序列 | 默认 `None`；覆盖方法的结果原样返回。 |
| `table_storage_options()` | `None`、表达式或其序列 | 默认 `None`；覆盖方法的结果原样返回。 |
| `table_partition()` | `None`、`PartitionClause` 或其序列 | 默认 `None`；覆盖方法的结果原样返回。 |
| `table_indexes()` | `Sequence[IndexDefinition]` | `__table_indexes__` 的浅拷贝。 |
| `create_table_statement_classes()` | `None`、类或类序列 | 默认 `None`；只提供声明候选，不实例化。 |
| `table_constraints()` | `Sequence[TableConstraint]` | 显式表约束的浅副本；复合主键按规则补充或复用显式定义。 |
| `table_inherits()` | `Optional[List[str]]` | 默认 `None`；覆盖方法的结果原样返回。 |
| `table_tablespace()` | `Optional[str]` | 默认 `None`；覆盖方法的结果原样返回。 |

### `column_constraints()` 的组合规则

收集器不是在模型类创建时预先写入一个完整约束列表，而是在读取时组合结果：

1. 按声明顺序复制所有 `UseConstraint` 的 `ColumnConstraint`。
2. 单列主键追加列级 `PRIMARY_KEY`。
3. 单列和复合主键成员都确保有 `NOT_NULL`。
4. 主键上的显式 `NULL` 会被移除。
5. 非主键、非 Optional 且没有显式 `NULL`/`NOT_NULL` 的字段追加 `NOT_NULL`。
6. 其他显式约束不会被删除；如果同时声明互相冲突的 `NULL` 和 `NOT_NULL`，两者都会保留，调用方应把它视为需要进一步校验的声明。

`UseConstraint(PRIMARY_KEY)` 在声明时会被拒绝，因为主键的唯一来源是 `__primary_key__`。复合主键的列约束在列级只产生 `NOT_NULL`；表级主键由 `table_constraints()` 提供。如果模型已经显式声明了列相同的复合主键，mixin 不会再次追加；若列不一致，则抛出 `ValueError`。

### 批量接口

以下方法不是独立的 DDL source 接口，而是对模型字段的便捷包装：

- `columns_name()`
- `columns_type()`
- `columns_constraints()`
- `columns_attributes()`
- `columns_indexes()`
- `columns_comment()`
- `columns_generated()`
- `columns_options()`

它们返回 `{字段名: 值}`。不传 `fields` 时使用 `model_fields` 的顺序；传入列表时按传入顺序生成字典。批量接口不会替你过滤后端候选或执行能力检查。

## `DDLSourceMixin` 的扩展 hook

下面三个方法存在于 `DDLSourceMixin`，但不属于当前 `DDLSource` 协议：

- `drop_table_statement_classes()`
- `create_index_statement_classes()`
- `drop_index_statement_classes()`

它们与 `create_table_statement_classes()` 一样只返回候选类，默认都是 `None`。保留它们作为 mixin 扩展点，可以让已有后端继续提供自己的语句类；需要把它们纳入正式协议时，应单独做一次接口变更，而不是让运行时协议检查自动猜测额外方法。

## 后端表达式如何接入

`UseSqlType` 可以携带通用类型和后端专属类型：

```python
from typing import Annotated
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.backend.expression.types import TextType
from rhosocial.activerecord.backend.impl.postgres.expression.types import PostgresUUIDType

identifier: Annotated[
    str,
    UseSqlType(PostgresUUIDType(), TextType()),
]
```

`DDLSourceMixin` 只保留这两个候选及其顺序。PostgreSQL 是否接受第一个候选、其他后端是否接受第二个候选，必须由后续方言消费者根据自身能力决定；source 不会在这里做替换或回退。

后端专属 `ColumnOptions` 不是核心 `Use*` 标记，不能仅靠在字段上写一个选项对象就自动收集。它需要像上面的 `BackendSettingHandler` 一样由处理器写入元数据。选项对象随后由后端表达式类使用：

```python
option = SomeColumnOptions(...)
column_class = option.column_definition_class()
column = column_class(dialect, "name", data_type)
option.apply_to(column)
```

这段代码属于后端表达式消费者，不属于 `DDLSourceMixin`。

## 后端差异速查

| 后端 | 常见声明/表达式 | 收集层的注意事项 |
|------|----------------|------------------|
| SQLite | 通用 `DataType`、`ColumnConstraint`、`IndexDefinition` | source 只收集通用声明；SQLite 的能力限制由 SQLite dialect 后续处理。 |
| MySQL | `MySQL*Type`、`MySQLColumnOptions`、`MySQLCreateTableOptions`、MySQL 分区表达式 | `UseIndex` 产生的定义可由支持内联索引的方言消费；source 本身不决定内联或独立创建。 |
| MariaDB | `MariaDB*Type`、`MariaDBColumnOptions`、`MariaDBCreateTableOptions`、MariaDB 分区表达式 | 与 MySQL 类似，具体语法和能力由 MariaDB dialect 决定。 |
| PostgreSQL | `Postgres*Type`、`PostgresColumnOptions`、`PostgresCreateTableOptions`、PostgreSQL 分区表达式 | schema、表空间和后端选项仍是声明值；能力门控不在 source 中执行。 |
| SQL Server | `SQLServer*Type`、`SQLServerColumnOptions`、`SQLServerCreateTableOptions`、SQL Server 分区表达式 | SQL Graph 或其他专属建表类只能通过扩展 hook/外部消费者选择。 |
| Oracle | `Oracle*Type`、`OracleColumnOptions`、Oracle 分区表达式 | 不支持的注释、分区或类型由 Oracle dialect 报错，不在收集阶段伪装支持。 |
| Snowflake | `Snowflake*Type`、`SnowflakeCreateTableOptions`、Snowflake 分区/克隆相关表达式 | VARIANT、OBJECT、ARRAY 等类型只是候选声明；source 不做 Snowflake 专属选择。 |
| ClickHouse | `ClickHouse*Type`、`ClickHouseColumnOptions`、`ClickHouseIndexDefinition`、ClickHouse 分区表达式 | UNIQUE、外键等不受支持的能力由 ClickHouse dialect fail-fast；source 仍可呈现用户声明。 |
| BigQuery | 当前主要使用通用 `DataType`、约束和 `CreateTableOptions` | 当前包没有与 `DDLSource` 自动绑定的 BigQuery 专属 `ColumnOptions`；通用声明仍可被收集。 |
| Firebird | `Firebird*Type`、`FirebirdColumnOptions`、`FirebirdCreateTableExpression`、Firebird 分区/计算列表达式 | 计算列、表空间和专属建表类由 Firebird 消费者处理。 |

后端测试应至少验证三件事：DDLSource 返回的对象和顺序、后端专属类型/选项没有被提前改写、收集结果可以交给该后端已有的表达式构造路径。收集测试不需要连接真实数据库；SQL 渲染应使用方言和最小表达式单独验证。

## 读取示例

```python
from typing import Annotated, Optional

from rhosocial.activerecord.base import (
    CollationAttribute,
    UseColumn,
    UseColumnAttributes,
    UseComment,
    UseConstraint,
    UseIndex,
    UseSqlType,
)
from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType
from rhosocial.activerecord.backend.expression.types import VarCharType
from rhosocial.activerecord.model import ActiveRecord


class Account(ActiveRecord):
    __table_name__ = "accounts"
    __schema_name__ = "app"
    __primary_key__ = "account_id"

    account_id: Annotated[int, UseColumn("id")]
    display_name: Annotated[
        str,
        UseSqlType(VarCharType(length=120)),
        UseIndex("idx_accounts_display_name"),
        UseColumnAttributes(CollationAttribute(name="und:ci")),
        UseComment("display name"),
    ]
    status: Annotated[
        str,
        UseConstraint(ColumnConstraintType.NOT_NULL),
    ] = "active"
    note: Optional[str] = None


print(Account.table_name())
print(Account.ddl_field_names())
print(Account.column_name("account_id"))
print(Account.column_type("display_name").data_types)
print(Account.column_indexes("display_name"))
print(Account.column_comment("display_name"))
print(Account.table_indexes())
```

这段代码只读取声明。`VarCharType`、`IndexDefinition` 和注释不会因为读取而自动变成 SQL；调用方可以在获得方言后自行构造并渲染表达式。

## 相关文档

- [DDL 表达式](ddl.md)：显式构造和渲染 DDL 表达式
- [DDLSource 使用示例](ddl_source_examples.md)：默认、注记、跨后端和不兼容表达式的实测示例
- [数据类型](../backend/expression/types.md)：`DataType` 的绑定与方言分发
- [字段定义](fields.md)：字段、列名映射和声明标记
