# 语句 (Statements)

`statements` 模块定义了核心的 DML（数据操作语言）和 DDL（数据定义语言）结构。这些类表示完整的 SQL 语句，如 `SELECT`、`INSERT`、`UPDATE` 和 `DELETE`。

## DML 语句

### QueryExpression (SELECT)

`QueryExpression` 表示 `SELECT` 语句。它将各种子句（SELECT、FROM、WHERE、GROUP BY 等）组合成一个完整的查询。

```python
from rhosocial.activerecord.backend.expression import QueryExpression, TableExpression, Column, Literal

# 基础 SELECT
query = QueryExpression(
    dialect,
    select=[Column(dialect, "name"), Column(dialect, "email")],
    from_=TableExpression(dialect, "users"),
    where=Column(dialect, "status") == Literal(dialect, "active")
)
sql, params = query.to_sql()
# sql: 'SELECT "name", "email" FROM "users" WHERE "status" = ?'
# params: ("active",)

# 带 DISTINCT 的 SELECT
from rhosocial.activerecord.backend.expression import SelectModifier
query = QueryExpression(
    dialect,
    select=[Column(dialect, "category")],
    from_=TableExpression(dialect, "products"),
    select_modifier=SelectModifier.DISTINCT
)
sql, params = query.to_sql()
# sql: 'SELECT DISTINCT "category" FROM "products"'
# params: ()
```

### InsertExpression (INSERT)

`InsertExpression` 表示 `INSERT` 语句。它支持单行、多行、`INSERT ... SELECT` 以及 `ON CONFLICT` 子句。

```python
from rhosocial.activerecord.backend.expression import InsertExpression, ValuesSource, Literal

# 单行插入
source = ValuesSource(dialect, values_list=[
    [Literal(dialect, "John Doe"), Literal(dialect, "john@example.com")]
])
insert = InsertExpression(
    dialect,
    into="users",
    columns=["name", "email"],
    source=source
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
insert = InsertExpression(
    dialect,
    into="products",
    columns=["id", "name"],
    source=source,
    on_conflict=on_conflict
)
sql, params = insert.to_sql()
# sql: 'INSERT INTO "products" ("id", "name") VALUES (?, ?) ON CONFLICT ("id") DO NOTHING'
# params: (...)
```

### UpdateExpression (UPDATE)

`UpdateExpression` 表示 `UPDATE` 语句。它支持 `SET` 赋值、`WHERE` 子句以及可选的 `FROM` 子句（用于连接更新）。

```python
from rhosocial.activerecord.backend.expression import UpdateExpression, Literal, Column

# 基础 UPDATE
update = UpdateExpression(
    dialect,
    table="users",
    assignments={
        "status": Literal(dialect, "inactive"),
        "updated_at": Literal(dialect, "2023-01-01")
    },
    where=Column(dialect, "last_login") < Literal(dialect, "2022-01-01")
)
sql, params = update.to_sql()
# sql: 'UPDATE "users" SET "status" = ?, "updated_at" = ? WHERE "last_login" < ?'
# params: ("inactive", "2023-01-01", "2022-01-01")

# 带 RETURNING 的 UPDATE
from rhosocial.activerecord.backend.expression import ReturningClause
update = UpdateExpression(
    dialect,
    table="items",
    assignments={"quantity": Column(dialect, "quantity") - Literal(dialect, 1)},
    where=Column(dialect, "id") == Literal(dialect, 123),
    returning=ReturningClause(dialect, [Column(dialect, "quantity")])
)
sql, params = update.to_sql()
# sql: 'UPDATE "items" SET "quantity" = "quantity" - ? WHERE "id" = ? RETURNING "quantity"'
# params: (1, 123)
```

### DeleteExpression (DELETE)

`DeleteExpression` 表示 `DELETE` 语句。它支持 `WHERE` 子句和可选的 `USING` 子句（用于连接删除）。

