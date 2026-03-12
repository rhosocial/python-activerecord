# Script Development Guide

When writing standalone scripts to test ActiveRecord models (outside of pytest), several common pitfalls exist. This guide documents the lessons learned.

## Common Pitfalls and Solutions

### 1. Import Errors

**Problem**: `ImportError: cannot import name 'ActiveRecord'`

**Solution**: ActiveRecord is in `rhosocial.activerecord.model`, not `rhosocial.activerecord`:

```python
# Wrong
from rhosocial.activerecord import ActiveRecord

# Correct
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin, IntegerPKMixin
```

### 2. Model Configuration

**Problem**: `TypeError: configure() got an unexpected keyword argument 'backend'`

**Solution**: `configure()` requires `config` and `backend_class`, not a backend instance:

```python
# Wrong
backend = SQLiteBackend(database=db_file)
User.configure(backend=backend)

# Correct
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
config = SQLiteConnectionConfig(database=db_file)
User.configure(config, SQLiteBackend)
```

### 3. Model Definition Requirements

**Problem**: `ValueError: "User" object has no field "id"` or `AttributeError: 'User' object has no attribute 'id'`

**Solution**: When using `IntegerPKMixin`, must define `id` field as Optional:

```python
# Wrong
class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    name: str

# Correct
class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    id: Optional[int] = None  # Primary key (auto-generated)
    name: str
    email: str
```

### 4. Table Name Required

**Problem**: `ValueError: table_name not set for User`

**Solution**: Must implement `table_name()` class method:

```python
class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    id: Optional[int] = None
    name: str
    
    @classmethod
    def table_name(cls) -> str:
        return "user"
```

### 5. Backend Initialization

**Problem**: `TypeError: __init__() takes 1 positional argument but 2 were given`

**Solution**: Backend classes use keyword arguments:

```python
# Wrong
backend = SQLiteBackend(db_file)

# Correct
backend = SQLiteBackend(database=db_file)
# or
backend = SQLiteBackend(database=":memory:")
```

### 6. Mixin Inheritance Order

**Problem**: Mixin not working correctly

**Solution**: Mixins should come before `ActiveRecord` in inheritance order:

```python
# Correct order
class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    pass

# Wrong - ActiveRecord should be last
class User(ActiveRecord, IntegerPKMixin, TimestampMixin):
    pass
```

## Complete Example Script

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
    id: Optional[int] = None  # Primary key (auto-generated)
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
        # Configure model
        config = SQLiteConnectionConfig(database=db_file)
        User.configure(config, SQLiteBackend)
        
        # Get backend instance for table creation
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

## Key Lessons Summary

| Issue | Cause | Solution |
|-------|-------|----------|
| Import error | Wrong import path | Use `rhosocial.activerecord.model` |
| configure() error | Wrong arguments | Use `configure(config, BackendClass)` |
| Missing id field | IntegerPKMixin requires field | Add `id: Optional[int] = None` |
| table_name error | Not implemented | Add `@classmethod def table_name(cls)` |
| Backend init error | Positional args | Use keyword args: `database=...` |
| Mixin not working | Wrong order | Put mixins before ActiveRecord |
