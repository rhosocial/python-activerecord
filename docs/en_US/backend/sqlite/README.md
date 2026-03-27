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
- **Database Introspection**: Complete database metadata query capabilities

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

## Database Introspection

The SQLite backend provides complete database introspection capabilities for querying database structure metadata. For detailed introspection API documentation, see [Database Introspection](../introspection.md).

### Database Information

```python
# Get basic database information
db_info = backend.introspector.get_database_info()
print(f"Database name: {db_info.name}")
print(f"SQLite version: {db_info.version}")
print(f"Database size: {db_info.size_bytes} bytes")
```

### Table Introspection

```python
# List all user tables
tables = backend.introspector.list_tables()
for table in tables:
    print(f"Table: {table.name}, Type: {table.table_type.value}")

# Include system tables
all_tables = backend.introspector.list_tables(include_system=True)
system_tables = [t for t in all_tables if t.table_type.value == "SYSTEM_TABLE"]
print(f"System tables count: {len(system_tables)}")

# Filter by specific type
base_tables = backend.introspector.list_tables(table_type="BASE TABLE")
views = backend.introspector.list_tables(table_type="VIEW")

# Check if table exists
if backend.introspector.table_exists("users"):
    print("users table exists")

# Get detailed table information
table_info = backend.introspector.get_table_info("users")
if table_info:
    print(f"Table name: {table_info.name}")
    print(f"Schema: {table_info.schema}")
```

### Column and Index Information

```python
# List all columns of a table
columns = backend.introspector.list_columns("users")
for col in columns:
    nullable = "NOT NULL" if col.nullable.value == "NOT_NULL" else "NULLABLE"
    pk = " [PK]" if col.is_primary_key else ""
    print(f"{col.name}: {col.data_type} {nullable}{pk}")

# Get primary key information
pk = backend.introspector.get_primary_key("users")
if pk:
    print(f"Primary key: {[c.name for c in pk.columns]}")

# List all indexes
indexes = backend.introspector.list_indexes("users")
for idx in indexes:
    unique = "UNIQUE " if idx.is_unique else ""
    print(f"{unique}Index: {idx.name}")
    for col in idx.columns:
        print(f"  - {col.name}")
```

### Foreign Keys and Views

```python
# List foreign keys
foreign_keys = backend.introspector.list_foreign_keys("posts")
for fk in foreign_keys:
    print(f"FK: {fk.name}")
    print(f"  Columns: {fk.columns} -> {fk.referenced_table}.{fk.referenced_columns}")
    print(f"  ON DELETE: {fk.on_delete.value}")
    print(f"  ON UPDATE: {fk.on_update.value}")

# List views
views = backend.introspector.list_views()
for view in views:
    print(f"View: {view.name}")

# Get view definition
view_info = backend.introspector.get_view_info("user_posts_summary")
if view_info:
    print(f"Definition: {view_info.definition}")
```

### Triggers

```python
# List all triggers
triggers = backend.introspector.list_triggers()
for trigger in triggers:
    print(f"Trigger: {trigger.name} on {trigger.table_name}")

# List triggers for a specific table
table_triggers = backend.introspector.list_triggers("users")
for trigger in table_triggers:
    print(f"Trigger: {trigger.name}")
```

### Async Introspection API

The async backend provides identical introspection methods with the same names as the sync version:

```python
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

backend = AsyncSQLiteBackend(database=":memory:")
await backend.connect()

# Async introspection methods
db_info = await backend.introspector.get_database_info()
tables = await backend.introspector.list_tables()
table_info = await backend.introspector.get_table_info("users")
columns = await backend.introspector.list_columns("users")
indexes = await backend.introspector.list_indexes("users")
foreign_keys = await backend.introspector.list_foreign_keys("posts")
views = await backend.introspector.list_views()
triggers = await backend.introspector.list_triggers()
```

### Cache Management

Introspection results are cached for performance. You can manage the cache:

```python
# Clear all introspection cache
backend.introspector.clear_cache()

# Invalidate specific scope
from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

# Invalidate all table-related cache
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE)

# Invalidate cache for a specific table
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.TABLE,
    name="users"
)
```

### SQLite-Specific: PragmaIntrospector

