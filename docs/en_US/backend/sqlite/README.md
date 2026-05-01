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

## Named Queries

Named Queries provide a way to define reusable SQL queries as Python callables (functions or classes) that can be executed through the CLI.

### Overview

Named queries are defined as Python functions or classes that return `BaseExpression` objects. They use the backend expression system to construct SQL queries, avoiding raw SQL strings and providing type safety.

### Defining Named Queries

Create a Python module with query definitions:

```python
# myapp/queries.py
from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression
from rhosocial.activerecord.backend.expression.core import TableExpression, Column, Literal
from rhosocial.activerecord.backend.expression.query_parts import WhereClause, LimitOffsetClause

def orders_by_status(dialect, status: str, limit: int = 100):
    """Query orders by status."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "*")],
        from_=TableExpression(dialect, "orders"),
        where=WhereClause(dialect, Column(dialect, "status") == Literal(dialect, status)),
        limit_offset=LimitOffsetClause(dialect, limit=limit),
    )
```

Key points:
- The first parameter must be `dialect` (injected by the CLI)
- Return type must be `BaseExpression` (or subclass)
- Use type annotations for parameter documentation
- Add docstrings for description

### Using Named Queries via CLI

#### Execute a Named Query

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.orders_by_status \
    --db-file mydb.sqlite \
    --param status=pending
```

#### Override Parameters

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.orders_by_status \
    --db-file mydb.sqlite \
    --param status=completed \
    --param limit=50
```

#### Describe Query (Show Signature)

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.orders_by_status \
    --describe
```

Output:
```
Query: myapp.queries.orders_by_status
Docstring: Query orders by status.
Signature: (dialect, status: str, limit: int = 100)
Parameters (excluding 'dialect'):
  status <class 'str'>
  limit <class 'int'> default=100
```

#### Preview SQL (Dry Run)

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.orders_by_status \
    --db-file mydb.sqlite \
    --param status=pending \
    --dry-run
```

Output:
```
[DRY RUN] SQL:
  SELECT * FROM "orders" WHERE "status" = ? LIMIT ?
Params: ('pending', 100)
```

#### List All Queries in a Module

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries \
    --list
```

Output:
```
Module: myapp.queries
  orders_by_status(dialect, status: str, limit: int = 100)
      Query orders by status.
  high_value_orders(dialect, threshold: float = 1000.0)
      High-value orders above threshold.
```

### Class-Based Queries

For complex queries with metadata, use classes:

```python
class MonthlyRevenue:
    """Monthly revenue report."""
    def __call__(self, dialect, month: int, year: int):
        return QueryExpression(
            dialect,
            select=[Column(dialect, "SUM(amount) as total")],
            from_=TableExpression(dialect, "orders"),
            where=WhereClause(dialect, ...),
        )
```

Execute:
```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    myapp.queries.MonthlyRevenue \
    --param month=3 \
    --param year=2026
```

### Security

The named query system enforces security:

1. **Return Type Validation**: Only `BaseExpression` is allowed. Raw SQL strings are rejected to prevent SQL injection.
2. **EXPLAIN Protection**: EXPLAIN queries are blocked for actual execution; use `--dry-run` to preview.
3. **Non-SELECT Warning**: DML/DDL statements trigger a warning; use `--force` to execute.

### Configuration

Set PYTHONPATH to include your query modules:

```bash
PYTHONPATH=src:examples python -m rhosocial.activerecord.backend.impl.sqlite \
    named-query examples.named_queries.order_queries.orders_by_status \
    --param status=pending
