# 语句 (Statements)

`statements` 模块定义了核心的 DML（数据操作语言）和 DDL（数据定义语言）结构。这些类表示完整的 SQL 语句，如 `SELECT`、`INSERT`、`UPDATE` 和 `DELETE`。

## DML 语句

### QueryStatement (SELECT)

`QueryStatement` 表示 `SELECT` 语句。它将各种子句（SELECT、FROM、WHERE、GROUP BY 等）组合成一个完整的查询。

```python
from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonOperator,
    ComparisonPredicate,
    Literal,
    NamedRelationRef,
    QueryStatement,
    StringColumn,
)
from rhosocial.activerecord.backend.expression.objects import Table

# 基础 SELECT —— 谓词由带类型的列构建
query = QueryStatement(
    dialect,
    select=[Column(dialect, "name"), Column(dialect, "email")],
    from_=NamedRelationRef(dialect, Table(dialect, "users")),
    where=StringColumn(dialect, "status") == "active"
)
sql, params = query.to_sql()
# sql: 'SELECT "name", "email" FROM "users" WHERE "status" = ?'
# params: ("active",)

# 同一个谓词写成显式节点
predicate = ComparisonPredicate(
    dialect,
    ComparisonOperator.EQ,
    Column(dialect, "status"),
    Literal(dialect, "active"),
)

# 带 DISTINCT 的 SELECT
from rhosocial.activerecord.backend.expression import SelectModifier
query = QueryStatement(
    dialect,
    select=[Column(dialect, "category")],
    from_=NamedRelationRef(dialect, Table(dialect, "products")),
    select_modifier=SelectModifier.DISTINCT
)
sql, params = query.to_sql()
# sql: 'SELECT DISTINCT "category" FROM "products"'
# params: ()
```

### InsertStatement (INSERT)

`InsertStatement` 表示 `INSERT` 语句。它支持单行、多行、`INSERT ... SELECT` 以及 `ON CONFLICT` 子句。

```python
from rhosocial.activerecord.backend.expression import InsertStatement, ValuesSource, Literal
from rhosocial.activerecord.backend.expression.objects import Table

# 单行插入
source = ValuesSource(dialect, values_list=[
    [Literal(dialect, "John Doe"), Literal(dialect, "john@example.com")]
])
insert = InsertStatement(
    dialect,
    Table(dialect, "users"),
    source=source,
    columns=["name", "email"]
)
sql, params = insert.to_sql()
# sql: 'INSERT INTO "users" ("name", "email") VALUES (?, ?)'
# params: ("John Doe", "john@example.com")

# 带 ON CONFLICT 的插入 (Upsert)
from rhosocial.activerecord.backend.expression import OnConflictClause
on_conflict = OnConflictClause(
    dialect,
    conflict_target=["id"],
    do_nothing=True
)
insert = InsertStatement(
    dialect,
    Table(dialect, "products"),
    source=source,
    columns=["id", "name"],
    on_conflict=on_conflict
)
sql, params = insert.to_sql()
# sql: 'INSERT INTO "products" ("id", "name") VALUES (?, ?) ON CONFLICT ("id") DO NOTHING'
# params: (...)
```

### UpdateStatement (UPDATE)

`UpdateStatement` 表示 `UPDATE` 语句。它支持 `SET` 赋值、`WHERE` 子句以及可选的 `FROM` 子句（用于连接更新）。

```python
from rhosocial.activerecord.backend.expression import (
    IntegerColumn,
    Literal,
    ReturningClause,
    StringColumn,
    UpdateStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table

# 基础 UPDATE
update = UpdateStatement(
    dialect,
    Table(dialect, "users"),
    assignments={
        "status": Literal(dialect, "inactive"),
        "updated_at": Literal(dialect, "2023-01-01")
    },
    where=StringColumn(dialect, "last_login") < "2022-01-01"
)
sql, params = update.to_sql()
# sql: 'UPDATE "users" SET "status" = ?, "updated_at" = ? WHERE "last_login" < ?'
# params: ("inactive", "2023-01-01", "2022-01-01")

# 带 RETURNING 的 UPDATE —— 算术需要数值列类
update = UpdateStatement(
    dialect,
    Table(dialect, "items"),
    assignments={"quantity": IntegerColumn(dialect, "quantity") - 1},
    where=IntegerColumn(dialect, "id") == 123,
    returning=ReturningClause(dialect, [IntegerColumn(dialect, "quantity")])
)
sql, params = update.to_sql()
# sql: 'UPDATE "items" SET "quantity" = "quantity" - ? WHERE "id" = ? RETURNING "quantity"'
# params: (1, 123)
```

