# DDLSource 使用示例：默认、注记、跨后端与不兼容表达式

本文是 [`ddl_source.md`](ddl_source.md) 的配套示例集。它展示如何阅读 `DDLSourceMixin` 收集到的声明，以及如何由外部消费者把声明绑定到方言并渲染表达式。

这些代码片段是文档示例，不是要加入 `src/` 或 `tests/` 的模块。示例中的 SQL 来自各后端方言的实际 `to_sql()` 探测；没有连接真实数据库。

## 先记住两个阶段

```text
模型声明
  → DDLSourceMixin 收集
  → 外部消费者读取并选择/绑定候选
  → ColumnDefinition / CreateTableExpression
  → dialect.to_sql()
```

`DDLSourceMixin` 只做第一阶段。下面这个辅助函数属于外部消费者，用来复制候选并绑定方言；它不是 `DDLSource` 的 API：

```python
from copy import copy

def bind(candidate, dialect):
    bound = copy(candidate)
    bound.dialect = dialect
    return bound


def render_column(dialect, marker, name="value", index=0):
    from rhosocial.activerecord.backend.expression.statements import ColumnDefinition

    return ColumnDefinition(
        dialect,
        name,
        bind(marker.data_types[index], dialect),
    ).to_sql()
```

复制是重要的：模型中的 `DataType` 是声明期对象，外部消费者不应把某个方言写回共享的模型声明。

## 场景一：默认情况，不定义额外 DDL 信息

### 模型

```python
from typing import Optional

from rhosocial.activerecord.model import ActiveRecord


class PlainAccount(ActiveRecord):
    __table_name__ = "plain_accounts"

    id: int
    name: str
    note: Optional[str] = None
```

### source 实际返回

```python
PlainAccount.table_name()
# 'plain_accounts'

PlainAccount.schema_name()
# None

PlainAccount.primary_key_columns()
# ('id',)

PlainAccount.ddl_field_names()
# ('id', 'name', 'note')

PlainAccount.column_type("id")
# None

PlainAccount.column_options("id")
# None

PlainAccount.table_options()
# None

PlainAccount.table_storage_options()
# None

PlainAccount.table_partition()
# None

PlainAccount.table_indexes()
# []

PlainAccount.table_constraints()
# []

PlainAccount.column_constraints("id")
# ColumnConstraint(PRIMARY_KEY), ColumnConstraint(NOT_NULL)

PlainAccount.column_constraints("name")
# ColumnConstraint(NOT_NULL)

PlainAccount.column_constraints("note")
# []
```

这里没有 `UseSqlType`，所以 `column_type()` 是 `None`。`id` 和必填的 `name` 仍然会得到自动组合的主键/非空约束；Optional 字段 `note` 不会自动得到 `NOT_NULL`。

如果消费者在没有类型的情况下直接构造列定义：

```python
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition

ColumnDefinition(dialect, "id", PlainAccount.column_type("id"))
# TypeError: data_type must be a DataType instance, got NoneType
```

因此“默认模型”只表示没有显式 DDL 注记，不表示 source 会凭空生成一个 `DataType`。

### 各后端的默认结果

| 后端 | `column_type("name")` | `table_options()` | 消费者必须注意 |
|------|------------------------|-------------------|----------------|
| SQLite | `None` | `None` | 只能由后续消费者决定 `INTEGER`、`TEXT` 等核心类型。 |
| MySQL | `None` | `None` | MySQL 不会替 source 自动补 `INT` 或 `VARCHAR`。 |
| MariaDB | `None` | `None` | 与 MySQL 相同。 |
| PostgreSQL | `None` | `None` | 需要显式提供 PostgreSQL 可渲染的类型。 |
| SQL Server | `None` | `None` | 需要显式提供 SQL Server 类型。 |
| Oracle | `None` | `None` | 需要显式提供 Oracle 类型或核心类型。 |
| Snowflake | `None` | `None` | `VARIANT` 等 Snowflake 类型不是默认推断结果。 |
| ClickHouse | `None` | `None` | 需要显式提供 ClickHouse 或核心类型。 |
| BigQuery | `None` | `None` | 当前没有 BigQuery 专属 DDL `DataType`，应使用核心类型。 |
| Firebird | `None` | `None` | 需要显式提供 Firebird 或核心类型。 |

## 场景二：部分字段带 DDL 注记

### 2.1 只使用通用核心表达式

