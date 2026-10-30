# DDL 语句

`rhosocial-activerecord` 提供了类型安全的、基于表达式的 DDL（Data Definition Language，数据定义语言）API。你可以使用 Python 对象构建表、索引、视图和模式，而无需编写原生 SQL 字符串。

> 本章介绍显式 DDL 表达式的构造和渲染。若要从 ActiveRecord 模型声明中读取 DDL 定义，请参阅 [DDLSource 声明收集](ddl_source.md)。当前 `DDLSourceMixin` 只收集并呈现声明，不自动生成或执行 DDL。

## 为什么要使用 DDL 表达式？

- **类型安全**：所有列名、数据类型和约束都在运行时经过验证。
- **后端可移植性**：相同的代码可在 SQLite、MySQL、PostgreSQL 上运行（由 dialect 处理差异）。
- **SQL 检查**：在任何表达式上调用 `.to_sql()` 即可在执行前检查生成的 SQL。
- **避免字符串拼接**：消除 SQL 注入风险和语法错误。

## 核心组件

### ColumnDefinition

定义列及其数据类型和可选约束。数据类型是 `DataType` 对象而非字符串——类型的拼写由 dialect 决定。

```python
from rhosocial.activerecord.backend.expression import ColumnDefinition
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnDefaultConstraint,
    ColumnNotNullConstraint,
    ColumnUniqueConstraint,
)

# 基本列
ColumnDefinition(dialect, "name", VarCharType(dialect, length=100))
# sql: '"name" TEXT'   （SQLite 把 VARCHAR 适配为 TEXT）

# 带约束的列
ColumnDefinition(
    dialect,
    "email",
    VarCharType(dialect, length=255),
    constraints=[
        ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
        ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect)),
    ]
)
# sql: '"email" TEXT NOT NULL UNIQUE'

# DEFAULT 也是约束分支，不是关键字参数
ColumnDefinition(
    dialect,
    "status",
    VarCharType(dialect, length=20),
    constraints=[
        ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, "active"))
    ]
)
# sql: '"status" TEXT DEFAULT \'active\''
```

### ColumnConstraint

列约束分两层，与语法结构对应：`ColumnConstraint` 是**子句**（`CONSTRAINT <name>` 前缀与尾部性状），每个备选形式是它引用的**分支**。分支不能单独写出；分支种类无法承载的性状在构造时就被拒绝，而不是在渲染时被丢弃。

| 分支 | 渲染结果 |
|------|---------|
| `ColumnPrimaryKeyConstraint` | `PRIMARY KEY`（SQLite 在 `is_auto_increment=True` 时追加 `AUTOINCREMENT`） |
| `ColumnUniqueConstraint` | `UNIQUE` |
| `ColumnNotNullConstraint` | `NOT NULL` |
| `ColumnNullableConstraint` | `NULL` |
| `ColumnDefaultConstraint` | `DEFAULT <value>` |
| `ColumnCheckConstraint` | `CHECK (<condition>)` |
| `ColumnForeignKeyConstraint` | `REFERENCES <table> (<columns>)` |
| `ColumnGeneratedConstraint` | `GENERATED ALWAYS AS (<expression>) [STORED\|VIRTUAL]` |

子句还承载标准允许出现在约束上的性状：

```python
from rhosocial.activerecord.backend.expression import (
    ColumnCheckConstraint,
    ColumnConstraint,
    ColumnUniqueConstraint,
    StringColumn,
)

# CONSTRAINT <name> <branch> ...
ColumnConstraint(
    dialect,
    branch=ColumnUniqueConstraint(dialect),
    name="uq_users_email"
)
# sql: ' CONSTRAINT "uq_users_email" UNIQUE'   （前导空格：该子句是追加到列定义上的）

# ... DEFERRABLE INITIALLY DEFERRED
ColumnConstraint(
    dialect,
    branch=ColumnUniqueConstraint(dialect),
    deferrable=True,
    initially_deferred=True
)
# sql: ' UNIQUE DEFERRABLE INITIALLY DEFERRED'

# CHECK (<condition>)
ColumnConstraint(
    dialect,
    branch=ColumnCheckConstraint(dialect, StringColumn(dialect, "status") != "deleted")
)
# sql: ' CHECK ("status" <> ?)'   params: ('deleted',)
```

