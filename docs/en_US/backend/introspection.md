# Database Introspection

Database introspection is the ability to query database structure metadata at runtime. rhosocial-activerecord provides a complete introspection system that supports querying metadata for databases, tables, columns, indexes, foreign keys, views, triggers, and more.

## Overview

The introspection system is accessible via the `backend.introspector` attribute and provides:

- **Database Information**: Name, version, encoding, size, etc.
- **Table Information**: Table list, table details, table types (base table, view, system table)
- **Column Information**: Column name, data type, nullability, default value, primary key info
- **Index Information**: Index name, columns, uniqueness, index type
- **Foreign Key Information**: Referenced table, column mapping, update/delete actions
- **View Information**: View definition SQL
- **Trigger Information**: Trigger event, timing, trigger SQL

## Architecture Design

### Module Structure

```
backend/introspection/
├── __init__.py          # Module exports
├── base.py              # Abstract base classes
├── types.py             # Data structure definitions
├── errors.py            # Introspection-specific exceptions
├── executor.py          # Executor abstraction
└── backend_mixin.py     # Backend mixin class
```

### Sync and Async Separation

The introspection system follows the project's sync/async parity principle:

- `SyncAbstractIntrospector` — Synchronous introspector
- `AsyncAbstractIntrospector` — Asynchronous introspector
- `IntrospectorMixin` — Shared non-I/O logic (caching, SQL generation, parsing)

## Data Structures

### DatabaseInfo

Basic database information:

```python
@dataclass
class DatabaseInfo:
    name: str                      # Database name
    version: str                   # Version string
    version_tuple: Tuple[int, ...] # Version tuple
    vendor: str                    # Database vendor
    encoding: Optional[str]        # Encoding
    collation: Optional[str]       # Collation
    timezone: Optional[str]        # Timezone
    size_bytes: Optional[int]      # Database size
    table_count: Optional[int]     # Table count
    extra: Dict[str, Any]          # Additional info
```

### TableInfo

Table information:

```python
@dataclass
class TableInfo:
    name: str                    # Table name
    schema: str                  # Schema name
    table_type: TableType        # Table type
    comment: Optional[str]       # Table comment
    row_count: Optional[int]     # Row count estimate
    size_bytes: Optional[int]    # Table size
    extra: Dict[str, Any]        # Additional info
```

### ColumnInfo

Column information:

```python
@dataclass
class ColumnInfo:
    name: str                         # Column name
    table_name: str                   # Owner table name
    data_type: str                    # Data type
    nullable: ColumnNullable          # Nullability
    default_value: Optional[str]      # Default value
    is_primary_key: bool              # Is primary key
    ordinal_position: int             # Column position
    comment: Optional[str]            # Column comment
    character_set: Optional[str]      # Character set
    collation: Optional[str]          # Collation
    extra: Dict[str, Any]             # Additional info
```

### IndexInfo

Index information:

```python
@dataclass
class IndexInfo:
    name: str                      # Index name
    table_name: str                # Owner table name
    columns: List[IndexColumnInfo] # Index columns
    is_unique: bool                # Is unique
    is_primary: bool               # Is primary key
    index_type: IndexType          # Index type
    comment: Optional[str]         # Index comment
    extra: Dict[str, Any]          # Additional info
```

### ForeignKeyInfo

Foreign key information:

```python
@dataclass
class ForeignKeyInfo:
    name: str                           # Foreign key name
    table_name: str                     # Owner table name
    columns: List[str]                  # Foreign key columns
    referenced_table: str               # Referenced table name
    referenced_columns: List[str]       # Referenced columns
    on_update: ReferentialAction        # Update action
    on_delete: ReferentialAction        # Delete action
    match_option: Optional[str]         # Match option
    extra: Dict[str, Any]               # Additional info
```

### ViewInfo

View information:

```python
@dataclass
class ViewInfo:
    name: str                    # View name
    schema: str                  # Schema name
    definition: str              # View definition SQL
    is_updatable: Optional[bool] # Is updatable
    comment: Optional[str]       # View comment
    extra: Dict[str, Any]        # Additional info
```

### TriggerInfo

Trigger information:

```python
@dataclass
class TriggerInfo:
    name: str                    # Trigger name
    table_name: str              # Associated table name
    event: TriggerEvent          # Trigger event
    timing: TriggerTiming        # Trigger timing
    statement: str               # Trigger SQL
    condition: Optional[str]     # Trigger condition
    extra: Dict[str, Any]        # Additional info
```

