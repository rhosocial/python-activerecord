# Statements

The `statements` module defines the core DML (Data Manipulation Language) and DDL (Data Definition Language) structures. These classes represent complete SQL statements like `SELECT`, `INSERT`, `UPDATE`, and `DELETE`.

## DML Statements

### QueryStatement (SELECT)

`QueryStatement` represents a `SELECT` statement. It composes various clauses (SELECT, FROM, WHERE, GROUP BY, etc.) into a complete query.

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

# Basic SELECT -- a typed column builds the predicate
query = QueryStatement(
    dialect,
    select=[Column(dialect, "name"), Column(dialect, "email")],
    from_=NamedRelationRef(dialect, Table(dialect, "users")),
    where=StringColumn(dialect, "status") == "active"
)
sql, params = query.to_sql()
# sql: 'SELECT "name", "email" FROM "users" WHERE "status" = ?'
# params: ("active",)

# The same predicate spelled out as a node
predicate = ComparisonPredicate(
    dialect,
    ComparisonOperator.EQ,
    Column(dialect, "status"),
    Literal(dialect, "active"),
)

# SELECT with DISTINCT
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

`InsertStatement` represents an `INSERT` statement. It supports single-row, multi-row, `INSERT ... SELECT`, and `ON CONFLICT` clauses.

```python
from rhosocial.activerecord.backend.expression import InsertStatement, ValuesSource, Literal
from rhosocial.activerecord.backend.expression.objects import Table

# Single row insert
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

# Insert with ON CONFLICT (Upsert)
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

`UpdateStatement` represents an `UPDATE` statement. It supports `SET` assignments, `WHERE` clauses, and optional `FROM` clauses (for joins).

```python
from rhosocial.activerecord.backend.expression import (
    IntegerColumn,
    Literal,
    ReturningClause,
    StringColumn,
    UpdateStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table

# Basic UPDATE
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

# UPDATE with RETURNING -- arithmetic needs a numeric column class
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

`DeleteStatement` represents a `DELETE` statement. It supports `WHERE` clauses and optional `USING` clauses (for joins).

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

# Basic DELETE
delete = DeleteStatement(
    dialect,
    Table(dialect, "sessions"),
    where=StringColumn(dialect, "expires_at") < "NOW()"
)
sql, params = delete.to_sql()
# sql: 'DELETE FROM "sessions" WHERE "expires_at" < ?'
# params: ("NOW()",)

# DELETE with USING (Join delete)
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

## DDL Statements

> **Inline Literals in DDL**
>
> DDL clauses (`DEFAULT`, `CHECK`, partial-index `WHERE`, partition boundaries, etc.) do **not** accept bind parameters — the database engine requires these positions to contain directly parseable SQL text. A literal therefore needs `inline=True` wherever the clause does not normalise the value itself:
>
> ```python
> # ✗ Wrong: DEFAULT ? in DDL causes execution failure
> Literal(dialect, 0)
>
> # ✓ Correct: inlined produces DEFAULT 0
> Literal(dialect, 0, inline=True)
> ```
>
> DML statements (`INSERT`/`SELECT`/`UPDATE`/`DELETE`) are not affected — the default bind-parameter mode works normally.

### CreateTableStatement

`CreateTableStatement` represents a `CREATE TABLE` statement.

Data types should use `DataType` expressions (e.g. `IntegerType`, `TextType`, `VarCharType`, etc.) rather than raw strings:

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

# Create table — using DataType expressions
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

#### Inline Literals in DEFAULT and CHECK Constraints

A DDL syntax position accepts no bind parameters. `ColumnDefaultConstraint`
normalises whatever it is given to an inline literal, so a plain value is
enough; a predicate inside `CHECK` keeps the literals it was built with, so mark
them `inline=True`:

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

# Column with DEFAULT value
ColumnDefinition(dialect, "status", TextType(dialect), constraints=[
    ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, "active")),
])
# -> "status" TEXT DEFAULT 'active'