每个性状都是一对互斥标志，并且经过两道关卡：

| 性状 | 标志 | 由谁授权 | 可承载的分支 |
|------|------|---------|-------------|
| 命名 | `name=` | `supports_constraint_naming` | 全部分支 |
| 延迟 | `deferrable` / `not_deferrable` | `supports_deferrable_constraint` | PRIMARY KEY、UNIQUE、FOREIGN KEY |
| 时机 | `initially_deferred` / `initially_immediate` | `supports_deferrable_constraint` | PRIMARY KEY、UNIQUE、FOREIGN KEY |
| 强制 | `enforced` / `not_enforced` | `supports_constraint_enforcement` | PRIMARY KEY、UNIQUE、FOREIGN KEY、CHECK |

同一对标志同时置位，或把性状用在种类上无此含义的分支，都是构造期错误：

```python
# ValueError: deferrable and not_deferrable are mutually exclusive options
try:
    ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect),
                     deferrable=True, not_deferrable=True)
except ValueError as exc:
    print(exc)

# ValueError: DEFERRABLE / INITIALLY cannot ride a ColumnNotNullConstraint;
#             the SQL:2016 kinds are PRIMARY KEY, UNIQUE and FOREIGN KEY
try:
    ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect), deferrable=True)
except ValueError as exc:
    print(exc)
```

dialect 无法拼写某个已被接受的性状时，会在渲染阶段拒绝，因此语句不会悄悄丢掉调用者要求的约束：

```python
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

try:
    ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect), enforced=True).to_sql()
except UnsupportedFeatureError as exc:
    print(exc)  # 'SQLite' dialect does not support ENFORCED/NOT ENFORCED constraint.
```

### TableConstraint

定义表级约束，如主键、唯一约束和外键。它与 `ColumnConstraint` 一样采用子句/分支的划分。

```python
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    ReferentialAction,
    TableConstraint,
    TableForeignKeyConstraint,
    TablePrimaryKeyConstraint,
)

# 复合主键
TableConstraint(
    dialect,
    branch=TablePrimaryKeyConstraint(dialect, ["user_id", "role_id"]),
)
# sql: 'PRIMARY KEY ("user_id", "role_id")'

# 带引用操作的外键
TableConstraint(
    dialect,
    branch=TableForeignKeyConstraint(
        dialect,
        ["author_id"],
        (Table(dialect, "authors"), ["id"]),
        on_delete=ReferentialAction.CASCADE,
        on_update=ReferentialAction.RESTRICT,
    ),
    name="fk_posts_author",
)
# sql: 'CONSTRAINT "fk_posts_author" FOREIGN KEY ("author_id")
#       REFERENCES "authors"("id") ON DELETE CASCADE ON UPDATE RESTRICT'
```


## 基本操作

### 创建表

表由 `Table` 对象命名，语句把它作为位置参数接收。

```python
from rhosocial.activerecord.backend.expression import (
    ColumnConstraint,
    ColumnDefinition,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnUniqueConstraint,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import CreateTableStatement
from rhosocial.activerecord.backend.expression.types import IntegerType, TimestampType, VarCharType

columns = [
    ColumnDefinition(
        dialect,
        "id",
        IntegerType(dialect),
        constraints=[ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect))]
    ),
    ColumnDefinition(
        dialect,
        "username",
        VarCharType(dialect, length=50),
        constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))]
    ),
    ColumnDefinition(
        dialect,
        "email",
        VarCharType(dialect, length=100),
        constraints=[
            ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect))
        ]
    ),
    ColumnDefinition(dialect, "created_at", TimestampType(dialect))
]

create = CreateTableStatement(
    dialect,
    Table(dialect, "users"),
    columns=columns
)

sql, params = create.to_sql()
# sql: 'CREATE TABLE "users" ("id" INTEGER PRIMARY KEY, "username" TEXT NOT NULL,
#      "email" TEXT NOT NULL UNIQUE, "created_at" NUMERIC)'
# params: ()
```