### DeleteStatement (DELETE)

`DeleteStatement` 表示 `DELETE` 语句。它支持 `WHERE` 子句和可选的 `USING` 子句（用于连接删除）。

```python
from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonOperator,
    ComparisonPredicate,
    DeleteStatement,
    NamedRelationRef,
    StringColumn,
)
from rhosocial.activerecord.backend.expression.objects import Table

# 基础 DELETE
delete = DeleteStatement(
    dialect,
    Table(dialect, "sessions"),
    where=StringColumn(dialect, "expires_at") < "NOW()"
)
sql, params = delete.to_sql()
# sql: 'DELETE FROM "sessions" WHERE "expires_at" < ?'
# params: ("NOW()",)

# 带 USING 的 DELETE (连接删除)
delete = DeleteStatement(
    dialect,
    Table(dialect, "users"),
    using=NamedRelationRef(dialect, Table(dialect, "old_users")),
    where=ComparisonPredicate(
        dialect,
        ComparisonOperator.EQ,
        Column(dialect, "id", "users"),
        Column(dialect, "old_id", "old_users")
    )
)
sql, params = delete.to_sql()
# sql: 'DELETE FROM "users" USING "old_users" WHERE "users"."id" = "old_users"."old_id"'
# params: ()
```

## DDL 语句

> **关于 DDL 中的参数内联**
>
> DDL 子句（`DEFAULT`、`CHECK`、部分索引 `WHERE`、分区边界等）**不接受绑定参数**——数据库引擎要求这些位置必须是直接可解析的 SQL 文本。因此，凡是子句本身不做规范化的位置，字面量都要写成 `inline=True`：
>
> ```python
> # ✗ 错误：DDL 中 DEFAULT ? 会导致执行失败
> Literal(dialect, 0)
>
> # ✓ 正确：内联后生成 DEFAULT 0
> Literal(dialect, 0, inline=True)
> ```
>
> DML 语句（`INSERT`/`SELECT`/`UPDATE`/`DELETE`）不受此限制，默认绑定参数模式即可正常工作。

### CreateTableStatement

`CreateTableStatement` 表示 `CREATE TABLE` 语句。

数据类型应使用 `DataType` 表达式（如 `IntegerType`、`TextType`、`VarCharType` 等），而非原始字符串：

```python
from rhosocial.activerecord.backend.expression import (
    ColumnConstraint,
    ColumnDefinition,
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import CreateTableStatement
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType, VarCharType

# 创建表 — 使用 DataType 表达式
create = CreateTableStatement(
    dialect,
    Table(dialect, "new_users"),
    columns=[
        ColumnDefinition(dialect, "id", IntegerType(dialect), constraints=[
            ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True)),
        ]),
        ColumnDefinition(dialect, "name", VarCharType(dialect, length=255), constraints=[
            ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
        ]),
        ColumnDefinition(dialect, "bio", TextType(dialect)),
    ],
    if_not_exists=True,
)
sql, params = create.to_sql()
# sql: 'CREATE TABLE IF NOT EXISTS "new_users" ("id" INTEGER PRIMARY KEY AUTOINCREMENT,
#        "name" TEXT NOT NULL, "bio" TEXT)'
# params: ()
```

#### DEFAULT 和 CHECK 约束中的内联字面量

DDL 语法位置不接受绑定参数。`ColumnDefaultConstraint` 会把收到的值规范化为内联字面量，所以直接传值即可；`CHECK` 中的谓词保留构造时的字面量，因此需要显式标记 `inline=True`：