## Basic Usage

### Accessing the Introspector

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database=":memory:")
backend.connect()

# Access via introspector attribute
introspector = backend.introspector
```

### Getting Database Information

```python
# Sync API
db_info = backend.introspector.get_database_info()
print(f"Database name: {db_info.name}")
print(f"Version: {db_info.version}")
print(f"Vendor: {db_info.vendor}")

# Async API
db_info = await backend.introspector.get_database_info()
```

### Listing Tables

```python
# List all user tables
tables = backend.introspector.list_tables()
for table in tables:
    print(f"Table: {table.name}, Type: {table.table_type.value}")

# Include system tables
all_tables = backend.introspector.list_tables(include_system=True)

# Filter by specific type
base_tables = backend.introspector.list_tables(table_type="BASE TABLE")
views = backend.introspector.list_tables(table_type="VIEW")

# Check if table exists
if backend.introspector.table_exists("users"):
    print("users table exists")

# Get table details
table_info = backend.introspector.get_table_info("users")
```

### Querying Column Information

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

# Get single column information
col_info = backend.introspector.get_column_info("users", "email")
```

### Querying Indexes

```python
# List all indexes of a table
indexes = backend.introspector.list_indexes("users")
for idx in indexes:
    unique = "UNIQUE " if idx.is_unique else ""
    print(f"{unique}Index: {idx.name}")
    for col in idx.columns:
        desc = "DESC" if col.is_descending else "ASC"
        print(f"  - {col.name} ({desc})")

# Check if index exists
if backend.introspector.index_exists("users", "idx_users_email"):
    print("email index exists")
```

### Querying Foreign Keys

```python
# List foreign keys of a table
foreign_keys = backend.introspector.list_foreign_keys("posts")
for fk in foreign_keys:
    print(f"FK: {fk.name}")
    print(f"  Columns: {fk.columns} -> {fk.referenced_table}.{fk.referenced_columns}")
    print(f"  ON DELETE: {fk.on_delete.value}")
    print(f"  ON UPDATE: {fk.on_update.value}")
```

### Querying Views

```python
# List all views
views = backend.introspector.list_views()
for view in views:
    print(f"View: {view.name}")

# Get view details
view_info = backend.introspector.get_view_info("user_posts_summary")
if view_info:
    print(f"Definition: {view_info.definition}")

# Check if view exists
if backend.introspector.view_exists("user_posts_summary"):
    print("View exists")
```

### Querying Triggers

```python
# List all triggers
triggers = backend.introspector.list_triggers()
for trigger in triggers:
    print(f"Trigger: {trigger.name} on {trigger.table_name}")

# List triggers for a specific table
table_triggers = backend.introspector.list_triggers("users")
for trigger in table_triggers:
    print(f"Trigger: {trigger.name}")
    print(f"  Event: {trigger.event.value}")
    print(f"  Timing: {trigger.timing.value}")

# Get trigger details
trigger_info = backend.introspector.get_trigger_info("users", "trg_users_audit")
```

## Async API

The async backend provides identical introspection methods with the same names as the sync version:

```python
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

backend = AsyncSQLiteBackend(database=":memory:")
await backend.connect()

# Async introspection methods (same names as sync version)
db_info = await backend.introspector.get_database_info()
tables = await backend.introspector.list_tables()
table_info = await backend.introspector.get_table_info("users")
columns = await backend.introspector.list_columns("users")
indexes = await backend.introspector.list_indexes("users")
foreign_keys = await backend.introspector.list_foreign_keys("posts")
views = await backend.introspector.list_views()
triggers = await backend.introspector.list_triggers()
```

## Caching Mechanism

Introspection results are cached by default for performance.

### Cache Configuration

```python
# Default TTL is 300 seconds (5 minutes)
# Automatically set when introspector is initialized
```

### Cache Management

```python
# Clear all cache
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

# Invalidate column-related cache
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.COLUMN,
    table_name="users"
)

# Invalidate index-related cache
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.INDEX,
    table_name="users",
    name="idx_users_email"
)
```

### Cache Scopes

| Scope | Description | Invalidation Parameters |
|-------|-------------|------------------------|
| `DATABASE` | Database information | None |
| `SCHEMA` | Schema information | `name` |
| `TABLE` | Table information | `name` |
| `COLUMN` | Column information | `table_name`, `name` |
| `INDEX` | Index information | `table_name`, `name` |
| `FOREIGN_KEY` | Foreign key information | `table_name`, `name` |
| `VIEW` | View information | `name` |
| `TRIGGER` | Trigger information | `table_name`, `name` |

