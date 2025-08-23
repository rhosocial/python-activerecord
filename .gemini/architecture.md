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
    BaseActiveRecord           # Core CRUD
):
    pass
```

### 3. Backend Layer

**Location**: `backend/`

**Purpose**: Database abstraction and operations

```python
# backend/base.py
class StorageBackend(ABC):
    """Abstract storage backend interface."""
    
    @abstractmethod
    def execute(self, sql: str, params: Dict) -> QueryResult:
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

@runtime_checkable
class TypeConverter(Protocol):
    """Type conversion protocol."""
    
    def can_handle(self, value: Any) -> bool: ...
    def to_database(self, value: Any) -> Any: ...
    def from_database(self, value: Any) -> Any: ...
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
```

### 4. Builder Pattern

**Implementation**: Query construction

```python
class QueryBuilder:
    def __init__(self, model_class):
        self.model_class = model_class
        self.conditions = {}
        self.ordering = []
        
    def where(self, **conditions):
        self.conditions.update(conditions)
        return self
        
    def order_by(self, *fields):
        self.ordering.extend(fields)
        return self
        
    def build(self):
        # Construct SQL
        pass

# Usage
users = User.where(age__gte=18).order_by("-created_at").limit(10)
```

### 5. Registry Pattern

**Purpose**: Manage type converters and backends

```python
class TypeRegistry:
    """Central registry for type converters."""
    
    def __init__(self):
        self._converters: List[TypeConverter] = []
    
    def register(self, converter: TypeConverter):
        self._converters.append(converter)
        self._converters.sort(key=lambda c: c.priority, reverse=True)
    
    def find_converter(self, value: Any) -> Optional[TypeConverter]:
        for converter in self._converters:
            if converter.can_handle(value):
                return converter
        return None
```

### 6. Template Method Pattern

**Purpose**: Define algorithm skeleton in base class

```python
class StorageBackend(ABC):
    """Template for query execution."""
    
    def execute(self, sql: str, params: Dict) -> QueryResult:
        # Template method
        sql = self._prepare_sql(sql, params)
        cursor = self._get_cursor()
        
        try:
            self._execute_query(cursor, sql, params)
            result = self._fetch_results(cursor)
            self._commit_if_needed()
            return result
        except Exception as e:
            self._handle_error(e)
            raise
    
    # Hook methods for subclasses
    @abstractmethod
    def _prepare_sql(self, sql: str, params: Dict) -> str: ...
    
    @abstractmethod
    def _execute_query(self, cursor, sql: str, params: Dict): ...
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
    └── IActiveRecord (Interface)
        └── BaseActiveRecord (Core implementation)
            └── QueryMixin
                └── RelationManagementMixin
                    └── ActiveRecord (Full implementation)
                        └── User, Post, etc. (User models)
```

### Backend Hierarchy

```
StorageBackend (ABC)
    ├── SQLBackend (Common SQL operations)
    │   ├── SQLiteBackend
    │   ├── MySQLBackend
    │   └── PostgreSQLBackend
    └── NoSQLBackend (Future)
        ├── MongoDBBackend
        └── RedisBackend
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
User.where(name="John")
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
        return cls.where(email=email).first()
    
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

### 2. Query Caching

```python
class CachedQueryMixin:
    _query_cache = {}
    
    @classmethod
    def where(cls, **conditions):
        cache_key = (cls.__name__, frozenset(conditions.items()))
        
        if cache_key in cls._query_cache:
            return cls._query_cache[cache_key]
        
        result = super().where(**conditions)
        cls._query_cache[cache_key] = result
        return result
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

### Connection Management

```python
import threading

class ThreadSafeBackend(StorageBackend):
    def __init__(self, config):
        self.config = config
        self._local = threading.local()
    
    @property
    def connection(self):
        if not hasattr(self._local, 'connection'):
            self._local.connection = self.create_connection()
        return self._local.connection
```

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