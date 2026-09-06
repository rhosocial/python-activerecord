# Introspection

## Two-Layer Architecture

The introspection API follows the same two-layer pattern as expressions:

1. **Core layer** — The `Introspector` interface provides common methods (`list_tables()`, `list_columns()`, `list_indexes()`, `list_foreign_keys()`) that work identically across all backends.

2. **Backend layer** — Each backend implements the introspector using database-specific system tables. MySQL queries `information_schema` and uses `SHOW` commands; PostgreSQL queries `pg_catalog`; SQLite reads `sqlite_master`.

## Basic Usage

### Accessing the Introspector

```python
# Get the introspector from the backend
introspector = User.backend().introspector

# List all tables
tables = introspector.list_tables()
print(tables)  # ['users', 'posts', 'comments']
```

### Database Info

```python
info = introspector.get_database_info()
print(info)
```

### Listing Tables

```python
# List all tables
tables = introspector.list_tables()

# List tables with pattern matching
tables = introspector.list_tables(pattern='user%')
```

### Querying Columns

```python
columns = introspector.list_columns('users')
for col in columns:
    print(f"{col.name}: {col.type}")
```

### Querying Indexes

```python
indexes = introspector.list_indexes('users')
for idx in indexes:
    print(f"{idx.name}: {idx.columns}")
```

### Querying Foreign Keys

```python
fks = introspector.list_foreign_keys('posts')
for fk in fks:
    print(f"{fk.column} -> {fk.referenced_table}.{fk.referenced_column}")
```

### Querying Views

```python
views = introspector.list_views()
```

## {database}-Specific Behaviors

### MySQL: ShowIntrospector

MySQL provides additional introspection via SHOW commands:

```python
from rhosocial.activerecord.backend.impl.{backend}.introspection import ShowIntrospector

show = ShowIntrospector(backend)

# SHOW CREATE TABLE
ddl = show.create_table('users')

# SHOW COLUMNS
columns = show.columns('users')

# SHOW TABLE STATUS
status = show.table_status('users')

# SHOW DATABASES
databases = show.databases()

# SHOW VARIABLES
variables = show.variables()
```

### PostgreSQL: Schema Support

PostgreSQL supports multiple schemas:

```python
# List schemas
schemas = introspector.list_schemas()

# Introspect a specific schema
columns = introspector.list_columns('users', schema='public')
```

### PostgreSQL: Materialized Views

PostgreSQL distinguishes between views and materialized views:

```python
views = introspector.list_views(include_materialized=True)
```

### Backend-Specific Index Types

| Backend | Supported Index Types |
|---------|----------------------|
| MySQL | B-Tree, Hash (InnoDB) |
| PostgreSQL | B-Tree, GIN, GiST, SPGIST, BRIN |
| SQLite | B-Tree |

## What Can You Discover at Runtime?

You can check introspection capabilities using the protocol system:

```python
from rhosocial.activerecord.backend.dialect.protocols import IntrospectionSupport

dialect = backend.dialect

# Check if introspection is supported at all
if isinstance(dialect, IntrospectionSupport):
    # Check specific introspection features
    if dialect.supports_table_introspection():
        tables = introspector.list_tables()

    if dialect.supports_column_introspection():
        columns = introspector.list_columns('users')

    if dialect.supports_index_introspection():
        indexes = introspector.list_indexes('users')

    if dialect.supports_foreign_key_introspection():
        fks = introspector.list_foreign_keys('posts')

    if dialect.supports_view_introspection():
        views = introspector.list_views()

    if dialect.supports_partition_info():
        # Get partition information (PostgreSQL, MySQL)
        partitions = introspector.list_partitions('users')
```

### What Each Backend Supports

| Feature | SQLite | MySQL | PostgreSQL |
|---------|--------|-------|------------|
| Table listing | Yes | Yes | Yes |
| Column introspection | Yes | Yes | Yes |
| Index introspection | Yes | Yes | Yes |
| Foreign key introspection | Yes | Yes | Yes |
| View introspection | Yes | Yes | Yes |
| Schema support | No | Yes (synonym for DATABASE) | Yes |
| Materialized views | No | No | Yes |
| Partition info | No | Yes | Yes |
| Extension info | No | No | Yes |
| DDL extraction | Yes | Yes | Yes |
| Runtime stats | No | Yes | Yes |
| Unused index detection | No | No | Yes |
| Object dependencies | No | No | Yes |

## Async API

```python
# Async introspection
tables = await async_introspector.list_tables()
columns = await async_introspector.list_columns('users')
```

## Cache Management

The introspector caches results to avoid repeated queries:

```python
# Clear all cache
introspector.clear_cache()

# Clear cache for a specific table
introspector.clear_cache(table='users')
```

## Command Line Introspection

```bash
# List tables
python -m rhosocial.activerecord.backend.impl.{backend}.cli introspect tables

# Describe a table
python -m rhosocial.activerecord.backend.impl.{backend}.cli introspect columns users

# Output formats
python -m rhosocial.activerecord.backend.impl.{backend}.cli introspect tables --format json
python -m rhosocial.activerecord.backend.impl.{backend}.cli introspect tables --format csv
```

## See Also

- [Dialect Expressions](dialect.md) — feature detection and protocol system
- [Core: Introspection](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/introspection)

💡 *AI Prompt:* "How do I check what indexes exist on a {database} table?"