```python
from typing import Annotated

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


class CoreDeclared(ActiveRecord):
    __table_name__ = "core_declared"

    id: Annotated[int, UseColumn("record_id")]
    name: Annotated[
        str,
        UseSqlType(VarCharType(length=64)),
        UseIndex("idx_core_declared_name", unique=True),
        UseColumnAttributes(CollationAttribute(name="und:ci")),
        UseComment("display name"),
    ]
    status: Annotated[
        str,
        UseConstraint(ColumnConstraintType.NOT_NULL),
    ] = "active"
```

收集结果：

```python
CoreDeclared.column_name("id")
# 'record_id'

CoreDeclared.column_type("name").data_types
# (VarCharType(length=64),)

CoreDeclared.column_indexes("name")[0].columns
# ['name']

CoreDeclared.column_comment("name")
# 'display name'

CoreDeclared.column_attributes("name")[0].name
# 'und:ci'

CoreDeclared.column_constraints("status")
# ColumnConstraint(NOT_NULL)
```

同一个核心表达式被各后端绑定后，实际 SQL 片段如下：

| 后端 | 消费者选择 `VarCharType(64)` 后得到的列片段 |
|------|------------------------------------------|
| SQLite | `"value" TEXT` |
| MySQL | `` `value` VARCHAR(64) `` |
| MariaDB | `` `value` VARCHAR(64) `` |
| PostgreSQL | `"value" VARCHAR(64)` |
| SQL Server | `[value] VARCHAR(64)` |
| Oracle | `"VALUE" VARCHAR2(64)` |
| Snowflake | `"value" VARCHAR(64)` |
| ClickHouse | `` `value` String `` |
| BigQuery | `` `value` STRING(64) `` |
| Firebird | `"VALUE" VARCHAR(64)` |

注意：SQLite 把 `VARCHAR(64)` 渲染为 `TEXT`，ClickHouse 把同一个核心字符串类型渲染为 `String`。这说明 source 保留的是声明，差异由方言决定。

### 2.2 使用后端专属表达式

下面每个片段都可以直接放进对应模型的字段注记中。示例只展示 source 收集和最小列渲染，不要求连接数据库。

#### SQLite

SQLite 的专属类型定义在核心包内：

```python
from rhosocial.activerecord.backend.impl.sqlite.expression.types import SQLiteTextType

value: Annotated[str, UseSqlType(SQLiteTextType())]
```

实测列片段：`"value" TEXT`。

#### MySQL

```python
from rhosocial.activerecord.backend.impl.mysql.expression.types import MySQLIntType

value: Annotated[int, UseSqlType(MySQLIntType(unsigned=True))]
```

实测列片段：`` `value` INT UNSIGNED ``。

MySQL 还可以用 `MySQLColumnOptions` 表达字符集、列格式、存储和不可见列：

```python
option = MySQLColumnOptions(
    character_set="utf8mb4",
    column_format=MySQLColumnFormat.FIXED,
    storage=MySQLColumnStorage.MEMORY,
    invisible=True,
)
column_class = option.column_definition_class()
column = column_class(dialect, "label", bind(VarCharType(length=32), dialect))
option.apply_to(column)
column.to_sql()
```

实测片段：

```sql
`label` VARCHAR(32) CHARACTER SET `utf8mb4` COLUMN_FORMAT FIXED STORAGE MEMORY INVISIBLE
```

#### MariaDB

```python
from rhosocial.activerecord.backend.impl.mariadb.expression.types import MariaDBIntType

value: Annotated[int, UseSqlType(MariaDBIntType(unsigned=True))]
```

实测列片段：`` `value` INT UNSIGNED ``。

`MariaDBColumnOptions` 的使用方式与 MySQL 同形，但必须使用 `MariaDBColumnDefinition`，不能把 MariaDB 选项应用到核心 `ColumnDefinition`。

#### PostgreSQL

```python
from rhosocial.activerecord.backend.impl.postgres.expression.types import PostgresUUIDType

identifier: Annotated[str, UseSqlType(PostgresUUIDType())]
```

实测列片段：`"identifier" UUID`。

列选项示例：

```python
option = PostgresColumnOptions(
    compression="lz4",
    storage=PostgresColumnStorage.EXTERNAL,
    statistics=500,
)
column = option.column_definition_class()(
    dialect,
    "label",
    bind(VarCharType(length=32), dialect),
)
option.apply_to(column)
column.to_sql()
```

实测片段：

```sql
"label" VARCHAR(32) COMPRESSION lz4 STORAGE EXTERNAL STATISTICS 500
```

#### SQL Server