### 创建表（带 IF NOT EXISTS）

```python
create = CreateTableStatement(
    dialect,
    Table(dialect, "users"),
    columns=columns,
    if_not_exists=True
)
sql, params = create.to_sql()
# sql: 'CREATE TABLE IF NOT EXISTS "users" (...)'
```

### 创建临时表

```python
create = CreateTableStatement(
    dialect,
    Table(dialect, "temp_sessions"),
    columns=columns,
    temporary=True
)
sql, params = create.to_sql()
# sql: 'CREATE TEMPORARY TABLE "temp_sessions" (...)'
```

### 删除表

```python
from rhosocial.activerecord.backend.expression import DropTableStatement

drop = DropTableStatement(
    dialect,
    Table(dialect, "old_users"),
    if_exists=True
)
sql, params = drop.to_sql()
# sql: 'DROP TABLE IF EXISTS "old_users"'
```

`cascade=True` 由 `supports_drop_table_cascade` 授权，因此 SQLite（`DROP TABLE` 既没有 `CASCADE` 也没有 `RESTRICT`）会直接拒绝，而不是悄悄丢掉子句：

```python
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

try:
    DropTableStatement(dialect, Table(dialect, "old_users"), cascade=True).to_sql()
except UnsupportedFeatureError as exc:
    print(exc)  # 'SQLite' dialect does not support DROP TABLE ... CASCADE.
```

### 修改表

每个动作都是独立节点，由语句持有列表。

```python
from rhosocial.activerecord.backend.expression import (
    AlterTableStatement,
    AddColumnAction,
    DropColumnAction
)

# 添加新列
alter = AlterTableStatement(
    dialect,
    Table(dialect, "users"),
    actions=[
        AddColumnAction(
            dialect,
            ColumnDefinition(dialect, "phone", VarCharType(dialect, length=20))
        )
    ]
)
sql, params = alter.to_sql()
# sql: 'ALTER TABLE "users" ADD COLUMN "phone" TEXT'

# 删除列
alter = AlterTableStatement(
    dialect,
    Table(dialect, "users"),
    actions=[
        DropColumnAction(dialect, "old_field")
    ]
)
sql, params = alter.to_sql()
# sql: 'ALTER TABLE "users" DROP COLUMN "old_field"'
```

## 索引操作

### 创建索引

索引与表都是具名对象，列名是普通列表。

```python
from rhosocial.activerecord.backend.expression import StringColumn
from rhosocial.activerecord.backend.expression.objects import Index, Table
from rhosocial.activerecord.backend.expression.statements import CreateIndexStatement

# 基本索引
create_idx = CreateIndexStatement(
    dialect,
    Index(dialect, "idx_users_email"),
    Table(dialect, "users"),
    columns=["email"]
)
sql, params = create_idx.to_sql()
# sql: 'CREATE INDEX "idx_users_email" ON "users" ("email")'

# 唯一索引
create_idx = CreateIndexStatement(
    dialect,
    Index(dialect, "idx_users_username"),
    Table(dialect, "users"),
    columns=["username"],
    unique=True
)

# 局部索引（带 WHERE 子句）—— 谓词由可比较的带类型列构建
create_idx = CreateIndexStatement(
    dialect,
    Index(dialect, "idx_active_users"),
    Table(dialect, "users"),
    columns=["email"],
    unique=True,
    where=StringColumn(dialect, "status") == "active"
)
sql, params = create_idx.to_sql()
# sql: 'CREATE UNIQUE INDEX "idx_active_users" ON "users" ("email") WHERE "status" = ?'
# params: ('active',)
```

