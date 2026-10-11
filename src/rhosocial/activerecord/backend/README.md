# Backend Module Design Documentation

## Overview

The Backend module is the database abstraction layer for rhosocial-activerecord, responsible for providing a unified database access interface while supporting multiple database backends. This module follows the Open-Closed Principle (OCP), with core interfaces decoupled from concrete implementations, allowing new database support to be added via plugins.

## Architecture Principles

1. **Separation of Abstraction and Implementation**: The core package only defines interfaces and base classes, without any concrete database dependencies
2. **Protocol-Driven Design**: Uses Protocol and ABC to define feature contracts, supporting fine-grained capability detection
3. **Sync/Async Symmetry**: Synchronous and asynchronous APIs share core logic, differing only in the I/O layer
4. **Mixin Composition Pattern**: Backend functionality is composed through multiple Mixin classes, improving code reuse

## Directory Structure

```text
backend/
├── __init__.py                  # Public interface exports
├── config.py                    # Connection configuration base class
├── errors.py                    # Exception definitions
├── result.py                    # Query result types
├── schema.py                    # Database schema and type definitions
├── helpers.py                   # Common helper functions
├── options.py                   # Backend options configuration
├── output.py                    # Output module
├── output_abc.py                # Output abstract base class
├── output_rich.py               # Rich library output implementation
├── type_adapter.py              # Type adapter protocol and presets
├── type_registry.py             # Type adapter registry
├── transaction.py               # Transaction management base (sync/async)
│
├── named_connection/             # Named connection support
│   ├── __init__.py           # Public interface exports
│   ├── resolver.py          # NamedConnectionResolver
│   ├── exceptions.py        # Exception definitions
│   ├── validators.py       # Configuration validators
│   └── cli.py              # CLI integration
│
├── base/                        # Backend base classes and Mixins
│   ├── __init__.py              # StorageBackend and AsyncStorageBackend
│   ├── base.py                  # Backend base class
│   ├── connection.py            # Connection management Mixin (sync/async)
│   ├── execution.py             # Query execution Mixin (sync/async)
│   ├── hooks.py                 # Execution hooks Mixin (sync/async)
│   ├── logging.py               # Logging Mixin
│   ├── operations.py            # SQL operations Mixin (sync/async)
│   ├── result_processing.py     # Result processing Mixin
│   ├── returning.py             # RETURNING clause Mixin
│   ├── sql_building.py          # SQL building Mixin
│   ├── transaction_management.py # Transaction management Mixin (sync/async)
│   └── type_adaption.py         # Type adaptation Mixin (sync/async)
│
├── dialect/                     # SQL dialect system
│   ├── __init__.py              # Dialect public interface
│   ├── base.py                  # SQLDialectBase class
│   ├── exceptions.py            # Dialect-related exceptions
│   ├── protocols.py             # Feature protocol definitions
│   └── mixins.py                # Dialect feature Mixins
│
├── expression/                  # SQL expression building blocks
│   ├── __init__.py              # Expression public interface
│   ├── bases.py                 # Expression base classes and protocols
│   ├── literals.py              # Literal expressions
│   ├── operators.py             # Operator expressions
│   ├── core.py                  # Core expressions (Column, FunctionCall, etc.)
│   ├── predicates.py            # Predicate expressions
│   ├── advanced_functions.py    # Advanced functions (window, JSON, array, etc.)
│   ├── functions.py             # Function factories
│   ├── query_parts.py           # Query components
│   ├── query_sources.py         # Query sources (CTE, subquery, etc.)
│   ├── statements.py            # SQL statements (DML/DDL)
│   ├── mixins.py                # Expression Mixins
│   └── graph.py                 # Graph query expressions
│
└── impl/                        # Concrete backend implementations
    ├── dummy/                   # Dummy backend (SQL generation only)
    │   ├── __init__.py
    │   ├── backend.py           # DummyBackend / AsyncDummyBackend
    │   └── dialect.py           # DummyDialect
    │
    └── sqlite/                  # SQLite implementation (built into core)
        ├── __init__.py
        ├── __main__.py          # CLI entry point
        ├── adapters.py          # SQLite type adapters
        ├── config.py            # SQLite connection configuration
        ├── dialect.py           # SQLite dialect
        ├── functions.py         # SQLite-specific function factories
        ├── mixins.py            # SQLite-specific Mixins
        ├── protocols.py         # SQLite-specific protocols
        ├── transaction.py       # Sync transaction management
        ├── async_transaction.py # Async transaction management
        │
        ├── backend/             # Backend implementation
        │   ├── __init__.py
        │   ├── common.py        # Shared logic
        │   ├── sync.py          # SQLiteBackend (sync)
        │   └── async_backend.py # AsyncSQLiteBackend (async)
        │
        ├── extension/           # Extension framework
        │   ├── __init__.py
        │   ├── base.py          # Extension base class
        │   ├── registry.py      # Extension registry
        │   └── extensions/      # Built-in extensions
        │       ├── json1.py     # JSON1 extension
        │       ├── fts3_4.py    # FTS3/FTS4 full-text search
        │       ├── fts5.py      # FTS5 full-text search
        │       ├── rtree.py     # R-Tree spatial index
        │       └── geopoly.py   # Geopoly polygon
        │
        └── pragma/              # PRAGMA management
            ├── __init__.py
            ├── base.py          # PRAGMA base class
            ├── compile_time.py  # Compile-time PRAGMAs
            ├── config.py        # Configuration PRAGMAs
            ├── debug.py         # Debug PRAGMAs
            ├── info.py          # Information PRAGMAs
            ├── performance.py   # Performance PRAGMAs
            └── wal.py           # WAL-related PRAGMAs
```