```python
from rhosocial.activerecord.backend.expression import DeleteExpression, Literal, Column

# 基础 DELETE
delete = DeleteExpression(
    dialect,
    table="sessions",
    where=Column(dialect, "expires_at") < Literal(dialect, "NOW()")
)
sql, params = delete.to_sql()
# sql: 'DELETE FROM "sessions" WHERE "expires_at" < ?'
# params: ("NOW()",)

# 带 USING 的 DELETE (连接删除)
delete = DeleteExpression(
    dialect,
    table="users",
    using="old_users",
    where=Column(dialect, "id", "users") == Column(dialect, "old_id", "old_users")
)
sql, params = delete.to_sql()
# sql: 'DELETE FROM "users" USING "old_users" WHERE "users"."id" = "old_users"."old_id"'
# params: ()
```

## DDL 语句

### CreateTableExpression

`CreateTableExpression` 表示 `CREATE TABLE` 语句。

```python
from rhosocial.activerecord.backend.expression import CreateTableExpression, ColumnDefinition

# 创建表
create = CreateTableExpression(
    dialect,
    table_name="new_users",
    columns=[
        ColumnDefinition(dialect, "id", "INTEGER", primary_key=True),
        ColumnDefinition(dialect, "name", "VARCHAR(255)", nullable=False)
    ],
    if_not_exists=True
)
sql, params = create.to_sql()
# sql: 'CREATE TABLE IF NOT EXISTS "new_users" ("id" INTEGER PRIMARY KEY, "name" VARCHAR(255) NOT NULL)'
# params: ()
```

#### 生成列（SQLite 3.31.0+、PostgreSQL、MySQL）

SQLite 3.31.0+ 支持生成列（计算列）。使用 `GeneratedColumnType` 指定存储类型：

```python
from rhosocial.activerecord.backend.expression import CreateTableExpression, ColumnDefinition, ColumnConstraint, ColumnConstraintType, GeneratedColumnType
from rhosocial.activerecord.backend.expression import Column, Literal, CaseExpression

# 创建带生成列的表
columns = [
    ColumnDefinition(name="id", data_type="INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
    ColumnDefinition(name="price", data_type="REAL"),
    ColumnDefinition(name="quantity", data_type="INTEGER"),
    # STORED 生成列 - 计算并存储在磁盘上
    ColumnDefinition(
        name="total",
        data_type="REAL",
        generated_expression=Column(dialect, "price") * Column(dialect, "quantity"),
        generated_type=GeneratedColumnType.STORED
    ),
    # VIRTUAL 生成列 - 使用 CaseExpression 表达条件逻辑
    ColumnDefinition(
        name="status_label",
        data_type="TEXT",
        generated_expression=CaseExpression(
            dialect,
            cases=[
                (Column(dialect, "quantity") > Literal(dialect, 0), Literal(dialect, "有货")),
            ],
            default=Literal(dialect, "缺货")
        ),
        generated_type=GeneratedColumnType.VIRTUAL
    )
]

create = CreateTableExpression(
    dialect=dialect,
    table_name="products",
    columns=columns
)
sql, params = create.to_sql()
# sql: 'CREATE TABLE "products" ("id" INTEGER PRIMARY KEY, "price" REAL, "quantity" INTEGER, 
# "total" REAL GENERATED ALWAYS AS ("price" * "quantity") STORED,
# "status_label" TEXT GENERATED ALWAYS AS (CASE WHEN "quantity" > ? THEN ? ELSE ? END) VIRTUAL)'
# params: (0, "有货", "缺货")

# 注意：生成列需要 SQLite 3.31.0+
# 使用 dialect.supports_generated_columns() 检查可用性
```

### DropTableExpression

`DropTableExpression` 表示 `DROP TABLE` 语句。

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
# params: ()
```

### CreateViewExpression / DropViewExpression

用于管理数据库视图的表达式。

```python
from rhosocial.activerecord.backend.expression import CreateViewExpression

