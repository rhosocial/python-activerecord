# rhosocial-activerecord Architecture Document

## Core Architecture Components

### 1. Expression-Dialect System

The Expression-Dialect System is the core query building component of rhosocial-activerecord, which achieves separation between database-agnostic SQL query building and database-specific SQL generation.

#### Architectural Principles
- **Expression classes** implement the `ToSQLProtocol` interface, defining how to generate SQL
- **Each expression class** must call its dialect's `format_*` methods instead of self-formatting
- **Dialect classes** are responsible for the actual SQL formatting and parameter handling
- **Expression classes** should never directly concatenate SQL strings; they should delegate to dialect
- This pattern ensures each dialect can customize formatting behavior while maintaining security

#### Relationship Model
```
Expression.to_sql() -> Dialect.format_*() -> SQL string and parameters
```

#### Main Modules
- `bases.py`: Abstract base classes and protocol definitions
- `core.py`: Core expression components (columns, literals, function calls, subqueries)
- `mixins.py`: Mixin classes that provide operator-overloading capabilities
- `operators.py`: SQL operations (binary, unary, arithmetic expressions)
- `predicates.py`: SQL predicate expressions (WHERE clause conditions)
- `query_parts.py`: SQL query clauses (WHERE, GROUP BY, HAVING, ORDER BY, etc.)
- `statements.py`: DML/DQL/DDL statements (SELECT, INSERT, UPDATE, DELETE, etc.)
- `functions.py`: Standalone factory functions for creating SQL expression objects
- `aggregates.py`: Expressions related to SQL aggregation and aggregate functions
- `advanced_functions.py`: Advanced SQL functions and expressions (CASE, CAST, EXISTS, window functions, etc.)
- `query_sources.py`: Data source expressions (VALUES, table functions, lateral joins, CTEs, etc.)
- `graph.py`: SQL Graph Query (MATCH) expression building blocks

#### Important Limitations
The expression system faithfully builds SQL according to user intent, but **does not validate** whether the generated SQL complies with SQL standards or can be successfully executed in the target database. Semantic validation is the responsibility of the database engine.

### 2. Backend System

The backend system is responsible for database connection management and actual SQL execution.

#### Main Components
- `StorageBackend`: Base class for storage backends
- `SQLDialectBase`: Base class for SQL dialects
- Concrete implementations: `sqlite`, `dummy`, etc.

### 3. Model Layer

The model layer provides the implementation of the Active Record pattern.

#### Main Components
- `ActiveRecord`: Base class for the Active Record pattern
- `FieldProxy`: Field proxy that bridges the gap between Python objects and SQL queries
- Mixins: `UUIDMixin`, `TimestampMixin`, etc.

### 4. Query Interface

The query interface provides a fluent, type-safe query API.

#### Main Components
- `ActiveQuery`: Most commonly used query object bound to ActiveRecord models
- `CTEQuery`: Query object for building Common Table Expressions (CTEs)
- `SetOperationQuery`: Set operation query object

## Design Patterns

### Sync-Async Parity
Synchronous and asynchronous implementations provide equivalent functionality with unified APIs.

### Gradual ORM
Balancing strict type safety (OLTP) with raw performance (OLAP).

### Layered Architecture
Clear distinction between Backend and ActiveRecord, avoiding tight coupling between database connection management and model definition in traditional ORMs.

## Core Architectural Principles

### 1. Independence from Existing ORMs
- **No ORM Dependencies**: Built from scratch without relying on SQLAlchemy, Django ORM, or other ORMs
- **Direct Driver Interaction**: Backends interact directly with database drivers
- **Lightweight Core**: Core functionality requires only Pydantic

### 2. Open-Closed Principle
- **Open for Extension**: New backends can be added without modifying core code
- **Closed for Modification**: Core interfaces remain stable
- **Implementation**: Protocol-based design with abstract base classes

### 3. Dependency Inversion
- High-level modules (ActiveRecord) don't depend on low-level modules (backends)
- Both depend on abstractions (interfaces)
- Dependency injection through configuration