## Independent Backend Packages

The following backends are distributed as independent packages, following the naming convention `rhosocial-activerecord-{backend}`:

### MySQL (`python-activerecord-mysql`)

```text
impl/mysql/
├── __init__.py
├── __main__.py              # CLI entry point
├── backend.py               # MySQLBackend (sync)
├── async_backend.py         # AsyncMySQLBackend (async)
├── config.py                # MySQL connection configuration
├── dialect.py               # MySQL dialect
├── transaction.py           # Sync transaction management
├── async_transaction.py     # Async transaction management
├── types.py                 # MySQL-specific types (ENUM, SET)
├── adapters.py              # Type adapters
├── functions.py             # MySQL-specific functions (JSON, spatial, full-text)
├── mixins.py                # MySQL-specific Mixins
└── protocols.py             # MySQL-specific protocols
```

**Driver Dependencies**:

- Sync: `mysql-connector-python`
- Async: `aiomysql` (optional, via lazy loading)

### PostgreSQL (`python-activerecord-postgres`)

```text
impl/postgres/
├── __init__.py
├── __main__.py              # CLI entry point
├── config.py                # PostgreSQL connection configuration
├── dialect.py               # PostgreSQL dialect
├── transaction.py           # Transaction management
├── statements.py            # PostgreSQL-specific statements
├── type_compatibility.py    # Type compatibility mapping
├── mixins.py                # PostgreSQL-specific Mixins
├── protocols.py             # PostgreSQL-specific protocols
│
├── backend/                 # Backend implementation
│   ├── __init__.py
│   ├── base.py              # Shared base class
│   ├── sync.py              # PostgresBackend (sync)
│   └── async_backend.py     # AsyncPostgresBackend (async)
│
├── types/                   # PostgreSQL-specific types
│   ├── json.py              # JSON/JSONB
│   ├── array.py             # Array types
│   ├── range.py             # Range types
│   ├── geometric.py         # Geometric types
│   ├── network_address.py   # Network address types
│   └── ...                  # Other types
│
├── adapters/                # Type adapters
│   ├── json.py
│   ├── geometric.py
│   ├── range.py
│   └── ...
│
└── functions/               # PostgreSQL-specific functions
    ├── json.py              # JSON functions
    ├── geometric.py         # Geometric functions
    ├── range.py             # Range functions
    └── ...
```

**Driver Dependencies**:

