# Script Development Lessons Learned

When writing standalone scripts to test ActiveRecord models (outside of pytest), we encountered several pitfalls. This document records the lessons learned and solutions.

## Problem Summary Table

| Issue | Error Message | Cause | Solution |
|-------|--------------|-------|----------|
| 1 | `ImportError: cannot import name 'ActiveRecord'` | Wrong import path | Use `rhosocial.activerecord.model` |
| 2 | `TypeError: configure() got an unexpected keyword argument 'backend'` | Wrong configure() arguments | Use `configure(config, BackendClass)` |
| 3 | `ValueError: "User" object has no field "id"` | Missing id field | Add `id: Optional[int] = None` |
| 4 | `AttributeError: 'User' object has no attribute 'id'` | IntegerPKMixin without field | Define id field in model |
| 5 | `ValueError: table_name not set for User` | Missing table_name() | Implement `@classmethod def table_name(cls)` |
| 6 | `TypeError: __init__() takes 1 positional argument but 2 were given` | Backend positional args | Use keyword args: `database=...` |
| 7 | `AttributeError: 'User' object has no attribute 'id'` after save | Field required error | Set `id: Optional[int] = None` |
| 8 | `AttributeError: 'SQLiteBackend' object has no attribute '_connection'` | Backend not initialized | Use proper backend initialization |

## Detailed Solutions

### 1. Correct Import Path

```python
# Wrong - ActiveRecord is not exported from root
from rhosocial.activerecord import ActiveRecord

# Correct - Import from model submodule
from rhosocial.activerecord.model import ActiveRecord

# Also correct for field mixins
from rhosocial.activerecord.field import TimestampMixin, IntegerPKMixin, UUIDMixin
```

### 2. Model Configuration

The `configure()` method requires `config` and `backend_class` parameters, not a backend instance:

```python
# Wrong - configure() doesn't accept backend instance
backend = SQLiteBackend(database=db_file)
User.configure(backend=backend)

# Correct - Pass config and backend class
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
config = SQLiteConnectionConfig(database=db_file)
User.configure(config, SQLiteBackend)
```

### 3. Model Definition with Mixins

When using `IntegerPKMixin` or `UUIDMixin`, must define the primary key field:

```python
# Wrong - IntegerPKMixin requires id field definition
class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    name: str

# Correct - Define id as Optional
class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    id: Optional[int] = None  # Primary key (auto-generated)
    name: str
    email: str
```

### 4. Table Name Required

All ActiveRecord models must implement `table_name()`:

```python
class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    id: Optional[int] = None
    name: str
    
    @classmethod
    def table_name(cls) -> str:
        return "user"  # Must return table name
```

### 5. Backend Initialization

Backend classes use keyword arguments, not positional:

```python
# Wrong - Positional argument
backend = SQLiteBackend(db_file)

# Correct - Keyword argument
backend = SQLiteBackend(database=db_file)

# Also correct
backend = SQLiteBackend(database=":memory:")
```

### 6. Mixin Inheritance Order

Mixins must come before `ActiveRecord` in inheritance:

```python
# Correct order - Mixins first, ActiveRecord last
class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    pass

# Wrong - ActiveRecord should be last
class User(ActiveRecord, IntegerPKMixin, TimestampMixin):
    pass
```

## Complete Working Example

```python
# scripts/test_timestamp_format.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin, IntegerPKMixin
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig


class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Test User model with timestamps."""
    id: Optional[int] = None
    name: str
    email: str
    
    @classmethod
    def table_name(cls) -> str:
        return "user"


def main():
    import tempfile
    
    # Create temporary database
    db_file = os.path.join(tempfile.gettempdir(), f"test_{os.getpid()}.sqlite")
    
    try:
        # Configure model - use config and backend_class
        config = SQLiteConnectionConfig(database=db_file)
        User.configure(config, SQLiteBackend)
        
        # Get backend instance for manual operations
        backend = User.__backend_class__(connection_config=config)
        backend.connect()
        
        # Create table manually if needed
        cursor = backend._connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        backend._connection.commit()
        
        # Test insert
        user = User(name="John Doe", email="john@example.com")
        user.save()
        print(f"Created user with id: {user.id}")
        
        # Test update
        user.email = "john.updated@example.com"
        user.save()
        print(f"Updated user, new email: {user.email}")
        
        backend.disconnect()
        
    finally:
        # Cleanup
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except:
                pass


if __name__ == "__main__":
    main()
```

## Key Takeaways

1. **Always use PYTHONPATH**: Set `PYTHONPATH=src` before running any script
2. **Import from correct submodule**: `rhosocial.activerecord.model` not root
3. **Use proper configure() signature**: `configure(config, BackendClass)`
4. **Define primary key field**: When using IntegerPKMixin/UUIDMixin
5. **Implement table_name()**: Required for all ActiveRecord models
6. **Use keyword arguments**: Backend initialization uses keyword args
7. **Mixin order matters**: Mixins before ActiveRecord in inheritance