```python
from rhosocial.activerecord.backend.expression import (
    ComparisonOperator,
    ComparisonPredicate,
    IntegerColumn,
    Literal,
)
from rhosocial.activerecord.backend.expression.statements import (
    ColumnCheckConstraint,
    ColumnDefaultConstraint,
)
from rhosocial.activerecord.backend.expression.types import RealType

# 带 DEFAULT 值的列
ColumnDefinition(dialect, "status", TextType(dialect), constraints=[
    ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, "active")),
])
# -> "status" TEXT DEFAULT 'active'

# 带 CHECK 约束的列 —— inline=True 让值不进入 params
ColumnDefinition(dialect, "age", IntegerType(dialect), constraints=[
    ColumnConstraint(dialect, branch=ColumnCheckConstraint(
        dialect,
        ComparisonPredicate(
            dialect,
            ComparisonOperator.GTE,
            IntegerColumn(dialect, "age"),
            Literal(dialect, 0, inline=True),  # -> CHECK ("age" >= 0)
        ),
    )),
])

# DEFAULT 数值
ColumnDefinition(dialect, "score", RealType(dialect), constraints=[
    ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, 0.0)),
])
# -> "score" REAL DEFAULT 0.0
```

#### 生成列（SQLite 3.31.0+、PostgreSQL 12+、MySQL 5.7+）

生成列（计算列）使用 `ColumnGeneratedConstraint` 表达式，通过 `dialect.format_column_generated_constraint` 渲染：

```python
from rhosocial.activerecord.backend.expression import (
    ColumnConstraint,
    ColumnDefinition,
    ColumnPrimaryKeyConstraint,
    IntegerColumn,
    NumericColumn,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.types import IntegerType, RealType
from rhosocial.activerecord.backend.expression.statements import (
    ColumnGeneratedConstraint,
    CreateTableStatement,
    GeneratedColumnType,
)

# 创建带生成列的表
columns = [
    ColumnDefinition(dialect, "id", IntegerType(dialect), constraints=[
        ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect)),
    ]),
    ColumnDefinition(dialect, "price", RealType(dialect)),
    ColumnDefinition(dialect, "quantity", IntegerType(dialect)),
    # STORED 生成列 - 计算并存储在磁盘上
    ColumnDefinition(dialect,
        "total",
        RealType(dialect),
        generated_expression=ColumnGeneratedConstraint(
            dialect,
            expression=NumericColumn(dialect, "price") * IntegerColumn(dialect, "quantity"),
            storage_type=GeneratedColumnType.STORED,
        ),
    ),
]

create = CreateTableStatement(
    dialect,
    Table(dialect, "products"),
    columns=columns,
)
sql, params = create.to_sql()
# sql: 'CREATE TABLE "products" ("id" INTEGER PRIMARY KEY, "price" REAL,
#        "quantity" INTEGER, "total" REAL GENERATED ALWAYS AS ("price" * "quantity") STORED)'
# params: ()

# 注意：使用前检查后端支持
# dialect.supports_generated_columns()        — 总开关
# dialect.supports_stored_generated_columns()  — STORED 支持
# dialect.supports_virtual_generated_columns() — VIRTUAL 支持
```

### DropTableStatement

`DropTableStatement` 表示 `DROP TABLE` 语句。

```python
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import DropTableStatement

drop = DropTableStatement(
    dialect,
    Table(dialect, "old_users"),
    if_exists=True,
    cascade=True
)
sql, params = drop.to_sql()
# sql: 'DROP TABLE IF EXISTS "old_users" CASCADE'
# params: ()
```

### CreateViewStatement / DropViewStatement

用于管理数据库视图的表达式。

```python
from rhosocial.activerecord.backend.expression.objects import Table, View
from rhosocial.activerecord.backend.expression.statements import (
    CreateViewStatement,
    DropViewStatement,
)

# 创建视图
query = QueryStatement(
    dialect,
    select=[Column(dialect, "name")],
    from_=NamedRelationRef(dialect, Table(dialect, "users"))
)
create_view = CreateViewStatement(
    dialect,
    View(dialect, "user_names"),
    query=query,
    replace=True
)
sql, params = create_view.to_sql()
# sql: 'CREATE OR REPLACE VIEW "user_names" AS SELECT "name" FROM "users"'
# params: ()

# 删除视图
drop_view = DropViewStatement(dialect, View(dialect, "user_names"), if_exists=True)
sql, params = drop_view.to_sql()
# sql: 'DROP VIEW IF EXISTS "user_names"'
# params: ()
```