# 创建视图
query = QueryExpression(
    dialect,
    select=[Column(dialect, "name")],
    from_=TableExpression(dialect, "users")
)
create_view = CreateViewExpression(
    dialect,
    view_name="user_names",
    query=query,
    or_replace=True
)
sql, params = create_view.to_sql()
# sql: 'CREATE OR REPLACE VIEW "user_names" AS SELECT "name" FROM "users"'
# params: ()
```

### TruncateExpression

`TruncateExpression` 表示 `TRUNCATE TABLE` 语句，用于快速删除表中所有行。

```python
from rhosocial.activerecord.backend.expression import TruncateExpression

# 基本 TRUNCATE
truncate = TruncateExpression(
    dialect,
    table_name="logs"
)
sql, params = truncate.to_sql()
# sql: 'TRUNCATE TABLE "logs"'
# params: ()

# 带 RESTART IDENTITY 和 CASCADE 的 TRUNCATE
truncate = TruncateExpression(
    dialect,
    table_name="orders",
    restart_identity=True,
    cascade=True
)
sql, params = truncate.to_sql()
# sql: 'TRUNCATE TABLE "orders" RESTART IDENTITY CASCADE'
# params: ()
```

### Schema DDL（模式定义语言）

#### CreateSchemaExpression

`CreateSchemaExpression` 表示 `CREATE SCHEMA` 语句，用于创建数据库模式（命名空间）。

```python
from rhosocial.activerecord.backend.expression.statement import CreateSchemaExpression

# 基本 CREATE SCHEMA
create_schema = CreateSchemaExpression(
    dialect,
    schema_name="my_schema"
)
sql, params = create_schema.to_sql()
# sql: 'CREATE SCHEMA "my_schema"'
# params: ()

# 带 IF NOT EXISTS 和 AUTHORIZATION 的 CREATE SCHEMA
create_schema = CreateSchemaExpression(
    dialect,
    schema_name="app_schema",
    if_not_exists=True,
    authorization="app_user"
)
sql, params = create_schema.to_sql()
# sql: 'CREATE SCHEMA IF NOT EXISTS "app_schema" AUTHORIZATION "app_user"'
# params: ()
```

#### DropSchemaExpression

`DropSchemaExpression` 表示 `DROP SCHEMA` 语句。

```python
from rhosocial.activerecord.backend.expression.statement import DropSchemaExpression

# 带 CASCADE 的 DROP SCHEMA
drop_schema = DropSchemaExpression(
    dialect,
    schema_name="old_schema",
    if_exists=True,
    cascade=True
)
sql, params = drop_schema.to_sql()
# sql: 'DROP SCHEMA IF EXISTS "old_schema" CASCADE'
# params: ()
```

### Index DDL（索引定义语言）

#### CreateIndexExpression

`CreateIndexExpression` 表示 `CREATE INDEX` 语句，支持多种索引类型和选项。

```python
from rhosocial.activerecord.backend.expression.statement import CreateIndexExpression

# 基本 CREATE INDEX
create_index = CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"]
)
sql, params = create_index.to_sql()
# sql: 'CREATE INDEX "idx_users_email" ON "users" ("email")'
# params: ()

# 带 WHERE 子句的 UNIQUE INDEX（部分索引）
create_index = CreateIndexExpression(
    dialect,
    index_name="idx_active_users",
    table_name="users",
    columns=["email"],
    unique=True,
    where=Column(dialect, "status") == Literal(dialect, "active")
)
sql, params = create_index.to_sql()
# sql: 'CREATE UNIQUE INDEX "idx_active_users" ON "users" ("email") WHERE "status" = ?'
# params: ("active",)

# 带索引类型的复合索引
create_index = CreateIndexExpression(
    dialect,
    index_name="idx_orders_user_date",
    table_name="orders",
    columns=["user_id", "created_at"],
    index_type="BTREE"
)
sql, params = create_index.to_sql()
# sql: 'CREATE INDEX "idx_orders_user_date" ON "orders" USING BTREE ("user_id", "created_at")'
# params: ()

