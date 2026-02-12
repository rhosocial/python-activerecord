---
name: activerecord-pattern
description: Patterns and best practices for using rhosocial-activerecord ORM including model definition, CRUD operations, queries, and relationships
license: MIT
compatibility: opencode
metadata:
  category: orm
  level: intermediate
---

## What I do

Help developers use rhosocial-activerecord correctly by providing:
- Model definition patterns with proper configuration
- CRUD operation examples (Create, Read, Update, Delete)
- Query building with method chaining
- Relationship management (belongs_to, has_one, has_many)
- Field types and mixins usage
- Anti-patterns to avoid

## When to use me

Use this skill when:
- Defining new ActiveRecord models
- Writing CRUD operations
- Building complex queries
- Setting up relationships between models
- Choosing field types and mixins
- Reviewing ActiveRecord usage for best practices

## Core Patterns

### Model Definition
Always configure backend before use:
```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

class User(ActiveRecord):
    __table_name__ = 'users'
    __primary_key__ = 'id'
    
    name: str
    email: str

# REQUIRED: Configure backend
backend = SQLiteBackend("sqlite:///app.db")
User.configure(backend)
```

### CRUD Operations
```python
# Create
user = User(name="John", email="john@example.com")
user.save()

# Read
user = User.find_one(1)
users = User.where(age__gte=18).all()

# Update
user.name = "Jane"
user.save()  # Only updates dirty fields

# Delete
user.delete()
```

### Query Building
```python
# Good - readable chaining
results = (
    User
    .where(age__gte=18, status='active')
    .order_by('-created_at')
    .limit(10)
)

# Relationships with eager loading
posts = Post.with_('user').all()
```

## Anti-patterns

❌ Never call `get_backend()` - use `backend()` or `__backend__`
❌ Never use models without configuring backend first
❌ Avoid circular imports at module level
