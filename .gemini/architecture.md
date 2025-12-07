# System Architecture and Design Patterns

## Overview

The rhosocial-activerecord project follows a modular, protocol-based architecture that emphasizes extensibility, type safety, and clean separation of concerns. This document describes the core architectural decisions and design patterns used throughout the system.

**Architectural Foundation**: The project is built as a **standalone ActiveRecord implementation** without dependencies on existing ORMs. It uses only Pydantic for data validation and model definition, with all database interaction logic implemented from scratch through a clean backend abstraction layer.

## Core Architecture Principles

### 1. Independence from Existing ORMs
- **No ORM Dependencies**: Built from scratch without relying on SQLAlchemy, Django ORM, or others
- **Direct Driver Interaction**: Backends interact directly with database drivers
- **Lightweight Core**: Only Pydantic is required for the core functionality

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
- Backends handle database specifics
- Models handle business logic
- Query builders handle query construction

### 5. Consistent SQL Identifier and Literal Formatting (Single Point of Call)

**Purpose**: Ensure all database identifiers (table names, column names, aliases) and literal values are consistently and correctly formatted according to the specific database dialect. This is crucial for conforming to dialect-specific quoting rules (e.g., `"name"`, ``` `name` ```, `[name]`) and ensuring broad compatibility.

**Note on Security**: While proper identifier formatting is essential for SQL correctness, the primary mechanism for preventing SQL injection vulnerabilities in this project is the use of **SQL placeholders and parameter separation**, ensuring that literal values are always bound securely and never concatenated directly into the SQL query string.

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

### Namespace Package Structure

```
rhosocial-activerecord/          # Core package
├── src/rhosocial/activerecord/
│   ├── __init__.py             # Namespace extension
│   ├── base/                   # Core functionality
│   ├── field/                  # Field types
│   ├── query/                  # Query building
│   ├── relation/               # Relationships
│   ├── interface/              # Public APIs
│   └── backend/                # Backend abstraction
│       ├── base.py             # Abstract backend
│       └── impl/               # Implementations
│           └── sqlite/         # Built-in SQLite

rhosocial-activerecord-mysql/   # Extension package
└── src/rhosocial/activerecord/
    └── backend/impl/
        └── mysql/               # MySQL implementation
```

### Namespace Extension Mechanism

```python
# Core package __init__.py
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
```

This allows multiple packages to contribute to the same namespace, enabling distributed backend implementations.

## Layer Architecture

### 1. Interface Layer

**Location**: `interface/`

**Purpose**: Define contracts for all components

```python
# interface/model.py
class IActiveRecord(BaseModel, ABC):
    """Core ActiveRecord interface."""
    
    @abstractmethod
    def save(self) -> bool:
        """Save record to database."""
        pass
    
    @abstractmethod
    def delete(self) -> bool:
        """Delete record from database."""
        pass
```

### 2. Model Layer

**Location**: `base/`, main `ActiveRecord` class

**Purpose**: Business logic and data management

```python
# Composition through mixins
class ActiveRecord(
    RelationManagementMixin,  # Relationship handling
    QueryMixin,                # Query capabilities
    FieldAdapterMixin,         # Field-specific type adaptation
    MetaclassMixin,            # Metaclass-based feature handling
    BaseActiveRecord           # Core CRUD
):
    pass
```

### 3. Backend Layer

**Location**: `backend/`

**Purpose**: Database abstraction and operations

```python
# backend/base.py
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
# backend/impl/sqlite/backend.py
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

# Mixins are also extensively used for backend composition (e.g., StorageBackend from backend/base.py)
# providing modular and reusable components for database interaction.
```

### 4. Builder Pattern

**Implementation**: Query construction

