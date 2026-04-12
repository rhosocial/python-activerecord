# DDL Statements

`rhosocial-activerecord` provides a type-safe, expression-based API for building DDL (Data Definition Language) statements. Instead of writing raw SQL strings, you can construct tables, indexes, views, and schemas using Python objects.

## Why Use DDL Expressions?

- **Type Safety**: All column names, types, and constraints are validated at runtime.
- **Backend Portability**: The same code works across SQLite, MySQL, PostgreSQL (dialect handles differences).
- **SQL Inspection**: Call `.to_sql()` on any expression to inspect the generated SQL before execution.
- **No String Concatenation**: Eliminates SQL injection risks and syntax errors.

## Core Components

### ColumnDefinition

Defines a column with its data type and optional constraints.

```python
from rhosocial.activerecord.backend.expression import ColumnDefinition
from rhosocial.activerecord.backend.expression.statements import ColumnConstraint, ColumnConstraintType

# Basic column
ColumnDefinition("name", "VARCHAR(100)")

# Column with constraints
ColumnDefinition(
    "email",
    "VARCHAR(255)",
    constraints=[
        ColumnConstraint(ColumnConstraintType.NOT_NULL),
        ColumnConstraint(ColumnConstraintType.UNIQUE)
    ]
)

# Column with default value
ColumnDefinition(
    "status",
    "VARCHAR(20)",
    default="active"
)
```

### ColumnConstraint

| Type | Description |
|------|-------------|
| `NOT_NULL` | Column cannot be NULL |
| `NULL` | Column allows NULL (default) |
| `PRIMARY_KEY` | Primary key column |
| `UNIQUE` | Column values must be unique |
| `AUTO_INCREMENT` | Auto-incrementing (database-dependent) |

### TableConstraint

Defines table-level constraints like primary keys, unique constraints, and foreign keys.

```python
from rhosocial.activerecord.backend.expression.statements import (
    TableConstraint,
    TableConstraintType,
    ForeignKeyConstraint,
    ReferentialAction
)

# Composite primary key
TableConstraint(
    TableConstraintType.PRIMARY_KEY,
    columns=["user_id", "role_id"]
)

# Foreign key with referential actions
ForeignKeyConstraint(
    columns=["author_id"],
    reference_table="authors",
    reference_columns=["id"],
    on_delete=ReferentialAction.CASCADE,
    on_update=ReferentialAction.RESTRICT
)
```

## Basic Operations

### Create Table

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

### Create Table with IF NOT EXISTS

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

### Create Temporary Table

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

### Drop Table

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

### Alter Table

```python
from rhosocial.activerecord.backend.expression import (
    AlterTableExpression,
    AddColumn,
    DropColumn,
    AlterColumn
)

# Add a new column
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

# Drop a column
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

## Index Operations

### Create Index

```python
from rhosocial.activerecord.backend.expression.statement import CreateIndexExpression

# Basic index
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_users_email",
    table_name="users",
    columns=["email"]
)
sql, params = create_idx.to_sql()
# sql: 'CREATE INDEX "idx_users_email" ON "users" ("email")'

# Unique index
create_idx = CreateIndexExpression(
    dialect,
    index_name="idx_users_username",
    table_name="users",
    columns=["username"],
    unique=True
)

# Partial index (with WHERE clause)
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

### Drop Index

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

## Schema Operations

### Create Schema

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

### Drop Schema

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

## Executing DDL Statements

DDL expressions can be executed directly on the backend:

```python
from rhosocial.activerecord.model import ActiveRecord

# Create table
create = CreateTableExpression(dialect, "users", columns)
User.__backend__.execute(create)

# Or build SQL first and inspect
sql, params = create.to_sql()
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

### Backend-Specific Differences

> ⚠️ **Important**: This documentation uses SQLite as the example backend. Different database backends have significant differences:

| Feature | SQLite | MySQL | PostgreSQL |
|---------|--------|-------|------------|
| **Introspection API** | `list_tables()`, `get_table_info()`, `pragma.*` | Different method names | Different method names |
| **DDL Support** | Limited ALTER TABLE (ADD/DROP column only) | Full ALTER TABLE | Full ALTER TABLE |
| **Index Types** | No USING clause | BTREE, HASH, etc. | BTREE, HASH, GIN, etc. |
| **Partial Indexes** | Supported (WHERE clause) | Not supported | Supported |
| **Generated Columns** | 3.31.0+ | 5.7.31+ | Supported |

Always refer to your specific backend's documentation for accurate API usage.

## Example Code

Full example code for this chapter can be found at:
[docs/examples/chapter_03_modeling/ddl_basic.py](../../../examples/chapter_03_modeling/ddl_basic.py)

More examples:
- [docs/examples/chapter_03_modeling/ddl_relationships.py](../../../examples/chapter_03_modeling/ddl_relationships.py) — Creating tables with foreign key relationships
- [docs/examples/chapter_03_modeling/ddl_indexes.py](../../../examples/chapter_03_modeling/ddl_indexes.py) — Index creation patterns