# Introspection

## Two-Layer Architecture

The introspection API follows the same two-layer pattern as expressions:

1. **Core layer** — The `Introspector` interface provides common methods (`list_tables()`, `list_columns()`, `list_indexes()`, `list_foreign_keys()`) that work identically across all backends.

2. **Backend layer** — Each backend implements the introspector using database-specific system tables. MySQL queries `information_schema` and uses `SHOW` commands; PostgreSQL queries `pg_catalog`; SQLite reads `sqlite_master`.

## Three Layers of Question

Every introspection family belongs to one of three layers, and the core API
treats them differently:

1. **Declaration** — what the catalogue says an object is: database, table,
   column, index, key, view, trigger. Cheap, cached, and usually one catalogue
   query.
2. **Operational** — what the engine has counted while running: usage
   counters, unused indexes, runtime metrics, dependencies, DDL. A number is
   valid only inside the engine's window, which is why its `source` travels
   with it.
3. **Data** — what the rows actually hold, as opposed to what the declaration
   promises: profiles, frequent values, join coverage. `None` means not
   measured, and every answer names its provenance.

A backend implements a family in all three places, not in one: a statement
class declares the question, a dialect formatter renders it, the introspector
parses the rows, the CLI types it, and a test proves it.

## The Author's Obligation

A capability probe is a promise, not a wish list. The project's §6 rule, seen
from the outside, says:

- **If your probe answers `True`**, that family must have a statement class, a
  dialect formatter, a parser, a CLI type and a test. A `True` with any of
  those missing is a `False` that lies.
- **If your engine cannot answer**, the probe answers `False`, and the reason
  goes in the probe's docstring: what the engine lacks and what a caller
  should do instead. A `False` with no stated reason is indistinguishable from
  one nobody implemented.

The probe is also the only correct way for a caller to find out; do not infer
support from an empty result.

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

### An Illustration, Not a Matrix

The table below shows the *shape* of a capability answer, one row per layer.
The answers are examples, not facts about any engine; do not copy them into
another backend's documentation.

| Layer | Probe | An example answer |
|-------|-------|-------------------|
| Declaration | `supports_table_introspection()` | `True` |
| Operational | `supports_unused_indexes_detection()` | `False` — the engine keeps no per-index counters |
| Data | `supports_column_data_profile()` | `True` |

The authoritative source for what a real backend supports is that backend's
own documentation, together with the probe itself: a `True` from the probe is
the promise described under [The Author's Obligation](#the-authors-obligation),
and the backend's docs say what its answer means and which window it covers.

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
python -m rhosocial.activerecord.backend.impl.{backend}.cli introspect tables -o json
python -m rhosocial.activerecord.backend.impl.{backend}.cli introspect tables -o csv
```

## See Also

- [Dialect Expressions](dialect.md) — feature detection and protocol system
- [Core: Introspection](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/introspection)

💡 *AI Prompt:* "How do I check what indexes exist on a {database} table?"