### 4. Single Responsibility
- Each module has one clear purpose
- Backends handle database-specific details
- Models handle business logic
- Query builders handle query construction

### 5. Consistent SQL Identifier and Literal Formatting (Single Point of Call)

**Purpose**: Ensure all database identifiers (table names, column names, aliases) and literal values are consistently and correctly formatted according to the specific database dialect. This is crucial for conforming to dialect-specific quoting rules (e.g., `"name"`, ``` `name` ```, `[name]`) and ensuring broad compatibility.

**Security Note**: While proper identifier formatting is essential for SQL correctness, the primary mechanism for preventing SQL injection vulnerabilities in this project is the use of **SQL placeholders and parameter separation**, ensuring that literal values are always bound securely and never concatenated directly into the SQL query string.

**Implementation**: The `SQLDialectBase` (and its concrete implementations like `SQLiteDialect`) provides dedicated methods for this:
- `format_identifier(self, identifier: str) -> str`: Formats and quotes identifiers.
- `format_string_literal(self, value: str) -> str`: Formats and quotes string literals.

All query building components (e.g., mixins, `SQLExpression` subclasses) are designed to route identifier and literal formatting through these dialect methods, ensuring a single, centralized point of control for SQL syntax generation.

```python
# In backend/dialect.py
class SQLDialectBase(ABC):
    @abstractmethod
    def format_identifier(self, identifier: str) -> str:
        """Format identifier (table name, column name)."""
        pass

    @abstractmethod
    def format_string_literal(self, value: str) -> str:
        """Format string literal."""
        pass

# Usage in query builder (conceptual)
# formatted_column = self.model_class.backend().dialect.format_identifier(column_name)
# formatted_string = self.model_class.backend().dialect.format_string_literal(string_value)
```

## Package Architecture

### Package Structure

