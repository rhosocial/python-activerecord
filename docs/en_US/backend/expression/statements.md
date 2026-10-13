# Statements

The `statements` module defines the core DML (Data Manipulation Language) and DDL (Data Definition Language) structures. These classes represent complete SQL statements like `SELECT`, `INSERT`, `UPDATE`, and `DELETE`.

## DML Statements

### QueryStatement (SELECT)

`QueryStatement` represents a `SELECT` statement. It composes various clauses (SELECT, FROM, WHERE, GROUP BY, etc.) into a complete query.

```python
from rhosocial.activerecord.backend.expression import QueryStatement, TableExpression, Column, Literal

# Basic SELECT
query = QueryStatement(
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
query = QueryStatement(
    dialect,
    select=[Column(dialect, "category")],
    from_=TableExpression(dialect, "products"),
    select_modifier=SelectModifier.DISTINCT
)
sql, params = query.to_sql()
# sql: 'SELECT DISTINCT "category" FROM "products"'
# params: ()
```

### InsertStatement (INSERT)

`InsertStatement` represents an `INSERT` statement. It supports single-row, multi-row, `INSERT ... SELECT`, and `ON CONFLICT` clauses.

```python
from rhosocial.activerecord.backend.expression import InsertStatement, ValuesSource, Literal

# Single row insert
source = ValuesSource(dialect, values_list=[
    [Literal(dialect, "John Doe"), Literal(dialect, "john@example.com")]
])
insert = InsertStatement(
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
insert = InsertStatement(
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

### UpdateStatement (UPDATE)

`UpdateStatement` represents an `UPDATE` statement. It supports `SET` assignments, `WHERE` clauses, and optional `FROM` clauses (for joins).

```python
from rhosocial.activerecord.backend.expression import UpdateStatement, Literal, Column

