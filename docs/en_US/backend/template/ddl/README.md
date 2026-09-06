# DDL Operations

## Overview

This section covers DDL (Data Definition Language) operations for the {backend} backend. DDL defines your database schema — tables, indexes, views, and other objects.

**Important**: All DDL in rhosocial-activerecord is **expression-based**. You define your schema in Python, the framework generates the SQL, and you execute it via the backend. The examples below use `ActiveRecord` for brevity, but `AsyncActiveRecord` works identically — the DDL generation is pure computation with no I/O involved.

The DDL chapter is divided into two parts:

1. **Backend DDL Capabilities** — The complete set of DDL operations the {backend} backend supports, expressed through backend-specific expression classes. This is the backend's full power.
2. **ActiveRecord DDL Derivation** — What the framework can automatically generate from model class declarations. This is a convenient subset that covers most common use cases.

---

# Part 1: Backend DDL Capabilities

The {backend} backend supports the following DDL operations. Each operation is expressed through a corresponding expression class — you construct the expression, then execute it via the backend.

## Supported Operations

| Operation | {database} Support | Expression Class |
|-----------|-------------------|-----------------|
| CREATE TABLE | ✅ | `CreateTableExpression` |
| ALTER TABLE | ✅ | `AlterTableExpression` |
| DROP TABLE | ✅ | `DropTableExpression` |
| CREATE INDEX | ✅ | `CreateIndexExpression` |
| DROP INDEX | ✅ | `DropIndexExpression` |
| CREATE VIEW | ✅ | `CreateViewExpression` |
| DROP VIEW | ✅ | `DropViewExpression` |
| TRUNCATE | ✅ | `TruncateExpression` |
| CREATE SCHEMA | ✅/{database}-specific | `CreateSchemaExpression` |
| CREATE SEQUENCE | {database}-specific | `CreateSequenceExpression` |
| CREATE MATERIALIZED VIEW | ✅ | `CreateMaterializedViewExpression` |
| PARTITION DDL | ✅ | Backend-specific classes |

## CREATE TABLE

### Basic Usage

```python
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression,
    ColumnDefinition,
    ColumnConstraint,
    ColumnConstraintType,
)

# Construct a CREATE TABLE expression
# Backend-specific DDL expression
```

### {database}-Specific Table Options

<!-- Document what happens when you use each option. -->

### IF NOT EXISTS

| Backend | IF NOT EXISTS |
|---------|--------------|
| SQLite | Yes |
| MySQL | Yes |
| PostgreSQL | Yes |

### Temporary Tables

| Backend | Temporary Table Support |
|---------|----------------------|
| SQLite | Yes (but limited) |
| MySQL | Yes |
| PostgreSQL | Yes |

## ALTER TABLE

### Adding Columns

| Backend | IF NOT EXISTS on ADD COLUMN |
|---------|--------------------------|
| SQLite | No (before 3.35.0) |
| MySQL | No |
| PostgreSQL | Yes |

### Dropping Columns

| Backend | IF EXISTS on DROP COLUMN | Minimum Version |
|---------|------------------------|----------------|
| SQLite | Yes | 3.35.0+ |
| MySQL | No | — |
| PostgreSQL | Yes | — |

### Renaming Columns

| Backend | RENAME COLUMN |
|---------|--------------|
| SQLite | Yes (3.25.0+) |
| MySQL | No (use `CHANGE COLUMN`) |
| PostgreSQL | Yes |

### Changing Column Types

| Backend | Syntax |
|---------|--------|
| MySQL | `MODIFY COLUMN` or `CHANGE COLUMN` |
| PostgreSQL | `ALTER COLUMN ... TYPE` |
| SQLite | Limited |

## DROP TABLE

| Backend | IF EXISTS | CASCADE/RESTRICT |
|---------|----------|-----------------|
| SQLite | Yes | No |
| MySQL | Yes | Parsed but ignored |
| PostgreSQL | Yes | Yes (default: `RESTRICT`) |

## CREATE INDEX

### Index Types

| Backend | Supported Index Types |
|---------|---------------------|
| SQLite | B-tree only |
| MySQL | BTREE, HASH |
| PostgreSQL | BTREE, HASH, GIN, GiST, SP-GiST, BRIN |

### Partial Indexes

| Backend | Partial Index Support |
|---------|---------------------|
| SQLite | Yes (since 3.8.0) |
| MySQL | No |
| PostgreSQL | Yes |

### Functional Indexes

| Backend | Functional Index Support |
|---------|------------------------|
| SQLite | Yes |
| MySQL | No |
| PostgreSQL | Yes |

### Concurrent Index Creation

| Backend | CONCURRENTLY Support |
|---------|---------------------|
| SQLite | No |
| MySQL | No |
| PostgreSQL | Yes |

### Full-Text Indexes

| Backend | Full-Text Index Syntax |
|---------|----------------------|
| SQLite | FTS5 virtual table |
| MySQL | `FULLTEXT INDEX` (InnoDB, MySQL 5.6+) |
| PostgreSQL | GIN index on `tsvector` column |

## CREATE VIEW