```python
from rhosocial.activerecord.backend.impl.sqlserver.expression.types import SQLServerNVarCharType

value: Annotated[str, UseSqlType(SQLServerNVarCharType(length=64))]
```

实测列片段：`[value] NVARCHAR(64)`。

```python
option = SQLServerColumnOptions(sparse=True, rowguidcol=True)
column = option.column_definition_class()(
    dialect,
    "value",
    bind(VarCharType(length=64), dialect),
)
option.apply_to(column)
column.to_sql()
```

实测片段：

```sql
[value] VARCHAR(64) ROWGUIDCOL SPARSE
```

#### Oracle

```python
from rhosocial.activerecord.backend.impl.oracle.expression.types import OracleVarChar2Type

value: Annotated[str, UseSqlType(OracleVarChar2Type(length=64))]
```

实测列片段：`"VALUE" VARCHAR2(64)`。

```python
option = OracleColumnOptions(invisible=True)
column = option.column_definition_class()(
    dialect,
    "value",
    bind(VarCharType(length=64), dialect),
)
option.apply_to(column)
column.to_sql()
```

实测片段：`"VALUE" VARCHAR2(64) INVISIBLE`。

#### Snowflake

```python
from rhosocial.activerecord.backend.impl.snowflake.expression.types import SnowflakeVariantType

payload: Annotated[dict, UseSqlType(SnowflakeVariantType())]
```

实测列片段：`"payload" VARIANT`。

Snowflake 没有专属 `ColumnOptions`；表选项可以使用 `SnowflakeCreateTableOptions`：

```python
options = SnowflakeCreateTableOptions(None, or_replace=True, transient=True)
```

实测建表片段以如下形式开始：

```sql
CREATE OR REPLACE TRANSIENT TABLE "docs_example" (...)
```

#### ClickHouse

```python
from rhosocial.activerecord.backend.impl.clickhouse.expression.types import ClickHouseStringType

payload: Annotated[str, UseSqlType(ClickHouseStringType())]
```

实测列片段：`` `payload` String ``。

ClickHouse 还可以使用 `ClickHouseColumnOptions(codec=("ZSTD",))` 和 `StorageOptionsExpression`；实测建表片段为：

```sql
CREATE OR REPLACE TABLE `docs_example` (
  `payload` String NOT NULL CODEC(ZSTD)
) ENGINE = MergeTree ORDER BY id
```

注意 ClickHouse 不支持普通 UNIQUE 索引；这类能力错误会在方言/表达式消费者阶段抛出，而不是由 source 预先拒绝。

#### BigQuery

BigQuery 当前没有 `Bigquery*Type`、`BigQueryColumnOptions` 或 `BigQueryColumnDefinition` 这样的专属 DDL 表达式类。它使用核心表达式：

```python
from rhosocial.activerecord.backend.expression.types import IntegerType, JsonType

id_value: Annotated[int, UseSqlType(IntegerType())]
payload: Annotated[dict, UseSqlType(JsonType())]
```

实测核心类型片段：

```sql
`id_value` INT64
`payload` JSON
```

表注释使用核心 `CreateTableOptions` 与 `TableCommentClause`，BigQuery 会把它渲染成表级 `OPTIONS(description=...)`。

#### Firebird

```python
from rhosocial.activerecord.backend.impl.firebird.expression.types import FirebirdVarCharType

value: Annotated[str, UseSqlType(FirebirdVarCharType(length=64))]
```

实测列片段：`"VALUE" VARCHAR(64) CHARACTER SET UTF8`。

```python
option = FirebirdColumnOptions(
    character_set="UTF8",
    collation="UNICODE",
)
column = option.column_definition_class()(
    dialect,
    "value",
    bind(VarCharType(length=64), dialect),
)
option.apply_to(column)
column.to_sql()
```

实测片段：

```sql
"VALUE" VARCHAR(64) CHARACTER SET UTF8 COLLATE UNICODE
```

## 场景三：一个字段声明跨后端候选

跨后端声明的核心不是让 source 自动挑选，而是把候选顺序写清楚，再由消费者按方言能力选择：

```python
from typing import Annotated

from rhosocial.activerecord.backend.expression.types import TextType, VarCharType
from rhosocial.activerecord.backend.impl.clickhouse.expression.types import ClickHouseStringType
from rhosocial.activerecord.backend.impl.postgres.expression.types import PostgresUUIDType
from rhosocial.activerecord.backend.impl.snowflake.expression.types import SnowflakeVariantType
from rhosocial.activerecord.base import UseSqlType

payload_marker = UseSqlType(
    PostgresUUIDType(),
    SnowflakeVariantType(),
    ClickHouseStringType(),
    VarCharType(length=64),
    TextType(),
)
payload: Annotated[str, payload_marker]
```

