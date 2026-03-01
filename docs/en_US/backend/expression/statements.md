# Statements

The `statements` module defines the core DML (Data Manipulation Language) and DDL (Data Definition Language) structures. These classes represent complete SQL statements like `SELECT`, `INSERT`, `UPDATE`, and `DELETE`.

## DML Statements

### QueryExpression (SELECT)

`QueryExpression` represents a `SELECT` statement. It composes various clauses (SELECT, FROM, WHERE, GROUP BY, etc.) into a complete query.

```python
from rhosocial.activerecord.backend.expression import QueryExpression, TableExpression, Column, Literal

# Basic SELECT
query = QueryExpression(
    dialect,
    select=[Column(dialect, "name"), Column(dialect, "email")],
    from_=TableExpression(dialect, "users"),
    where=Column(dialect, "status") == Literal(dialect, "active")
)
sql, params = query.to_sql()
# sql: 'SELECT "name", "email" FROM "users" WHERE "status" = ?'
# params: ("active",)

# SELECT with DISTINCT
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

`InsertExpression` represents an `INSERT` statement. It supports single-row, multi-row, `INSERT ... SELECT`, and `ON CONFLICT` clauses.

```python
from rhosocial.activerecord.backend.expression import InsertExpression, ValuesSource, Literal

# Single row insert
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

# Insert with ON CONFLICT (Upsert)
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

`UpdateExpression` represents an `UPDATE` statement. It supports `SET` assignments, `WHERE` clauses, and optional `FROM` clauses (for joins).

```python
from rhosocial.activerecord.backend.expression import UpdateExpression, Literal, Column

# Basic UPDATE
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

# UPDATE with RETURNING
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

`DeleteExpression` represents a `DELETE` statement. It supports `WHERE` clauses and optional `USING` clauses (for joins).

```python
from rhosocial.activerecord.backend.expression import DeleteExpression, Literal, Column

# Basic DELETE
delete = DeleteExpression(
    dialect,
    table="sessions",
    where=Column(dialect, "expires_at") < Literal(dialect, "NOW()")
)
sql, params = delete.to_sql()
# sql: 'DELETE FROM "sessions" WHERE "expires_at" < ?'
# params: ("NOW()",)

# DELETE with USING (Join delete)
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

## DDL Statements

### CreateTableExpression

`CreateTableExpression` represents a `CREATE TABLE` statement.

```python
from rhosocial.activerecord.backend.expression import CreateTableExpression, ColumnDefinition

# Create table
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

### DropTableExpression

`DropTableExpression` represents a `DROP TABLE` statement.

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

Expressions for managing database views.

```python
from rhosocial.activerecord.backend.expression import CreateViewExpression

# Create View
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

`TruncateExpression` represents a `TRUNCATE TABLE` statement for fast row deletion.

```python
from rhosocial.activerecord.backend.expression import TruncateExpression

# Basic TRUNCATE
truncate = TruncateExpression(
    dialect,
    table_name="logs"
)
sql, params = truncate.to_sql()
# sql: 'TRUNCATE TABLE "logs"'
# params: ()

# TRUNCATE with RESTART IDENTITY and CASCADE
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

### Schema DDL

#### CreateSchemaExpression

`CreateSchemaExpression` represents a `CREATE SCHEMA` statement for creating database schemas (namespaces).

```python
from rhosocial.activerecord.backend.expression.statement import CreateSchemaExpression

# Basic CREATE SCHEMA
create_schema = CreateSchemaExpression(
    dialect,
    schema_name="my_schema"
)
sql, params = create_schema.to_sql()
# sql: 'CREATE SCHEMA "my_schema"'
# params: ()

# CREATE SCHEMA IF NOT EXISTS with AUTHORIZATION
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

`DropSchemaExpression` represents a `DROP SCHEMA` statement.

```python
from rhosocial.activerecord.backend.expression.statement import DropSchemaExpression

# DROP SCHEMA with options
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

### Index DDL

#### CreateIndexExpression

`CreateIndexExpression` represents a `CREATE INDEX` statement with support for various index types and options.

```python
from rhosocial.activerecord.backend.expression.statement import CreateIndexExpression

# Basic CREATE INDEX
create_index = CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"]
)
sql, params = create_index.to_sql()
# sql: 'CREATE INDEX "idx_users_email" ON "users" ("email")'
# params: ()

# UNIQUE INDEX with WHERE clause (partial index)
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

# Composite index with index type
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

# Index with INCLUDE clause (covering index)
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

`DropIndexExpression` represents a `DROP INDEX` statement.

```python
from rhosocial.activerecord.backend.expression.statement import DropIndexExpression

# DROP INDEX
drop_index = DropIndexExpression(
    dialect,
    index_name="idx_old_index",
    if_exists=True,
    table_name="users"  # Optional: provides table context
)
sql, params = drop_index.to_sql()
# sql: 'DROP INDEX IF EXISTS "idx_old_index" ON "users"'
# params: ()
```

### Sequence DDL

#### CreateSequenceExpression

`CreateSequenceExpression` represents a `CREATE SEQUENCE` statement for generating unique numeric identifiers.

```python
from rhosocial.activerecord.backend.expression.statement import CreateSequenceExpression

# Basic CREATE SEQUENCE
create_seq = CreateSequenceExpression(
    dialect,
    sequence_name="user_id_seq"
)
sql, params = create_seq.to_sql()
# sql: 'CREATE SEQUENCE "user_id_seq" NO CYCLE'
# params: ()

# CREATE SEQUENCE with all options
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

`DropSequenceExpression` represents a `DROP SEQUENCE` statement.

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

`AlterSequenceExpression` represents an `ALTER SEQUENCE` statement for modifying existing sequences.

```python
from rhosocial.activerecord.backend.expression.statement import AlterSequenceExpression

# Restart sequence
alter_seq = AlterSequenceExpression(
    dialect,
    sequence_name="user_id_seq",
    restart=1000
)
sql, params = alter_seq.to_sql()
# sql: 'ALTER SEQUENCE "user_id_seq" RESTART WITH 1000'
# params: ()

# Multiple changes
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

`MergeExpression` represents a `MERGE` statement (Upsert).

```python
from rhosocial.activerecord.backend.expression import MergeExpression, MergeAction, MergeActionType

# Define Actions
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

# Merge Statement
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
