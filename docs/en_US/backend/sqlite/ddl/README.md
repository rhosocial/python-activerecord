# DDL Operations

## Overview

This section covers DDL (Data Definition Language) operations for the SQLite backend. All DDL in rhosocial-activereord is expression-based — you define your schema in Python, the framework generates the SQL, and you execute it via the backend.

SQLite has significant DDL limitations compared to other databases. This chapter documents what is supported and the workarounds available.

## Supported Operations

| Operation | SQLite Support | Notes |
|-----------|---------------|-------|
| CREATE TABLE | Yes | Including IF NOT EXISTS, temporary tables |
| ALTER TABLE | Limited | No ALTER COLUMN; limited RENAME/DROP |
| DROP TABLE | Yes | No CASCADE/RESTRICT support |
| CREATE INDEX | Yes | B-tree only; supports partial and functional indexes |
| DROP INDEX | Yes | Supports IF EXISTS |
| CREATE VIEW | Yes | No OR REPLACE, no materialized views |
| DROP VIEW | Yes | Supports IF EXISTS |
| TRUNCATE | No | Use DELETE FROM + VACUUM |
| CREATE SCHEMA | No | SQLite has no schema concept |
| CREATE SEQUENCE | No | Use AUTOINCREMENT instead |

## CREATE TABLE

SQLite supports CREATE TABLE with IF NOT EXISTS. The backend generates SQLite-specific DDL:

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

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return 'users'
```

Generated SQL for SQLite:

```sql
CREATE TABLE IF NOT EXISTS "users" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT,
    "username" VARCHAR NOT NULL,
    "email" VARCHAR NOT NULL,
    "age" INTEGER NOT NULL,
    "is_active" BOOLEAN NOT NULL DEFAULT 1
)
```

Key SQLite differences:
- Uses `AUTOINCREMENT` on `INTEGER PRIMARY KEY` (not a column attribute)
- No ENGINE, CHARSET, or COLLATE options
- Boolean values stored as INTEGER (0/1)

## ALTER TABLE

SQLite's ALTER TABLE support is significantly limited compared to other databases:

### Adding Columns

```python
# Supported — but no IF NOT EXISTS before SQLite 3.35.0
ALTER TABLE users ADD COLUMN phone VARCHAR
```

### Renaming Columns

Requires SQLite 3.25.0+:

```python
# SQLite 3.25.0+
ALTER TABLE users RENAME COLUMN phone TO telephone
```

### Dropping Columns

Requires SQLite 3.35.0+:

```python
# SQLite 3.35.0+
ALTER TABLE users DROP COLUMN phone
```

### What Is NOT Supported

| Operation | SQLite | MySQL | PostgreSQL |
|-----------|--------|-------|------------|
| ALTER COLUMN (type change) | No | MODIFY COLUMN | ALTER COLUMN ... TYPE |
| ALTER COLUMN (rename) | No | CHANGE COLUMN | ALTER COLUMN ... RENAME |
| ADD COLUMN with IF NOT EXISTS | No (< 3.35.0) | No | Yes |
| DROP COLUMN with IF EXISTS | No (< 3.35.0) | No | Yes |

For column type changes in SQLite, you typically need to create a new table, copy data, drop the old table, and rename the new table.

## DROP TABLE

```python
# Basic drop
DROP TABLE users

# With IF EXISTS
DROP TABLE IF EXISTS users
```

SQLite does not support CASCADE or RESTRICT keywords. If you pass them, they are silently ignored.

## CREATE INDEX

SQLite supports B-tree indexes with partial and functional index capabilities:

```python
# Basic index
CREATE INDEX idx_users_email ON users(email)

# Unique index
CREATE UNIQUE INDEX idx_users_email ON users(email)

# Partial index (SQLite 3.8.0+)
CREATE INDEX idx_active_users ON users(email) WHERE is_active = 1

# Functional index
CREATE INDEX idx_users_lower_email ON users(lower(email))
```

| Index Feature | SQLite | MySQL | PostgreSQL |
|--------------|--------|-------|------------|
| B-tree | Yes | Yes | Yes |
| HASH | No | Yes | Yes |
| GIN/GiST/BRIN | No | No | Yes |
| Partial indexes | Yes | No | Yes |
| Functional indexes | Yes | No | Yes |
| CONCURRENTLY | No | No | Yes |

## Schema Support

SQLite has no schema or namespace concept. If you set `schema()` on an ActiveRecord model, it is silently ignored.

## Sequences

SQLite does not support sequences. Instead, use `AUTOINCREMENT` on `INTEGER PRIMARY KEY`:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)
```

Note that AUTOINCREMENT prevents rowid reuse and increases storage overhead. For most cases, omitting AUTOINCREMENT and relying on the implicit rowid behavior is sufficient.

## Running DDL

```python
# Generate DDL SQL without executing
from rhosocial.activerecord.base.ddl_generator import DDLGenerator

create_sql = DDLGenerator.generate_create_table(User)
print(create_sql)

# Execute DDL via backend
with User.connection() as conn:
    conn.execute(create_sql)

# Or generate and execute in one step
DDLGenerator.create_table(User)
```

## See Also

- [Backend Specific Features](../backend_specific_features/README.md) — SQLite-specific capabilities
- [Type Adapters](../type_adapters/README.md) — type mapping
- [Core: DDL](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/ddl)

💡 *AI Prompt:* "How do I rename a column in SQLite when ALTER TABLE is limited?"