此时无论模型最终配置哪个方言，source 都返回同样的候选元组：

```python
[type(item).__name__ for item in payload_marker.data_types]
# ['PostgresUUIDType', 'SnowflakeVariantType', 'ClickHouseStringType',
#  'VarCharType', 'TextType']
```

消费者可以查询能力面后显式选择：

```python
supported = dialect.supports_data_types()
selected = next(
    item for item in payload_marker.data_types if item.name in supported
)
selected = bind(selected, dialect)
```

以下是每个后端使用这类候选时的实测选择结果。表中的“首选支持候选”是消费者选出的结果，不是 `DDLSourceMixin` 自动选出的结果。

| 后端 | 候选顺序示例 | 首个受支持候选 | 渲染片段 |
|------|--------------|----------------|----------|
| SQLite | `PostgresUUIDType, SQLiteTextType, VarCharType` | `SQLiteTextType` | `"value" TEXT` |
| MySQL | `PostgresUUIDType, MySQLLongTextType, VarCharType` | `MySQLLongTextType` | `` `value` LONGTEXT `` |
| MariaDB | `PostgresUUIDType, MariaDBLongTextType, VarCharType` | `MariaDBLongTextType` | `` `value` LONGTEXT `` |
| PostgreSQL | `MySQLIntType, PostgresUUIDType, VarCharType` | `PostgresUUIDType` | `"value" UUID` |
| SQL Server | `OracleVarChar2Type, SQLServerNVarCharType, VarCharType` | `SQLServerNVarCharType` | `[value] NVARCHAR(64)` |
| Oracle | `SQLServerNVarCharType, OracleVarChar2Type, VarCharType` | `OracleVarChar2Type` | `"VALUE" VARCHAR2(64)` |
| Snowflake | `ClickHouseStringType, SnowflakeVariantType, VarCharType` | `SnowflakeVariantType` | `"value" VARIANT` |
| ClickHouse | `SnowflakeVariantType, ClickHouseStringType, VarCharType` | `ClickHouseStringType` | `` `value` String `` |
| BigQuery | `SnowflakeVariantType, VarCharType, JsonType` | `VarCharType` | `` `value` STRING(64) `` |
| Firebird | `OracleVarChar2Type, FirebirdVarCharType, VarCharType` | `FirebirdVarCharType` | `"VALUE" VARCHAR(64) CHARACTER SET UTF8` |

如果消费者直接取 `marker.data_type`（也就是第一个候选），而第一个候选属于其他后端，就会进入下面的边界情况；source 不会替消费者跳到第二个候选。

## 场景四：只有不适配的后端表达式

这一场景故意不提供通用核心候选：

```python
class ForeignOnly(ActiveRecord):
    __table_name__ = "foreign_only"

    id: int
    value: Annotated[str, UseSqlType(ForeignType())]
```

类定义和 `column_type("value")` 都可以成功；只有消费者把候选绑定到当前方言并渲染时才失败。下面的 `ForeignType` 和错误摘要是各后端实测结果：

| 当前方言 | 声明的唯一表达式 | 收集阶段 | 渲染阶段 |
|----------|------------------|----------|----------|
| SQLite | `PostgresUUIDType()` | 成功返回 `UseSqlType` | `TypeError`：没有 `format_data_type_postgres_uuid` |
| MySQL | `PostgresUUIDType()` | 成功返回 `UseSqlType` | `TypeError`：MySQL 不支持 `postgres_uuid` |
| MariaDB | `PostgresUUIDType()` | 成功返回 `UseSqlType` | `TypeError`：MariaDB 不支持 `postgres_uuid` |
| PostgreSQL | `MySQLIntType(unsigned=True)` | 成功返回 `UseSqlType` | `TypeError`：PostgreSQL 不支持 `mysql_int` |
| SQL Server | `OracleVarChar2Type(length=64)` | 成功返回 `UseSqlType` | `TypeError`：SQL Server 不支持 `oracle_varchar2` |
| Oracle | `SQLServerNVarCharType(length=64)` | 成功返回 `UseSqlType` | `TypeError`：Oracle 不支持 `sqlserver_nvarchar` |
| Snowflake | `ClickHouseStringType()` | 成功返回 `UseSqlType` | `TypeError`：Snowflake 不支持 `clickhouse_string` |
| ClickHouse | `SnowflakeVariantType()` | 成功返回 `UseSqlType` | `TypeError`：ClickHouse 不支持 `snowflake_variant` |
| BigQuery | `SnowflakeVariantType()` | 成功返回 `UseSqlType` | `TypeError`：BigQuery 不支持 `snowflake_variant` |
| Firebird | `OracleVarChar2Type(length=64)` | 成功返回 `UseSqlType` | `TypeError`：Firebird 不支持 `oracle_varchar2` |