### TruncateStatement

`TruncateStatement` 表示 `TRUNCATE TABLE` 语句，用于快速删除表中所有行。

```python
from rhosocial.activerecord.backend.expression import TruncateStatement

# 基本 TRUNCATE
truncate = TruncateStatement(
    dialect,
    Table(dialect, "logs")
)
sql, params = truncate.to_sql()
# sql: 'TRUNCATE TABLE "logs"'
# params: ()

# 带 RESTART IDENTITY 和 CASCADE 的 TRUNCATE
truncate = TruncateStatement(
    dialect,
    Table(dialect, "orders"),
    restart_identity=True,
    cascade=True
)
sql, params = truncate.to_sql()
# sql: 'TRUNCATE TABLE "orders" RESTART IDENTITY CASCADE'
# params: ()
```

### Schema DDL（模式定义语言）

#### CreateSchemaStatement

`CreateSchemaStatement` 表示 `CREATE SCHEMA` 语句，用于创建数据库模式（命名空间）。

```python
from rhosocial.activerecord.backend.expression.objects import Schema
from rhosocial.activerecord.backend.expression.statements import CreateSchemaStatement

# 基本 CREATE SCHEMA
create_schema = CreateSchemaStatement(
    dialect,
    Schema(dialect, "my_schema")
)
sql, params = create_schema.to_sql()
# sql: 'CREATE SCHEMA "my_schema"'
# params: ()

# 带 IF NOT EXISTS 和 AUTHORIZATION 的 CREATE SCHEMA
create_schema = CreateSchemaStatement(
    dialect,
    Schema(dialect, "app_schema"),
    if_not_exists=True,
    authorization="app_user"
)
sql, params = create_schema.to_sql()
# sql: 'CREATE SCHEMA IF NOT EXISTS "app_schema" AUTHORIZATION "app_user"'
# params: ()
```

#### DropSchemaStatement

`DropSchemaStatement` 表示 `DROP SCHEMA` 语句。

```python
from rhosocial.activerecord.backend.expression.statements import DropSchemaStatement

# 带 CASCADE 的 DROP SCHEMA
drop_schema = DropSchemaStatement(
    dialect,
    Schema(dialect, "old_schema"),
    if_exists=True,
    cascade=True
)
sql, params = drop_schema.to_sql()
# sql: 'DROP SCHEMA IF EXISTS "old_schema" CASCADE'
# params: ()
```

### Index DDL（索引定义语言）

#### CreateIndexStatement

`CreateIndexStatement` 表示 `CREATE INDEX` 语句，支持多种索引类型和选项。

```python
from rhosocial.activerecord.backend.expression import StringColumn
from rhosocial.activerecord.backend.expression.objects import Index, Table
from rhosocial.activerecord.backend.expression.statements import CreateIndexStatement

# 基本 CREATE INDEX
create_index = CreateIndexStatement(
    dialect,
    Index(dialect, "idx_users_email"),
    Table(dialect, "users"),
    columns=["email"]
)
sql, params = create_index.to_sql()
# sql: 'CREATE INDEX "idx_users_email" ON "users" ("email")'
# params: ()

# 带 WHERE 子句的 UNIQUE INDEX（部分索引）
create_index = CreateIndexStatement(
    dialect,
    Index(dialect, "idx_active_users"),
    Table(dialect, "users"),
    columns=["email"],
    unique=True,
    where=StringColumn(dialect, "status") == "active"
)
sql, params = create_index.to_sql()
# sql: 'CREATE UNIQUE INDEX "idx_active_users" ON "users" ("email") WHERE "status" = ?'
# params: ("active",)

# 带索引类型的复合索引
create_index = CreateIndexStatement(
    dialect,
    Index(dialect, "idx_orders_user_date"),
    Table(dialect, "orders"),
    columns=["user_id", "created_at"],
    index_type="BTREE"
)
sql, params = create_index.to_sql()
# sql: 'CREATE INDEX "idx_orders_user_date" ON "orders" USING BTREE ("user_id", "created_at")'
# params: ()

# 带 INCLUDE 子句的索引（覆盖索引）
create_index = CreateIndexStatement(
    dialect,
    Index(dialect, "idx_users_email"),
    Table(dialect, "users"),
    columns=["email"],
    include=["id", "name"]
)
sql, params = create_index.to_sql()
# sql: 'CREATE INDEX "idx_users_email" ON "users" ("email") INCLUDE ("id", "name")'
# params: ()
```

