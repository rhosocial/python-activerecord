# SQLite Backend

SQLite is the default database backend included in the rhosocial-activerecord core library. It is a lightweight embedded database, ideal for development, testing, and small-scale applications.

## Overview

The SQLite backend provides:

- **Full CRUD Operations**: Create, Read, Update, Delete
- **Sync and Async APIs**: Both APIs are fully equivalent
- **Expression System**: Support for complex query building
- **Relationship Support**: One-to-one, one-to-many, many-to-many relationships
- **Transaction Management**: Support for nested transactions and savepoints
- **Pragma System**: Complete SQLite PRAGMA support
- **Extension Framework**: Support for FTS5, JSON1, R-Tree, and other extensions

## Version Requirements

- **Minimum Version**: SQLite 3.8.3 (basic CTE support)
- **Recommended Version**: SQLite 3.35.0+ (most modern features supported)

Feature support varies by version; the backend automatically adjusts functionality based on the actual SQLite version.

## Sync and Async APIs

The SQLite backend provides both synchronous and asynchronous implementations:

```python
# Sync API
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database=":memory:")
backend.connect()

# Async API
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

backend = AsyncSQLiteBackend(database=":memory:")
await backend.connect()
```

### Async Dependencies

The async SQLite backend requires `aiosqlite`:

```bash
pip install aiosqlite
```

Or install the complete package:

```bash
pip install rhosocial-activerecord[all]
```

## Documentation

- **[Pragma System](pragma.md)**: SQLite PRAGMA configuration and queries
- **[Extension Framework](extension.md)**: Extension detection and management
- **[Full-Text Search (FTS5)](fts5.md)**: FTS5 full-text search functionality

## Quick Start

### Basic Configuration

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

# In-memory database
backend = SQLiteBackend(database=":memory:")

# File database
backend = SQLiteBackend(database="/path/to/database.db")

# Connect
backend.connect()
```

### Check Version and Features

```python
# Get SQLite version
version = backend.dialect.version
print(f"SQLite Version: {version}")

# Check feature support
if backend.dialect.supports_window_functions():
    print("Window functions supported")

if backend.dialect.supports_fts5():
    print("FTS5 full-text search supported")
```

### Using Pragma

```python
# Get pragma info
info = backend.dialect.get_pragma_info('foreign_keys')
print(f"foreign_keys info: {info}")

# Generate pragma SQL
sql = backend.dialect.get_pragma_sql('journal_mode')
print(f"SQL: {sql}")  # PRAGMA journal_mode

# Generate pragma set SQL
sql = backend.dialect.set_pragma_sql('foreign_keys', 1)
print(f"SQL: {sql}")  # PRAGMA foreign_keys = 1
```

### Detecting Extensions

```python
# Detect all available extensions
extensions = backend.dialect.detect_extensions()
for name, info in extensions.items():
    status = "available" if info.installed else "not available"
    print(f"{name}: {status}")

# Check specific extension
if backend.dialect.is_extension_available('fts5'):
    print("FTS5 extension available")

# Check extension feature
if backend.dialect.check_extension_feature('fts5', 'trigram_tokenizer'):
    print("FTS5 trigram tokenizer available")
```

## Data Type Mapping

SQLite uses a dynamic type system; the backend handles type conversion automatically:

| SQLite Type | Python Type |
|------------|------------|
| INTEGER | int |
| REAL | float |
| TEXT | str |
| BLOB | bytes |
| NULL | None |

Additionally, the backend supports special types:

| Python Type | SQLite Storage | Notes |
|------------|------------|------|
| datetime.datetime | TEXT (ISO8601) | Auto-serialized |
| datetime.date | TEXT (ISO8601) | Auto-serialized |
| uuid.UUID | TEXT (36 chars) | Auto-serialized |
| decimal.Decimal | TEXT | Exact numeric |
| dict/list | TEXT (JSON) | Requires JSON1 extension |

## Transaction Support

The SQLite backend supports complete transaction management:

```python
# Manual transaction
with backend.transaction():
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))

# Nested transactions (savepoints)
with backend.transaction():
    backend.execute("INSERT INTO users (name) VALUES (?)", ("Alice",))
    with backend.transaction():  # Creates savepoint
        backend.execute("INSERT INTO users (name) VALUES (?)", ("Bob",))
```

## Limitations

1. **Concurrency**: SQLite uses file locking; write concurrency is limited
2. **Network Storage**: Not recommended for network storage (e.g., NFS)
3. **RIGHT/FULL JOIN**: SQLite does not support RIGHT JOIN and FULL JOIN
4. **Database Size**: SQLite database files support up to 281 TB

## Command Line Tool

The SQLite backend provides a command-line tool for quick testing and environment inspection:

### Execute SQL Queries

```bash
# Execute SQL query (using in-memory database)
python -m rhosocial.activerecord.backend.impl.sqlite "SELECT sqlite_version();"

# Use database file
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my.db "SELECT * FROM users;"

# Execute SQL from file
python -m rhosocial.activerecord.backend.impl.sqlite --file script.sql

# Execute multi-statement script
python -m rhosocial.activerecord.backend.impl.sqlite --executescript --file dump.sql
```

### Environment Information

Use `--info` to inspect the current SQLite environment:

```bash
# Show basic info (protocol family overview)
python -m rhosocial.activerecord.backend.impl.sqlite --info

# Show verbose info (includes specific protocol support)
python -m rhosocial.activerecord.backend.impl.sqlite --info -v

# Show full details (includes each protocol method status)
python -m rhosocial.activerecord.backend.impl.sqlite --info -vv

# JSON format output
python -m rhosocial.activerecord.backend.impl.sqlite --info --output json
```

The `--info` output includes:

- **SQLite Version**: Current SQLite version number
- **Extension Support**: Availability of FTS5, JSON1, R-Tree, etc.
- **Pragma System**: Count of pragmas in each category
- **Protocol Support**: Backend protocol implementation status grouped by functionality

### Output Formats

```bash
# Table format (default, requires rich library)
python -m rhosocial.activerecord.backend.impl.sqlite --output table "SELECT 1;"

# JSON format
python -m rhosocial.activerecord.backend.impl.sqlite --output json "SELECT 1;"

# CSV format
python -m rhosocial.activerecord.backend.impl.sqlite --output csv "SELECT * FROM users;"

# TSV format
python -m rhosocial.activerecord.backend.impl.sqlite --output tsv "SELECT * FROM users;"
```

> **Recommendation**: Other backends (e.g., MySQL, PostgreSQL) should implement similar command-line tools following this pattern to provide a consistent user experience.
