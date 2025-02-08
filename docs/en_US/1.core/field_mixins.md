# Field Mixins

Field mixins provide pre-built field combinations and behaviors for common model patterns. RhoSocial ActiveRecord includes several built-in mixins that you can use to quickly add functionality to your models.

## TimestampMixin

Adds automatic timestamp management with `created_at` and `updated_at` fields.

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.fields import TimestampMixin
from datetime import datetime

class Post(TimestampMixin, ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    title: str
    content: str
    # Automatically includes:
    # created_at: datetime
    # updated_at: datetime

# Usage
post = Post(title='Hello', content='World')
post.save()
print(post.created_at)  # Current timestamp
print(post.updated_at)  # Same as created_at

# After update
post.title = 'Updated Title'
post.save()
print(post.updated_at)  # New timestamp
```

## SoftDeleteMixin

Implements soft delete functionality with `deleted_at` field.

```python
from rhosocial.activerecord.fields import SoftDeleteMixin
from typing import Optional

class User(SoftDeleteMixin, ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    # Automatically includes:
    # deleted_at: Optional[datetime]

# Usage
user = User(username='john', email='john@example.com')
user.save()

# Soft delete
user.delete()  # Sets deleted_at instead of removing record
print(user.deleted_at)  # Current timestamp

# Query excluding soft deleted records (automatic)
active_users = User.query().all()  # Only returns non-deleted users

# Include soft deleted records
all_users = User.query().with_deleted().all()

# Restore soft deleted record
user.restore()  # Clears deleted_at
```

## OptimisticLockMixin

Implements optimistic locking with version field for concurrent access control.

```python
from rhosocial.activerecord.fields import OptimisticLockMixin

class Order(OptimisticLockMixin, ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    total: Decimal
    status: str
    # Automatically includes:
    # version: int

# Usage
order = Order.find_one(1)
print(order.version)  # 1

# Concurrent update protection
order.total += 100
order.save()  # Increments version to 2

# If another process modified the record
other_order = Order.find_one(1)
other_order.total -= 50
other_order.save()  # Raises error if version mismatch
```

## UUIDMixin

Uses UUID as primary key instead of integer.

```python
from rhosocial.activerecord.fields import UUIDMixin
from uuid import UUID

class Document(UUIDMixin, ActiveRecord):
    __table_name__ = 'documents'
    
    # id field is automatically UUID type
    title: str
    content: str

# Usage
doc = Document(title='Sample', content='Content')
doc.save()
print(doc.id)  # UUID like '123e4567-e89b-12d3-a456-426614174000'
```

## IntegerPKMixin

Explicitly defines integer primary key behavior.

```python
from rhosocial.activerecord.fields import IntegerPKMixin

class Product(IntegerPKMixin, ActiveRecord):
    __table_name__ = 'products'
    
    # id field is automatically integer type
    name: str
    price: Decimal
```

## Combining Multiple Mixins

Mixins can be combined to add multiple features:

```python
class Post(TimestampMixin, SoftDeleteMixin, ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    title: str
    content: str
    # Includes:
    # created_at: datetime
    # updated_at: datetime
    # deleted_at: Optional[datetime]

# Complex E-commerce Example
class Order(
    UUIDMixin,
    TimestampMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    ActiveRecord
):
    __table_name__ = 'orders'
    
    user_id: int
    total: Decimal
    status: str
    # Includes:
    # id: UUID
    # created_at: datetime
    # updated_at: datetime
    # version: int
    # deleted_at: Optional[datetime]
    
    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_SAVE, self._validate_status)
    
    def _validate_status(self, instance: 'Order', is_new: bool):
        valid_statuses = {'pending', 'processing', 'completed', 'cancelled'}
        if self.status not in valid_statuses:
            raise ValueError(f'Invalid status: {self.status}')
```

## Creating Custom Mixins

You can create your own mixins:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.interface import ModelEvent
from datetime import datetime

class AuditMixin(ActiveRecord):
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    last_audit: Optional[datetime] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_SAVE, self._update_audit)
    
    def _update_audit(self, instance: 'AuditMixin', is_new: bool):
        current_user_id = self.get_current_user_id()  # Your implementation
        if is_new:
            self.created_by = current_user_id
        self.updated_by = current_user_id
        self.last_audit = datetime.now()

# Usage
class Document(AuditMixin, TimestampMixin, ActiveRecord):
    __table_name__ = 'documents'
    
    id: int
    title: str
    content: str
```

## Best Practices

1. **Mixin Order**: Place mixins before ActiveRecord in inheritance order
2. **Initialization**: Always call `super().__init__()` in custom mixins
3. **Event Handlers**: Use model events for automatic behaviors
4. **Validation**: Include validation logic in mixins when appropriate
5. **Documentation**: Document mixin requirements and behaviors

## Next Steps

1. Learn about [Field Validation](field_validation.md)
2. Explore [Custom Fields](custom_fields.md)
3. Study [Relationships](relationships.md)
4. Understand [Model Events](model_events.md)