#### DropIndexStatement

`DropIndexStatement` 表示 `DROP INDEX` 语句。

```python
from rhosocial.activerecord.backend.expression.statements import DropIndexStatement

# DROP INDEX
drop_index = DropIndexStatement(
    dialect,
    Index(dialect, "idx_old_index"),
    if_exists=True,
    table=Table(dialect, "users")  # 可选：提供表上下文
)
sql, params = drop_index.to_sql()
# sql: 'DROP INDEX IF EXISTS "idx_old_index" ON "users"'
# params: ()
```

### Sequence DDL（序列定义语言）

#### CreateSequenceStatement

`CreateSequenceStatement` 表示 `CREATE SEQUENCE` 语句，用于生成唯一数字标识符。

```python
from rhosocial.activerecord.backend.expression.objects import Sequence
from rhosocial.activerecord.backend.expression.statements import CreateSequenceStatement

# 基本 CREATE SEQUENCE
create_seq = CreateSequenceStatement(
    dialect,
    Sequence(dialect, "user_id_seq")
)
sql, params = create_seq.to_sql()
# sql: 'CREATE SEQUENCE "user_id_seq" NO CYCLE'
# params: ()

# 带所有选项的 CREATE SEQUENCE
create_seq = CreateSequenceStatement(
    dialect,
    Sequence(dialect, "order_seq"),
    if_not_exists=True,
    start=1000,
    increment=1,
    minvalue=1000,
    maxvalue=999999,
    cycle=True,
    cache=20,
    owned_by="orders.id"
)
sql, params = create_seq.to_sql()
# sql: 'CREATE SEQUENCE IF NOT EXISTS "order_seq" START WITH 1000 INCREMENT BY 1 MINVALUE 1000 MAXVALUE 999999 CYCLE CACHE 20 OWNED BY orders.id'
# params: ()
```

#### DropSequenceStatement

`DropSequenceStatement` 表示 `DROP SEQUENCE` 语句。

```python
from rhosocial.activerecord.backend.expression.statements import DropSequenceStatement

drop_seq = DropSequenceStatement(
    dialect,
    Sequence(dialect, "old_seq"),
    if_exists=True
)
sql, params = drop_seq.to_sql()
# sql: 'DROP SEQUENCE IF EXISTS "old_seq"'
# params: ()

```

#### AlterSequenceStatement

`AlterSequenceStatement` 表示 `ALTER SEQUENCE` 语句，用于修改现有序列。

```python
from rhosocial.activerecord.backend.expression.statements import AlterSequenceStatement

# 重启序列
alter_seq = AlterSequenceStatement(
    dialect,
    Sequence(dialect, "user_id_seq"),
    restart=1000
)
sql, params = alter_seq.to_sql()
# sql: 'ALTER SEQUENCE "user_id_seq" RESTART WITH 1000'
# params: ()

# 多项修改
alter_seq = AlterSequenceStatement(
    dialect,
    Sequence(dialect, "order_seq"),
    increment=2,
    maxvalue=1000000,
    cycle=True
)
sql, params = alter_seq.to_sql()
# sql: 'ALTER SEQUENCE "order_seq" INCREMENT BY 2 MAXVALUE 1000000 CYCLE'
# params: ()
```

### MergeStatement (MERGE)

`MergeStatement` 表示 `MERGE` 语句 (Upsert)。

