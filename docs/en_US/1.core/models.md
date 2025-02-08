# Models

Models are the core component of RhoSocial ActiveRecord. Each model class represents a database table and provides an object-oriented interface for database operations.

## Basic Model Definition

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime
from typing import Optional

class User(ActiveRecord):
    __table_name__ = 'users'  # Database table name
    
    # Field definitions with type hints
    id: int
    username: str
    email: str
    created_at: datetime
    deleted_at: Optional[datetime] = None
```

## Model Configuration

Configure database connection for models:

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig

# Basic configuration
User.configure(
    ConnectionConfig(database='app.db'),
    backend_class=SQLiteBackend
)

# Configuration with options
User.configure(
    ConnectionConfig(
        database='app.db',
        pool_size=5,
        pool_timeout=30,
        options={'journal_mode': 'WAL'}
    ),
    backend_class=SQLiteBackend
)
```

## Model Instance Operations

### Creating Records

```python
# Create instance
user = User(
    username='john_doe',
    email='john@example.com',
    created_at=datetime.now()
)

# Save to database
user.save()

# Create and save in one step
user = User.create(
    username='jane_doe',
    email='jane@example.com',
    created_at=datetime.now()
)
```

### Reading Records

```python
# Find by primary key
user = User.find_one(1)

# Find with conditions
user = User.find_one({
    'email': 'john@example.com'
})

# Find or raise exception
user = User.find_one_or_fail(1)

# Find multiple records
users = User.find_all([1, 2, 3])
active_users = User.find_all({
    'deleted_at': None
})
```

### Updating Records

```python
# Update single record
user.username = 'john_smith'
user.save()

# Mass update
User.query()\
    .where('status = ?', ('inactive',))\
    .update({'deleted_at': datetime.now()})
```

### Deleting Records

```python
# Delete single record
user.delete()

# Batch delete
User.query()\
    .where('created_at < ?', (one_year_ago,))\
    .delete()
```

## Model Events

Models support lifecycle events:

```python
from rhosocial.activerecord.interface import ModelEvent

class User(ActiveRecord):
    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_SAVE, self._before_save)
        self.on(ModelEvent.AFTER_SAVE, self._after_save)
    
    def _before_save(self, instance: 'User', is_new: bool):
        if is_new:
            self.created_at = datetime.now()
        
    def _after_save(self, instance: 'User', is_new: bool):
        # Log or trigger notifications
        pass
```

## Complex Example: E-Commerce Order System

```python
from decimal import Decimal
from typing import List
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.relations import HasMany, BelongsTo

class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    user_id: int
    total: Decimal
    status: str
    created_at: datetime
    
    # Relationships
    items: List['OrderItem'] = HasMany('OrderItem', foreign_key='order_id')
    user: 'User' = BelongsTo('User', foreign_key='user_id')
    
    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_SAVE, self._calculate_total)
    
    def _calculate_total(self, instance: 'Order', is_new: bool):
        """Calculate order total from items"""
        if self.items:
            self.total = sum(item.price * item.quantity for item in self.items)
    
    @classmethod
    def create_with_items(cls, user_id: int, items: List[dict]) -> 'Order':
        """Create order with items in a transaction"""
        with cls.transaction():
            # Create order
            order = cls(
                user_id=user_id,
                status='pending',
                created_at=datetime.now()
            )
            order.save()
            
            # Create order items
            for item_data in items:
                OrderItem(
                    order_id=order.id,
                    **item_data
                ).save()
            
            # Reload order with items
            order.refresh()
            return order
```

## Model Validation

Models support validation through Pydantic:

```python
from pydantic import EmailStr, validator
from typing import ClassVar

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    email: EmailStr
    username: str
    status: str
    
    # Class-level validation
    VALID_STATUSES: ClassVar[set] = {'active', 'inactive', 'suspended'}
    
    @validator('username')
    def username_must_be_valid(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters')
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v
    
    @validator('status')
    def status_must_be_valid(cls, v: str) -> str:
        if v not in cls.VALID_STATUSES:
            raise ValueError(f'Status must be one of: {cls.VALID_STATUSES}')
        return v
```

## Model Mixins

Use mixins to share functionality:

```python
from rhosocial.activerecord.fields import TimestampMixin, SoftDeleteMixin

class User(TimestampMixin, SoftDeleteMixin, ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    # Inherits created_at, updated_at from TimestampMixin
    # Inherits deleted_at from SoftDeleteMixin
```

## Advanced Model Features

### Custom Primary Keys

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    __primary_key__ = 'user_id'  # Custom primary key
    
    user_id: int
    username: str
```

### Table Inheritance

```python
class Content(ActiveRecord):
    """Base content model"""
    id: int
    title: str
    body: str
    author_id: int
    created_at: datetime

class Article(Content):
    """Article specific content"""
    __table_name__ = 'articles'
    category: str
    published_at: Optional[datetime]

class Page(Content):
    """Page specific content"""
    __table_name__ = 'pages'
    slug: str
    menu_order: int
```

## Next Steps

1. Learn about [Fields](fields.md) in detail
2. Explore [Relationships](relationships.md)
3. Master [Querying](querying.md)
4. Study [Validation](field_validation.md)