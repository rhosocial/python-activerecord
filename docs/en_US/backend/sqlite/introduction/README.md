# Introduction

## SQLite Backend Overview

The SQLite backend is included in the `rhosocial-activerecord` core library — no separate package is needed. SQLite is a lightweight embedded database that requires no server process, making it ideal for development, testing, mobile applications, and small-to-medium workloads.

### What the SQLite Backend Provides

- Full CRUD operations with the ActiveRecord pattern
- Sync and async APIs with identical method signatures
- Expression system for complex query building
- Relationships (one-to-one, one-to-many, many-to-many)
- Transaction management with savepoints
- PRAGMA system for database configuration
- Extension framework (FTS5, JSON1, R-Tree, Geopoly)
- Database introspection for metadata queries

### Version Requirements

| Requirement | Version |
|-------------|---------|
| Minimum SQLite | 3.8.3 (basic CTE support) |
| Recommended SQLite | 3.35.0+ (RETURNING, DROP COLUMN, modern features) |
| Python | 3.8+ |

Feature availability varies by SQLite version. The backend automatically detects the runtime version and adjusts capabilities accordingly.

## Synchronous and Asynchronous

The SQLite backend provides both synchronous and asynchronous APIs that are functionally equivalent. All examples in this documentation use the synchronous API — the async version uses identical method names with `await`.

### Naming Convention

| Component | Sync | Async |
|-----------|------|-------|
| Backend class | `SQLiteBackend` | `AsyncSQLiteBackend` |
| Transaction manager | `SQLiteTransactionManager` | `AsyncSQLiteTransactionManager` |
| Connection config | `SQLiteConnectionConfig` | `SQLiteConnectionConfig` (shared) |
| Dialect | `SQLiteDialect` | `SQLiteDialect` (shared) |

The connection config and dialect are shared between sync and async — they are pure data objects, not active connections.

### Model Layer

| Operation | `ActiveRecord` (sync) | `AsyncActiveRecord` (async) |
|-----------|----------------------|----------------------------|
| Find one | `find_one()` | `async find_one()` |
| Find all | `find_all()` | `async find_all()` |
| Save | `save()` | `async save()` |
| Delete | `delete()` | `async delete()` |

### Configuration

```python
# Synchronous
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

class User(ActiveRecord):
    ...

User.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
user = User.find_one(1)

# Asynchronous
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend, SQLiteConnectionConfig

class User(AsyncActiveRecord):
    ...

User.configure(SQLiteConnectionConfig(database=":memory:"), AsyncSQLiteBackend)
user = await User.find_one(1)
```

### Async Driver Requirements

The async SQLite backend requires `aiosqlite`:

```bash
pip install aiosqlite
```

Or install the complete package with all optional dependencies:

```bash
pip install rhosocial-activerecord[all]
```

If you import `AsyncSQLiteBackend` and `aiosqlite` is not installed, you will get an `ImportError` at import time.

## Quick Start

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

# In-memory database (great for testing)
backend = SQLiteBackend(database=":memory:")
backend.connect()

# File-based database
backend = SQLiteBackend(database="/path/to/database.db")
backend.connect()

# Check SQLite version
version = backend.dialect.version
print(f"SQLite Version: {version}")

# Check feature support
if backend.dialect.supports_window_functions():
    print("Window functions supported")

backend.disconnect()
```

## Known Limitations and Quirks

| Quirk | Description |
|-------|-------------|
| Limited ALTER TABLE | No ALTER COLUMN; RENAME COLUMN requires 3.25.0+; DROP COLUMN requires 3.35.0+ |
| NOT NULL without DEFAULT | Cannot add NOT NULL column without DEFAULT (unless STRICT tables in 3.37.0+) |
| DELETE FROM doesn't reclaim space | Use VACUUM to reclaim space; VACUUM cannot run inside a transaction |
| AUTOINCREMENT | Only on `INTEGER PRIMARY KEY`; prevents rowid reuse but increases storage |
| No CASCADE/RESTRICT | DROP TABLE does not support CASCADE or RESTRICT keywords |
| Type affinity | All string types (CHAR/VARCHAR/TEXT) have TEXT affinity |
| No RIGHT/FULL JOIN | SQLite does not support RIGHT JOIN and FULL JOIN |
| Concurrency | File locking limits write concurrency |
| Network storage | Not recommended for NFS or similar network filesystems |

💡 *AI Prompt:* "What is the ActiveRecord pattern? How does it differ from DataMapper pattern?"
