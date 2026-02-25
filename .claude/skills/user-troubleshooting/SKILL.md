---
name: user-troubleshooting
description: Common errors and troubleshooting guide for rhosocial-activerecord - import errors, backend configuration, query issues, relationship problems, and debugging techniques
license: MIT
compatibility: opencode
metadata:
  category: troubleshooting
  level: beginner
  audience: users
  order: 9
  prerequisites:
    - user-getting-started
---

# Troubleshooting Guide

This guide covers common errors and issues encountered when using rhosocial-activerecord, with solutions and debugging techniques.

## Import Errors

### ModuleNotFoundError: No module named 'rhosocial'

**Problem**: Python cannot find the rhosocial module.

**Solution**: Set PYTHONPATH to include the src directory.

```bash
# Linux/macOS
export PYTHONPATH=src
python your_script.py

# Windows PowerShell
$env:PYTHONPATH = "src"
python your_script.py

# In pytest
PYTHONPATH=src pytest tests/
```

**Alternative**: Install the package in development mode.

```bash
pip install -e .
```

### Circular Import Errors

**Problem**: Modules importing each other causing import failures.

**Solution**: Use lazy imports or TYPE_CHECKING.

```python
# Avoid circular imports with TYPE_CHECKING
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import User
    from .repositories import UserRepository
```

**Alternative**: Restructure imports to avoid circular dependencies.

```python
# Option 1: Import at function level
def some_function():
    from .models import User
    return User.query().all()

# Option 2: Move shared code to separate module
# Create a new module for common utilities
```

## Backend Configuration Errors

### NoBackendConfiguredError

**Problem**: Model is used without configuring a backend.

```python
# ❌ Error - no backend configured
class User(ActiveRecord):
    __table_name__ = 'users'
    ...

user = User(name="John")
user.save()  # Raises NoBackendConfiguredError
```

**Solution**: Configure backend before using models.

```python
# ✅ Configure backend first
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

# Configure the model with a backend
User.configure(SQLiteBackend("sqlite:///app.db"))

# Or set at class level
class User(ActiveRecord):
    __table_name__ = 'users'
    __backend__ = SQLiteBackend("sqlite:///app.db")
    ...

user = User(name="John")
user.save()  # Works!
```

### Backend Connection Errors

**Problem**: Cannot connect to the database.

```python
# Check connection configuration
backend = SQLiteBackend("sqlite:///nonexistent/path/app.db")
backend.connect()  # May fail if path doesn't exist
```

**Solution**: Verify connection string and database path.

```python
# Use absolute paths for SQLite
import os
db_path = os.path.abspath("app.db")
backend = SQLiteBackend(f"sqlite:///{db_path}")

# Check if file can be created
if os.path.exists(os.path.dirname(db_path)):
    backend.connect()
else:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    backend.connect()
```

### Multiple Backends Error

**Problem**: Mixing models from different backends.

**Solution**: Use consistent backend configuration.

```python
# ❌ Problematic - different backends
class User(ActiveRecord):
    __table_name__ = 'users'
    __backend__ = backend1

class Order(ActiveRecord):
    __table_name__ = 'orders'
    __backend__ = backend2

# User and Order can't be used together in queries

# ✅ Consistent backend
shared_backend = SQLiteBackend("sqlite:///app.db")

class User(ActiveRecord):
    __table_name__ = 'users'
    __backend__ = shared_backend

class Order(ActiveRecord):
    __table_name__ = 'orders'
    __backend__ = shared_backend

# Now User and Order can be joined
```

## Query Errors

### FieldNotFoundError

**Problem**: Referencing a field that doesn't exist on the model.

```python
# ❌ Error - 'email' field doesn't exist
class User(ActiveRecord):
    __table_name__ = 'users'
    id: int = Field(primary_key=True)
    name: str = Field()

User.query().where(User.c.email == "test@example.com")
```

**Solution**: Verify field names match the model definition.

```python
# ✅ Correct - use existing fields
User.query().where(User.c.name == "John")

# Or add the missing field
class User(ActiveRecord):
    __table_name__ = 'users'
    id: int = Field(primary_key=True)
    name: str = Field()
    email: str = Field()  # Add email field

User.query().where(User.c.email == "test@example.com")
```

### InvalidOperatorError

**Problem**: Using an invalid operator in a where clause.

