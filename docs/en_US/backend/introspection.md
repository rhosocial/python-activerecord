# Database Introspection

Database introspection is the ability to query database structure metadata at runtime. rhosocial-activerecord provides a complete introspection system that supports querying metadata for databases, tables, columns, indexes, foreign keys, views, triggers, and more.

## Overview

The introspection system is accessible via the `backend.introspector` attribute and provides:

- **Database Information**: Name, version, encoding, size, etc.
- **Table Information**: Table list, table details, table types (`BASE_TABLE`, `VIEW`, `MATERIALIZED_VIEW`, `FOREIGN_TABLE`, `PARTITIONED_TABLE`, `SYSTEM_TABLE`, `TEMPORARY`, `EXTERNAL`)
- **Column Information**: Column name, data type, nullability, default value, primary key info
- **Index Information**: Index name, columns, uniqueness, index type
- **Foreign Key Information**: Referenced table, column mapping, update/delete actions
- **View Information**: View definition SQL
- **Trigger Information**: Trigger event, timing, trigger SQL

## What You Can Ask

Introspection answers three layers of question, and this page covers the first in detail:

- **Declaration layer** — what the catalogue says objects are: databases, tables, columns, indexes, foreign keys, views and triggers. The dialect's capability probes say which of these an engine answers at all; see [Capabilities](introspection/capabilities.md).
- **Operational layer** — what the engine has counted while running: unused indexes, table and index usage counters, runtime measurements, object dependencies and DDL retrieval; see [Operational Families](introspection/operations.md).
- **Data layer** — what the rows actually hold, rather than what the schema promises: column profiles, frequent values and join coverage; see [Column Data Profiles](introspection/data-profiles.md).

A family whose capability probe answers `False` is not available on that engine; the backend's own documentation states which probes answer `True` and what its answers mean.

## Architecture Design

### Module Structure

```
backend/introspection/
├── __init__.py          # Module exports
├── base.py              # Abstract introspector bases (sync and async)
├── types.py             # Data structure definitions (TableType, ...)
├── errors.py            # Introspection-specific exceptions
├── executor.py          # Executor abstraction
├── cache.py             # IntrospectionCache -- the injectable result cache
├── backend_mixin.py     # Backend mixin class
└── status/              # Server status overview (config, performance, storage)
```

### A Catalogue Question Is a Statement

Introspection does not build SQL text inline. Each question is a statement class
(named `*Statement`, e.g. `TableListQueryStatement`), rendered by a dialect
`format_*_query_statement` method; the introspector holds the public method pairs
(`list_tables()` / `parse_tables()`, and so on) that use them. Two consequences
matter to a backend author:

- the expression layer keeps no state -- a statement holds what it needs to be
  rendered anywhere;
- a backend answers a catalogue question by declaring a statement plus a
  formatter, not by overriding a method that assembles a string.

### Sync and Async Separation

The introspection system follows the project's sync/async parity principle:

- `AbstractIntrospector` — Synchronous introspector
- `AsyncAbstractIntrospector` — Asynchronous introspector
- `IntrospectorMixin` — Shared non-I/O base: it knows the default schema and exposes the `dialect` and `server_version` shortcuts, but holds no state, performs no I/O and never sees a result row. Caching and row parsing belong to the manager that inherits it, and SQL is rendered by the dialect's `format_*` methods from statement objects. `server_version` is the version the introspector read from the server, so a capability question can be answered without asking again

## Data Structures

### IntrospectionDatabaseInfo

Basic database information:

```python
@dataclass
class IntrospectionDatabaseInfo:
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

### IntrospectionTableInfo

Table information:

```python
@dataclass
class IntrospectionTableInfo:
    name: str                    # Table name
    schema: str                  # Schema name
    table_type: TableType        # Table type (BASE_TABLE, VIEW, MATERIALIZED_VIEW,
                                 #  FOREIGN_TABLE, PARTITIONED_TABLE, SYSTEM_TABLE,
                                 #  TEMPORARY, EXTERNAL)
    comment: Optional[str]       # Table comment
    row_count: Optional[int]     # Row count estimate
    size_bytes: Optional[int]    # Table size
    extra: Dict[str, Any]        # Additional info
