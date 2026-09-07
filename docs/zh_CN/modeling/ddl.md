# DDL 语句

`rhosocial-activerecord` 提供了类型安全的、基于表达式的 DDL（Data Definition Language，数据定义语言）API。你可以使用 Python 对象构建表、索引、视图和模式，而无需编写原生 SQL 字符串。

## 为什么要使用 DDL 表达式？

- **类型安全**：所有列名、数据类型和约束都在运行时经过验证。
- **后端可移植性**：相同的代码可在 SQLite、MySQL、PostgreSQL 上运行（由 dialect 处理差异）。
- **SQL 检查**：在任何表达式上调用 `.to_sql()` 即可在执行前检查生成的 SQL。
- **避免字符串拼接**：消除 SQL 注入风险和语法错误。

## 从模型声明推导 DDL（Spec）

除了手工构造 DDL 表达式，你还可以**在模型上声明 DDL 特征（Spec）**，由框架调用
`Model.generate_create_table(dialect)` 自动推导出 `CreateTableExpression`。

### 方言认领机制

Spec 是纯声明对象——定义时**不需要**任何方言/后端。生成 DDL 时，当前方言对每个
Spec 调用 `build_spec(spec)`：接受则返回构造好的表达式实例；不接受返回 `None`
（该 Spec 被静默忽略）。是否支持某个特征由后端自行决定。

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.expression.core import Column

class Order(ActiveRecord):
    __table_name__ = "orders"

    # 表级声明：复合约束 / 跨列 CHECK / 分区
    __table_constraints__ = [
        UniqueSpec(columns=["account_id", "period"], name="uq_acc_period"),
        CheckSpec(
            condition=lambda d: Column(d, "debit_total") == Column(d, "credit_total"),
            name="ck_balance",
        ),
    ]

    # 后端自定分区：每个后端认领自己的，SQLite 上自动忽略（建普通表）
    __table_partition__ = [
        PostgresRangePartition(column="created_at"),
        MySQLRangePartition(column="created_at", partitions=[...]),
    ]

    account_id: int
    period: str
    debit_total: float
    credit_total: float

expr = Order.generate_create_table(dialect)  # CreateTableExpression
sql, params = expr.to_sql()
```

### 通用 Spec 一览

| Spec | 说明 | 默认翻译 |
|------|------|----------|
| `CheckSpec(condition, name=?)` | CHECK 约束；`condition` 可为就绪谓词或惰性工厂 `(dialect) -> SQLPredicate` | `TableConstraint(CHECK)` |
| `UniqueSpec(columns, name=?)` | UNIQUE 约束 | `TableConstraint(UNIQUE)` |
| `NotNullSpec(column, name=?)` | NOT NULL | `ColumnConstraint(NOT_NULL)` |
| `PrimaryKeySpec(columns, name=?)` | 主键（单列→列级，复合→表级） | PK 约束 |
| `DefaultSpec(column, value)` | 字面量默认值（惰性值 `(dialect) -> Any` 可用）；表达式默认用后端特定 Spec | `ColumnConstraint(DEFAULT)` |
| `ForeignKeySpec(local_columns, ref_table, ref_columns, ...)` | 外键（含 on_delete / on_update） | `ForeignKeyConstraint` |
| `IndexSpec(columns, name=?, unique=?, partial_condition=?)` | 索引（部分索引受 `supports_partial_index` 门控） | `IndexDefinition` |
| `PartialIndexSpec(columns, condition, ...)` | 部分索引便捷形态 | `IndexDefinition` |
| `JsonColumnSpec(column)` | JSON 列（便携 `JsonType`，各后端原生或 TEXT 渲染） | 列类型补丁 |
| `GeneratedColumnSpec(column, expression, stored=?)` | 生成列（受 `supports_generated_columns` 门控） | `ColumnDefinition.generated_*` |

### 两级入口

- **字段级注解**（字段自身内容）：`UseSqlType` / `UseConstraint` / `UseIndex`，
  其 `check_condition` / `partial_condition` 同样支持惰性谓词工厂；
- **表级声明列表**（复合/跨列/表级内容）：`__table_constraints__` /
  `__table_indexes__` / `__table_partition__`，条目可为 Spec 或预构建表达式对象
  （`TableConstraint` / `IndexDefinition`），两者混用均可。

### 最简化定义是默认路径

不写任何 Spec 也能建表：字段名即列名、Python 类型经
`dialect.suggest_column_type()` 映射为列类型、必填字段自动 `NOT NULL`、主键按
`primary_key_columns()` 规则。Spec 只在需要偏离默认时书写。

### 后端特定 Spec

分区、序列默认、原生类型列等由各后端包定义（如 `MySQLRangePartition`、
`PostgresSequenceDefault`、`OracleIntervalPartition.monthly(...)`、
`SQLServerRangePartition`），仅归属后端认领。详见各后端文档。

## 核心组件

### ColumnDefinition

定义列及其数据类型和可选约束。

```python
from rhosocial.activerecord.backend.expression import ColumnDefinition
from rhosocial.activerecord.backend.expression.statements import ColumnConstraint, ColumnConstraintType