```
rhosocial-activerecord/          # Core package (PEP 420 namespace package - no __init__.py at
├── src/rhosocial/activerecord/  #   the activerecord/ and backend/ levels; see below)
│   │   ├── bulk_operations.py  # Bulk operations support
│   │   ├── column_name_mixin.py # Column name handling mixin
│   │   ├── derived_field_handler.py # Derived field handler
│   │   ├── derived_field_mixin.py # Derived field mixin
│   │   ├── field_adapter_mixin.py # Field adapter mixin
│   │   ├── field_proxy.py      # Field proxy implementation
│   │   ├── fields.py           # Field definitions
│   │   ├── metaclass.py        # Model metaclass
│   │   └── query_mixin.py      # Query functionality mixin
│   ├── field/                  # Field mixins and types
│   │   ├── __init__.py
│   │   ├── composite_pk.py     # Composite primary key mixin
│   │   ├── integer_pk.py       # Integer primary key mixin
│   │   ├── README.md
│   │   ├── soft_delete.py      # Soft delete mixin
│   │   ├── timestamp.py        # Timestamp mixin
│   │   ├── uuid.py             # UUID mixin
│   │   └── version.py          # Version mixin
│   ├── interface/              # Public API interfaces
│   │   ├── __init__.py
│   │   ├── base.py             # Base interfaces
│   │   ├── model.py            # Model interface
│   │   ├── query.py            # Query interface
│   │   ├── update.py           # Update interface
│   ├── query/                  # Query building components
│   │   ├── __init__.py
│   │   ├── active_query.py     # Main query interface
│   │   ├── aggregate.py        # Aggregate query functionality
│   │   ├── async_join.py       # Async join functionality
│   │   ├── async_relational.py # Async relational query functionality
│   │   ├── base.py             # Base query functionality
│   │   ├── cte_query.py        # CTE query functionality
│   │   ├── join.py             # Join query functionality
│   │   ├── range.py            # Range query functionality
│   │   ├── relational.py       # Relational query functionality
│   │   ├── set_operation.py    # Set operation query functionality
│   │   └── utils.py            # Query utilities (placeholder conversion, etc.)
│   ├── relation/               # Relationship components
│   │   ├── __init__.py
│   │   ├── async_descriptors.py # Async relationship descriptors
│   │   ├── base.py             # Base relationship functionality
│   │   ├── cache.py            # Relationship caching
│   │   ├── cache_backend.py    # Cache backend abstraction
│   │   ├── cache_backends/     # Cache backend implementations (in_memory, redis)
│   │   ├── descriptors.py      # Relationship descriptors
│   │   ├── interfaces.py       # Relationship interfaces
│   │   └── type_resolver.py    # Relation type resolver
│   ├── model.py                # ActiveRecord + AsyncActiveRecord classes
│   ├── connection/             # Named connection support
│   ├── logging/                # Logging infrastructure
│   ├── worker/                 # Background worker support
│   ├── types.py
│   └── backend/                # Backend abstraction and implementations
│       ├── base/               # Backend base classes
│       │   ├── __init__.py
│       │   └── base.py         # StorageBackend base class
│       ├── dialect/            # SQL dialect implementations
│       │   ├── __init__.py
│       │   └── base.py         # SQLDialect base class
│       ├── expression/         # Expression system
│       │   ├── __init__.py     # Expression system entry point
│       │   ├── advanced_functions.py # Advanced SQL functions (CASE, CAST, etc.)
│       │   ├── aggregates.py   # Aggregate function expressions
│       │   ├── bases.py        # Base expression classes and protocols
│       │   ├── collation.py    # Collation expressions
│       │   ├── core.py         # Core expressions (Column, Literal, etc.)
│       │   ├── datetime.py     # Date/time expressions
│       │   ├── executable.py   # Executable expression support
│       │   ├── functions/      # Factory functions (directory package)
│       │   ├── graph.py        # Graph query expressions
│       │   ├── introspection.py # Introspection expressions
│       │   ├── literals.py     # Literal expressions
│       │   ├── mixins.py       # Expression mixins with operator overloading
│       │   ├── operators.py    # SQL operation expressions
│       │   ├── predicates.py   # Predicate expressions
│       │   ├── query_parts.py  # Query clause expressions
│       │   ├── query_sources.py # Query source expressions
│       │   ├── serialization.py # Expression serialization
│       │   ├── statements/     # SQL statement expressions (directory package)
│       │   ├── transaction.py  # Transaction-related expressions
│       │   ├── types/          # Type-related expressions (directory package)
│       │   └── xml.py          # SQL/XML expressions
│       ├── impl/               # Backend implementations
│       │   ├── dummy/          # Dummy backend for testing
│       │   │   ├── __init__.py
│       │   │   ├── backend.py
│       │   │   └── dialect.py
│       │   └── sqlite/         # SQLite backend implementation
│       │       ├── __init__.py
│       │       ├── __main__.py
│       │       ├── adapters.py # SQLite type adapters
│       │       ├── backend/    # Backend implementation (directory package)
│       │       │   ├── sync.py         # SQLiteBackend
│       │       │   ├── async_backend.py # AsyncSQLiteBackend
│       │       │   └── common.py
│       │       ├── config.py   # SQLite configuration
│       │       ├── dialect.py  # SQLite dialect implementation
│       │       ├── transaction.py # SQLite transaction handling
│       │       ├── async_transaction.py # SQLite async transaction handling
│       │       ├── expression/ # SQLite-specific expressions
│       │       ├── functions/  # SQLite-specific SQL functions
│       │       ├── mixins/     # SQLite dialect mixins
│       │       ├── extension/  # SQLite extensions (FTS5, RTree, etc.)
│       │       ├── pragma/     # PRAGMA support
│       │       ├── explain/    # EXPLAIN support
│       │       ├── introspection/ # SQLite introspection
│       │       ├── schema/     # SQLite schema helpers
│       │       ├── protocols.py # SQLite protocol declarations
│       │       ├── cli/        # SQLite CLI tools
│       │       └── examples/   # SQLite examples
│       ├── config.py           # Backend configuration base classes
│       ├── errors.py           # Backend-specific errors
│       ├── helpers.py          # Backend helper functions
│       ├── options.py          # Backend options
│       ├── output_abc.py       # Output abstraction
│       ├── output_rich.py      # Rich output implementation
│       ├── output.py           # Output utilities
│       ├── protocols.py        # Backend protocol declarations
│       ├── README.md           # Backend documentation
│       ├── result.py           # Query result handling
│       ├── schema/             # Schema management (directory package: snapshot, differ, ...)
│       ├── transaction.py      # Transaction base classes
│       ├── type_adapter.py     # Type adaptation system
│       └── type_registry.py    # Type adapter registry
```