- `psycopg` (version 3.x) - Supports both sync and async

## Core Components

### StorageBackend / AsyncStorageBackend

Abstract base classes for backends, implementing full functionality through Mixin composition:

```python
class StorageBackend(
    StorageBackendBase,
    LoggingMixin,
    TypeAdaptionMixin,
    SQLBuildingMixin,
    ReturningClauseMixin,
    ResultProcessingMixin,
    SQLOperationsMixin,
    ExecutionMixin,
    ExecutionHooksMixin,
    ConnectionMixin,
    TransactionManagementMixin,
    ABC,
):
    """Synchronous storage backend abstract base class."""

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def ping(self, reconnect: bool = True) -> bool: ...

    @abstractmethod
    def get_server_version(self) -> tuple: ...
```

### Dialect Protocol System

Defines optional advanced features through Protocols, supporting fine-grained capability detection:

```python
from rhosocial.activerecord.backend.dialect import (
    SQLDialectBase,
    WindowFunctionSupport,
    CTESupport,
    ReturningSupport,
    UpsertSupport,
    JSONSupport,
    ArraySupport,
    # ... more protocols
)

# Check feature support
dialect = SQLiteDialect()
if isinstance(dialect, WindowFunctionSupport):
    if dialect.supports_window_functions():
        # Use window functions
        pass
```

**Available Protocols**:

- **Query Features**: `WindowFunctionSupport`, `CTESupport`, `AdvancedGroupingSupport`, `SetOperationSupport`, `JoinSupport`, `WildcardSupport`, `DqlOrderSupport`, `CollationSupport`
- **Data Operations**: `ReturningSupport`, `UpsertSupport`, `MergeSupport`, `FilterClauseSupport`
- **Data Types**: `JSONSupport`, `ArraySupport`, `DataTypeSupport`, `DateTimeSupport`
- **Query Optimization**: `ExplainSupport`, `PivotSupport`, `OrderedSetAggregationSupport`
- **Concurrency Control**: `LockingSupport`, `QualifyClauseSupport`, `TransactionControlSupport`
- **DDL Operations**: `CreateTableSupport`, `DropTableSupport`, `AlterTableSupport`, `CreateViewSupport`, `DropViewSupport`, `MaterializedViewSupport`, `CreateIndexSupport`, `DropIndexSupport`, `FulltextIndexSupport`, `PartitionSupport`, `CreateSequenceSupport`, `CreateTypeSupport`, `CreateDomainSupport`, `CreateRoutineSupport`, `CreateTriggerSupport`, `CreateSchemaSupport`, `CreateDatabaseSupport`, `ConstraintSupport`, `CommentSupport`, `TruncateSupport`
- **Object Naming**: `TableObjectSupport`, `ViewObjectSupport`, `MaterializedViewObjectSupport`, `ForeignTableObjectSupport`, `IndexObjectSupport`, `SequenceObjectSupport`, `TypeObjectSupport`, `RoutineObjectSupport`, `TriggerObjectSupport`, `SynonymObjectSupport`, `NamespaceSupport`
- **Advanced Features**: `LateralJoinSupport`, `TemporalTableSupport`, `GraphSupport`, `GraphTableSupport`, `ILIKESupport`, `SQLXMLSupport`, `IntrospectionSupport`

`NamespaceSupport` is the naming protocol, not a DDL one: it answers whether a name may be
qualified with a catalog or a schema. Whether the engine *has* those objects is a separate
question answered by `CreateSchemaSupport` / `CreateDatabaseSupport`, and an engine can
answer the two differently — PostgreSQL has a database and qualifies names with it, while
its `CREATE SCHEMA` support is a separate matter entirely.

### Expression System

SQL expression building blocks, following the Expression-Dialect separation pattern:

```python
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall,
    QueryExpression, InsertExpression, UpdateExpression,
    CTEExpression,
    # Function factories
    count, sum_, avg, row_number, rank,
    json_extract, array_agg,
)

# Expressions delegate to dialect for formatting
# Expression.to_sql() -> Dialect.format_*() -> SQL string and parameters
```

