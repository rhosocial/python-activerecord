# DDL Statements

`rhosocial-activerecord` provides a type-safe, expression-based API for building DDL (Data Definition Language) statements. Instead of writing raw SQL strings, you can construct tables, indexes, views, and schemas using Python objects.

> This chapter describes explicit DDL expression construction and rendering. To read DDL declarations from an ActiveRecord model, see [DDLSource Declarations](ddl_source.md). The current `DDLSourceMixin` only collects and presents declarations; it does not generate or execute DDL automatically.

## Why Use DDL Expressions?

- **Type Safety**: All column names, types, and constraints are validated at runtime.
- **Backend Portability**: The same code works across SQLite, MySQL, PostgreSQL (dialect handles differences).
- **SQL Inspection**: Call `.to_sql()` on any expression to inspect the generated SQL before execution.
- **No String Concatenation**: Eliminates SQL injection risks and syntax errors.

## Core Components

### ColumnDefinition

Defines a column with its data type and optional constraints. The data type is a
`DataType` object, not a string: the dialect is what knows how a type is spelled.

```python
from rhosocial.activerecord.backend.expression import ColumnDefinition
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnDefaultConstraint,
    ColumnNotNullConstraint,
    ColumnUniqueConstraint,
)

# Basic column
ColumnDefinition(dialect, "name", VarCharType(dialect, length=100))
# sql: '"name" TEXT'   (SQLite adapts VARCHAR to TEXT)

# Column with constraints
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

# A DEFAULT is a constraint branch, not a keyword argument
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

A column constraint is two levels, mirroring the grammar: `ColumnConstraint` is
the *clause* (the `CONSTRAINT <name>` prefix and the trailing traits) and each
alternative is a *branch* it refers to. A branch cannot be written on its own,
and a trait a branch's kind cannot carry is refused at construction time rather
than dropped at render time.

| Branch | Renders |
|--------|---------|
| `ColumnPrimaryKeyConstraint` | `PRIMARY KEY` (SQLite adds `AUTOINCREMENT` when `is_auto_increment=True`) |
| `ColumnUniqueConstraint` | `UNIQUE` |
| `ColumnNotNullConstraint` | `NOT NULL` |
| `ColumnNullableConstraint` | `NULL` |
| `ColumnDefaultConstraint` | `DEFAULT <value>` |
| `ColumnCheckConstraint` | `CHECK (<condition>)` |
| `ColumnForeignKeyConstraint` | `REFERENCES <table> (<columns>)` |
| `ColumnGeneratedConstraint` | `GENERATED ALWAYS AS (<expression>) [STORED\|VIRTUAL]` |

The clause also carries the traits the standard allows on a constraint:

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
# sql: ' CONSTRAINT "uq_users_email" UNIQUE'   (leading space: the clause is appended to a column)

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

Each trait is a pair of mutually exclusive flags, and each is gated twice:

| Trait | Flags | Authorised by | Branches that carry it |
|-------|-------|---------------|------------------------|
| Name | `name=` | `supports_constraint_naming` | every branch |
| Deferral | `deferrable` / `not_deferrable` | `supports_deferrable_constraint` | PRIMARY KEY, UNIQUE, FOREIGN KEY |
| Timing | `initially_deferred` / `initially_immediate` | `supports_deferrable_constraint` | PRIMARY KEY, UNIQUE, FOREIGN KEY |
| Enforcement | `enforced` / `not_enforced` | `supports_constraint_enforcement` | PRIMARY KEY, UNIQUE, FOREIGN KEY, CHECK |

Both flags of a pair at once, or a trait on a branch whose kind has no meaning
for it, is an error at construction:

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

A dialect that cannot spell an accepted trait refuses at render time, so a
statement never silently loses a constraint the caller asked for:

```python
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

try:
    ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect), enforced=True).to_sql()
except UnsupportedFeatureError as exc:
    print(exc)  # 'SQLite' dialect does not support ENFORCED/NOT ENFORCED constraint.
```

### TableConstraint

Defines table-level constraints like primary keys, unique constraints, and foreign keys. It follows the same clause/branch split as `ColumnConstraint`.

```python
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    ReferentialAction,
    TableConstraint,
    TableForeignKeyConstraint,
    TablePrimaryKeyConstraint,
)

# Composite primary key
TableConstraint(
    dialect,
    branch=TablePrimaryKeyConstraint(dialect, ["user_id", "role_id"]),
)
# sql: 'PRIMARY KEY ("user_id", "role_id")'

# Foreign key with referential actions
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


## Basic Operations

### Create Table

A table is named by a `Table` object; the statement takes it positionally.

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

### Create Table with IF NOT EXISTS

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

### Create Temporary Table

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

### Drop Table

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

`cascade=True` is authorised by `supports_drop_table_cascade`, so SQLite — which
has neither `CASCADE` nor `RESTRICT` on `DROP TABLE` — refuses rather than
dropping the clause:

```python
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

try:
    DropTableStatement(dialect, Table(dialect, "old_users"), cascade=True).to_sql()
except UnsupportedFeatureError as exc:
    print(exc)  # 'SQLite' dialect does not support DROP TABLE ... CASCADE.
```

### Alter Table

Each action is its own node; the statement holds the list.