> Note: `src/rhosocial/activerecord/` and `backend/` are **PEP 420 namespace packages** — they
> intentionally have **no `__init__.py`**, so extension backends
> (`rhosocial-activerecord-mysql`, `rhosocial-activerecord-postgres`, ...) can drop their
> packages into `backend/impl/{name}/` without modifying core. The tree above is representative,
> not exhaustive; the project evolves quickly and additional modules/subpackages may exist.

### Namespace Package Structure

The `rhosocial.activerecord` package uses **PEP 420 implicit namespace packages** (no
`__init__.py` at the `activerecord/` and `backend/` levels). This allows multiple distributions
to contribute to the same namespace: the core package provides `base/`, `query/`, `relation/`,
`backend/impl/dummy/`, `backend/impl/sqlite/`, etc., while extension projects ship their own
`backend/impl/{name}/` directory (e.g., `mysql`, `postgres`) in separate distributions.

```python
# No __init__.py and no pkgutil.extend_path() is required anywhere in the core package.
# Python's namespace-package mechanism resolves the merged package automatically when the
# core and extension distributions are installed side by side.
```

This allows multiple packages to contribute to the same namespace, enabling distributed backend implementations.

## Layer Architecture

### 1. Interface Layer

**Location**: `interface/`

**Purpose**: Define contracts for all components

```python
# interface/model.py
class IActiveRecord(ActiveRecordBase):  # ActiveRecordBase(BaseModel, ABC)
    """Core ActiveRecord interface."""

    @abstractmethod
    def save(self) -> int:
        """Save record to database; returns number of affected rows."""
        pass

    @abstractmethod
    def delete(self) -> int:
        """Delete record from database; returns number of affected rows."""
        pass

    # Additional abstract members (find_one, find_all, find_one_or_fail, refresh(), ...)
```

> Note: `save()`/`delete()` return `int` (affected row count), not `bool`. An
> `IAsyncActiveRecord` parallel interface also exists.

### 2. Model Layer

**Location**: `base/`, main `ActiveRecord` class

**Purpose**: Business logic and data management

```python
# model.py - composition through mixins (sync)
class ActiveRecord(
    RelationManagementMixin,  # Relationship handling
    QueryMixin,                # Query capabilities
    ColumnNameMixin,           # Column name mapping
    FieldAdapterMixin,         # Field-specific type adaptation
    DerivedFieldMixin,         # Derived/computed fields
    MetaclassMixin,            # Metaclass-based feature handling
    BaseActiveRecord           # Core CRUD
):
    pass

# A parallel AsyncActiveRecord uses AsyncQueryMixin + AsyncBaseActiveRecord.
```

### 3. Backend Layer

**Location**: `backend/base/` (base classes), `backend/impl/` (implementations)

**Purpose**: Database abstraction and operations

```python
# backend/base/base.py -> StorageBackendBase (ABC)
# backend/base/__init__.py -> composed StorageBackend / AsyncStorageBackend
class StorageBackend(
    # ...composed from LoggingMixin, CapabilityMixin, TypeAdaptionMixin, SQLBuildingMixin, etc.
    ABC
):
    """
    Abstract storage backend, primarily composed from various functional mixins.
    Its `execute` method acts as a template method orchestrating these mixins.
    """

    # The actual execute method is a template method, coordinating mixins
    def execute(self, sql: str, params: Dict, **kwargs) -> QueryResult:
        # ... implementation coordinates mixins for connection, parsing,
        #     returning clause, cursor, SQL building, execution, result processing ...
        pass
```

