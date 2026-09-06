# Introduction

## {database} Backend Overview

`rhosocial-activerecord-{backend}` is the {database} database backend implementation for the rhosocial-activerecord core library. It provides complete ActiveRecord pattern support, optimized specifically for {database} database features.

## Synchronous and Asynchronous

The {backend} backend provides both synchronous and asynchronous APIs that are functionally equivalent. The documentation will use synchronous examples throughout, but the asynchronous API usage is identical — just replace method calls with their async equivalents.

### Naming Convention

The framework uses a consistent naming convention across all backends:

| Component | Sync | Async |
|-----------|------|-------|
| Backend class | `{Backend}Backend` | `Async{Backend}Backend` |
| Transaction manager | `{Backend}TransactionManager` | `Async{Backend}TransactionManager` |
| Connection config | `{Backend}ConnectionConfig` | `{Backend}ConnectionConfig` (shared) |
| Dialect | `{Backend}Dialect` | `{Backend}Dialect` (shared) |

The connection config and dialect are shared between sync and async — they are pure data objects, not active connections.

### Model Layer

The model layer provides two base classes with identical method names but different calling conventions:

| Operation | `ActiveRecord` (sync) | `AsyncActiveRecord` (async) |
|-----------|----------------------|----------------------------|
| Find one | `find_one()` | `async find_one()` |
| Find all | `find_all()` | `async find_all()` |
| Save | `save()` | `async save()` |
| Delete | `delete()` | `async delete()` |
| Query builder | `.query()` → `ActiveQuery` | `.query()` → `AsyncActiveQuery` |

The method names are **identical** — there is no `a` prefix convention. The distinction is at the class level, not the method level.

### Configuration

```python
# Synchronous
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.{backend} import {Backend}Backend, {Backend}ConnectionConfig

class User(ActiveRecord):
    ...

User.configure({Backend}ConnectionConfig(...), {Backend}Backend)
user = User.find_one(1)

# Asynchronous
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.backend.impl.{backend} import Async{Backend}Backend, {Backend}ConnectionConfig

class User(AsyncActiveRecord):
    ...

User.configure({Backend}ConnectionConfig(...), Async{Backend}Backend)
user = await User.find_one(1)
```

### Async Driver Requirements

Each backend uses a specific async driver. Some backends use the same library for both sync and async; others require a separate async package:

| Backend | Sync Driver | Async Driver | Notes |
|---------|-------------|--------------|-------|
| MySQL | `mysql-connector-python` | `mysql.connector.aio` | Same package, sub-module |
| PostgreSQL | `psycopg` | `psycopg` (AsyncConnection) | Same library, async API |
| MariaDB | `mariadb` | `mariadb` (asyncConnect) | Same library, v2.0.0+ |
| SQL Server | `pyodbc` | `aioodbc` | Separate async wrapper |
| Oracle | `oracledb` | `oracledb` (thin mode) | Same library, native async |

**Important**: Some backends lazy-load their async components to avoid requiring async driver packages when only the sync API is used. If you import `Async{Backend}Backend` and the async driver is not installed, you will get an `ImportError` at import time.

## Quick Links

- **[Relationship with Core Library](./relationship.md)**: Learn how the {backend} backend works with the core library
- **[Supported Versions](./supported_versions.md)**: View supported {database}, Python, and dependency versions

## Known Limitations and Quirks

Every database has its own behavior that differs from the SQL standard. This section documents {database}-specific quirks that may surprise you.

<!-- Fill in the section below with backend-specific quirks. Examples for common backends:

### MySQL

| Quirk | Description |
|-------|-------------|
| No RETURNING clause | MySQL does not support RETURNING. Use `ON DUPLICATE KEY UPDATE` for upserts. |
| No MERGE statement | Use `INSERT ... ON DUPLICATE KEY UPDATE` or `REPLACE INTO` instead. |
| affected_rows for upserts | `ON DUPLICATE KEY UPDATE` returns affected_rows=2 when an update occurs (1 for insert). |
| UPDATE with no change | `UPDATE` that sets a column to its current value returns affected_rows=0 (not 1). |
| NO_BACKSLASH_ESCAPES | When this SQL mode is active, backslash is treated as a literal character. |
| lastrowid for batch inserts | `lastrowid` is only reliable for single-row inserts with auto-increment. |

### PostgreSQL

| Quirk | Description |
|-------|-------------|
| SERIAL vs IDENTITY | `SERIAL` creates a sequence implicitly; `IDENTITY` (10+) is the SQL standard approach. |
| Single ON CONFLICT | PostgreSQL allows only one `ON CONFLICT` clause per INSERT statement. |
| RETURNING with affected_rows | When RETURNING is used, `affected_rows` from `cursor.rowcount` may be 0 — data is in the result set. |
| SERIALIZABLE uses predicate locking | True serializability, not just snapshot isolation. May raise serialization failures. |
| Async single-connection | `psycopg` async backend cannot use `asyncio.gather` for concurrency within the same connection. |

### SQLite

| Quirk | Description |
|-------|-------------|
| Limited ALTER TABLE | No ALTER COLUMN; RENAME COLUMN requires 3.25.0+; DROP COLUMN requires 3.35.0+ |
| NOT NULL without DEFAULT | Cannot add NOT NULL column without DEFAULT (unless STRICT tables in 3.37.0+) |
| DELETE FROM doesn't reclaim space | Use VACUUM to reclaim space; VACUUM cannot run inside a transaction |
| AUTOINCREMENT | Only on `INTEGER PRIMARY KEY`; prevents rowid reuse but increases storage |
| No CASCADE/RESTRICT | DROP TABLE does not support CASCADE or RESTRICT keywords |
| Type affinity | All string types (CHAR/VARCHAR/TEXT) have TEXT affinity |

### SQL Server

| Quirk | Description |
|-------|-------------|
| @@IDENTITY vs SCOPE_IDENTITY() | The backend uses @@IDENTITY, which may return trigger-generated values |
| OUTPUT clause | SQL Server uses OUTPUT instead of RETURNING for retrieving DML results |
| OFFSET FETCH requires 2012+ | Pre-2012 versions need ROW_NUMBER() for pagination |
| SET NOCOUNT ON | When enabled, cursor.rowcount may return -1 |

### Oracle

| Quirk | Description |
|-------|-------------|
| ROWNUM for pagination | Pre-12c uses ROWNUM (no offset support); 12c+ uses FETCH FIRST/OFFSET |
| Sequences for auto-increment | Use NEXTVAL/CURRVAL; sequences are not owned by table columns |
| RETURNING INTO syntax | Requires output bind variables, not simple RETURNING |
| Empty string = NULL | Oracle treats empty strings as NULL |
| No native BOOLEAN | Emulated via adapter (typically 1/0) |
| CURRVAL requires NEXTVAL | Must call NEXTVAL before CURRVAL in a session |

### MariaDB

| Quirk | Description |
|-------|-------------|
| RETURNING not for UPDATE | RETURNING works for INSERT/DELETE/REPLACE (10.5+) but NOT for UPDATE |
| REPLACE INTO changes AUTO_INCREMENT | Deletes and re-inserts rows, changing AUTO_INCREMENT values |
| System-versioned tables | 10.3+ supports `WITH SYSTEM VERSIONING` for temporal data |
| OR REPLACE | Supports `CREATE OR REPLACE` for tables, triggers, and routines |
| Version boundaries differ from MySQL | CTEs since 10.2, window functions since 10.2, etc. |

-->

💡 *AI Prompt:* "What is the ActiveRecord pattern? How does it differ from DataMapper pattern?"