```

### Named Query Writing Standards

When defining named queries, follow these standards to ensure consistency and usability.

#### Basic Function Structure

```python
def query_name(dialect, param1: str, param2: int = 100):
    """Brief description of what this query does.

    Args:
        dialect: The SQL dialect instance (injected by CLI).
        param1: Description of param1. Can be passed as string from CLI.
                Will be converted to expected type internally.
        param2: Description of param2 with default value.

    Returns:
        QueryExpression: A DQL expression representing the query.

    Raises:
        ValueError: If parameters cannot be converted to expected types.

    CLI Examples:
        # Use defaults
        %(prog)s module.path.query_name

        # With custom parameters
        %(prog)s module.path.query_name --param param1=value1 --param param2=200
    """
    # Parameter validation and conversion
    param1_value = str(param1)  # CLI passes strings, convert as needed
    param2_value = int(param2)

    # Validation logic
    if param2_value <= 0:
        raise ValueError(f"param2 must be positive, got {param2_value}")

    # Build and return expression
    return QueryExpression(
        dialect,
        select=[Column(dialect, "*")],
        from_=TableExpression(dialect, "table_name"),
        where=WhereClause(dialect, ...),
    )
```

#### Key Standards

| Standard | Description |
|----------|-------------|
| **First parameter** | Must be `dialect` (injected by CLI) |
| **Return type** | Must be `BaseExpression` (or subclass like `QueryExpression`) |
| **Type annotations** | Keep for documentation; CLI always passes strings |
| **Docstring format** | Include Args, Returns, Raises, and CLI Examples sections |
| **Parameter conversion** | Functions must convert and validate CLI string parameters |
| **%(prog)s placeholder** | Use `%(prog)s` in CLI Examples for the program name |

#### Parameter Handling (Critical)

CLI parameters are **always passed as strings**. The function is responsible for converting and validating:

```python
# Simple conversion
limit_value = int(limit)

# Complex conversion (e.g., comma-separated list)
id_list = [int(x.strip()) for x in ids.split(",")]

# JSON parsing
import json
filters_dict = json.loads(filters)
```

**Important**: The type annotations in the function signature (e.g., `param: int`) represent the **desired type** after conversion, not the CLI input type. CLI always passes strings.

#### Shared Parameter Conversion Helpers

If multiple query functions share the same parameter types, define reusable conversion helpers:

```python
# myapp/queries/helpers.py
def parse_int(value: str, default: int = 0) -> int:
    """Convert string to int with default."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def parse_bool(value: str) -> bool:
    """Convert string to boolean."""
    return value.lower() in ("true", "1", "yes")

def parse_list_int(value: str) -> list[int]:
    """Convert comma-separated string to list of ints."""
    return [int(x.strip()) for x in value.split(",") if x.strip()]
```

Then use in your query functions:

```python
from myapp.queries.helpers import parse_int, parse_bool, parse_list_int

def get_orders(dialect, status: str, limit: int = 100, active_only: bool = True):
    """Query orders with parsed parameters."""
    limit_value = parse_int(limit, 100)
    active = parse_bool(active_only)
    return QueryExpression(...)
```

#### Handling Unknown Parameters

If you pass a parameter that the function doesn't expect, the resolver will detect it before calling the function:

```bash
# This will fail if 'filter' is not a valid parameter
python -m ... named-query myapp.queries.orders --param filter=pending
```

Error output:
```
Error: Invalid parameter: filter. Unknown parameter(s): filter. Available parameters: ['status', 'limit']
```

If multiple unknown parameters are passed, all will be listed:

```
Error: Invalid parameter: filter. Unknown parameter(s): filter, offset, page. Available parameters: ['status', 'limit']
```

The resolver checks parameters against the function signature before execution, providing clear feedback about which parameters are valid.

#### Listing and Describing Queries

```bash
# List all queries in a module
python -m ... named-query myapp.queries --list

# Show details for a specific query (two ways)
python -m ... named-query myapp.queries.query_name --list
python -m ... named-query myapp.queries --example query_name
```

Output from `--list`:
```
Module: myapp.queries
Name                           Parameters                               Brief
------------------------------------------------------------------------------------
query_name                    (param1: str, param2: int = 100)        Brief description here
```

#### Best Practices

1. **Use descriptive names**: `high_value_orders` > `query1`
2. **Include one-line brief**: First line of docstring appears in `--list` output
3. **Document parameters**: Explain what each parameter does and its valid range
4. **Validate early**: Check parameter validity before building expressions
5. **Use executable expressions**: Return `QueryExpression`, `InsertExpression`, etc. - not raw SQL strings