### 4. Implementation Layer

**Location**: `backend/impl/`

**Purpose**: Concrete database implementations

```python
# backend/impl/sqlite/backend/sync.py
class SQLiteBackend(StorageBackend):
    """SQLite-specific implementation."""

    def execute(self, sql: str, params: Dict) -> QueryResult:
        # SQLite-specific execution
        pass
```

## Design Patterns

### 1. Active Record Pattern

**Implementation**: Core pattern of the library

```python
class User(ActiveRecord):
    __table_name__ = "users"

    name: str
    email: str

# Usage
user = User(name="John", email="john@example.com")
user.save()  # Persists to database
```

**Benefits**:
- Intuitive API
- Encapsulated persistence logic
- Domain model and data access combined

### 2. Protocol Pattern

**Purpose**: Define interfaces without inheritance

```python
from typing import Protocol, runtime_checkable

# Example: SQLTypeAdapter protocol
from typing import Protocol, runtime_checkable, Any, Type, Dict, Optional

@runtime_checkable
class SQLTypeAdapter(Protocol):
    """Protocol for type conversion between Python and database values."""

    def to_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any: ...
    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any: ...

    @property
    def supported_types(self) -> Dict[Type, Set[Type]]: ...
```

**Benefits**:
- Duck typing with type safety
- No forced inheritance hierarchy
- Runtime type checking available

### 3. Mixin Pattern

**Purpose**: Composable functionality

```python
class TimestampMixin:
    """Add timestamp tracking."""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

class SoftDeleteMixin:
    """Add soft delete capability."""
    deleted_at: Optional[datetime] = None

    def delete(self):
        self.deleted_at = datetime.now()
        return self.save()

# Composition
class Article(TimestampMixin, SoftDeleteMixin, ActiveRecord):
    __table_name__ = "articles"
    title: str
    content: str

# Mixins are also extensively used for backend composition (e.g., StorageBackend in backend/base/)
# providing modular and reusable components for database interaction.
```

### 4. Builder Pattern

**Implementation**: Query construction

```python
# The project's query builder is ActiveQuery, composed from specialized mixins.
from rhosocial.activerecord.query import (
    ActiveQuery, BaseQueryMixin, AggregateQueryMixin, JoinQueryMixin,
    RangeQueryMixin, RelationalQueryMixin,
)

class ActiveQuery(
    AggregateQueryMixin,
    BaseQueryMixin,
    JoinQueryMixin,
    RelationalQueryMixin,
    RangeQueryMixin,
    IActiveQuery,
    ISetOperationQuery,
):
    """
    Complete ActiveQuery implementation, combining all query mixins.
    It builds SQL by collecting conditions, orders, joins, etc.,
    and delegates to its mixins for specific functionalities.

    NOTE: CTE queries are built with a separate CTEQuery class (cte_query.py),
    which is NOT part of ActiveQuery's inheritance.
    """
    pass
```

### 5. Registry Pattern

**Purpose**: Manage type converters and backends

```python
# The project uses backend.type_registry.TypeRegistry for SQLTypeAdapter instances
from typing import Dict, Tuple, Type, Optional
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter

class TypeRegistry:
    """Central registry for SQLTypeAdapter instances."""
    def __init__(self):
        self._adapters: Dict[Tuple[Type, Type], SQLTypeAdapter] = {}

    def register(self, adapter: SQLTypeAdapter, py_type: Type, db_type: Type) -> None:
        self._adapters[(py_type, db_type)] = adapter

    def get_adapter(self, py_type: Type, db_type: Type) -> Optional[SQLTypeAdapter]:
        return self._adapters.get((py_type, db_type))
```

### 6. Template Method Pattern