```python
# ❌ Error - invalid operator
User.query().where(User.c.name % "John%")  # % is not valid
```

**Solution**: Use valid operators.

```python
# ✅ Valid operators
User.query().where(User.c.name == "John")           # Equality
User.query().where(User.c.name != "John")          # Inequality
User.query().where(User.c.age > 18)                # Greater than
User.query().where(User.c.age >= 18)               # Greater or equal
User.query().where(User.c.age < 65)                # Less than
User.query().where(User.c.age <= 65)               # Less or equal
User.query().where(User.c.name.like("J%"))         # LIKE pattern
User.query().where(User.c.name.ilike("j%"))       # Case-insensitive LIKE
User.query().where(User.c.id.is_in([1, 2, 3]))     # IN list
User.query().where(User.c.name.is_null())          # IS NULL
User.query().where(User.c.age.between(18, 65))    # BETWEEN
```

### QuerySyntaxError

**Problem**: Malformed query expression.

**Solution**: Check query expression structure.

```python
# ❌ Error - missing parentheses
User.query().where User.c.name == "John"

# ✅ Correct - proper method chaining
User.query().where(User.c.name == "John")

# ❌ Error - invalid combination
User.query().where(User.c.name == "John").and_(User.c.age > 18)

# ✅ Correct - use & operator or pass multiple conditions
User.query().where(
    (User.c.name == "John") & (User.c.age > 18)
)
# Or
User.query().where(User.c.name == "John").where(User.c.age > 18)
```

### EmptyResultError

**Problem**: Query returns no results when results are expected.

```python
# Check if results exist before accessing
user = User.find_one(User.c.id == 999)
if user is None:
    # Handle not found case
    print("User not found")
else:
    print(user.name)
```

### TypeMismatchError

**Problem**: Query parameter type doesn't match field type.

```python
# ❌ Error - string for integer field
class User(ActiveRecord):
    __table_name__ = 'users'
    age: int = Field()

User.query().where(User.c.age == "25")  # String instead of int

# ✅ Correct - use correct type
User.query().where(User.c.age == 25)   # Integer
```

## Relationship Errors

### RelationNotDefinedError

**Problem**: Trying to access a relation that doesn't exist.

```python
# ❌ Error - no 'orders' relation defined
class User(ActiveRecord):
    __table_name__ = 'users'
    ...

user = User.find_one()
orders = user.orders  # No relation defined
```

**Solution**: Define the relation first.

```python
# ✅ Define the relation
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(ActiveRecord):
    __table_name__ = 'users'
    id: int = Field(primary_key=True)
    name: str = Field()
    
    # User has many Orders - declare as ClassVar
    orders: ClassVar[HasMany['Order']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )

class Order(ActiveRecord):
    __table_name__ = 'orders'
    id: int = Field(primary_key=True)
    user_id: int = Field()
    total: float = Field()
    
    # Order belongs to User - declare as ClassVar
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='orders'
    )

# Usage
user = User.find_one()
orders = user.orders  # Access as attribute
```

### InvalidRelationError

**Problem**: Relation is defined incorrectly.

**Solution**: Check relation definition syntax.

```python
# ❌ Error - incorrect relation definition
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import BelongsTo, HasMany

class Order(ActiveRecord):
    __table_name__ = 'orders'
    user_id: int = Field()
    
    # Wrong: BelongsTo should reference the parent, not self
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='order_id',  # Wrong! Should be 'user_id'
        inverse_of='orders'
    )

# ✅ Correct relation definition
class Order(ActiveRecord):
    __table_name__ = 'orders'
    id: int = Field(primary_key=True)
    user_id: int = Field()
    
    # Correct: foreign_key points to parent model's primary key
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',  # Correct!
        inverse_of='orders'
    )
```

### EagerLoadError

**Problem**: Error when using eager loading.

**Solution**: Verify relation name and structure.

```python
# ❌ Error - wrong relation name
User.query().includes('oderrs').all()  # Typo

# ✅ Correct - use exact relation name
User.query().includes('orders').all()

# ❌ Error - nested relation doesn't exist
User.query().includes({'orders': 'itms'}).all()  # 'itms' doesn't exist

# ✅ Correct - use valid nested relation
User.query().includes({'orders': 'items'}).all()
```

## Validation Errors

### ValidationError

**Problem**: Field validation failed.

