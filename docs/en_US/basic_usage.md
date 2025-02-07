# Basic Usage

## Model Definition

### Simple Model

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime
from typing import Optional
from pydantic import Field, EmailStr

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str = Field(min_length=2, max_length=50)
    email: EmailStr
    age: Optional[int] = Field(ge=0, lt=150)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

### Field Types

RhoSocial ActiveRecord supports all Pydantic field types and provides additional validations:

```python
from decimal import Decimal
from uuid import UUID

class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    price: Decimal = Field(ge=Decimal('0.00'))
    stock: int = Field(ge=0)
    category: str = Field(max_length=50)
    description: Optional[str] = None
    is_active: bool = True
```

## CRUD Operations

### Create

```python
# Simple creation
user = User(name='John Doe', email='john@example.com')
user.save()

# Bulk creation
users = [
    User(name='User 1', email='user1@example.com'),
    User(name='User 2', email='user2@example.com')
]
User.save_all(users)
```

### Read

```python
# Find by primary key
user = User.find_one(1)

# Find by conditions
user = User.find_one({'email': 'john@example.com'})

# Find all
all_users = User.find_all()

# Find with conditions
active_users = User.find_all({'is_active': True})

# Find or fail (raises RecordNotFound if not found)
user = User.find_one_or_fail(1)
```

### Update

```python
# Single record update
user = User.find_one(1)
user.name = 'Jane Doe'
user.save()

# Mass update
User.query()
    .where('age < ?', (18,))
    .update({'is_active': False})
```

### Delete

```python
# Single record delete
user = User.find_one(1)
user.delete()

# Mass delete
User.query()
    .where('created_at < ?', (one_year_ago,))
    .delete()
```

## Basic Querying

### Simple Queries

```python
# Basic where clause
users = User.query()
    .where('age > ?', (18,))
    .all()

# Multiple conditions
users = User.query()
    .where('age > ?', (18,))
    .where('is_active = ?', (True,))
    .all()

# ORDER BY
users = User.query()
    .order_by('created_at DESC')
    .all()

# LIMIT and OFFSET
users = User.query()
    .limit(10)
    .offset(20)
    .all()
```

### Aggregations

```python
# Count
total = User.query().count()

# Sum
total_stock = Product.query().sum('stock')

# Average
avg_price = Product.query().avg('price')

# Min/Max
newest_user = User.query().max('created_at')
oldest_user = User.query().min('created_at')
```

## Validation

ActiveRecord models inherit Pydantic validation:

```python
try:
    # This will raise ValidationError
    user = User(name='A', email='invalid-email')
except ValidationError as e:
    print(e.errors())
```

## Event Handling

Models support lifecycle events:

```python
from rhosocial.activerecord.interface import ModelEvent

class User(ActiveRecord):
    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_SAVE, self._before_save)
        self.on(ModelEvent.AFTER_SAVE, self._after_save)
    
    def _before_save(self, instance, **kwargs):
        instance.updated_at = datetime.now()
    
    def _after_save(self, instance, **kwargs):
        print(f"User {instance.id} saved!")
```

## Type Conversion

ActiveRecord automatically handles type conversion between Python and database types:

```python
class Settings(ActiveRecord):
    __table_name__ = 'settings'
    
    id: int
    data: Dict[str, Any]  # Stored as JSON in database
    tags: List[str]       # Stored as JSON array
    flags: Set[str]       # Stored as JSON array
```

## Error Handling

```python
from rhosocial.activerecord.backend.errors import (
    DatabaseError,
    RecordNotFound,
    ValidationError,
    IntegrityError
)

try:
    user = User.find_one_or_fail(999)
except RecordNotFound:
    print("User not found")

try:
    user.save()
except IntegrityError:
    print("Constraint violation")
except ValidationError as e:
    print("Validation failed:", e.errors())
except DatabaseError as e:
    print("Database error:", str(e))
```

## Next Steps

- Learn about [Model Definition in Detail](model_definition.md)
- Explore [Advanced Querying](querying.md)
- Understand [Relationships](relationships.md)
- Work with [Transactions](transactions.md)