**Purpose**: Define algorithm skeleton in base class

```python
# The execute method in StorageBackend acts as a Template Method
# Located in backend/base/ (StorageBackendBase in base.py; the composed StorageBackend
# and AsyncStorageBackend in __init__.py). Mixin names below are illustrative of the
# responsibilities; concrete composition lives in backend/base/.
class StorageBackend(
    # ...composed from various functional mixins like SQLBuildingMixin,
    # QueryAnalysisMixin, ReturningClauseMixin, ResultProcessingMixin, etc.
    ABC
):
    """
    Abstract storage backend. Its `execute` method is a Template Method
    that orchestrates the query execution process by coordinating its
    composed functional mixins.
    """

    # This is the actual Template Method
    def execute(self, sql: str, params: Optional[Tuple] = None, **kwargs) -> QueryResult:
        # 1. Start timer
        # 2. Log SQL and parameters
        # 3. Handle connection setup (if not already connected)
        # 4. Parse statement type (via QueryAnalysisMixin)
        # 5. Process RETURNING clause (via ReturningClauseMixin)
        # 6. Get cursor
        # 7. Prepare SQL and parameters (via SQLBuildingMixin)
        # 8. Execute query (hook method `_execute_query` in concrete backend)
        # 9. Process results (via TypeAdaptionMixin, ResultProcessingMixin)
        # 10. Log completion
        # 11. Build QueryResult
        # 12. Handle auto-commit (hook method `_handle_auto_commit_if_needed`)
        # 13. Handle errors (hook method `_handle_execution_error`)
        pass

    # Hook methods (some are abstract in StorageBackend, others in mixins)
    @abstractmethod
    def _execute_query(self, cursor, sql: str, params: Optional[Tuple]): ...
    # ... other abstract hook methods like connect(), disconnect(), etc.
```

### 7. Backend Registration and Binding

There is **no generic `create_backend()` factory function** in the core package. Backends are
bound to a model via `configure()`, which instantiates the backend under the hood.

```python
# configure() builds the backend from a config + backend_class and binds it to the model.
User.configure(config, SQLiteBackend)   # or MySQLBackend, PostgresBackend, etc.
# -> internally: cls.__backend__ = backend_class(connection_config=config, ...)
#    and calls backend.introspect_and_adapt()
```

Because all backends share a namespace package (`rhosocial.activerecord.backend.impl.{name}`),
each backend can be imported and configured independently without a central factory mapping
backend names to classes.

## Class Hierarchy

### Model Hierarchy

```
BaseModel (Pydantic)
    └── IActiveRecord (Interface - implemented by BaseActiveRecord)
        └── BaseActiveRecord / AsyncBaseActiveRecord (Core implementations)
            # ActiveRecord is composed from these mixins and BaseActiveRecord
            └── RelationManagementMixin
            └── QueryMixin            # AsyncActiveRecord uses AsyncQueryMixin
            └── ColumnNameMixin
            └── FieldAdapterMixin
            └── DerivedFieldMixin
            └── MetaclassMixin
                └── ActiveRecord (Full sync implementation)
                └── AsyncActiveRecord (Full async implementation)
                    └── User, Post, etc. (User models)
```

Note: The actual composition (`model.py`) is `ActiveRecord(RelationManagementMixin,
QueryMixin, ColumnNameMixin, FieldAdapterMixin, DerivedFieldMixin, MetaclassMixin,
BaseActiveRecord)`, and a parallel `AsyncActiveRecord` class exists for async support.

### Backend Hierarchy

```
StorageBackendBase (ABC)                # backend/base/base.py
    # Composed from mixins for sync operations
    └── StorageBackend (ABC)            # backend/base/__init__.py
        └── SQLiteBackend               # backend/impl/sqlite/backend/sync.py
        # └── MySQLBackend (extension: rhosocial-activerecord-mysql)
        # └── PostgreSQLBackend (extension: rhosocial-activerecord-postgres)
        # ...

StorageBackendBase (ABC)
    # Composed from mixins for async operations
    └── AsyncStorageBackend (ABC)       # backend/base/__init__.py
        └── AsyncSQLiteBackend          # backend/impl/sqlite/backend/async_backend.py (implemented)
        # └── AsyncMySQLBackend (extension)
        # ...
```