## Backend-Specific Implementations

### SQLite

SQLite uses `PRAGMA` directives for introspection:

```python
# SQLite-specific: Direct access to PragmaIntrospector
pragma = backend.introspector.pragma

# Use PRAGMA directives
table_info = pragma.pragma_table_info("users")
index_list = pragma.pragma_index_list("users")
foreign_keys = pragma.pragma_foreign_key_list("posts")
```

### MySQL

MySQL uses `information_schema` and `SHOW` statements for introspection:

```python
# MySQL-specific: Direct access to ShowIntrospector
show = backend.introspector.show

# Use SHOW statements
tables = show.show_tables()
columns = show.show_columns("users")
indexes = show.show_index("users")
create_table = show.show_create_table("users")
```

## Error Handling

The introspection system defines specific exceptions:

```python
from rhosocial.activerecord.backend.introspection.errors import (
    IntrospectionError,       # Base introspection exception
    TableNotFoundError,       # Table not found
    ColumnNotFoundError,      # Column not found
    IndexNotFoundError,       # Index not found
    ViewNotFoundError,        # View not found
    TriggerNotFoundError,     # Trigger not found
)

try:
    table_info = backend.introspector.get_table_info("nonexistent")
except TableNotFoundError as e:
    print(f"Table not found: {e}")
```

## Best Practices

### 1. Use Caching

Introspection operations typically involve multiple database queries. Leverage caching:

```python
# First query caches the result
tables = backend.introspector.list_tables()

# Subsequent queries return from cache
tables_again = backend.introspector.list_tables()

# Only clear cache when table structure changes
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE, name="users")
```

### 2. Batch Operations

Prefer batch query methods when possible:

```python
# Good: One query for all columns
columns = backend.introspector.list_columns("users")

# Avoid: Multiple single-column queries
for col_name in column_names:
    col = backend.introspector.get_column_info("users", col_name)  # I/O each time
```

### 3. Check Existence

Check if objects exist before performing dependent operations:

```python
if backend.introspector.table_exists("users"):
    columns = backend.introspector.list_columns("users")
else:
    print("Table doesn't exist, skipping processing")
```

### 4. Using in Async Environments

```python
async def get_schema_info(backend):
    # Async methods have the same names as sync
    tables = await backend.introspector.list_tables()

    # Concurrently fetch columns for multiple tables
    import asyncio
    tasks = [
        backend.introspector.list_columns(table.name)
        for table in tables
    ]
    all_columns = await asyncio.gather(*tasks)
    return dict(zip([t.name for t in tables], all_columns))
```

## Limitations and Considerations

1. **Permission Requirements**: Introspection requires database users to have metadata read permissions
2. **Performance Impact**: Introspection on large-scale databases may be slow; caching is recommended
3. **Version Differences**: Metadata availability may vary across database versions
4. **Consistency**: Introspection results reflect the database state at query time, not real-time

## API Reference

### Core Methods

| Method | Description | Parameters |
|--------|-------------|------------|
| `get_database_info()` | Get database information | None |
| `list_tables()` | List tables | `include_system`, `table_type`, `schema` |
| `get_table_info(name)` | Get table details | `name`, `schema` |
| `table_exists(name)` | Check table exists | `name`, `schema` |
| `list_columns(table_name)` | List columns | `table_name`, `schema` |
| `get_column_info(table_name, column_name)` | Get column details | `table_name`, `column_name`, `schema` |
| `get_primary_key(table_name)` | Get primary key | `table_name`, `schema` |
| `list_indexes(table_name)` | List indexes | `table_name`, `schema` |
| `get_index_info(table_name, index_name)` | Get index details | `table_name`, `index_name`, `schema` |
| `index_exists(table_name, index_name)` | Check index exists | `table_name`, `index_name`, `schema` |
| `list_foreign_keys(table_name)` | List foreign keys | `table_name`, `schema` |
| `list_views()` | List views | `schema` |
| `get_view_info(name)` | Get view details | `name`, `schema` |
| `view_exists(name)` | Check view exists | `name`, `schema` |
| `list_triggers(table_name)` | List triggers | `table_name`, `schema` |
| `get_trigger_info(table_name, trigger_name)` | Get trigger details | `table_name`, `trigger_name`, `schema` |
| `clear_cache()` | Clear cache | None |
| `invalidate_cache(scope, ...)` | Invalidate cache | `scope`, `name`, `table_name` |