```python
# The project's query builder is ActiveQuery, composed from specialized mixins.
from rhosocial.activerecord.query import ActiveQuery, BaseQueryMixin, AggregateQueryMixin, CTEQueryMixin, JoinQueryMixin, RangeQueryMixin, RelationalQueryMixin

class ActiveQuery(
    CTEQueryMixin,
    JoinQueryMixin,
    RelationalQueryMixin,
    RangeQueryMixin,
    # BaseQueryMixin and AggregateQueryMixin are inherited through CTEQueryMixin
):
    """
    Complete ActiveQuery implementation, combining all query mixins.
    It builds SQL by collecting conditions, orders, joins, etc.,
    and delegates to its mixins for specific functionalities.
    """
    pass

# Usage
users = User.query().where("age >= ?", (18,)).order_by("-created_at").limit(10).all()
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

### 7. Factory Pattern

**Purpose**: Create backend instances

```python
def create_backend(backend_type: str, **config) -> StorageBackend:
    """Factory for backend creation."""
    backends = {
        'sqlite': SQLiteBackend,
        'mysql': MySQLBackend,
        'postgresql': PostgreSQLBackend,
    }
    
    backend_class = backends.get(backend_type)
    if not backend_class:
        raise ValueError(f"Unknown backend: {backend_type}")
    
    return backend_class(**config)
```

## Class Hierarchy

### Model Hierarchy

```
BaseModel (Pydantic)
    └── IActiveRecord (Interface - implemented by BaseActiveRecord)
        └── BaseActiveRecord (Core implementation, implements IActiveRecord)
            # ActiveRecord is composed from these mixins and BaseActiveRecord
            └── QueryMixin
            └── RelationManagementMixin
            └── FieldAdapterMixin
            └── MetaclassMixin
                └── ActiveRecord (Full implementation, combines BaseActiveRecord and mixins)
                    └── User, Post, etc. (User models)
```

### Backend Hierarchy

```
StorageBackendBase (ABC)
    # Composed from mixins for sync operations
    └── StorageBackend (ABC)
        └── SQLiteBackend # Concrete implementation
        # └── MySQLBackend (if implemented)
        # └── PostgreSQLBackend (if implemented)

StorageBackendBase (ABC)
    # Composed from mixins for async operations
    └── AsyncStorageBackend (ABC)
        └── # AsyncSQLiteBackend (if implemented)
        # └── AsyncMySQLBackend (if implemented)
```

## Module Interactions

### Configuration Flow

```python
# 1. User configures model
from rhosocial.activerecord import ActiveRecord
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
User.where("name = ?", ("John",))
    ↓
QueryBuilder.where()
    ↓
QueryBuilder.build()
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

```python
# Minimal core dependencies - Pydantic only
dependencies = [
    "pydantic>=2.0.0",  # Data validation and model definition
    "typing_extensions>=4.0.0",  # Backported typing features for Python 3.8
]
```

**Important**: This is a **standalone ActiveRecord implementation** with no dependencies on existing ORMs like SQLAlchemy, Django ORM, or others. All database interaction logic is implemented from scratch.

### Optional Dependencies

```python
extras_require = {
    "mysql": ["mysql-connector-python>=8.0.0"],  # MySQL backend
    "postgresql": ["psycopg2>=2.9.0"],  # PostgreSQL backend
    "dev": ["pytest", "black", "mypy"],  # Development tools
}
```

### Backend Discovery

```python
# Dynamic backend loading - no ORM dependencies
def discover_backends():
    """Discover installed backends."""
    backends = {}
    
    # Check for installed backends (each uses only native drivers)
    try:
        from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
        backends['mysql'] = MySQLBackend  # Uses mysql-connector-python directly
    except ImportError:
        pass
    
    try:
        from rhosocial.activerecord.backend.impl.postgresql import PostgreSQLBackend
        backends['postgresql'] = PostgreSQLBackend  # Uses psycopg2 directly
    except ImportError:
        pass
    
    return backends
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
        return cls.where("email = ?", (email,)).first()
    
    @classmethod
    def active_users(cls):
        return cls.where(is_active=True)

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