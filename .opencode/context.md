# opencode Context - rhosocial-activerecord

## Project Core Positioning

**rhosocial-activerecord** is a **pure Python ActiveRecord implementation**, built from scratch with no dependencies on any existing ORM.

### Fundamental Differences from Other ORMs

| Feature | This Project | SQLAlchemy | Django ORM |
|---------|--------------|------------|------------|
| Dependencies | Pydantic 2.x only | SQLAlchemy-core | Django framework |
| Architecture | Expression-Dialect separation | Core + ORM | Model-centric |
| Async | Native support | 1.4+ | 3.0+ |
| Type Safety | Pydantic validation | SQLAlchemy 2.0 | Limited |

## Core Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      ActiveRecord Layer                      │
│         (BaseActiveRecord / AsyncBaseActiveRecord)           │
├─────────────────────────────────────────────────────────────┤
│                       Query Layer                            │
│    (ActiveQuery / CTEQuery / SetOperationQuery / ...)        │
├─────────────────────────────────────────────────────────────┤
│                     Relation Layer                           │
│              (Relation / RelationCache)                      │
├─────────────────────────────────────────────────────────────┤
│                      Backend Layer                           │
│  ┌─────────────┬─────────────────┬─────────────────────────┐│
│  │Expression   │ Dialect         │ StorageBackend          ││
│  │(Structure)  │ (SQL Generation)│ (Connection Mgmt)       ││
│  └─────────────┴─────────────────┴─────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 1. Expression-Dialect Separation (Most Critical)

**Principle**: Query structure definition is separate from SQL generation

```python
# 1. Expression only defines structure, doesn't generate SQL
# src/rhosocial/activerecord/backend/expression/core.py
class SQLColumn(bases.SQLValueExpression):
    def to_sql(self) -> 'bases.SQLQueryAndParams':
        # Delegate to dialect
        return self.dialect.format_column_reference(self.table, self.name), ()

# 2. Dialect handles all SQL generation
# src/rhosocial/activerecord/backend/dialect.py
class SQLDialectBase(ABC):
    @abstractmethod
    def format_column_reference(self, table: str, column: str) -> str:
        return f'"{table}"."{column}"'  # PostgreSQL style
```

### 2. Dual-Mode API Design (Sync/Async Parity)

**Sync**: `BaseActiveRecord` → `ActiveQuery` → `StorageBackend`
**Async**: `AsyncBaseActiveRecord` → `AsyncActiveQuery` → `AsyncStorageBackend`

**Parity Rules**:

1. **Class names**: Async version adds `Async` prefix
   - `BaseActiveRecord` → `AsyncBaseActiveRecord`
   - `ActiveQuery` → `AsyncActiveQuery`
   - `StorageBackend` → `AsyncStorageBackend`

2. **Method names**: Remain completely identical (no `_async` suffix)
   ```python
   # Sync version
   class BaseActiveRecord:
       def save(self) -> int:
           ...
   
       def delete(self) -> int:
           ...
   
       @classmethod
       def find_one(cls, ...) -> Optional['BaseActiveRecord']:
           ...
   
   # Async version - identical method names
   class AsyncBaseActiveRecord:
       async def save(self) -> int:
           ...
   
       async def delete(self) -> int:
           ...
   
       @classmethod
       async def find_one(cls, ...) -> Optional['AsyncBaseActiveRecord']:
           ...
   ```

3. **Docstrings**: Must be equivalent, async version notes "asynchronously" in first sentence
   ```python
   def save(self) -> int:
       """Save the record to database..."""
       ...
   
   async def save(self) -> int:
       """Save the record to database asynchronously..."""
       ...
   ```

4. **Field order**: Declaration order of methods and fields must be identical

5. **Functional parity**: Logic must be completely identical between sync and async versions

6. **Testing Parity**:
   - **Fixture parity**: Each sync fixture must have corresponding async fixture
     ```python
     # Sync fixture
     @pytest.fixture
     def order_fixtures(backend_provider):
         return backend_provider.setup_order_fixtures(scenario)
     
     # Async fixture - class name adds Async prefix, same method name
     @pytest.fixture
     def async_order_fixtures(backend_provider):
         return backend_provider.setup_async_order_fixtures(scenario)
     ```
   
   - **Test case parity**: Each test class/method must have corresponding async version
     ```python
     class TestQuery:
         def test_basic_query(self, order_fixtures):
             User, Order = order_fixtures
             result = Order.query().where(...).all()
             assert len(result) > 0
         
         @pytest.mark.asyncio
         async def test_basic_query(self, async_order_fixtures):
             AsyncUser, AsyncOrder = async_order_fixtures
             result = await AsyncOrder.query().where(...).all()
             assert len(result) > 0
     ```
   
   - **Schema sharing**: Sync and async tests use the same SQL schema files
       ```
       tests/
       └── schemas/
           └── feature/
               └── query/
                   ├── users.sql        # Shared
                   ├── orders.sql       # Shared
                   └── order_items.sql  # Shared
       ```