SQLite introspector provides direct access to PRAGMA directives:

```python
# Access PragmaIntrospector
pragma = backend.introspector.pragma

# Use PRAGMA directives
table_info = pragma.pragma_table_info("users")
index_list = pragma.pragma_index_list("users")
foreign_keys = pragma.pragma_foreign_key_list("posts")
```

## Version Differences

### Introspection Version Differences

SQLite introspection behavior varies by version:

| Feature | SQLite < 3.37.0 | SQLite >= 3.37.0 |
|---------|-----------------|------------------|
| Table list method | `sqlite_master` query | `PRAGMA table_list` |
| System tables in list | Manual detection | Automatic (type='shadow') |
| Column hidden info | `PRAGMA table_info` | `PRAGMA table_xinfo` |

**Important notes**:

- **SQLite < 3.37.0**: System tables (like `sqlite_schema`) are **not stored in `sqlite_master`**. The backend automatically detects and includes known system tables when `include_system=True`.
- **SQLite >= 3.37.0**: `PRAGMA table_list` returns system tables with `type='shadow'`, which is mapped to `TableType.SYSTEM_TABLE`.

### Known SQLite System Tables

| System Table | Description | Existence Condition |
|--------------|-------------|---------------------|
| `sqlite_schema` | Database schema information | Always exists |
| `sqlite_master` | Alias for `sqlite_schema` | Always exists |
| `sqlite_stat1` | Index statistics | After ANALYZE |
| `sqlite_stat2/3/4` | Extended statistics | After ANALYZE in specific versions |
| `sqlite_sequence` | AUTOINCREMENT counter | After using AUTOINCREMENT |

### Version Feature Support Matrix

| Feature | Minimum Version | Recommended Version |
|---------|-----------------|---------------------|
| Basic CTE | 3.8.3 | 3.8.3+ |
| Recursive CTE | 3.8.3 | 3.8.3+ |
| Window functions | 3.25.0 | 3.25.0+ |
| RETURNING clause | 3.35.0 | 3.35.0+ |
| JSON operations | 3.38.0 | 3.38.0+ |
| PRAGMA table_list | 3.37.0 | 3.37.0+ |

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

## Command Line Introspection

The SQLite backend provides command-line introspection commands to query database metadata without writing code.

### Basic Usage

```bash
# List all tables
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db

# List all views
python -m rhosocial.activerecord.backend.impl.sqlite introspect views --db-file my.db

# Get database information
python -m rhosocial.activerecord.backend.impl.sqlite introspect database --db-file my.db

# Include system tables
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db --include-system
```

### Querying Table Details

```bash
# Get complete table info (columns, indexes, foreign keys)
python -m rhosocial.activerecord.backend.impl.sqlite introspect table users --db-file my.db

# Query only column information
python -m rhosocial.activerecord.backend.impl.sqlite introspect columns users --db-file my.db

# Query only index information
python -m rhosocial.activerecord.backend.impl.sqlite introspect indexes users --db-file my.db

# Query only foreign key information
python -m rhosocial.activerecord.backend.impl.sqlite introspect foreign-keys posts --db-file my.db

# Query triggers
python -m rhosocial.activerecord.backend.impl.sqlite introspect triggers --db-file my.db

# Query triggers for a specific table
python -m rhosocial.activerecord.backend.impl.sqlite introspect triggers users --db-file my.db
```

### Introspection Types

| Type | Description | Table Name Required |
|------|-------------|---------------------|
| `tables` | List all tables | No |
| `views` | List all views | No |
| `database` | Database information | No |
| `table` | Complete table details (columns, indexes, foreign keys) | Yes |
| `columns` | Column information | Yes |
| `indexes` | Index information | Yes |
| `foreign-keys` | Foreign key information | Yes |
| `triggers` | Trigger information | Optional |

### Output Formats

```bash
# Table format (default, requires rich library)
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db

# JSON format
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db --output json

# CSV format
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db --output csv

# TSV format
python -m rhosocial.activerecord.backend.impl.sqlite introspect tables --db-file my.db --output tsv
```

### Using In-Memory Database

```bash
# Uses in-memory database when --db-file is not specified
python -m rhosocial.activerecord.backend.impl.sqlite introspect database
```
