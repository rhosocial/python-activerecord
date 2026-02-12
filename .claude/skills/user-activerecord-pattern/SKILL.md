---
name: user-activerecord-pattern
description: Patterns and best practices for rhosocial-activerecord application developers - model definition with FieldProxy, expression-based query building, CRUD operations, and relationships
license: MIT
compatibility: opencode
metadata:
  category: orm
  level: intermediate
  audience: users
  order: 2
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

Define models with type hints and FieldProxy for query building:

```python
from typing import ClassVar, Optional
from datetime import datetime
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.base import FieldProxy

class User(ActiveRecord):
    __table_name__ = 'users'
    
    name: str = Field(..., max_length=100)
    email: str
    age: int = 0
    created_at: Optional[datetime] = None
    
    # REQUIRED: Enable type-safe query building
    c: ClassVar[FieldProxy] = FieldProxy()

# REQUIRED: Configure backend before use
backend = SQLiteBackend("sqlite:///app.db")
User.configure(backend)
```

**Key Points:**
- Use `c: ClassVar[FieldProxy] = FieldProxy()` to enable type-safe column references in queries
- Use Pydantic `Field()` for validation constraints (max_length, ge, etc.)
- Configure backend once per model class with `Model.configure(backend)`

### CRUD Operations

```python
from typing import ClassVar
from rhosocial.activerecord.base import FieldProxy

class User(ActiveRecord):
    __table_name__ = 'users'
    name: str
    email: str
    age: int = 0
    
    # Enable type-safe column references
    c: ClassVar[FieldProxy] = FieldProxy()

# Configure backend first
User.configure(backend)

# Create
user = User(name="John", email="john@example.com")
user.save()  # Returns number of affected rows (1)

# Read
user = User.find_one({'id': 1})  # By primary key dictionary
user = User.query().where(User.c.id == 1).one()  # Using query builder

# Query multiple records
users = User.query().where(User.c.age >= 18).all()

# Update
user.name = "Jane"
user.save()  # Only updates dirty fields

# Delete
user.delete()  # Returns number of affected rows
```

**Note:** Use `find_one()` with dictionary arguments for primary key lookups, and `query()` with `FieldProxy` (User.c) for complex queries.

### Query Building

Query building uses expression-based syntax with FieldProxy for type-safe column references.

```python
from typing import ClassVar
from rhosocial.activerecord.base import FieldProxy

class User(ActiveRecord):
    __table_name__ = 'users'
    name: str
    age: int
    status: str
    created_at: datetime
    
    # Enable type-safe column references
    c: ClassVar[FieldProxy] = FieldProxy()

# Configure backend
User.configure(backend)

# Query building with expressions
results = (
    User.query()
    .where((User.c.age >= 18) & (User.c.status == 'active'))
    .order_by((User.c.created_at, "DESC"))
    .limit(10)
    .all()
)

# Select specific columns
users = User.query().select(User.c.id, User.c.name).all()

# Use aliases
users = User.query().select(User.c.name.as_("username")).all()

# Combined conditions with OR
admins = User.query().where(
    (User.c.role == 'admin') | (User.c.role == 'moderator')
).all()

# Dictionary syntax (automatically AND conditions)
users = User.query().where({"name": "Alice", "age": 25}).all()

# Inspect SQL before execution
query = User.query().where(User.c.age >= 18)
sql, params = query.to_sql()
print(f"SQL: {sql}")  # SELECT * FROM users WHERE age >= ?

# Relationships with eager loading
posts = Post.query().with_('author', 'comments').all()
```

**Important Notes:**
- Always use `User.c.column_name` for column references in queries
- When using `&` (AND) and `|` (OR), **always use parentheses** around conditions
- Call `.to_sql()` on any query to inspect generated SQL before execution

**Full Documentation:** See `docs/en_US/querying/active_query.md` for complete query building reference including JOINs, aggregations, CTEs, and window functions.

## Anti-patterns

❌ **Never call `get_backend()`** - use `backend()` or `__backend__` instead

❌ **Never use models without configuring backend first**
```python
# WRONG - will raise "No backend configured"
user = User(name="John")
user.save()

# CORRECT
User.configure(backend)
user = User(name="John")
user.save()
```

❌ **Don't use string-based column references in queries**
```python
# WRONG - not type-safe
User.query().where("age >= 18")

# CORRECT - use FieldProxy
User.query().where(User.c.age >= 18)
```

❌ **Don't forget parentheses with & and | operators**
```python
# WRONG - operator precedence issues
User.query().where(User.c.age >= 18 & User.c.status == 'active')

# CORRECT - always use parentheses
User.query().where((User.c.age >= 18) & (User.c.status == 'active'))
```

### Avoid Circular Imports

When models reference each other, use string forward references in relationship descriptors.

```python
# CORRECT - Use string forward reference
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany

class User(ActiveRecord):
    __table_name__ = 'users'
    name: str
    
    # Define relationship with string reference
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='author'
    )

class Post(ActiveRecord):
    __table_name__ = 'posts'
    title: str
    user_id: int
    
    author: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )
```

## Additional Resources

- **Full Query Documentation:** `docs/en_US/querying/active_query.md`
- **Relationship Guide:** `docs/en_US/relationships/`
- **Backend Development:** `docs/en_US/backend/`