| Backend | OR REPLACE | TEMPORARY | Materialized | WITH CHECK OPTION |
|---------|-----------|----------|-------------|------------------|
| SQLite | No | No | No | No |
| MySQL | Yes | Yes | No | Yes |
| PostgreSQL | Yes | Yes | Yes | Yes |

## TRUNCATE

| Backend | Supported | RESTART IDENTITY | CASCADE |
|---------|----------|-----------------|---------|
| SQLite | No (use `DELETE FROM`) | N/A | N/A |
| MySQL | Yes | No | No |
| PostgreSQL | Yes | Yes | Yes |

## Schema Support

| Backend | Schemas | CREATE/DROP SCHEMA |
|---------|---------|-------------------|
| SQLite | No | No |
| MySQL | No (schema = database) | `CREATE DATABASE` (synonym) |
| PostgreSQL | Yes (true namespaces) | Yes |

## Sequences

| Backend | Sequences | AUTO_INCREMENT Mechanism |
|---------|----------|------------------------|
| SQLite | No | `AUTOINCREMENT` on `INTEGER PRIMARY KEY` |
| MySQL | No | `AUTO_INCREMENT` column attribute |
| PostgreSQL | Yes (`SERIAL`, `IDENTITY`) | `SERIAL` or `GENERATED ... AS IDENTITY` |

## Partitioning

| Backend | Partitioning | Strategies |
|---------|-------------|------------|
| SQLite | **No** | — |
| MySQL | Yes (5.1+) | RANGE, LIST, HASH, KEY, COLUMNS, subpartitioning |
| PostgreSQL | Yes (PG 10+) | RANGE, LIST, HASH |

> **Note**: Partition DDL is not integrated into the model declaration layer. You must use backend-specific expression classes directly. See [Partitioning](../backend_specific_features/partition.md) for details.

## Backend-Specific Expression Classes

### MySQL

| Expression | Purpose |
|-----------|---------|
| `MySQLPartitionClause` | Partition DDL |
| `MySQLRenameTableExpression` | Rename table with options |
| `MySQLAnalyzeTableExpression` | ANALYZE TABLE |
| `MySQLLoadDataExpression` | LOAD DATA INFILE |

### PostgreSQL

| Expression | Purpose |
|-----------|---------|
| `PostgresCreatePartitionExpression` | Create partition |
| `PostgresDetachPartitionExpression` | Detach partition |
| `PostgresRefreshMaterializedViewExpression` | Refresh materialized view |
| `PostgresCreateExtensionExpression` | CREATE EXTENSION |
| `PostgresVacuumExpression` | VACUUM |
| `PostgresCommentExpression` | COMMENT ON |

## Checking Feature Support

Use the protocol system to check if a feature is available:

```python
from rhosocial.activerecord.backend.dialect.protocols import (
    TableSupport,
    IndexSupport,
    SchemaSupport,
    PartitionSupport,
)

dialect = backend.dialect

if isinstance(dialect, PartitionSupport):
    if dialect.supports_table_partitioning():
        # Use partition DDL expression classes
        ...

if isinstance(dialect, IndexSupport):
    if dialect.supports_partial_index():
        # Create partial indexes
        ...
```

## What Happens with Unsupported Features

When you use a feature on a backend that does not support it:

| Feature | SQLite | MySQL | PostgreSQL |
|---------|--------|-------|------------|
| `ENGINE=InnoDB` | Ignored | Applied | Ignored |
| `CHARSET=utf8mb4` | Ignored | Applied | Ignored |
| `TABLESPACE` | Ignored | Ignored | Applied |
| `PARTITION BY` | Error | Applied | Applied |
| `GIN` index type | Error | Error | Applied |
| `CONCURRENTLY` | Error | Error | Applied |
| `SERIAL` type | Maps to `INTEGER` | Maps to `INT` | Applied |

**Rule of thumb**: Options that are structural (like `ENGINE`) are silently ignored if unsupported. Options that change SQL syntax (like `GIN` index type) raise errors if unsupported.

---

# Part 2: ActiveRecord DDL Derivation

`ModelSchemaGenerator` derives DDL from your ActiveRecord model declarations. You define fields, table names, indexes, and constraints on the model class — the framework generates the SQL.

This is a convenient subset of the backend's full DDL capabilities. For features not covered here (partitioning, sequences, triggers, stored procedures), use the backend's expression classes directly (Part 1).

## What Can Be Derived from Models

| Feature | Model-Integrated | How to Use |
|---------|-----------------|------------|
| Table creation | Yes | `ModelSchemaGenerator.generate_create_table()` |
| Column definitions | Yes | Declare fields on the model class |
| Indexes | Yes | `indexes()` class method |
| Constraints | Yes | `UseConstraint` annotations |
| Engine / CHARSET (MySQL) | Yes | `engine()`, `charset()` class methods |
| Table comment | Yes | `comment()` class method |
| Schema | Yes | `schema()` class method |
| Partitioning | **No** | Backend-specific expression classes only |
| Sequences | **No** | Backend-specific expression classes only |
| Triggers | **No** | Backend-specific expression classes only |
| Stored procedures | **No** | Backend-specific expression classes only |