### 3. Namespace Package Architecture

```python
# Core package
rhosocial.activerecord           # rhosocial-activerecord

# Backend extensions (separate packages)
rhosocial.activerecord.mysql     # rhosocial-activerecord-mysql
rhosocial.activerecord.pgsql     # rhosocial-activerecord-postgresql

# Automatically merged via pkgutil.extend_path
```

### 4. Protocol-Based Design

```python
# Backend feature detection uses Protocol, not inheritance
from rhosocial.activerecord.backend.dialect.protocols import CTESupport

@requires_protocol(CTESupport, 'supports_recursive_cte')
def test_recursive_cte():
    pass
```

## Code Modification Checklist

### Before Modification
- [ ] Target file has correct path comment (`# src/...`)
- [ ] Understand the involved architecture layer (Query? Backend? Field?)

### During Modification
- [ ] When modifying sync API, check if async version needs corresponding changes
- [ ] Does Expression modification delegate to Dialect?
- [ ] Are type annotations complete?
- [ ] Is line width ≤ 100 characters?

### After Modification
- [ ] Run corresponding tests: `pytest tests/path/to/test_xxx.py -v`
- [ ] Run linter: `ruff check src/`
- [ ] Need to create changelog fragment?

## Common Issue Resolution

### "ModuleNotFoundError: No module named 'rhosocial'"
```bash
export PYTHONPATH=src  # Must be set
pytest tests/
```

### "No backend configured"
```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
Model.configure(SQLiteBackend("sqlite:///test.db"))
```

### Circular Imports
- Use `TYPE_CHECKING` to import types
- Lazy import inside functions
- Redesign module structure

### Type Adapter Errors
- Check `TypeAdapter` registration
- Confirm Python type ↔ database type mappings
- Reference `backend/impl/sqlite/type_adapter.py`

## Key File Quick Reference

| Feature | File Path |
|---------|-----------|
| ActiveRecord base class | `src/rhosocial/activerecord/base/base.py` |
| Async base class | `src/rhosocial/activerecord/base/async_base.py` |
| Query builder | `src/rhosocial/activerecord/query/active_query.py` |
| Expression system | `src/rhosocial/activerecord/backend/expression/` |
| Dialect base | `src/rhosocial/activerecord/backend/dialect.py` |
| Backend abstraction | `src/rhosocial/activerecord/backend/base/base.py` |
| Field types | `src/rhosocial/activerecord/field/` |
| Relation management | `src/rhosocial/activerecord/relation/` |
| Protocol definitions | `src/rhosocial/activerecord/interface/` |

## Code Style Quick Reference

```python
# File header path comment
# src/rhosocial/activerecord/base/base.py

# Import order
import os                           # Standard library
from typing import Optional         # typing
from pydantic import BaseModel      # Third-party (Pydantic only)
from ..interface import IActiveRecord  # Local absolute import
from .utils import helper           # Relative import

# Class docstring
class User(ActiveRecord):
    """User model.
    
    Attributes:
        __table_name__: Database table name
        __primary_key__: Primary key column name
        
    Example:
        >>> user = User(name="John")
        >>> user.save()
    """

# Naming
class PascalCase:
    CONSTANT_VALUE = 1
    _private_var = 2
    
    def public_method(self): pass
    def _protected_method(self): pass
    def __private_method(self): pass
```

## Quick Command Reference

- `/test` - Run all tests
- `/test-feature basic` - Run basic feature tests
- `/test-feature query` - Run query feature tests
- `/lint` - Code linting
- `/new-feature` - Create new feature wizard

## Further Reading

Detailed documentation in `.gemini/` directory:
- `architecture.md` - Complete architecture documentation
- `code_style.md` - Code style guide
- `testing.md` - Testing architecture
- `version_control.md` - Version management
- `backend_development.md` - Backend development guide
- `feature_points.md` - Feature list