```python
from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonOperator,
    ComparisonPredicate,
    MergeAction,
    MergeActionType,
    MergeStatement,
    NamedRelationRef,
)
from rhosocial.activerecord.backend.expression.objects import Table

# 定义动作
when_matched = MergeAction(
    dialect,
    action_type=MergeActionType.UPDATE,
    assignments={"name": Column(dialect, "name", "source")}
)
when_not_matched = MergeAction(
    dialect,
    action_type=MergeActionType.INSERT,
    assignments={
        "id": Column(dialect, "id", "source"),
        "name": Column(dialect, "name", "source")
    }
)

# Merge 语句
merge = MergeStatement(
    dialect,
    target_table=Table(dialect, "target"),
    source=NamedRelationRef(dialect, Table(dialect, "source"), alias="s"),
    on_condition=ComparisonPredicate(
        dialect,
        ComparisonOperator.EQ,
        Column(dialect, "id", "target"),
        Column(dialect, "id", "s")
    ),
    when_matched=[when_matched],
    when_not_matched=[when_not_matched]
)

sql, params = merge.to_sql()
# sql: 'MERGE INTO "target" USING "source" AS "s" ON "target"."id" = "s"."id" ...'
# params: ()
```

### Materialized View DDL（物化视图定义语言）

物化视图是预先计算并存储结果的数据库对象，适用于复杂查询结果的缓存。

> **注意**: 物化视图支持因数据库而异：
> - PostgreSQL: 完整支持（包括 CONCURRENTLY 刷新、TABLESPACE 等）
> - Oracle: 完整支持
> - MySQL: 不支持（可使用表替代）
> - SQLite: 不支持

#### CreateMaterializedViewStatement

`CreateMaterializedViewStatement` 表示 `CREATE MATERIALIZED VIEW` 语句。

```python
from rhosocial.activerecord.backend.expression import (
    Column,
    FunctionCall,
    GroupByHavingClause,
)
from rhosocial.activerecord.backend.expression.objects import MaterializedView, Table
from rhosocial.activerecord.backend.expression.statements import CreateMaterializedViewStatement

# 基本 CREATE MATERIALIZED VIEW
query = QueryStatement(
    dialect,
    select=[Column(dialect, "user_id"), FunctionCall(dialect, "COUNT", Column(dialect, "id"))],
    from_=NamedRelationRef(dialect, Table(dialect, "orders")),
    group_by_having=GroupByHavingClause(dialect, group_by=[Column(dialect, "user_id")])
)
create_mv = CreateMaterializedViewStatement(
    dialect,
    MaterializedView(dialect, "order_counts"),
    query=query
)
sql, params = create_mv.to_sql()
# sql: 'CREATE MATERIALIZED VIEW "order_counts" AS SELECT "user_id", COUNT("id") FROM "orders" GROUP BY "user_id" WITH DATA'
# params: ()

# 带 TABLESPACE 的物化视图（PostgreSQL）
create_mv = CreateMaterializedViewStatement(
    dialect,
    MaterializedView(dialect, "user_summary"),
    query=query,
    tablespace="fast_storage",
    no_data=True
)
sql, params = create_mv.to_sql()
# sql: 'CREATE MATERIALIZED VIEW "user_summary" TABLESPACE "fast_storage" AS SELECT ... WITH NO DATA'
# params: ()
```

#### DropMaterializedViewStatement

`DropMaterializedViewStatement` 表示 `DROP MATERIALIZED VIEW` 语句。

```python
from rhosocial.activerecord.backend.expression.statements import DropMaterializedViewStatement

# DROP MATERIALIZED VIEW
drop_mv = DropMaterializedViewStatement(
    dialect,
    MaterializedView(dialect, "old_summary"),
    if_exists=True,
    cascade=True
)
sql, params = drop_mv.to_sql()
# sql: 'DROP MATERIALIZED VIEW IF EXISTS "old_summary" CASCADE'
# params: ()
```

#### RefreshMaterializedViewStatement

`RefreshMaterializedViewStatement` 表示 `REFRESH MATERIALIZED VIEW` 语句，用于刷新物化视图的数据。