## Creating a Table

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from typing import ClassVar

class User(ActiveRecord):
    id: int | None = None
    username: str
    email: str
    age: int
    is_active: bool = True
    metadata: dict = {}

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'
```

The generated SQL differs per backend:

| Backend | Generated SQL |
|---------|--------------|
| SQLite | `CREATE TABLE IF NOT EXISTS "users" ("id" INTEGER PRIMARY KEY AUTOINCREMENT, "username" VARCHAR NOT NULL, "email" VARCHAR NOT NULL, "age" INTEGER NOT NULL, "is_active" BOOLEAN NOT NULL DEFAULT 1, "metadata" JSON)` |
| MySQL | ``CREATE TABLE IF NOT EXISTS `users` (`id` INT NOT NULL AUTO_INCREMENT, `username` VARCHAR(255) NOT NULL, `email` VARCHAR(255) NOT NULL, `age` INT NOT NULL, `is_active` BOOLEAN NOT NULL DEFAULT TRUE, `metadata` JSON, PRIMARY KEY (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`` |
| PostgreSQL | `CREATE TABLE IF NOT EXISTS "users" ("id" SERIAL PRIMARY KEY, "username" VARCHAR(255) NOT NULL, "email" VARCHAR(255) NOT NULL, "age" INTEGER NOT NULL, "is_active" BOOLEAN NOT NULL DEFAULT TRUE, "metadata" JSONB)` |

Notice the differences:
- **SQLite**: Uses `AUTOINCREMENT` on `INTEGER PRIMARY KEY`, no `ENGINE` or `CHARSET`
- **MySQL**: Uses `AUTO_INCREMENT` column attribute, `ENGINE=InnoDB`, `DEFAULT CHARSET=utf8mb4`
- **PostgreSQL**: Uses `SERIAL` for auto-increment, `JSONB` for JSON

## Backend-Specific Table Options

### MySQL: ENGINE, CHARSET, COLLATE, COMMENT

```python
class User(ActiveRecord):
    @classmethod
    def engine(cls) -> str:
        return 'InnoDB'

    @classmethod
    def charset(cls) -> str:
        return 'utf8mb4'

    @classmethod
    def collate(cls) -> str:
        return 'utf8mb4_unicode_ci'

    @classmethod
    def comment(cls) -> str:
        return 'User accounts table'
```

**Note**: `ENGINE`, `CHARSET`, `COLLATE` are MySQL-specific. If you use these on PostgreSQL or SQLite, they are silently ignored.

### PostgreSQL: TABLESPACE, WITH (storage options)

```python
class User(ActiveRecord):
    @classmethod
    def tablespace(cls) -> str:
        return 'fast_storage'

    @classmethod
    def storage_parameters(cls) -> dict:
        return {'fillfactor': 90}
```

**Note**: `TABLESPACE` and `WITH` are PostgreSQL-specific. MySQL ignores these options.

## Indexes

### Basic Index

```python
class User(ActiveRecord):
    email: str

    @classmethod
    def indexes(cls) -> list:
        return [
            {'columns': ['email']},
        ]
```

### Unique Index

```python
{'columns': ['email'], 'unique': True}
```

### Partial Index

```python
{'columns': ['status'], 'where': "status = 'pending'"}
```

| Backend | Partial Index Support |
|---------|---------------------|
| SQLite | Yes |
| MySQL | No |
| PostgreSQL | Yes |

### Index Type

```python
{'columns': ['tags'], 'type': 'GIN'}  # PostgreSQL only
{'columns': ['data'], 'type': 'BTREE'}  # MySQL
```

## Schema

```python
class User(ActiveRecord):
    @classmethod
    def schema(cls) -> str:
        return 'public'  # PostgreSQL
```

**Note**: If you set `schema()` on SQLite, it is silently ignored. On MySQL, it maps to `USE database`. On PostgreSQL, it produces schema-qualified table names.

## Generating DDL SQL

You can generate DDL SQL without executing it:

```python
from rhosocial.activerecord.base.ddl_generator import DDLGenerator

class User(ActiveRecord):
    id: int | None = None
    username: str
    email: str

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'

# Generate CREATE TABLE SQL
create_sql = DDLGenerator.generate_create_table(User)
print(create_sql)
```

This generates the SQL for the currently configured backend's dialect.

## Running DDL

To execute DDL, use the backend directly:

```python
# Sync
with User.connection() as conn:
    conn.execute(create_sql)

# Async
async with User.connection() as conn:
    await conn.execute(create_sql)
```

Or use the DDL generator's built-in execution:

```python
# This generates and executes in one step
DDLGenerator.create_table(User)
```

---

## See Also

- [Field Types](../backend_specific_features/field_types.md) — DataType hierarchy and backend-specific types
- [Indexing](../backend_specific_features/indexing.md) — index types and optimization
- [Partitioning](../backend_specific_features/partition.md) — table partitioning strategies
- [Dialect Expressions](../backend_specific_features/dialect.md) — feature detection and protocol system
- [Core: DDL](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/ddl)

💡 *AI Prompt:* "How does DDL generation differ between MySQL and PostgreSQL?"