```python
# ❌ Error - validation failure
class User(ActiveRecord):
    __table_name__ = 'users'
    name: str = Field(max_length=10)
    email: str = Field(max_length=255)

user = User(name="Very long name that exceeds 10 characters", email="test")
user.save()  # ValidationError
```

**Solution**: Provide valid data or adjust validation constraints.

```python
# ✅ Provide valid data
user = User(name="Short name", email="test@example.com")
user.save()  # Works

# Or adjust the constraint
class User(ActiveRecord):
    __table_name__ = 'users'
    name: str = Field(max_length=100)  # Increased limit
```

### UniqueConstraintViolation

**Problem**: Inserting duplicate value for unique field.

```python
# ❌ Error - duplicate email
class User(ActiveRecord):
    __table_name__ = 'users'
    email: str = Field(unique=True)

User.create(name="John", email="test@example.com")
User.create(name="Jane", email="test@example.com")  # UniqueConstraintViolation
```

**Solution**: Check for existing records before creating.

```python
# ✅ Check before creating
existing = User.find_one(User.c.email == "test@example.com")
if existing:
    print("User with this email already exists")
else:
    User.create(name="Jane", email="test@example.com")

# Or use update_or_create
user, created = User.update_or_create(
    {'email': 'test@example.com'},
    name='Jane'
)
```

## Async Errors

### RuntimeError: No running event loop

**Problem**: Calling async method without an event loop.

```python
# ❌ Error - no event loop in sync context
user = await User.find_one(User.c.id == 1)  # Error in sync code
```

**Solution**: Use async/await only in async contexts.

```python
# ✅ Correct - in async function
import asyncio

async def get_user(user_id):
    return await User.find_one(User.c.id == user_id)

user = asyncio.run(get_user(1))
```

### TypeError: object type can't be used in await expression

**Problem**: Awaiting a non-coroutine.

```python
# ❌ Error - sync method doesn't return coroutine
user = await User.query()  # query() is sync
```

**Solution**: Use appropriate sync or async methods.

```python
# ✅ Async version
from rhosocial.activerecord.model import AsyncActiveRecord

class AsyncUser(AsyncActiveRecord):
    __table_name__ = 'users'
    id: int = Field(primary_key=True)
    name: str = Field()
    email: str = Field()

async def get_user(user_id):
    return await AsyncUser.find_one(AsyncUser.c.id == user_id)

user = asyncio.run(get_user(1))
```

## Debugging Techniques

### Enable Query Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# Enable SQL logging
logger = logging.getLogger('rhosocial.activerecord')
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(sql)s'))
logger.addHandler(handler)
```

### Print Query SQL

```python
# Get the SQL for a query
query = User.query().where(User.c.status == 'active')
sql, params = query.compile().to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")
```

### Verify Field Values

```python
# Check field values before saving
user = User(name="John")
print(user.__dict__)  # See all field values

# Validate manually
from pydantic import BaseModel
try:
    user = User(name="John")
    user_validator = User.model_validator(user)
    print("Validation passed")
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Check Backend Configuration

```python
# Verify backend is configured
print(User.__backend__)
print(User.__backend__.connected)

# Test connection
try:
    User.__backend__.execute("SELECT 1")
    print("Backend is working")
except Exception as e:
    print(f"Backend error: {e}")
```

## Common Error Messages and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `NoBackendConfiguredError` | No backend configured | Call `Model.configure(backend)` |
| `ModuleNotFoundError` | PYTHONPATH not set | `export PYTHONPATH=src` |
| `FieldNotFoundError` | Wrong field name | Check model definition |
| `ValidationError` | Invalid field value | Validate input data |
| `UniqueConstraintViolation` | Duplicate unique value | Check before creating |
| `RelationNotDefinedError` | Missing relation definition | Define relation with decorators |
| `DatabaseLockedError` | SQLite concurrent access | Use connection pooling or retry |
| `CircularImportError` | Import cycle | Use TYPE_CHECKING or lazy imports |

## Getting Help

1. **Check documentation**: See `docs/en_US/` for comprehensive guides
2. **Review tests**: Check `tests/` for usage examples
3. **Check examples**: See `examples/` directory for sample applications
4. **Search issues**: Check GitHub issues for similar problems
5. **Create issue**: If no solution exists, create a new issue with:
   - Error message
   - Minimal reproduction code
   - Expected behavior
   - Environment details (OS, Python version, package versions)
