---
name: user-modeling-guide
description: Comprehensive guide for defining models in rhosocial-activerecord - fields, validation, FieldProxy, mixins, and best practices
license: MIT
compatibility: opencode
metadata:
  category: modeling
  level: intermediate
  audience: users
  order: 3
  prerequisites:
    - user-getting-started
---

## What I do

Help you define robust, type-safe models with:
- Field types and Pydantic validation
- FieldProxy for type-safe queries
- Mixins (Timestamp, UUID, SoftDelete, Version)
- Relationships setup
- Validation and constraints

## When to use me

- Defining new models
- Adding validation rules
- Setting up relationships
- Choosing field types
- Understanding mixins

## Complete Model Example

```python
import uuid
from typing import ClassVar, Optional
from datetime import datetime
from pydantic import Field, validator
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin

class User(UUIDMixin, TimestampMixin, SoftDeleteMixin, VersionMixin, ActiveRecord):
    """
    Example model showing all features.
    
    Mixins provide:
    - UUIDMixin: id field (UUID primary key)
    - TimestampMixin: created_at, updated_at
    - SoftDeleteMixin: deleted_at for soft deletion
    - VersionMixin: version for optimistic locking
    """
    __table_name__ = 'users'
    
    # Basic fields with validation
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    age: int = Field(default=0, ge=0, le=150)
    bio: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True
    
    # REQUIRED: Enable type-safe queries
    c: ClassVar[FieldProxy] = FieldProxy()
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v.lower()

# Configure
User.configure(SQLiteBackend("app.db"))
```

## Field Types

### Basic Types

```python
from typing import Optional
from datetime import datetime, date, time
from decimal import Decimal

class Product(ActiveRecord):
    __table_name__ = 'products'
    
    # Strings
    name: str
    description: Optional[str] = None
    
    # Numbers
    price: Decimal  # Use Decimal for money
    quantity: int = 0
    rating: float = 0.0
    
    # Dates and times
    created_at: Optional[datetime] = None
    release_date: Optional[date] = None
    start_time: Optional[time] = None
    
    # Boolean
    is_available: bool = True
    
    # JSON (if backend supports it)
    metadata: Optional[dict] = None
```

### Pydantic Validation

```python
from pydantic import Field, validator, root_validator

class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    # Field constraints
    quantity: int = Field(..., ge=1, le=1000)
    price: float = Field(..., gt=0)
    email: str = Field(..., regex=r'^.+@.+$')
    
    # Custom validator
    @validator('email')
    def validate_email_domain(cls, v):
        if not v.endswith(('@company.com', '@partner.com')):
            raise ValueError('Only company emails allowed')
        return v
    
    # Cross-field validation
    @root_validator
    def validate_total(cls, values):
        quantity = values.get('quantity', 0)
        price = values.get('price', 0)
        if quantity * price > 100000:
            raise ValueError('Order total exceeds limit')
        return values
```

## FieldProxy (REQUIRED)

**Every model MUST have this for type-safe queries:**

```python
from typing import ClassVar
from rhosocial.activerecord.base import FieldProxy

class User(ActiveRecord):
    __table_name__ = 'users'
    name: str
    age: int
    
    # REQUIRED for query building
    c: ClassVar[FieldProxy] = FieldProxy()

# Usage in queries
users = User.query().where(User.c.age >= 18).all()
```

## Available Mixins

### TimestampMixin

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin

class Post(TimestampMixin, ActiveRecord):
    """Adds created_at and updated_at automatically."""
    __table_name__ = 'posts'
    title: str
    
    c: ClassVar[FieldProxy] = FieldProxy()

# Usage
post = Post(title="Hello")
post.save()
print(post.created_at)  # Auto-set
print(post.updated_at)  # Auto-set, auto-updated on save
```

### UUIDMixin

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import UUIDMixin

class File(UUIDMixin, ActiveRecord):
    """Uses UUID as primary key instead of auto-increment int."""
    __table_name__ = 'files'
    filename: str
    
    c: ClassVar[FieldProxy] = FieldProxy()

# Usage
file = File(filename="doc.pdf")
file.save()
print(file.id)  # UUID like '550e8400-e29b-41d4-a716-446655440000'
```

### SoftDeleteMixin

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import SoftDeleteMixin

class Comment(SoftDeleteMixin, ActiveRecord):
    """Soft deletion - records marked but not removed."""
    __table_name__ = 'comments'
    content: str
    
    c: ClassVar[FieldProxy] = FieldProxy()

# Usage
comment = Comment(content="Nice post!")
comment.save()
comment.delete()  # Sets deleted_at, doesn't actually delete

# Query non-deleted only (automatic)
comments = Comment.query().all()  # Excludes soft-deleted
```

### VersionMixin (Optimistic Locking)

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import VersionMixin

class Inventory(VersionMixin, ActiveRecord):
    """Prevents concurrent update conflicts."""
    __table_name__ = 'inventory'
    product_name: str
    quantity: int
    
    c: ClassVar[FieldProxy] = FieldProxy()

# Usage
item = Inventory.query().where(Inventory.c.product_name == "Widget").one()
item.quantity -= 1
item.save()  # Automatically checks version, increments it
```

## Relationships Setup

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(ActiveRecord):
    __table_name__ = 'users'
    name: str
    
    c: ClassVar[FieldProxy] = FieldProxy()
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')

class Post(ActiveRecord):
    __table_name__ = 'posts'
    title: str
    user_id: int
    
    c: ClassVar[FieldProxy] = FieldProxy()
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')
```

## Common Patterns

### Table Name Convention

```python
class UserProfile(ActiveRecord):
    __table_name__ = 'user_profiles'  # Snake case, plural
```

### Default Values

```python
from datetime import datetime

class Article(ActiveRecord):
    __table_name__ = 'articles'
    
    title: str
    status: str = "draft"  # Default value
    views: int = 0
    published_at: Optional[datetime] = None
```

### Optional vs Required

```python
class Product(ActiveRecord):
    __table_name__ = 'products'
    
    # Required (no default)
    name: str
    price: float
    
    # Optional (with default or Optional)
    description: Optional[str] = None
    discount: float = 0.0
```

## Anti-patterns

❌ **Missing FieldProxy**
```python
class User(ActiveRecord):
    # WRONG - can't use User.c in queries
    name: str
```

❌ **Wrong FieldProxy placement**
```python
class User(ActiveRecord):
    c = FieldProxy()  # WRONG - needs ClassVar type hint
```

❌ **Circular imports in relationships**
```python
# WRONG - at module level
from .post import Post

class User(ActiveRecord):
    posts = HasMany('Post')

# CORRECT - use string reference
class User(ActiveRecord):
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')
```

## Full Documentation

- **Modeling Guide:** `docs/en_US/modeling/`
- **Field Types:** `docs/en_US/modeling/field_types.md`
- **Validation:** `docs/en_US/modeling/validation.md`
- **Mixins:** `docs/en_US/modeling/mixins.md`