# 基本列
ColumnDefinition("name", "VARCHAR(100)")

# 带约束的列
ColumnDefinition(
    "email",
    "VARCHAR(255)",
    constraints=[
        ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ColumnConstraint(ColumnConstraintType.UNIQUE)
    ]
)

# 带默认值的列
ColumnDefinition(
    "status",
    "VARCHAR(20)",
    default="active"
)
```

### ColumnConstraint

| 类型 | 说明 |
|------|------|
| `NOT_NULL` | 列不能为 NULL |
| `NULL` | 列允许 NULL（默认） |
| `PRIMARY_KEY` | 主键列 |
| `UNIQUE` | 列值必须唯一 |
| `AUTO_INCREMENT` | 自增（取决于数据库） |

### TableConstraint

定义表级约束，如主键、唯一约束和外键。

```python
from rhosocial.activerecord.backend.expression.statements import (
    TableConstraint,
    TableConstraintType,
    ForeignKeyConstraint,
    ReferentialAction
)

# 复合主键
TableConstraint(
    TableConstraintType.PRIMARY_KEY,
    columns=["user_id", "role_id"]
)

# 带引用操作的外键
ForeignKeyConstraint(
    columns=["author_id"],
    reference_table="authors",
    reference_columns=["id"],
    on_delete=ReferentialAction.CASCADE,
    on_update=ReferentialAction.RESTRICT
)
```

## 基本操作

### 创建表

```python
from rhosocial.activerecord.backend.expression import CreateTableExpression

columns = [
    ColumnDefinition(
        "id",
        "INTEGER",
        constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
    ),
    ColumnDefinition(
        "username",
        "VARCHAR(50)",
        constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
    ),
    ColumnDefinition(
        "email",
        "VARCHAR(100)",
        constraints=[
            ColumnConstraint(ColumnConstraintType.NOT_NULL),
            ColumnConstraint(ColumnConstraintType.UNIQUE)
        ]
    ),
    ColumnDefinition("created_at", "TIMESTAMP")
]

create = CreateTableExpression(
    dialect=dialect,
    table_name="users",
    columns=columns
)

sql, params = create.to_sql()
# sql: 'CREATE TABLE "users" ("id" INTEGER PRIMARY KEY, "username" VARCHAR(50) NOT NULL,
#      "email" VARCHAR(100) NOT NULL UNIQUE, "created_at" TIMESTAMP)'
# params: ()
```

### 创建表（带 IF NOT EXISTS）

```python
create = CreateTableExpression(
    dialect=dialect,
    table_name="users",
    columns=columns,
    if_not_exists=True
)
sql, params = create.to_sql()
# sql: 'CREATE TABLE IF NOT EXISTS "users" (...)'
```

### 创建临时表

```python
create = CreateTableExpression(
    dialect=dialect,
    table_name="temp_sessions",
    columns=columns,
    temporary=True
)
sql, params = create.to_sql()
# sql: 'CREATE TEMPORARY TABLE "temp_sessions" (...)'
```

### 删除表

```python
from rhosocial.activerecord.backend.expression import DropTableExpression

drop = DropTableExpression(
    dialect,
    table_name="old_users",
    if_exists=True,
    cascade=True
)
sql, params = drop.to_sql()
# sql: 'DROP TABLE IF EXISTS "old_users" CASCADE'
```

### 修改表

```python
from rhosocial.activerecord.backend.expression import (
    AlterTableExpression,
    AddColumn,
    DropColumn,
    AlterColumn
)

# 添加新列
alter = AlterTableExpression(
    dialect,
    table_name="users",
    actions=[
        AddColumn(
            ColumnDefinition(
                "phone",
                "VARCHAR(20)"
            )
        )
    ]
)
sql, params = alter.to_sql()
# sql: 'ALTER TABLE "users" ADD COLUMN "phone" VARCHAR(20)'