# Column with CHECK constraint -- inline=True keeps the value out of params
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

# DEFAULT numeric value
ColumnDefinition(dialect, "score", RealType(dialect), constraints=[
    ColumnConstraint(dialect, branch=ColumnDefaultConstraint(dialect, 0.0)),
])
# -> "score" REAL DEFAULT 0.0
```

#### Generated Columns (SQLite 3.31.0+, PostgreSQL 12+, MySQL 5.7+)

Generated columns (computed columns) use the `ColumnGeneratedConstraint` expression, rendered through `dialect.format_column_generated_constraint`:

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

# Create table with generated columns
columns = [
    ColumnDefinition(dialect, "id", IntegerType(dialect), constraints=[
        ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect)),
    ]),
    ColumnDefinition(dialect, "price", RealType(dialect)),
    ColumnDefinition(dialect, "quantity", IntegerType(dialect)),
    # STORED generated column - computed and stored on disk
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

# Note: Check backend support before use
# dialect.supports_generated_columns()        - master switch
# dialect.supports_stored_generated_columns()  - STORED support
# dialect.supports_virtual_generated_columns() - VIRTUAL support
```

### DropTableStatement

`DropTableStatement` represents a `DROP TABLE` statement.

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

Expressions for managing database views.

```python
from rhosocial.activerecord.backend.expression.objects import Table, View
from rhosocial.activerecord.backend.expression.statements import (
    CreateViewStatement,
    DropViewStatement,
)

# Create View
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

# Drop View
drop_view = DropViewStatement(dialect, View(dialect, "user_names"), if_exists=True)
sql, params = drop_view.to_sql()
# sql: 'DROP VIEW IF EXISTS "user_names"'
# params: ()
```

### TruncateStatement

`TruncateStatement` represents a `TRUNCATE TABLE` statement for fast row deletion.

```python
from rhosocial.activerecord.backend.expression import TruncateStatement

# Basic TRUNCATE
truncate = TruncateStatement(
    dialect,
    Table(dialect, "logs")
)
sql, params = truncate.to_sql()
# sql: 'TRUNCATE TABLE "logs"'
# params: ()

# TRUNCATE with RESTART IDENTITY and CASCADE
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

### Schema DDL

#### CreateSchemaStatement

`CreateSchemaStatement` represents a `CREATE SCHEMA` statement for creating database schemas (namespaces).

```python
from rhosocial.activerecord.backend.expression.objects import Schema
from rhosocial.activerecord.backend.expression.statements import CreateSchemaStatement

# Basic CREATE SCHEMA
create_schema = CreateSchemaStatement(
    dialect,
    Schema(dialect, "my_schema")
)
sql, params = create_schema.to_sql()
# sql: 'CREATE SCHEMA "my_schema"'
# params: ()

# CREATE SCHEMA IF NOT EXISTS with AUTHORIZATION
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

`DropSchemaStatement` represents a `DROP SCHEMA` statement.

```python
from rhosocial.activerecord.backend.expression.statements import DropSchemaStatement

# DROP SCHEMA with options
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

### Index DDL

#### CreateIndexStatement

`CreateIndexStatement` represents a `CREATE INDEX` statement with support for various index types and options.

```python
from rhosocial.activerecord.backend.expression import StringColumn
from rhosocial.activerecord.backend.expression.objects import Index, Table
from rhosocial.activerecord.backend.expression.statements import CreateIndexStatement

# Basic CREATE INDEX
create_index = CreateIndexStatement(
    dialect,
    Index(dialect, "idx_users_email"),
    Table(dialect, "users"),
    columns=["email"]
)
sql, params = create_index.to_sql()
# sql: 'CREATE INDEX "idx_users_email" ON "users" ("email")'
# params: ()

# UNIQUE INDEX with WHERE clause (partial index)
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

# Composite index with index type
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

# Index with INCLUDE clause (covering index)
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

