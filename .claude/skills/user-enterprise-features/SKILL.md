---
name: user-enterprise-features
description: Enterprise features in rhosocial-activerecord - optimistic locking with VersionMixin, soft delete, timestamp management, UUID fields, and event system
license: MIT
compatibility: opencode
metadata:
  category: enterprise
  level: intermediate
  audience: users
  order: 6
  prerequisites:
    - user-modeling-guide
---

## What I do

Implement enterprise-grade features:
- **Optimistic Locking** - Version-based concurrency control
- **Soft Delete** - Logical deletion without data loss
- **Timestamp Management** - Automatic created_at/updated_at
- **UUID Support** - Native UUID primary keys
- **Event System** - Lifecycle hooks for business logic

## When to use me

- Building enterprise applications
- Need concurrent update protection
- Implementing soft delete patterns
- Audit trail requirements
- Event-driven architectures

## Optimistic Locking with VersionMixin

### What It Does

Automatically prevents concurrent update conflicts by tracking record version.

### Basic Usage

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import (
    TimestampMixin, SoftDeleteMixin, VersionMixin, UUIDMixin
)
from rhosocial.activerecord.base import FieldProxy

class Inventory(VersionMixin, ActiveRecord):
    __table_name__ = 'inventory'
    
    product_name: str
    quantity: int
    
    c: ClassVar = FieldProxy()

# Configure backend
Inventory.configure(backend)
```

### How It Works

```python
# User A reads record (version=1)
item_a = Inventory.find_one(1)
# version: 1

# User B reads same record (version=1)
item_b = Inventory.find_one(1)

# User A updates
item_a.quantity = 10
item_a.save()
# version incremented to 2 in database

# User B tries to update (stale version!)
item_b.quantity = 5
item_b.save()  # Raises VersionConflictError!
```

### Handling Conflicts

```python
from rhosocial.activerecord.exceptions import VersionConflictError

try:
    item_b.save()
except VersionConflictError:
    # Handle stale data
    print("Record was modified by another user!")
    
    # Reload and retry
    item_b = Inventory.find_one(item_b.id)
    item_b.quantity = 5
    item_b.save()
```

### Use Cases

- Inventory management
- Booking systems
- Payment processing
- Concurrent form editing

## Soft Delete with SoftDeleteMixin

### What It Does

Marks records as deleted without removing data, enabling recovery and audit trails.

### Basic Usage

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import SoftDeleteMixin
from rhosocial.activerecord.base import FieldProxy

class Comment(SoftDeleteMixin, ActiveRecord):
    __table_name__ = 'comments'
    
    content: str
    author: str
    
    c: ClassVar = FieldProxy()

Comment.configure(backend)
```

### How It Works

```python
# Create
comment = Comment(content="Hello world!")
comment.save()

# Soft delete (sets deleted_at)
comment.delete()  # deleted_at = NOW()

# Query (automatically excludes deleted)
comments = Comment.query().all()  # No deleted records!

# Include deleted records
all_comments = Comment.query(
    include_deleted=True
).all()

# Restore deleted record
comment.restore()

# Permanently delete (if needed)
comment.hard_delete()
```

### Querying Deleted Records

```python
# Get only deleted
deleted = Comment.query(
    include_deleted=True
).where(Comment.c.deleted_at != None).all()

# Get all (active + deleted)
all_comments = Comment.query(
    include_deleted=True
).all()

# Filter by delete time
old_deleted = Comment.query(
    include_deleted=True
).where(
    Comment.c.deleted_at < '2024-01-01'
).permanently_delete()  # Permanently remove old records
```

### Use Cases

- User management (deactivate vs delete)
- Order cancellation
- Content moderation
- Audit compliance

## Timestamp Management with TimestampMixin

### What It Does

Automatically manages `created_at` and `updated_at` fields.

### Basic Usage

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin
from rhosocial.activerecord.base import FieldProxy

class Article(TimestampMixin, ActiveRecord):
    __table_name__ = 'articles'
    
    title: str
    content: str
    
    c: ClassVar = FieldProxy()

Article.configure(backend)
```

### Automatic Fields

| Field | Set On | Updated On |
|-------|---------|------------|
| created_at | INSERT | Never |
| updated_at | INSERT | UPDATE |

### Manual Override

```python
article = Article(title="Test")
article.save()
print(article.created_at)  # Auto-set
print(article.updated_at)  # Auto-set

article.title = "Updated"
article.save()
print(article.updated_at)  # Auto-updated!