### Type Adapters

Convert between Python types and database types:

```python
from rhosocial.activerecord.backend.type_adapter import (
    SQLTypeAdapter,
    DateTimeAdapter,
    JSONAdapter,
    UUIDAdapter,
    EnumAdapter,
    BooleanAdapter,
    DecimalAdapter,
    ArrayAdapter,
)

# Adapters are stateless and thread-safe
adapter = DateTimeAdapter()
db_value = adapter.to_database(datetime.now(), str)  # ISO format string
py_value = adapter.from_database("2024-01-01T00:00:00", datetime)
```

### Transaction Management

Supports nested transactions (via savepoint) and isolation level control:

```python
from rhosocial.activerecord.backend.transaction import (
    TransactionManager,
    AsyncTransactionManager,
    IsolationLevel,
    TransactionState,
)

# Sync transaction
with backend.transaction_manager.transaction():
    # Nested transactions automatically use savepoints
    with backend.transaction_manager.transaction():
        # ...
        pass

# Async transaction
async with backend.transaction_manager.transaction():
    # ...
    pass
```

### Dummy Backend

For generating SQL without an actual database connection:

```python
from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend

backend = DummyBackend()
# All operations requiring a real connection will raise NotImplementedError
# But SQL generation works correctly
```

## Database Feature Comparison

| Feature | SQLite | MySQL | PostgreSQL |
|---------|--------|-------|------------|
| **RETURNING Support** | ✅ v3.35.0+ | ❌ | ✅ All versions |
| **CTE** | ✅ v3.8.3+ | ✅ v8.0+ | ✅ All versions |
| **Recursive CTE** | ✅ | ✅ v8.0+ | ✅ |
| **Window Functions** | ✅ v3.25.0+ | ✅ v8.0+ | ✅ |
| **JSON Operations** | ✅ v3.38.0+ | ✅ | ✅ (JSONB) |
| **Array Types** | ❌ | ❌ | ✅ |
| **Upsert** | ✅ ON CONFLICT | ✅ ON DUPLICATE KEY | ✅ ON CONFLICT |
| **MERGE** | ❌ | ✅ | ✅ |
| **LATERAL JOIN** | ❌ | ✅ v8.0.14+ | ✅ |
| **Graph Queries** | ❌ | ❌ | ❌ (planned) |
| **Async Support** | ✅ (aiosqlite) | ✅ (aiomysql) | ✅ (psycopg async) |

## Usage Examples

### Basic Configuration

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend

class User(ActiveRecord):
    id: int
    name: str
    email: str

    class Meta:
        table_name = "users"

# Configure backend
User.configure(
    connection_config={"database": "app.db"},
    backend_class=SQLiteBackend
)
```

### Dynamic Backend Loading

```python
def create_backend(backend_type: str, **config):
    """Factory function to create backend instances."""
    if backend_type == 'sqlite':
        from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
        return SQLiteBackend(**config)
    elif backend_type == 'mysql':
        from rhosocial.activerecord.backend.impl.mysql.backend import MySQLBackend
        return MySQLBackend(**config)
    elif backend_type == 'postgres':
        rhosocial.activerecord.backend.impl.postgres.backend import PostgresBackend
        return PostgresBackend(**config)
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")
```

### Async Backend Usage

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import AsyncSQLiteBackend

async def main():
    backend = AsyncSQLiteBackend(database=":memory:")
    await backend.connect()

    async with backend.transaction_manager.transaction():
        # Execute query
        result = await backend.execute("SELECT * FROM users")
        print(result.rows)

    await backend.disconnect()
```

## Design Benefits

1. **Extensibility**: Adding new database support requires no changes to core code
2. **Testability**: DummyBackend supports database-free testing
3. **Flexibility**: Protocol system supports runtime feature detection
4. **Code Reuse**: Mixin composition avoids duplication, sync/async share logic
5. **Type Safety**: Complete type hints, supporting IDE auto-completion
6. **Decoupling**: Core package has no concrete database driver dependencies