```

`table_type` keeps the distinction the catalogue actually makes rather than
folding every relation into "table". How a particular engine classifies a
relation is that backend's own documentation to state.

### IntrospectionColumnInfo

Column information:

```python
@dataclass
class IntrospectionColumnInfo:
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

### IntrospectionForeignKeyInfo

Foreign key information:

```python
@dataclass
class IntrospectionForeignKeyInfo:
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

### IntrospectionViewInfo

View information:

```python
@dataclass
class IntrospectionViewInfo:
    name: str                    # View name
    schema: str                  # Schema name
    definition: str              # View definition SQL
    is_updatable: Optional[bool] # Is updatable
    comment: Optional[str]       # View comment
    extra: Dict[str, Any]        # Additional info
```

### IntrospectionTriggerInfo

Trigger information:

```python
@dataclass
class IntrospectionTriggerInfo:
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
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend

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

# Check if an index exists
if backend.introspector.get_index_info("users", "idx_users_email"):
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
trigger_info = backend.introspector.get_trigger_info("trg_users_audit")
```

## Async API

The async backend provides identical introspection methods with the same names as the sync version:

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import AsyncSQLiteBackend

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

Introspection results are cached by default for performance. The cache is a
component the manager **owns** and a caller may replace, rather than a hidden
attribute: `backend.introspector.cache`.

### The Cache Contract

`IntrospectionCache` (`rhosocial.activerecord.backend.introspection.cache`) is a
protocol, so a backend can put its own implementation behind the manager instead
of inheriting this package's expiry policy:

| Method | Purpose |
|--------|---------|
| `key(scope, name=None, schema=None, extra=None)` | Build the key two callers asking the same question share |
| `get(key)` | Return a cached result, or `None` |
| `set(key, value)` | Store a result |
| `invalidate(scope=None, name=None)` | Drop results from everything down to one object |
| `clear()` | Drop every cached result |

`InMemoryIntrospectionCache` is the default: in-process, expiring after a TTL
(300 seconds by default), dropped lazily the moment somebody looks at an expired
entry rather than by a background sweeper.

```python
from rhosocial.activerecord.backend.introspection.cache import InMemoryIntrospectionCache

# Default: in-process, 300 s TTL
backend.introspector.cache = InMemoryIntrospectionCache(ttl=60)

# Or a cache of your own: anything that satisfies the protocol
class NoCache:
    def key(self, scope, name=None, schema=None, extra=None):
        return (scope, name, schema, extra)

    def get(self, key):
        return None

    def set(self, key, value):
        pass

    def invalidate(self, scope=None, name=None):
        pass

    def clear(self):
        pass

backend.introspector.cache = NoCache()
```

### Cache Management

```python
# Clear all cache
backend.introspector.clear_cache()

# Invalidate specific scope
from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

# Invalidate all table-related cache
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE)