# Manual override (rarely needed)
article.created_at = datetime(2023, 1, 1)
article.save()
```

## UUID Support with UUIDMixin

### What It Does

Uses UUID instead of auto-increment integer as primary key.

### Basic Usage

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin
from rhosocial.activerecord.base import FieldProxy

class File(UUIDMixin, ActiveRecord):
    __table_name__ = 'files'
    
    filename: str
    size: int
    
    c: ClassVar = FieldProxy()

File.configure(backend)
```

### Benefits

```python
# Auto-generated UUID
file = File(filename="document.pdf", size=1024)
file.save()
print(file.id)  # '550e8400-e29b-41d4-a716-446655440000'

# URL-safe
url = f"/files/{file.id}"  # No enumeration attacks!

# Distributed systems
# Multiple services can generate IDs without collision
```

### Custom UUID Generation

```python
from rhosocial.activerecord.field import UUIDMixin
import uuid

class CustomFile(UUIDMixin, ActiveRecord):
    __table_name__ = 'files'
    
    @classmethod
    def _generate_uuid(cls):
        return uuid.uuid5(uuid.NAMESPACE_DNS, f"{cls.__table_name__}.{uuid.uuid4()}")
```

## Event System

### What It Does

Hooks into model lifecycle for business logic.

### Available Events

| Event | When |
|--------|------|
| before_save | Before INSERT or UPDATE |
| after_save | After INSERT or UPDATE |
| before_insert | Before INSERT |
| after_insert | After INSERT |
| before_update | Before UPDATE |
| after_update | After UPDATE |
| before_delete | Before DELETE |
| after_delete | After DELETE |

### Basic Usage

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin
from rhosocial.activerecord.base import FieldProxy

class Order(TimestampMixin, ActiveRecord):
    __table_name__ = 'orders'
    
    amount: float
    status: str = 'pending'
    
    c: ClassVar = FieldProxy()
    
    def before_save(self):
        if self.amount > 10000:
            self.status = 'requires_approval'
    
    def after_save(self):
        print(f"Order {self.id} saved!")

Order.configure(backend)
```

### Complete Example with All Events

```python
class AuditLog(ActiveRecord):
    __table_name__ = 'audit_logs'
    
    action: str
    details: str
    
    c: ClassVar = FieldProxy()

class User(TimestampMixin, ActiveRecord):
    __table_name__ = 'users'
    
    name: str
    email: str
    
    c: ClassVar = FieldProxy()
    
    def before_save(self):
        self.email = self.email.lower()
    
    def after_save(self):
        AuditLog(
            action='user_save',
            details=f"User {self.id} saved"
        ).save()
    
    def before_delete(self):
        # Soft delete instead of hard delete
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.save()
        return False  # Prevent hard delete
    
    def after_delete(self):
        AuditLog(
            action='user_delete',
            details=f"User {self.id} deleted"
        ).save()
```

### Async Events

```python
import asyncio

class Notification(TimestampMixin, ActiveRecord):
    __table_name__ = 'notifications'
    
    user_id: int
    message: str
    sent: bool = False
    
    c: ClassVar = FieldProxy()
    
    async def after_save(self):
        # Async event handler
        await send_notification(self.user_id, self.message)
```

## Combining Mixins

### Common Pattern

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import (
    UUIDMixin,
    TimestampMixin,
    SoftDeleteMixin,
    VersionMixin
)
from rhosocial.activerecord.base import FieldProxy

class Product(
    UUIDMixin,           # UUID primary key
    TimestampMixin,      # created_at, updated_at
    SoftDeleteMixin,     # deleted_at
    VersionMixin,       # version for concurrency
    ActiveRecord
):
    __table_name__ = 'products'
    
    name: str
    price: float
    inventory: int
    
    c: ClassVar = FieldProxy()

Product.configure(backend)
```

### Mixin Order

```python
# Convention: Base classes first, then mixins
class MyModel(
    UUIDMixin,           # 1. ID generation
    TimestampMixin,      # 2. Timestamps
    SoftDeleteMixin,     # 3. Deletion
    VersionMixin,        # 4. Concurrency
    ActiveRecord        # 5. Base
):
```

## Full Documentation

- **Optimistic Locking:** `docs/en_US/modeling/optimistic_locking.md`
- **Soft Delete:** `docs/en_US/modeling/soft_delete.md`
- **Timestamps:** `docs/en_US/modeling/timestamps.md`
- **UUID Fields:** `docs/en_US/modeling/uuid.md`
- **Events:** `docs/en_US/events/`