```python
from rhosocial.activerecord.backend.expression.statements import RefreshMaterializedViewStatement

# 基本刷新
refresh_mv = RefreshMaterializedViewStatement(
    dialect,
    MaterializedView(dialect, "order_counts")
)
sql, params = refresh_mv.to_sql()
# sql: 'REFRESH MATERIALIZED VIEW "order_counts"'
# params: ()

# CONCURRENTLY 刷新（PostgreSQL 9.4+，需要唯一索引）
refresh_mv = RefreshMaterializedViewStatement(
    dialect,
    MaterializedView(dialect, "order_counts"),
    concurrent=True
)
sql, params = refresh_mv.to_sql()
# sql: 'REFRESH MATERIALIZED VIEW CONCURRENTLY "order_counts"'
# params: ()

# 带 WITH DATA/WITH NO DATA 选项
refresh_mv = RefreshMaterializedViewStatement(
    dialect,
    MaterializedView(dialect, "order_counts"),
    with_data=True
)
sql, params = refresh_mv.to_sql()
# sql: 'REFRESH MATERIALIZED VIEW "order_counts" WITH DATA'
# params: ()
```

#### Partition DDL（表分区）

`PartitionClause`（定义在 `rhosocial.activerecord.backend.expression.statements.ddl_partition`）为 `CREATE TABLE` 语句添加 `PARTITION BY` 子句。

支持三种分区策略：

| 策略 | 说明 | 示例 |
|------|------|------|
| `RANGE` | 范围分区 | `PARTITION BY RANGE (created_at)` |
| `LIST` | 列表分区 | `PARTITION BY LIST (region)` |
| `HASH` | 哈希分区 | `PARTITION BY HASH (user_id)` |

```python
from rhosocial.activerecord.backend.expression import (
    Column,
    ColumnConstraint,
    ColumnDefinition,
    ColumnPrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import CreateTableStatement
from rhosocial.activerecord.backend.expression.statements.ddl_partition import (
    PartitionClause,
    PartitionStrategy,
)
from rhosocial.activerecord.backend.expression.types import DecimalType, IntegerType, TimestampType

# RANGE 分区 —— keys 是表达式，不是字符串
partition = PartitionClause(
    dialect,
    method=PartitionStrategy.RANGE,
    keys=[Column(dialect, "created_at")]
)

# 在 CREATE TABLE 中使用
create = CreateTableStatement(
    dialect,
    Table(dialect, "orders"),
    columns=[
        ColumnDefinition(dialect, "id", IntegerType(dialect), constraints=[
            ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect)),
        ]),
        ColumnDefinition(dialect, "created_at", TimestampType(dialect)),
        ColumnDefinition(dialect, "amount", DecimalType(dialect, precision=10, scale=2)),
    ],
    partition=partition,
)
# sql: 'CREATE TABLE "orders" ("id" INTEGER PRIMARY KEY, "created_at" TIMESTAMP,
#        "amount" DECIMAL(10,2)) PARTITION BY RANGE ("created_at")'
# params: ()
```
# params: ()
```

### 方言检查

在使用分区功能之前，应检查数据库是否支持：

```python
# 检查表分区支持
if dialect.supports_table_partitioning():
    # 可以使用 PARTITION BY
    pass

# 检查具体分区类型
if dialect.supports_range_table_partitioning():
    pass
if dialect.supports_list_table_partitioning():
    pass
if dialect.supports_hash_table_partitioning():
    pass
```

> **注意**：通用分区表达式由 dialect 的 `PartitionMixin` 提供。核心协议保留 7 个分区能力与格式化查询接口，不提供分区生命周期编排。

### 检查物化视图支持

在使用物化视图之前，应检查数据库是否支持相关功能：

```python
# 检查基本物化视图支持
if dialect.supports_materialized_view():
    # 可以创建物化视图
    pass

# 检查刷新支持
if dialect.supports_refresh_materialized_view():
    # 可以刷新物化视图
    pass

# 检查 CONCURRENTLY 刷新支持（PostgreSQL 9.4+）
if dialect.supports_refresh_materialized_view():
    # 可以使用 CONCURRENTLY 选项
    pass

# 检查 TABLESPACE 支持
if dialect.supports_materialized_view_tablespace():
    # 可以为物化视图指定表空间
    pass

# 检查 WITH [NO] DATA 子句支持
if dialect.supports_with_data_clause():
    # 可以拼写 WITH [NO] DATA 子句
    pass
```
