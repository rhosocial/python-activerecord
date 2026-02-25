# Common Errors and Solutions

This document helps you quickly identify and resolve common issues when using `rhosocial-activerecord`.

## Quick Diagnosis

| Error Message | Go To |
|--------------|-------|
| `No backend configured` | [Backend Not Configured](#backend-not-configured) |
| `FieldProxy not found` / Query fields not auto-completing | [FieldProxy Not Defined](#fieldproxy-not-defined) |
| `ModuleNotFoundError` / `ImportError` | [Import Errors](#import-errors) |
| `PYTHONPATH` related warnings (developers only) | [PYTHONPATH Issues](#pythonpath-issues) |
| Type checking errors | [Type Annotation Errors](#type-annotation-errors) |
| `RuntimeError: cannot be used in async context` | [Sync/Async Mixing](#syncasync-mixing) |
| Database connection failures | [Database Connection Issues](#database-connection-issues) |

---

## Backend Not Configured

### Error Message

```python
NoBackendConfiguredError: No backend configured for model User. 
Call User.configure(backend) first.
```

### Cause

You tried to use a model before configuring its database backend.

### Solution

Call `configure()` before using the model:

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

# 1. Create configuration
config = SQLiteConnectionConfig(database='myapp.db')

# 2. Configure model (must be done before first use)
User.configure(config, SQLiteBackend)

# 3. Now it can be used
user = User(name="Alice")
user.save()
```

### Best Practice

Configure all models at application startup:

```python
# app/config.py
def setup_database():
    config = SQLiteConnectionConfig(database='app.db')
    
    # Configure all models
    User.configure(config, SQLiteBackend)
    Post.configure(config, SQLiteBackend)  # Share same backend
    Comment.configure(config, SQLiteBackend)
    
    # Create tables (development environment)
    create_tables()

# main.py
from app.config import setup_database

if __name__ == "__main__":
    setup_database()  # Configure at startup
    # ... rest of your code
```

> 💡 **AI Prompt:** "My rhosocial-activerecord model shows 'No backend configured', please write a complete configuration example."

---

## FieldProxy Not Defined

### Symptoms

- IDE cannot auto-complete query fields (e.g., `User.c.name`)
- Runtime error: `AttributeError: 'FieldProxy' object has no attribute 'xxx'`
- Type checking failures in queries

### Cause

Forgot to define the `c` field in your model, or used incorrect type annotation.

### Solution

Ensure every model properly defines `FieldProxy`:

```python
from typing import ClassVar
from rhosocial.activerecord.base import FieldProxy

class User(ActiveRecord):
    # ❌ Wrong: No FieldProxy defined
    name: str
    
    # ✅ Correct: Define FieldProxy as ClassVar
    c: ClassVar[FieldProxy] = FieldProxy()
    name: str
```

### Common Mistakes

```python
# ❌ Mistake 1: Not ClassVar
class User(ActiveRecord):
    c = FieldProxy()  # Pydantic treats it as a model field

# ❌ Mistake 2: Wrong type annotation
class User(ActiveRecord):
    c: FieldProxy = FieldProxy()  # Missing ClassVar

# ❌ Mistake 3: Wrong position (after fields)
class User(ActiveRecord):
    name: str
    c: ClassVar[FieldProxy] = FieldProxy()  # Should be at the top

# ✅ Correct
class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    name: str
    email: str
```

> 💡 **AI Prompt:** "Why does rhosocial-activerecord need FieldProxy? Explain the role of ClassVar."

---

## Import Errors

### Symptom

```python
ModuleNotFoundError: No module named 'rhosocial'
```

### Cause 1: Package Not Installed

```bash
# ❌ Wrong: Using source directly without installing
python my_script.py  # Error
```

### Solution 1: Install Package

```bash
# Install from PyPI
pip install rhosocial-activerecord

# Or install from local source (development mode)
cd /path/to/rhosocial-activerecord
pip install -e .
```

### Cause 2: PYTHONPATH Not Set

If you're using source directly without installing, you need to set `PYTHONPATH`.

### Solution 2: Set PYTHONPATH

```bash
# macOS/Linux
export PYTHONPATH=/path/to/src:$PYTHONPATH
python my_script.py

# Windows PowerShell
$env:PYTHONPATH = "C:\path\to\src;$env:PYTHONPATH"
python my_script.py

# Windows CMD
set PYTHONPATH=C:\path\to\src;%PYTHONPATH%
python my_script.py
```

### Setting PYTHONPATH in IDE

**VS Code:**
Create `.env` file in project root:
```
PYTHONPATH=src
```

**PyCharm:**
1. Run → Edit Configurations
2. Add to Environment variables: `PYTHONPATH=src`

> 💡 **AI Prompt:** "How to set PYTHONPATH in VS Code / PyCharm for developing rhosocial-activerecord?"

### Cause 3: Wrong Import Statement

```python
# ❌ Wrong: Cannot import directly from rhosocial.activerecord
from rhosocial.activerecord import ActiveRecord  # ModuleNotFoundError!
```

### Solution 3: Use Correct Import Path

```python
# ✅ Correct: Import from model module
from rhosocial.activerecord.model import ActiveRecord

# ✅ Correct: Import other common components
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.field import TimestampMixin
```

### Why Does This Happen?

`rhosocial.activerecord` is a **namespace package** designed to support backend extension plugins (like `rhosocial-activerecord-mysql`, `rhosocial-activerecord-postgres`, etc.). Therefore, it **does not have an `__init__.py`** file and you cannot import classes directly from it.

All core functionality is distributed across submodules:
- `rhosocial.activerecord.model` - `ActiveRecord` and `AsyncActiveRecord` classes
- `rhosocial.activerecord.base` - Base components like `FieldProxy`
- `rhosocial.activerecord.backend.impl.sqlite` - SQLite backend
- `rhosocial.activerecord.field` - Field mixins (e.g., `TimestampMixin`)
- `rhosocial.activerecord.relation` - Relation definitions (e.g., `HasMany`)

> 💡 **AI Prompt:** "Why can't I use `from rhosocial.activerecord import ActiveRecord` in rhosocial-activerecord?"

---

## PYTHONPATH Issues (Framework/Backend Developers Only)

> ⚠️ **Note**: This issue only affects **developers working directly on the rhosocial-activerecord framework or its database backends**. Regular users who install via `pip install` will not encounter this problem.

### Scenario

When running the framework from source or developing custom backends without using `pip install -e .` for editable installation:

```bash
# You run it like this (without pip install -e .)
git clone https://github.com/rhosocial/rhosocial-activerecord.git
cd rhosocial-activerecord
python -c "from rhosocial.activerecord.model import ActiveRecord"  # ModuleNotFoundError!
```

### Solutions

#### Option 1: Editable Install (Recommended)

```bash
# In the framework source directory
pip install -e .

# Now you can import normally
python -c "from rhosocial.activerecord.model import ActiveRecord"
```

#### Option 2: Set PYTHONPATH

If you prefer not to install, set the environment variable temporarily:

```bash
# macOS/Linux
export PYTHONPATH=src
pytest tests/

# Windows PowerShell
$env:PYTHONPATH = "src"
pytest tests/

# Or use Python -m pytest (from project root)
PYTHONPATH=src python -m pytest tests/
```

#### Option 3: Add conftest.py

Create `conftest.py` in `tests/` directory (for testing scenarios):

```python
# tests/conftest.py
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
```

### For Regular Users

If you're a regular user, simply install via pip:

```bash
pip install rhosocial-activerecord
```

Once installed, you can use it normally without any PYTHONPATH configuration.

---

## Type Annotation Errors

### Error 1: Python 3.8 Compatibility

```python
# ❌ Python 3.8 doesn't support list[str] (needs from __future__ import annotations)
def get_users() -> list[User]:
    ...

# ✅ Python 3.8 compatible
from typing import List

def get_users() -> List[User]:
    ...
```

### Error 2: Optional Field Not Marked

```python
# ❌ Missing Optional, Pydantic requires it
class User(ActiveRecord):
    bio: str  # Error: bio is required

# ✅ Correctly mark as Optional
from typing import Optional

class User(ActiveRecord):
    bio: Optional[str] = None
    # Or
    bio: Optional[str] = Field(default=None)
```

### Error 3: ClassVar vs Regular Field Confusion

```python
# ❌ Wrong: FieldProxy not ClassVar
class User(ActiveRecord):
    c: FieldProxy = FieldProxy()  # Pydantic tries to validate it

# ✅ Correct
class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
```

> 💡 **AI Prompt:** "Type annotation best practices for rhosocial-activerecord, especially ClassVar and Optional usage."

---

## Sync/Async Mixing

### Error 1: Using Sync Model in Async Code

```python
# ❌ Wrong: Using sync model in async function
async def get_user():
    user = User(name="Alice")
    user.save()  # RuntimeError: cannot be used in async context
```

### Solution 1: Use Async Model

```python
# ✅ Correct
async def get_user():
    user = AsyncUser(name="Alice")
    await user.save()  # Use await
```

### Error 2: Forgetting await

```python
# ❌ Wrong: Forgot await
async def get_user():
    user = await AsyncUser.find_one({'name': 'Alice'})
    posts = user.posts()  # Returns coroutine object, not list

# ✅ Correct
async def get_user():
    user = await AsyncUser.find_one({'name': 'Alice'})
    posts = await user.posts()  # Remember to await
```

### Error 3: Mixing Sync and Async Backends

```python
# ❌ Wrong: User uses sync backend, AsyncUser also configured with sync backend
User.configure(sync_config, SQLiteBackend)
AsyncUser.configure(sync_config, SQLiteBackend)  # Wrong!

# ✅ Correct
User.configure(sync_config, SQLiteBackend)
AsyncUser.configure(async_config, AsyncSQLiteBackend)  # Use async backend
```

### Quick Reference Table

| Operation | Sync | Async |
|-----------|------|-------|
| Base Class | `ActiveRecord` | `AsyncActiveRecord` |
| Backend | `SQLiteBackend` | `AsyncSQLiteBackend` |
| Save | `user.save()` | `await user.save()` |
| Query | `User.find_one(...)` | `await AsyncUser.find_one(...)` |
| Relation | `user.posts()` | `await user.posts()` |

> 💡 **AI Prompt:** "What's the difference between sync and async models in rhosocial-activerecord? How to avoid mixing them?"

---

## Database Connection Issues

### Error 1: Wrong Database File Path

```python
# ❌ Relative path may cause file not found
config = SQLiteConnectionConfig(database='app.db')
# Depends on current working directory, might not find it

# ✅ Use absolute path
from pathlib import Path

db_path = Path(__file__).parent / "app.db"
config = SQLiteConnectionConfig(database=str(db_path))
```

### Error 2: Permission Issues

```python
# ❌ Creating database in read-only directory
config = SQLiteConnectionConfig(database='/var/lib/app.db')  # Permission denied

# ✅ Ensure write permission
config = SQLiteConnectionConfig(database='/home/user/app.db')
```

### Error 3: Connection Leaks

```python
# ❌ Multiple configurations causing connection chaos
User.configure(config1, SQLiteBackend)
User.configure(config2, SQLiteBackend)  # Overwrites previous config

# ✅ Configure only once during application lifecycle
```

### Error 4: In-Memory Database Not Shared

```python
# ❌ Each model uses separate in-memory database
User.configure(SQLiteConnectionConfig(database=':memory:'), SQLiteBackend)
Post.configure(SQLiteConnectionConfig(database=':memory:'), SQLiteBackend)  # Different database!

# ✅ Share the same backend
backend = SQLiteBackend(SQLiteConnectionConfig(database=':memory:'))
User.configure(backend)
Post.configure(backend)  # Shared connection
```

> 💡 **AI Prompt:** "How to share SQLite in-memory database connections in rhosocial-activerecord?"

---

## Other Common Issues

### Table Does Not Exist Error

```python
OperationalError: no such table: users
```

**Cause:** Forgot to create table or table name mismatch

**Solution:**

```python
# Ensure table name is correct
class User(ActiveRecord):
    @classmethod
    def table_name(cls) -> str:
        return 'users'  # Confirm matches database table name

# Create table
User.backend().execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT
    )
""")
```

### Field Validation Failure

```python
ValidationError: 1 validation error for User
name
  ensure this value has at most 50 characters (type=value_error.any_str.max_length)
```

**Solution:** Check Pydantic validation rules

```python
class User(ActiveRecord):
    name: str = Field(..., max_length=50)  # Ensure value meets requirements
```

### Primary Key Conflict

```python
IntegrityError: UNIQUE constraint failed: users.id
```

**Solution:** Check if instance already exists before saving

```python
if user.id is None:
    user.save()  # INSERT
else:
    user.save()  # UPDATE
```

---

## Still Having Issues?

If the above solutions don't resolve your problem:

1. **View detailed error information**: `python -v my_script.py` for full stack trace
2. **Enable debug mode**: Set environment variable `DEBUG=1`
3. **Submit an Issue**: Create a GitHub issue with:
   - Python version
   - Complete error message
   - Minimal reproducible code

> 💡 **AI Prompt:** "I encountered [error description], here's my code: [paste code], please help me find the problem."

---

## See Also

- [Installation Guide](installation.md) — Complete installation steps
- [Configuration](configuration.md) — Database configuration details
- [Your First CRUD App](first_crud.md) — Complete getting started example