`DropIndexStatement` represents a `DROP INDEX` statement.

```python
from rhosocial.activerecord.backend.expression.statements import DropIndexStatement

# DROP INDEX
drop_index = DropIndexStatement(
    dialect,
    Index(dialect, "idx_old_index"),
    if_exists=True,
    table=Table(dialect, "users")  # Optional: provides table context
)
sql, params = drop_index.to_sql()
# sql: 'DROP INDEX IF EXISTS "idx_old_index" ON "users"'
# params: ()
```

### Sequence DDL

#### CreateSequenceStatement

`CreateSequenceStatement` represents a `CREATE SEQUENCE` statement for generating unique numeric identifiers.

```python
from rhosocial.activerecord.backend.expression.objects import Sequence
from rhosocial.activerecord.backend.expression.statements import CreateSequenceStatement

# Basic CREATE SEQUENCE
create_seq = CreateSequenceStatement(
    dialect,
    Sequence(dialect, "user_id_seq")
)
sql, params = create_seq.to_sql()
# sql: 'CREATE SEQUENCE "user_id_seq" NO CYCLE'
# params: ()

# CREATE SEQUENCE with all options
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

`DropSequenceStatement` represents a `DROP SEQUENCE` statement.

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

`AlterSequenceStatement` represents an `ALTER SEQUENCE` statement for modifying existing sequences.

```python
from rhosocial.activerecord.backend.expression.statements import AlterSequenceStatement

# Restart sequence
alter_seq = AlterSequenceStatement(
    dialect,
    Sequence(dialect, "user_id_seq"),
    restart=1000
)
sql, params = alter_seq.to_sql()
# sql: 'ALTER SEQUENCE "user_id_seq" RESTART WITH 1000'
# params: ()

# Multiple changes
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

`MergeStatement` represents a `MERGE` statement (Upsert).

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

# Define Actions
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

# Merge Statement
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
from rhosocial.activerecord.backend.expression import (
    Column,
    FunctionCall,
    GroupByHavingClause,
)
from rhosocial.activerecord.backend.expression.objects import MaterializedView, Table
from rhosocial.activerecord.backend.expression.statements import CreateMaterializedViewStatement

# Basic CREATE MATERIALIZED VIEW
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

# Materialized view with TABLESPACE (PostgreSQL)
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

`DropMaterializedViewStatement` represents a `DROP MATERIALIZED VIEW` statement.

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

`RefreshMaterializedViewStatement` represents a `REFRESH MATERIALIZED VIEW` statement for refreshing materialized view data.

```python
from rhosocial.activerecord.backend.expression.statements import RefreshMaterializedViewStatement

# Basic refresh
refresh_mv = RefreshMaterializedViewStatement(
    dialect,
    MaterializedView(dialect, "order_counts")
)
sql, params = refresh_mv.to_sql()
# sql: 'REFRESH MATERIALIZED VIEW "order_counts"'
# params: ()

# CONCURRENTLY refresh (PostgreSQL 9.4+, requires unique index)
refresh_mv = RefreshMaterializedViewStatement(
    dialect,
    MaterializedView(dialect, "order_counts"),
    concurrent=True
)
sql, params = refresh_mv.to_sql()
# sql: 'REFRESH MATERIALIZED VIEW CONCURRENTLY "order_counts"'
# params: ()

# WITH DATA/WITH NO DATA option
refresh_mv = RefreshMaterializedViewStatement(
    dialect,
    MaterializedView(dialect, "order_counts"),
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

# Check TABLESPACE support
if dialect.supports_materialized_view_tablespace():
    # Can specify tablespace for materialized view
    pass

# Check storage options support (WITH DATA / WITH NO DATA)
if dialect.supports_with_data_clause():
    # Can spell the WITH [NO] DATA clause
    pass

# Check storage options support
if dialect.supports_materialized_view_storage_options():
    # Can specify storage parameters
    pass
```