# 带 INCLUDE 子句的索引（覆盖索引）
create_index = CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"],
    include=["id", "name"]
)
sql, params = create_index.to_sql()
# sql: 'CREATE INDEX "idx_users_email" ON "users" ("email") INCLUDE ("id", "name")'
# params: ()
```

#### DropIndexExpression

`DropIndexExpression` 表示 `DROP INDEX` 语句。

```python
from rhosocial.activerecord.backend.expression.statement import DropIndexExpression

# DROP INDEX
drop_index = DropIndexExpression(
    dialect,
    index_name="idx_old_index",
    if_exists=True,
    table_name="users"  # 可选：提供表上下文
)
sql, params = drop_index.to_sql()
# sql: 'DROP INDEX IF EXISTS "idx_old_index" ON "users"'
# params: ()
```

### Sequence DDL（序列定义语言）

#### CreateSequenceExpression

`CreateSequenceExpression` 表示 `CREATE SEQUENCE` 语句，用于生成唯一数字标识符。

```python
from rhosocial.activerecord.backend.expression.statement import CreateSequenceExpression

# 基本 CREATE SEQUENCE
create_seq = CreateSequenceExpression(
    dialect,
    sequence_name="user_id_seq"
)
sql, params = create_seq.to_sql()
# sql: 'CREATE SEQUENCE "user_id_seq" NO CYCLE'
# params: ()