> Note: `StorageBackendBase` lives in `backend/base/base.py`; the composed `StorageBackend` and
> `AsyncStorageBackend` (both ABC) are re-exported from `backend/base/__init__.py`. The async
> SQLite backend is fully implemented.

## Module Interactions

### Configuration Flow

```python
# 1. User configures model
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

class User(ActiveRecord):
    __table_name__ = "users"
    name: str

# 2. Configure backend
config = SQLiteConnectionConfig(database="app.db")
User.configure(config, SQLiteBackend)

# 3. Backend initialized and attached
# User.__backend__ = SQLiteBackend(config)
```

### Query Execution Flow

```
User.query().where("name = ?", ("John",))
    ↓
ActiveQuery.where()  # builds a RawSQLPredicate / typed predicate in the WHERE clause
    ↓
ActiveQuery.to_sql()
    ↓
Backend.execute()
    ↓
Database
    ↓
Backend.fetch_results()
    ↓
Model instantiation
    ↓
User instances
```

## Dependency Management

### Core Dependencies

The project maintains **minimal core dependencies** by design:

```toml
# Minimal core dependencies - Pydantic only
[project]
dependencies = [
    "pydantic==2.10.6; python_version == '3.8'",          # Data validation and model definition
    "pydantic>=2.12.0; python_version >= '3.9'",
    "typing_extensions>=4.0.0",                            # Backported typing features for Python 3.8
]
```

**Important**: This is a **standalone ActiveRecord implementation** with no dependencies on existing ORMs like SQLAlchemy, Django ORM, or others. All database interaction logic is implemented from scratch.

### Optional Dependencies

The core package does **not** depend on any native database driver directly. Backend support is
provided by separate extension distributions, exposed as optional extras:

```toml
[project.optional-dependencies]
mysql = ["rhosocial-activerecord-mysql>=1.0.0,<2.0.0"]    # MySQL backend extension
postgres = ["rhosocial-activerecord-postgres>=1.0.0,<2.0.0"]  # PostgreSQL backend extension
```

Each backend extension depends on its own native driver (e.g., `mysql-connector-python`,
`psycopg`) and ships its own `backend/impl/{name}/` package.

### Backend Discovery

There is **no `discover_backends()` function** in the core package. Backends are imported
explicitly and bound to models via `configure()`:

```python
# Users (or extension entry points) import the backend explicitly.
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
# Installed extensions are importable the same way:
#   from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
#   from rhosocial.activerecord.backend.impl.postgres import PostgresBackend

User.configure(SQLiteConnectionConfig(database="app.db"), SQLiteBackend)
```

## Extension Points

### 1. Custom Fields

```python
class EncryptedField(Field):
    """Custom encrypted field type."""

    def __set__(self, instance, value):
        encrypted = encrypt(value)
        super().__set__(instance, encrypted)

    def __get__(self, instance, owner):
        value = super().__get__(instance, owner)
        return decrypt(value) if value else None
```

### 2. Custom Validators

```python
from pydantic import field_validator

class User(ActiveRecord):
    email: str

    @field_validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v.lower()
```

### 3. Custom Query Methods

```python
class UserQueryMixin:
    @classmethod
    def find_by_email(cls, email: str):
        return cls.query().where("email = ?", (email,)).one()

    @classmethod
    def active_users(cls):
        return cls.query().where(cls.c.is_active == True).all()  # noqa: E712

class User(UserQueryMixin, ActiveRecord):
    pass
```

### 4. Event Hooks

```python
class User(ActiveRecord):
    def before_save(self):
        """Called before saving."""
        self.updated_at = datetime.now()

    def after_save(self):
        """Called after saving."""
        cache.invalidate(f"user:{self.id}")
```

