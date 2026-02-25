---
name: user-getting-started
description: 5-minute quick start guide for new rhosocial-activerecord users - installation, first model, and basic CRUD
license: MIT
compatibility: opencode
metadata:
  category: getting-started
  level: beginner
  audience: users
  order: 1
---

## What I do

Get you up and running with rhosocial-activerecord in 5 minutes. This skill covers:
- Installation and setup
- Your first ActiveRecord model
- Basic CRUD operations
- Quick tips for common pitfalls

## When to use me

- You're new to rhosocial-activerecord
- You need a quick refresher on basics
- You want to verify your setup is correct
- You're creating a proof-of-concept

## Prerequisites

- Python 3.8+ installed
- pip or pipenv

## Quick Start (5 Minutes)

### 1. Install

```bash
pip install rhosocial-activerecord
```

### 2. Create Your First Model

Create `models.py`:

```python
from typing import ClassVar, Optional
from datetime import datetime
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.base import FieldProxy

class User(ActiveRecord):
    __table_name__ = 'users'
    
    name: str
    email: str
    age: int = 0
    created_at: Optional[datetime] = None
    
    # REQUIRED: Enable type-safe queries
    c: ClassVar[FieldProxy] = FieldProxy()

# Configure backend
User.configure(SQLiteBackend("myapp.db"))
```

### 3. Use It

```python
# Create
user = User(name="Alice", email="alice@example.com", age=30)
user.save()

# Query
adults = User.query().where(User.c.age >= 18).all()

# Update
user.email = "new@example.com"
user.save()

# Delete
user.delete()
```

## Common First Steps

### Check Your Setup

```python
# Verify installation
import rhosocial.activerecord
print(rhosocial.activerecord.__version__)

# Check SQLite version (must be 3.25+)
import sqlite3
print(sqlite3.sqlite_version)
```

### Environment Variable

Always set this before running:

```bash
export PYTHONPATH=src  # If running from source
```

## Next Steps

Ready for more? Try these skills:
- **@user-modeling-guide** - Learn advanced model definition
- **@user-query-advanced** - Master query building
- **@user-relationships** - Set up model relationships

## Quick Troubleshooting

❌ **"No backend configured"**
→ You forgot to call `User.configure(backend)`. Do this once per model class.

❌ **"ModuleNotFoundError"**
→ Set `PYTHONPATH=src` before running.

❌ **Validation errors**
→ Check your Pydantic field types and constraints.

## Full Documentation

- **Getting Started:** `docs/en_US/getting_started/`
- **Installation:** `docs/en_US/getting_started/installation.md`
- **Quick Start:** `docs/en_US/getting_started/quick_start.md`