> 谓词来自能够比较的列类，而不是裸 `Column` 上的 `==`：`Column` 只提供别名、空值判断和类型转换，因此 `Column(...) == ...` 只是一次 Python 同一性比较。任何需要比较的场合都请使用 `StringColumn`、`NumericColumn` 及其兄弟类。

### 删除索引

```python
from rhosocial.activerecord.backend.expression.statements import DropIndexStatement

drop_idx = DropIndexStatement(
    dialect,
    Index(dialect, "idx_users_email"),
    if_exists=True
)
sql, params = drop_idx.to_sql()
# sql: 'DROP INDEX IF EXISTS "idx_users_email"'
```


## 模式操作

### 创建模式

模式是 `Schema` 对象。SQLite 没有模式，因此它的 dialect 会拒绝该语句，而不是生成引擎会拒绝的 SQL：

```python
from rhosocial.activerecord.backend.expression.objects import Schema
from rhosocial.activerecord.backend.expression.statements import CreateSchemaStatement

create_schema = CreateSchemaStatement(
    dialect,
    Schema(dialect, "app_schema"),
    if_not_exists=True
)
# 在支持模式的后端上：
# sql: 'CREATE SCHEMA IF NOT EXISTS "app_schema"'
# 在 SQLite 上：
# UnsupportedFeatureError: 'SQLite' dialect does not support CREATE SCHEMA.
```

### 删除模式

```python
from rhosocial.activerecord.backend.expression.statements import DropSchemaStatement

drop_schema = DropSchemaStatement(
    dialect,
    Schema(dialect, "old_schema"),
    cascade=True
)
# 在支持模式的后端上：
# sql: 'DROP SCHEMA "old_schema" CASCADE'
```

## 执行 DDL 语句

语句渲染为 `(sql, params)`；后端执行的是 SQL 文本，所以两步是分开的：

```python
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import CreateTableStatement

# 创建表
create = CreateTableStatement(
    dialect,
    Table(dialect, "users"),
    columns=columns
)
sql, params = create.to_sql()
backend.execute(sql, params)

# 或者先构建 SQL 并检查
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

`TableType` 区分目录实际报告的种类 —— `BASE_TABLE`、`VIEW`、`MATERIALIZED_VIEW`、`FOREIGN_TABLE`、`PARTITIONED_TABLE`、`SYSTEM_TABLE`、`EXTERNAL` —— 关系不会被悄悄折叠成"表"。

### 后端差异

> ⚠️ **重要提示**：本文档以 SQLite 作为示例后端。不同的数据库后端存在显著差异：

| 特性 | SQLite | MySQL | PostgreSQL |
|------|--------|-------|------------|
| **内省 API** | `list_tables()`、`get_table_info()`、`pragma.*` | 不同的方法名 | 不同的方法名 |
| **DDL 支持** | 有限的 ALTER TABLE（仅支持 ADD/DROP column）；没有 `CREATE SCHEMA` | 完整的 ALTER TABLE | 完整的 ALTER TABLE |
| **索引类型** | 不支持 USING 子句 | BTREE、HASH 等 | BTREE、HASH、GIN 等 |
| **局部索引** | 支持（WHERE 子句） | 不支持 | 支持 |
| **生成列** | 3.31.0+ | 5.7.31+ | 支持 |
| **约束性状** | 命名与延迟可渲染；`ENFORCED` 被拒绝 | 命名可渲染 | 全部可渲染 |

请始终参考你所用后端的文档以获取准确的 API 用法。

## 示例代码

本章的完整示例代码可以在以下位置找到：
[docs/examples/chapter_03_modeling/ddl_basic.py](../../examples/chapter_03_modeling/ddl_basic.py)

更多示例：
- [docs/examples/chapter_03_modeling/ddl_relationships.py](../../examples/chapter_03_modeling/ddl_relationships.py) — 创建带外键关系的表
- [docs/examples/chapter_03_modeling/ddl_indexes.py](../../examples/chapter_03_modeling/ddl_indexes.py) — 索引创建模式