```python
from rhosocial.activerecord.backend.expression import (
    AlterTableStatement,
    AddColumnAction,
    DropColumnAction
)

# Add a new column
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

# Drop a column
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


## Index Operations

### Create Index

The index and the table are both named objects, and the columns are a plain list
of names.

```python
from rhosocial.activerecord.backend.expression import StringColumn
from rhosocial.activerecord.backend.expression.objects import Index, Table
from rhosocial.activerecord.backend.expression.statements import CreateIndexStatement

# Basic index
create_idx = CreateIndexStatement(
    dialect,
    Index(dialect, "idx_users_email"),
    Table(dialect, "users"),
    columns=["email"]
)
sql, params = create_idx.to_sql()
# sql: 'CREATE INDEX "idx_users_email" ON "users" ("email")'

# Unique index
create_idx = CreateIndexStatement(
    dialect,
    Index(dialect, "idx_users_username"),
    Table(dialect, "users"),
    columns=["username"],
    unique=True
)

# Partial index (with WHERE clause) -- the predicate is built by a typed column
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

> Predicates come from a column class that can be compared, not from `==` on a
> bare `Column`: `Column` carries only aliasing, null tests and casting, so
> `Column(...) == ...` is a Python identity test. Use `StringColumn`,
> `NumericColumn` and their siblings for anything a predicate compares.

### Drop Index

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

## Schema Operations

### Create Schema

A schema is a `Schema` object. SQLite has no schemas, so its dialect refuses the
statement rather than emitting something the engine rejects:

```python
from rhosocial.activerecord.backend.expression.objects import Schema
from rhosocial.activerecord.backend.expression.statements import CreateSchemaStatement

create_schema = CreateSchemaStatement(
    dialect,
    Schema(dialect, "app_schema"),
    if_not_exists=True
)
# On a dialect that supports schemas:
# sql: 'CREATE SCHEMA IF NOT EXISTS "app_schema"'
# On SQLite:
# UnsupportedFeatureError: 'SQLite' dialect does not support CREATE SCHEMA.
```

### Drop Schema

```python
from rhosocial.activerecord.backend.expression.statements import DropSchemaStatement

drop_schema = DropSchemaStatement(
    dialect,
    Schema(dialect, "old_schema"),
    cascade=True
)
# On a dialect that supports schemas:
# sql: 'DROP SCHEMA "old_schema" CASCADE'
```


## Executing DDL Statements

A statement renders to `(sql, params)`; the backend executes SQL text, so the
two steps are separate:

```python
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import CreateTableStatement

# Create table
create = CreateTableStatement(
    dialect,
    Table(dialect, "users"),
    columns=columns
)
sql, params = create.to_sql()
backend.execute(sql, params)

# Or build SQL first and inspect
print(f"SQL: {sql}")
print(f"Params: {params}")
```

> **Note**: DDL statements in `rhosocial-activerecord` don't require `ExecutionOptions(stmt_type=StatementType.DDL)` — the expression objects carry their own statement type information.


## Introspection for Schema Verification

After creating, modifying, or deleting tables, you can use the backend's **introspection API** to verify schema changes:

```python
from rhosocial.activerecord.backend.introspection import TableType

# List all tables
tables = backend.introspector.list_tables()
for t in tables:
    print(f"Table: {t.name}, Type: {t.table_type}")

# Get detailed table info (columns, indexes, foreign keys)
table_info = backend.introspector.get_table_info("users")
if table_info:
    for col in table_info.columns:
        print(f"Column: {col.name}, Type: {col.data_type}, PK: {col.is_primary_key}")
```

`TableType` distinguishes the kinds a catalogue reports — `BASE_TABLE`,
`VIEW`, `MATERIALIZED_VIEW`, `FOREIGN_TABLE`, `PARTITIONED_TABLE`,
`SYSTEM_TABLE`, `EXTERNAL` — so a relation is not silently folded into "table".

### Backend-Specific Differences

> ⚠️ **Important**: This documentation uses SQLite as the example backend. Different database backends have significant differences:

| Feature | SQLite | MySQL | PostgreSQL |
|---------|--------|-------|------------|
| **Introspection API** | `list_tables()`, `get_table_info()`, `pragma.*` | Different method names | Different method names |
| **DDL Support** | Limited ALTER TABLE (ADD/DROP column only); no `CREATE SCHEMA` | Full ALTER TABLE | Full ALTER TABLE |
| **Index Types** | No USING clause | BTREE, HASH, etc. | BTREE, HASH, GIN, etc. |
| **Partial Indexes** | Supported (WHERE clause) | Not supported | Supported |
| **Generated Columns** | 3.31.0+ | 5.7.31+ | Supported |
| **Constraint traits** | name and deferral render; `ENFORCED` refused | name renders | all render |

Always refer to your specific backend's documentation for accurate API usage.

## Example Code

Full example code for this chapter can be found at:
[docs/examples/chapter_03_modeling/ddl_basic.py](../../examples/chapter_03_modeling/ddl_basic.py)

More examples:
- [docs/examples/chapter_03_modeling/ddl_relationships.py](../../examples/chapter_03_modeling/ddl_relationships.py) — Creating tables with foreign key relationships
- [docs/examples/chapter_03_modeling/ddl_indexes.py](../../examples/chapter_03_modeling/ddl_indexes.py) — Index creation patterns