# Invalidate cache for a specific table, index, column set, ...
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.TABLE,
    name="users"
)
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.INDEX,
    name="idx_users_email"
)
```

### Cache Scopes

A scope says which cached answers an invalidation reaches, so the table a
question is about travels in the `name` (or, for `key()`, in `schema`/`extra`):

| Scope | Description |
|-------|-------------|
| `DATABASE` | Database information |
| `SCHEMA` | Schema information |
| `TABLE` | Table information |
| `COLUMN` | Column information |
| `INDEX` | Index information |
| `FOREIGN_KEY` | Foreign key information |
| `VIEW` | View information |
| `TRIGGER` | Trigger information |


## Backend-Specific Implementations

The common methods are assembled over helper introspectors the backend supplies — the built-in SQLite backend's `PragmaIntrospector` and, for example, MySQL's `ShowIntrospector` are two — and each backend's own documentation states which helpers it has, what they answer, and what those answers mean.

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

Three facts explain almost every surprising introspection answer:

1. **A counter is a window, not a lifetime.** The operational families report
   what the engine has counted *since the statistics were last reset*. A zero
   means "nothing in this window", never "nothing ever happened".
2. **A profile may describe an older table.** Figures read from a statistics
   catalogue can be as stale as the engine's last refresh; `collected_at`
   travels beside them so a reader can tell what moment they describe.
3. **Some engines cannot answer some questions.** Ask the dialect's capability
   probe first — see [Capabilities](introspection/capabilities.md). A `False`
   is a definite "this engine does not answer this family", and each backend's
   own documentation says which probes answer `True` and what its answers mean.

## API Reference

The signatures below omit `self`; the sync and async introspectors have the
same method names and parameters.

### Core Methods — Declaration Layer

What the catalogue says objects are. Every result is cached under the scope it
belongs to.

| Method | Parameters (defaults) | Description |
|--------|-----------------------|-------------|
| `get_database_info()` | — | Database information |
| `list_tables()` | `schema=None, include_system=False, table_type=None` | List tables (and views) |
| `get_table_info(table_name)` | `schema=None` | Table details, with columns, indexes and foreign keys |
| `table_exists(table_name)` | `schema=None` | Whether the table exists |
| `list_columns(table_name)` | `schema=None` | List columns |
| `get_column_info(table_name, column_name)` | `schema=None` | Column details |
| `column_exists(table_name, column_name)` | `schema=None` | Whether the column exists |
| `get_primary_key(table_name)` | `schema=None` | Primary key index |
| `list_indexes(table_name)` | `schema=None` | List indexes |
| `get_index_info(table_name, index_name)` | `schema=None` | Index details |
| `list_foreign_keys(table_name)` | `schema=None` | List foreign keys |
| `get_foreign_key_info(table_name, fk_name)` | `schema=None` | Foreign key details |
| `list_views()` | `schema=None, include_system=False` | List views |
| `get_view_info(view_name)` | `schema=None` | View details |
| `view_exists(view_name)` | `schema=None` | Whether the view exists |
| `list_triggers()` | `table_name=None, schema=None` | List triggers, optionally for one table |
| `get_trigger_info(trigger_name)` | `schema=None` | Trigger details |

### Core Methods — Operational Layer

Counters here are windows, not lifetimes: a zero means "nothing since the
statistics were last reset" (see
[Limitations and Considerations](#limitations-and-considerations)). Check the
dialect's capability probe before calling; a `False` means the family is not
available on that engine.

| Method | Parameters (defaults) | Description |
|--------|-----------------------|-------------|
| `list_unused_indexes()` | `schema=None` | Indexes the engine reports as never having served a query |
| `list_table_usage_stats()` | `schema=None` | Per-table read/write counters, since the last statistics reset |
| `list_runtime_metrics()` | `schema=None` | Live runtime measurements; each item's `source` states its window |
| `list_index_usage_stats()` | `schema=None` | Per-index use counters ("how much", not "ever") |
| `list_object_dependencies()` | `object_name=None, schema=None` | The dependency graph, or one object's dependants |
| `get_ddl_statement(object_name)` | `object_type=None, schema=None` | DDL that recreates one object, or `None` |

### Core Methods — Data Layer

The declaration says what a column *promises*; these say what it *holds*.
`None` means not measured, never zero, and a profile's `source` says where its
figures came from.

| Method | Parameters (defaults) | Description |
|--------|-----------------------|-------------|
| `list_column_data_profiles(table_name)` | `schema=None` | Profile every column of one table |
| `sample_column_values(table_name, column_name)` | `limit=VALUE_SAMPLE_LIMIT, schema=None` | A column's most frequent values, up to `limit` |
| `estimate_join_coverage(left_table, left_column, right_table, right_column)` | `schema=None` | How much two columns' value domains overlap; `None` when unmeasured |

`VALUE_SAMPLE_LIMIT` is defined once in
`backend/introspection/defaults.py` (currently 100); the signature names the
constant rather than repeating its value.

### Cache and Invalidation

The cache is the component every layer's results pass through; it is not a
layer of its own.

| Method | Parameters (defaults) | Description |
|--------|-----------------------|-------------|
| `clear_cache()` | — | Drop every cached result |
| `invalidate_cache()` | `scope=None, name=None` | Drop cached results, from everything down to one object |