典型错误形式：

```text
SQLServerDialect does not support the generic type 'oracle_varchar2'
(no format_data_type_oracle_varchar2). Use a type this backend supports.
```

这个错误说明三件事：

1. `DDLSourceMixin` 不会在模型导入时验证表达式是否属于当前方言。
2. `supports_data_types()` 和 `suggested_data_types()` 是能力查询，不是自动替换器。
3. 如果模型只有不兼容的后端表达式，调用方必须明确处理 `TypeError`；不能期待 source 隐式退回 `VARCHAR`、`TEXT` 或其他通用类型。

## 后端专属选项的额外注意事项

`ColumnOptions` 不是 `DDLAnnotation`。如果希望通过字段注记让 `column_options()` 返回后端选项，需要用自定义 `DDLAnnotation` 包装它并注册 handler；如果只是手工构造表达式，可以直接实例化后端选项。

| 后端 | 选项/表表达式 | 实测行为 |
|------|---------------|----------|
| SQLite | 核心 `CreateTableOptions` | 使用 SQLite 方言渲染核心选项。 |
| MySQL | `MySQLCreateTableOptions(engine="InnoDB", charset="utf8mb4")` | 产生 `ENGINE`、`DEFAULT CHARSET` 等 MySQL 表选项。 |
| MariaDB | `MariaDBCreateTableOptions` | 产生与 MariaDB 方言匹配的表选项。 |
| PostgreSQL | `PostgresCreateTableOptions(unlogged=True)` | 产生 `CREATE UNLOGGED TABLE`；版本能力由 PostgreSQL 方言检查。 |
| SQL Server | `SQLServerCreateTableOptions(memory_optimized=True)`、`SQLServerCreateTableExpression` | 产生 `WITH (MEMORY_OPTIMIZED = ON)`；需要 SQL Server 2014+。 |
| Oracle | 核心 `CreateTableOptions`、`tablespace="TS_DATA"` | 表空间由 Oracle 建表 formatter 处理；通用 `StorageOptionsExpression` 在 Oracle 建表路径会 fail-fast。 |
| Snowflake | `SnowflakeCreateTableOptions(transient=True)` | 产生 `CREATE OR REPLACE TRANSIENT TABLE`。 |
| ClickHouse | `ClickHouseColumnOptions`、`StorageOptionsExpression` | 产生 `CODEC(...)`、`ENGINE = ...` 等 ClickHouse 子句。 |
| BigQuery | 核心 `CreateTableOptions` + `TableCommentClause` | 产生表级 `OPTIONS(description=...)`；当前没有 BigQuery 专属 `ColumnOptions`。 |
| Firebird | `FirebirdCreateTableExpression`、`FirebirdColumnOptions` | 产生 `CREATE GLOBAL TEMPORARY TABLE`、`CHARACTER SET` 等 Firebird 子句。 |

把某个后端的 `ColumnOptions` 应用到另一个后端的核心 `ColumnDefinition`，通常会得到 `TypeError`；但如果应用到了另一个后端自己的列定义类，某些不认识的后端字段可能被 formatter 静默忽略。因此示例中应始终让选项类和列定义类来自同一个后端，并让方言也来自同一个后端。

## 结论

- 没有 DDL 注记时，source 仍能返回表名、主键、字段集合和自动组合的约束，但不会产生 `DataType`。
- 通用核心表达式和后端表达式都只是 `UseSqlType` 的候选；source 保留声明顺序，不做选择。
- 跨后端候选必须由消费者结合 `supports_data_types()` 明确选择。
- 只有不兼容后端表达式时，模型和 source 读取可以成功，错误会延迟到方言绑定/表达式渲染阶段，并以 `TypeError` 暴露。
- 后端选项属于额外的表达式/方言能力，不是 source 自动推断的结果。

## 相关文档

- [DDLSource 接口参考](ddl_source.md)
- [DDL 表达式](ddl.md)
- [数据类型与方言分发](../backend/expression/types.md)