# Basic UPDATE
update = UpdateStatement(
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
update = UpdateStatement(
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

### DeleteStatement (DELETE)

`DeleteStatement` represents a `DELETE` statement. It supports `WHERE` clauses and optional `USING` clauses (for joins).

```python
from rhosocial.activerecord.backend.expression import DeleteStatement, Literal, Column

# Basic DELETE
delete = DeleteStatement(
    dialect,
    table="sessions",
    where=Column(dialect, "expires_at") < Literal(dialect, "NOW()")
)
sql, params = delete.to_sql()
# sql: 'DELETE FROM "sessions" WHERE "expires_at" < ?'
# params: ("NOW()",)

# DELETE with USING (Join delete)
delete = DeleteStatement(
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

> **Inline Literals in DDL**
>
> DDL clauses (`DEFAULT`, `CHECK`, partial-index `WHERE`, partition boundaries, etc.) do **not** accept bind parameters — the database engine requires these positions to contain directly parseable SQL text. Therefore, when using `Literal` expressions in DDL, you **must** set `inline_literals=True`:
>
> ```python
> # ✗ Wrong: DEFAULT ? in DDL causes execution failure
> default_value=Literal(dialect, 0)
>
> # ✓ Correct: inlined produces DEFAULT 0
> default_value=Literal(dialect, 0, inline_literals=True)
> ```
>
> DML statements (`INSERT`/`SELECT`/`UPDATE`/`DELETE`) are not affected — the default bind-parameter mode works normally.

### CreateTableStatement

`CreateTableStatement` represents a `CREATE TABLE` statement.

Data types should use `DataType` expressions (e.g. `IntegerType`, `TextType`, `VarCharType`, etc.) rather than raw strings:

```python
from rhosocial.activerecord.backend.expression import (
    CreateTableStatement, ColumnDefinition,
    ColumnConstraint, Literal, Column,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType, VarCharType, RealType

# Create table — using DataType expressions
create = CreateTableStatement(
    dialect,
    table="new_users",
    columns=[
        ColumnDefinition(dialect, "id", IntegerType(dialect), constraints=[
            ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True)),
        ]),
        ColumnDefinition(dialect, "name", VarCharType(dialect, length=255), constraints=[
            ColumnConstraint(dialect, branch=dialectNotNullConstraint(dialect)),
        ]),
        ColumnDefinition(dialect, "bio", TextType(dialect)),
    ],
    if_not_exists=True,
)
sql, params = create.to_sql()
# sql: 'CREATE TABLE IF NOT EXISTS "new_users" ("id" INTEGER PRIMARY KEY AUTOINCREMENT,
#        "name" VARCHAR(255) NOT NULL, "bio" TEXT)'
# params: ()
```

#### Inline Literals in DEFAULT and CHECK Constraints

DDL `DEFAULT` and `CHECK` clauses require inline literals. Use `Literal(..., inline_literals=True)`:

```python
# Column with DEFAULT value
ColumnDefinition(dialect, "status", TextType(dialect), constraints=[
    ColumnConstraint(dialect,
        branch=ColumnDefaultConstraint(
            value=Literal(dialect, "active", inline_literals=True),  # -> DEFAULT 'active'
    ),
]),

# Column with CHECK constraint
ColumnDefinition(dialect, "age", IntegerType(dialect), constraints=[
    ColumnConstraint(dialect,
        branch=ColumnCheckConstraint(
            condition=ComparisonPredicate(
            dialect, ">=",
            Column(dialect, "age"),
            Literal(dialect, 0, inline_literals=True),  # -> CHECK ("age" >= 0)
        ),
    ),
]),

# DEFAULT numeric value
ColumnDefinition(dialect, "score", RealType(dialect), constraints=[
    ColumnConstraint(dialect,
        branch=ColumnDefaultConstraint(
            value=Literal(dialect, 0.0, inline_literals=True),  # -> DEFAULT 0.0
    ),
]),
```

#### Generated Columns (SQLite 3.31.0+, PostgreSQL 12+, MySQL 5.7+)

Generated columns (computed columns) use the `ColumnGeneratedConstraint` expression, rendered through `dialect.format_column_generated_constraint`:

```python
from rhosocial.activerecord.backend.expression import (
    CreateTableStatement, ColumnDefinition, ColumnConstraint, Column,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, RealType
from rhosocial.activerecord.backend.expression.statements import (
    ColumnGeneratedConstraint, GeneratedColumnType,
)

# Create table with generated columns
columns = [
    ColumnDefinition(dialect, "id", IntegerType(dialect), constraints=[
        ColumnConstraint(dialect, branch=dialectPrimaryKeyConstraint(dialect)),
    ]),
    ColumnDefinition(dialect, "price", RealType(dialect)),
    ColumnDefinition(dialect, "quantity", IntegerType(dialect)),
    # STORED generated column - computed and stored on disk
    ColumnDefinition(dialect,
        name="total",
        data_type=RealType(dialect),
        generated_expression=ColumnGeneratedConstraint(
            dialect,
            expression=Column(dialect, "price") * Column(dialect, "quantity"),
            storage_type=GeneratedColumnType.STORED,
        ),
    ),
]

create = CreateTableStatement(
    dialect=dialect,
    table="products",
    columns=columns,
)
sql, params = create.to_sql()
# sql: 'CREATE TABLE "products" ("id" INTEGER PRIMARY KEY, "price" REAL,
#        "quantity" INTEGER, "total" REAL GENERATED ALWAYS AS ("price" * "quantity") STORED)'
# params: ()

# Note: Check backend support before use
# dialect.supports_generated_columns()        - master switch
# dialect.supports_stored_generated_columns()  - STORED support
# dialect.supports_virtual_generated_columns() - VIRTUAL support
```

### DropTableStatement

`DropTableStatement` represents a `DROP TABLE` statement.

```python
from rhosocial.activerecord.backend.expression import DropTableStatement

drop = DropTableStatement(
    dialect,
    table_name="old_users",
    if_exists=True,
    cascade=True
)
sql, params = drop.to_sql()
# sql: 'DROP TABLE IF EXISTS "old_users" CASCADE'
# params: ()
```

### CreateViewStatement / DropViewStatement

Expressions for managing database views.

```python
from rhosocial.activerecord.backend.expression import CreateViewStatement

# Create View
query = QueryStatement(
    dialect,
    select=[Column(dialect, "name")],
    from_=TableExpression(dialect, "users")
)
create_view = CreateViewStatement(
    dialect,
    view_name="user_names",
    query=query,
    or_replace=True
)
sql, params = create_view.to_sql()
# sql: 'CREATE OR REPLACE VIEW "user_names" AS SELECT "name" FROM "users"'
# params: ()
```

### TruncateStatement

`TruncateStatement` represents a `TRUNCATE TABLE` statement for fast row deletion.

```python
from rhosocial.activerecord.backend.expression import TruncateStatement

# Basic TRUNCATE
truncate = TruncateStatement(
    dialect,
    table_name="logs"
)
sql, params = truncate.to_sql()
# sql: 'TRUNCATE TABLE "logs"'
# params: ()

# TRUNCATE with RESTART IDENTITY and CASCADE
truncate = TruncateStatement(
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

#### CreateSchemaStatement

`CreateSchemaStatement` represents a `CREATE SCHEMA` statement for creating database schemas (namespaces).

```python
from rhosocial.activerecord.backend.expression.statement import CreateSchemaStatement

# Basic CREATE SCHEMA
create_schema = CreateSchemaStatement(
    dialect,
    schema_name="my_schema"
)
sql, params = create_schema.to_sql()
# sql: 'CREATE SCHEMA "my_schema"'
# params: ()

# CREATE SCHEMA IF NOT EXISTS with AUTHORIZATION
create_schema = CreateSchemaStatement(
    dialect,
    schema_name="app_schema",
    if_not_exists=True,
    authorization="app_user"
)
sql, params = create_schema.to_sql()
# sql: 'CREATE SCHEMA IF NOT EXISTS "app_schema" AUTHORIZATION "app_user"'
# params: ()
```

#### DropSchemaStatement

`DropSchemaStatement` represents a `DROP SCHEMA` statement.

```python
from rhosocial.activerecord.backend.expression.statement import DropSchemaStatement

# DROP SCHEMA with options
drop_schema = DropSchemaStatement(
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

#### CreateIndexStatement

`CreateIndexStatement` represents a `CREATE INDEX` statement with support for various index types and options.

```python
from rhosocial.activerecord.backend.expression.statement import CreateIndexStatement

# Basic CREATE INDEX
create_index = CreateIndexStatement(
    dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"]
)
sql, params = create_index.to_sql()
# sql: 'CREATE INDEX "idx_users_email" ON "users" ("email")'
# params: ()

# UNIQUE INDEX with WHERE clause (partial index)
create_index = CreateIndexStatement(
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
create_index = CreateIndexStatement(
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
create_index = CreateIndexStatement(
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

#### DropIndexStatement

`DropIndexStatement` represents a `DROP INDEX` statement.

```python
from rhosocial.activerecord.backend.expression.statement import DropIndexStatement

# DROP INDEX
drop_index = DropIndexStatement(
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

#### CreateSequenceStatement

`CreateSequenceStatement` represents a `CREATE SEQUENCE` statement for generating unique numeric identifiers.

```python
from rhosocial.activerecord.backend.expression.statement import CreateSequenceStatement

# Basic CREATE SEQUENCE
create_seq = CreateSequenceStatement(
    dialect,
    sequence_name="user_id_seq"
)
sql, params = create_seq.to_sql()
# sql: 'CREATE SEQUENCE "user_id_seq" NO CYCLE'
# params: ()

# CREATE SEQUENCE with all options
create_seq = CreateSequenceStatement(
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

#### DropSequenceStatement

`DropSequenceStatement` represents a `DROP SEQUENCE` statement.

```python
from rhosocial.activerecord.backend.expression.statement import DropSequenceStatement

drop_seq = DropSequenceStatement(
    dialect,
    sequence_name="old_seq",
    if_exists=True
)
sql, params = drop_seq.to_sql()
# sql: 'DROP SEQUENCE IF EXISTS "old_seq"'
# params: ()
```

#### AlterSequenceStatement

`AlterSequenceStatement` represents an `ALTER SEQUENCE` statement for modifying existing sequences.

```python
from rhosocial.activerecord.backend.expression.statement import AlterSequenceStatement

# Restart sequence
alter_seq = AlterSequenceStatement(
    dialect,
    sequence_name="user_id_seq",
    restart=1000
)
sql, params = alter_seq.to_sql()
# sql: 'ALTER SEQUENCE "user_id_seq" RESTART WITH 1000'
# params: ()

# Multiple changes
alter_seq = AlterSequenceStatement(
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

### MergeStatement (MERGE)

`MergeStatement` represents a `MERGE` statement (Upsert).

```python
from rhosocial.activerecord.backend.expression import MergeStatement, MergeAction, MergeActionType

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
merge = MergeStatement(
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

### Materialized View DDL

Materialized views are database objects that pre-compute and store query results, suitable for caching complex query results.

> **Note**: Materialized view support varies by database:
> - PostgreSQL: Full support (including CONCURRENTLY refresh, TABLESPACE, etc.)
> - Oracle: Full support
> - MySQL: Not supported (use tables as alternative)
> - SQLite: Not supported

#### CreateMaterializedViewStatement

`CreateMaterializedViewStatement` represents a `CREATE MATERIALIZED VIEW` statement.

```python
from rhosocial.activerecord.backend.expression.statement import CreateMaterializedViewStatement

# Basic CREATE MATERIALIZED VIEW
query = QueryStatement(
    dialect,
    select=[Column(dialect, "user_id"), FunctionCall(dialect, "COUNT", Column(dialect, "id"))],
    from_=TableExpression(dialect, "orders"),
    group_by_having=GroupByHavingClause(dialect, group_by=[Column(dialect, "user_id")])
)
create_mv = CreateMaterializedViewStatement(
    dialect,
    view_name="order_counts",
    query=query
)
sql, params = create_mv.to_sql()
# sql: 'CREATE MATERIALIZED VIEW "order_counts" AS SELECT "user_id", COUNT("id") FROM "orders" GROUP BY "user_id" WITH DATA'
# params: ()

# Materialized view with TABLESPACE (PostgreSQL)
create_mv = CreateMaterializedViewStatement(
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

#### DropMaterializedViewStatement

`DropMaterializedViewStatement` represents a `DROP MATERIALIZED VIEW` statement.

```python
from rhosocial.activerecord.backend.expression.statement import DropMaterializedViewStatement

# DROP MATERIALIZED VIEW
drop_mv = DropMaterializedViewStatement(
    dialect,
    view_name="old_summary",
    if_exists=True,
    cascade=True
)
sql, params = drop_mv.to_sql()
# sql: 'DROP MATERIALIZED VIEW IF EXISTS "old_summary" CASCADE'
# params: ()
```

#### RefreshMaterializedViewStatement

`RefreshMaterializedViewStatement` represents a `REFRESH MATERIALIZED VIEW` statement for refreshing materialized view data.

```python
from rhosocial.activerecord.backend.expression.statement import RefreshMaterializedViewStatement

# Basic refresh
refresh_mv = RefreshMaterializedViewStatement(
    dialect,
    view_name="order_counts"
)
sql, params = refresh_mv.to_sql()
# sql: 'REFRESH MATERIALIZED VIEW "order_counts"'
# params: ()

# CONCURRENTLY refresh (PostgreSQL 9.4+, requires unique index)
refresh_mv = RefreshMaterializedViewStatement(
    dialect,
    view_name="order_counts",
    concurrent=True
)
sql, params = refresh_mv.to_sql()
# sql: 'REFRESH MATERIALIZED VIEW CONCURRENTLY "order_counts"'
# params: ()

# WITH DATA/WITH NO DATA option
refresh_mv = RefreshMaterializedViewStatement(
    dialect,
    view_name="order_counts",
    with_data=True
)
sql, params = refresh_mv.to_sql()
# sql: 'REFRESH MATERIALIZED VIEW "order_counts" WITH DATA'
# params: ()
```

#### Checking Materialized View Support

Before using materialized views, check if the database supports the relevant features:

```python
# Check basic materialized view support
if dialect.supports_materialized_view():
    # Can create materialized view
    pass

# Check refresh support
if dialect.supports_refresh_materialized_view():
    # Can refresh materialized view
    pass

# Check CONCURRENTLY refresh support (PostgreSQL 9.4+)
if dialect.supports_materialized_view_concurrent_refresh():
    # Can use CONCURRENTLY option
    pass

# Check TABLESPACE support
if dialect.supports_materialized_view_tablespace():
    # Can specify tablespace for materialized view
    pass

# Check storage options support
if dialect.supports_materialized_view_storage_options():
    # Can specify storage parameters
    pass
```