# 带所有选项的 CREATE SEQUENCE
create_seq = CreateSequenceExpression(
    dialect,
    sequence_name="order_seq",
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

#### DropSequenceExpression

`DropSequenceExpression` 表示 `DROP SEQUENCE` 语句。

```python
from rhosocial.activerecord.backend.expression.statement import DropSequenceExpression

drop_seq = DropSequenceExpression(
    dialect,
    sequence_name="old_seq",
    if_exists=True
)
sql, params = drop_seq.to_sql()
# sql: 'DROP SEQUENCE IF EXISTS "old_seq"'
# params: ()
```

#### AlterSequenceExpression

`AlterSequenceExpression` 表示 `ALTER SEQUENCE` 语句，用于修改现有序列。

```python
from rhosocial.activerecord.backend.expression.statement import AlterSequenceExpression

# 重启序列
alter_seq = AlterSequenceExpression(
    dialect,
    sequence_name="user_id_seq",
    restart=1000
)
sql, params = alter_seq.to_sql()
# sql: 'ALTER SEQUENCE "user_id_seq" RESTART WITH 1000'
# params: ()

# 多项修改
alter_seq = AlterSequenceExpression(
    dialect,
    sequence_name="order_seq",
    increment=2,
    maxvalue=1000000,
    cycle=True
)
sql, params = alter_seq.to_sql()
# sql: 'ALTER SEQUENCE "order_seq" INCREMENT BY 2 MAXVALUE 1000000 CYCLE'
# params: ()
```

### MergeExpression (MERGE)

`MergeExpression` 表示 `MERGE` 语句 (Upsert)。

```python
from rhosocial.activerecord.backend.expression import MergeExpression, MergeAction, MergeActionType

# 定义动作
when_matched = MergeAction(
    action_type=MergeActionType.UPDATE,
    assignments={"name": Column(dialect, "name", "source")}
)
when_not_matched = MergeAction(
    action_type=MergeActionType.INSERT,
    assignments={
        "id": Column(dialect, "id", "source"),
        "name": Column(dialect, "name", "source")
    }
)

# Merge 语句
merge = MergeExpression(
    dialect,
    target_table=TableExpression(dialect, "target", "t"),
    source=TableExpression(dialect, "source", "s"),
    on_condition=Column(dialect, "id", "t") == Column(dialect, "id", "s"),
    when_matched=[when_matched],
    when_not_matched=[when_not_matched]
)

sql, params = merge.to_sql()
# sql: 'MERGE INTO "target" AS "t" USING "source" AS "s" ON "t"."id" = "s"."id" ...'
# params: ()
```

### Materialized View DDL（物化视图定义语言）

物化视图是预先计算并存储结果的数据库对象，适用于复杂查询结果的缓存。

> **注意**: 物化视图支持因数据库而异：
> - PostgreSQL: 完整支持（包括 CONCURRENTLY 刷新、TABLESPACE 等）
> - Oracle: 完整支持
> - MySQL: 不支持（可使用表替代）
> - SQLite: 不支持

#### CreateMaterializedViewExpression

`CreateMaterializedViewExpression` 表示 `CREATE MATERIALIZED VIEW` 语句。

```python
from rhosocial.activerecord.backend.expression.statement import CreateMaterializedViewExpression

# 基本 CREATE MATERIALIZED VIEW
query = QueryExpression(
    dialect,
    select=[Column(dialect, "user_id"), FunctionCall(dialect, "COUNT", Column(dialect, "id"))],
    from_=TableExpression(dialect, "orders"),
    group_by_having=GroupByHavingClause(dialect, group_by=[Column(dialect, "user_id")])
)
create_mv = CreateMaterializedViewExpression(
    dialect,
    view_name="order_counts",
    query=query
)
sql, params = create_mv.to_sql()
# sql: 'CREATE MATERIALIZED VIEW "order_counts" AS SELECT "user_id", COUNT("id") FROM "orders" GROUP BY "user_id" WITH DATA'
# params: ()

# 带 TABLESPACE 的物化视图（PostgreSQL）
create_mv = CreateMaterializedViewExpression(
    dialect,
    view_name="user_summary",
    query=query,
    tablespace="fast_storage",
    with_data=False
)
sql, params = create_mv.to_sql()
# sql: 'CREATE MATERIALIZED VIEW "user_summary" TABLESPACE "fast_storage" AS SELECT ... WITH NO DATA'
# params: ()
```

#### DropMaterializedViewExpression

`DropMaterializedViewExpression` 表示 `DROP MATERIALIZED VIEW` 语句。

```python
from rhosocial.activerecord.backend.expression.statement import DropMaterializedViewExpression

# DROP MATERIALIZED VIEW
drop_mv = DropMaterializedViewExpression(
    dialect,
    view_name="old_summary",
    if_exists=True,
    cascade=True
)
sql, params = drop_mv.to_sql()
# sql: 'DROP MATERIALIZED VIEW IF EXISTS "old_summary" CASCADE'
# params: ()
```

#### RefreshMaterializedViewExpression

`RefreshMaterializedViewExpression` 表示 `REFRESH MATERIALIZED VIEW` 语句，用于刷新物化视图的数据。

```python
from rhosocial.activerecord.backend.expression.statement import RefreshMaterializedViewExpression

# 基本刷新
refresh_mv = RefreshMaterializedViewExpression(
    dialect,
    view_name="order_counts"
)
sql, params = refresh_mv.to_sql()
# sql: 'REFRESH MATERIALIZED VIEW "order_counts"'
# params: ()

# CONCURRENTLY 刷新（PostgreSQL 9.4+，需要唯一索引）
refresh_mv = RefreshMaterializedViewExpression(
    dialect,
    view_name="order_counts",
    concurrent=True
)
sql, params = refresh_mv.to_sql()
# sql: 'REFRESH MATERIALIZED VIEW CONCURRENTLY "order_counts"'
# params: ()

# 带 WITH DATA/WITH NO DATA 选项
refresh_mv = RefreshMaterializedViewExpression(
    dialect,
    view_name="order_counts",
    with_data=True
)
sql, params = refresh_mv.to_sql()
# sql: 'REFRESH MATERIALIZED VIEW "order_counts" WITH DATA'
# params: ()
```

#### 检查物化视图支持

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
if dialect.supports_materialized_view_concurrent_refresh():
    # 可以使用 CONCURRENTLY 选项
    pass

# 检查 TABLESPACE 支持
if dialect.supports_materialized_view_tablespace():
    # 可以为物化视图指定表空间
    pass

# 检查存储参数支持
if dialect.supports_materialized_view_storage_options():
    # 可以指定存储参数
    pass
```