# 删除列
alter = AlterTableExpression(
    dialect,
    table_name="users",
    actions=[
        DropColumn("old_field")
    ]
)
sql, params = alter.to_sql()
# sql: 'ALTER TABLE "users" DROP COLUMN "old_field"'
```

## 索引操作

### 创建索引

```python
from rhosocial.activerecord.backend.expression.statement import CreateIndexExpression

# 基本索引
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"]
)
sql, params = create_idx.to_sql()
# sql: 'CREATE INDEX "idx_users_email" ON "users" ("email")'

# 唯一索引
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_users_username",
    table_name="users",
    columns=["username"],
    unique=True
)

# 局部索引（带 WHERE 子句）
from rhosocial.activerecord.backend.expression import Column, Literal

create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_active_users",
    table_name="users",
    columns=["email"],
    where=Column(dialect, "status") == Literal(dialect, "active")
)
sql, params = create_idx.to_sql()
# sql: 'CREATE INDEX "idx_active_users" ON "users" ("email") WHERE "status" = ?'
```

### 删除索引

```python
from rhosocial.activerecord.backend.expression.statement import DropIndexExpression

drop_idx = DropIndexExpression(
    dialect,
    index_name="idx_users_email",
    if_exists=True
)
sql, params = drop_idx.to_sql()
# sql: 'DROP INDEX IF EXISTS "idx_users_email"'
```

## 模式操作

### 创建模式

```python
from rhosocial.activerecord.backend.expression.statement import CreateSchemaExpression

create_schema = CreateSchemaExpression(
    dialect,
    schema_name="app_schema",
    if_not_exists=True
)
sql, params = create_schema.to_sql()
# sql: 'CREATE SCHEMA IF NOT EXISTS "app_schema"'
```

### 删除模式

```python
from rhosocial.activerecord.backend.expression.statement import DropSchemaExpression

drop_schema = DropSchemaExpression(
    dialect,
    schema_name="old_schema",
    cascade=True
)
sql, params = drop_schema.to_sql()
# sql: 'DROP SCHEMA "old_schema" CASCADE'
```

## 执行 DDL 语句

DDL 表达式可以直接在后端上执行：

```python
from rhosocial.activerecord.model import ActiveRecord

# 创建表
create = CreateTableExpression(dialect, "users", columns)
User.__backend__.execute(create)

# 或者先构建 SQL 并检查
sql, params = create.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")
```

> **注意**：`rhosocial-activerecord` 中的 DDL 语句不需要 `ExecutionOptions(stmt_type=StatementType.DDL)` — 表达式对象自带语句类型信息。

## 内省用于架构验证

在创建、修改或删除表之后，你可以使用后端的**内省 API** 来验证架构变化：

```python
from rhosocial.activerecord.backend.introspection import TableType

# 列出所有表
tables = backend.introspector.list_tables()
for t in tables:
    print(f"Table: {t.name}, Type: {t.table_type}")

# 获取详细的表信息（列、索引、外键）
table_info = backend.introspector.get_table_info("users")
if table_info:
    for col in table_info.columns:
        print(f"Column: {col.name}, Type: {col.data_type}, PK: {col.is_primary_key}")
```

### 后端差异

> ⚠️ **重要提示**：本文档以 SQLite 作为示例后端。不同的数据库后端存在显著差异：

| 特性 | SQLite | MySQL | PostgreSQL |
|------|--------|-------|------------|
| **内省 API** | `list_tables()`、`get_table_info()`、`pragma.*` | 不同的方法名 | 不同的方法名 |
| **DDL 支持** | 有限的 ALTER TABLE（仅支持 ADD/DROP column） | 完整的 ALTER TABLE | 完整的 ALTER TABLE |
| **索引类型** | 不支持 USING 子句 | BTREE、HASH 等 | BTREE、HASH、GIN 等 |
| **局部索引** | 支持（WHERE 子句） | 不支持 | 支持 |
| **生成列** | 3.31.0+ | 5.7.31+ | 支持 |

请始终参考你所用后端的文档以获取准确的 API 用法。

## 示例代码

本章的完整示例代码可以在以下位置找到：
[docs/examples/chapter_03_modeling/ddl_basic.py](../../../examples/chapter_03_modeling/ddl_basic.py)

更多示例：
- [docs/examples/chapter_03_modeling/ddl_relationships.py](../../../examples/chapter_03_modeling/ddl_relationships.py) — 创建带外键关系的表
- [docs/examples/chapter_03_modeling/ddl_indexes.py](../../../examples/chapter_03_modeling/ddl_indexes.py) — 索引创建模式