## Performance Optimization

### 0. Lightweight Foundation

The architecture is designed for minimal overhead:
- **No ORM layers**: Direct database driver communication
- **Single dependency**: Only Pydantic required for core functionality
- **Fast startup**: Minimal imports and initialization
- **Low memory footprint**: No heavy framework baggage

### 1. Connection Pooling

```python
class PooledBackend(StorageBackend):
    def __init__(self, config, pool_size=10):
        self.pool = ConnectionPool(config, size=pool_size)

    def get_connection(self):
        return self.pool.acquire()
```

### 2. Relation Caching (Instance-level)

```python
from rhosocial.activerecord.relation.cache import InstanceCache, CacheConfig

# In RelationDescriptor (used by mixins like RelationalQueryMixin)
class RelationDescriptor:
    # ...
    def _load_relation(self, instance: Any) -> Optional[T]:
        """
        Load relation with instance-level caching support.
        """
        cached = InstanceCache.get(instance, self.name, self._cache_config)
        if cached is not None:
            return cached

        data = self._loader.load(instance)
        InstanceCache.set(instance, self.name, data, self._cache_config)
        return data

# Cache configuration can be global or per-relation
global_config = GlobalCacheConfig()
global_config.set_config(enabled=True, ttl=300, max_size=1000)
```

### 3. Lazy Loading

```python
class RelationDescriptor:
    def __get__(self, instance, owner):
        if not hasattr(instance, '_relation_cache'):
            instance._relation_cache = {}

        if self.name not in instance._relation_cache:
            # Load relation only when accessed
            instance._relation_cache[self.name] = self.load(instance)

        return instance._relation_cache[self.name]
```

## Thread Safety

### Key Thread Safety Mechanisms

# The project utilizes specific mechanisms for thread safety:
# 1. ThreadSafeDict for mutable shared state (e.g., query eager loads, _eager_loads in RelationalQueryMixin)
# 2. InstanceCache for per-instance caching (thread-safe for each instance's data)
# 3. Backend connection management (e.g., SQLiteBackend uses sqlite3.connect which can be thread-safe for basic ops,
#    or relies on external connection pooling for more robust solutions in other DBs).

# Example: ThreadSafeDict (from interface/query.py)
from typing import Dict, Any, TypeVar
from threading import local

K = TypeVar('K')
V = TypeVar('V')

class ThreadSafeDict(Dict[K, V]):
    """A thread-safe dictionary that behaves exactly like a normal dict."""
    def __init__(self, *args, **kwargs):
        self._local = local()
        if not hasattr(self._local, 'data'):
            self._local.data = {}
        if args or kwargs:
            self.update(*args, **kwargs)

    def __getitem__(self, key: K) -> V:
        return self._local.data[key]

# InstanceCache for relation caching (from relation/cache.py)
# This design ensures thread-safety by storing cache data on the instance itself
# or using thread-local storage where appropriate, preventing race conditions
# on shared cache structures.

## Error Handling Strategy

### Exception Hierarchy

```python
class ActiveRecordError(Exception):
    """Base exception for all ActiveRecord errors."""

class DatabaseError(ActiveRecordError):
    """Database operation errors."""

class ValidationError(ActiveRecordError):
    """Data validation errors."""

class RecordNotFound(DatabaseError):
    """Record not found in database."""
```

### Error Propagation

```
User Input
    ↓
Validation (ValidationError)
    ↓
Model Operations
    ↓
Backend Operations (DatabaseError)
    ↓
Database Driver (Driver-specific errors)
```

## Testing Architecture

### Test Organization

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests with real databases
├── fixtures/       # Shared test fixtures
└── benchmarks/     # Performance benchmarks
```

### Fixture Pattern

```python
@pytest.fixture
def backend_matrix():
    """Test across multiple backends."""
    backends = []

    # Always test SQLite
    backends.append(SQLiteBackend)

    # Test others if available
    if mysql_available():
        backends.append(MySQLBackend)

    return backends
```