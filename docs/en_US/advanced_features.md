# Advanced Features

## Soft Delete

Soft delete allows you to mark records as deleted without actually removing them from the database.

### Basic Usage

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import SoftDeleteMixin
from datetime import datetime
from typing import Optional

class User(SoftDeleteMixin, ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    email: str
    # deleted_at from SoftDeleteMixin
    
# Standard queries automatically exclude deleted records
users = User.query().all()

# Include deleted records
all_users = User.query_with_deleted().all()

# Only deleted records
deleted_users = User.query_only_deleted().all()

# Soft delete a record
user = User.find_one(1)
user.delete()  # Sets deleted_at, doesn't remove from database

# Restore a soft-deleted record
user = User.query_with_deleted().find_one(1)
user.restore()
```

## Optimistic Locking

Optimistic locking helps prevent concurrent updates by using a version number.

### Basic Usage

```python
from rhosocial.activerecord.field import OptimisticLockMixin

class Product(OptimisticLockMixin, ActiveRecord):
    __table_name__ = 'products'
    
    id: int
    name: str
    stock: int
    # version field added by OptimisticLockMixin
    
# Update with version check
product = Product.find_one(1)
product.stock -= 1
try:
    product.save()
except DatabaseError as e:
    print("Product was updated by another process")
```

## UUID Support

UUID fields provide globally unique identifiers.

### Basic Usage

```python
from rhosocial.activerecord.field import UUIDMixin
from uuid import UUID

class Document(UUIDMixin, ActiveRecord):
    __table_name__ = 'documents'
    
    # id field is UUID type from UUIDMixin
    title: str
    content: str
    
# UUID is automatically generated
doc = Document(title="My Doc", content="Content")
doc.save()
print(doc.id)  # UUID object

# Find by UUID
doc = Document.find_one("550e8400-e29b-41d4-a716-446655440000")
```

## Timestamps

Automatic timestamp management for created_at and updated_at fields.

### Basic Usage

```python
from rhosocial.activerecord.field import TimestampMixin

class Post(TimestampMixin, ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    title: str
    content: str
    # created_at and updated_at from TimestampMixin

# Timestamps are automatically managed
post = Post(title="New Post", content="Content")
post.save()
print(post.created_at)  # Creation time
print(post.updated_at)  # Last update time

# updated_at is automatically updated
post.title = "Updated Title"
post.save()
print(post.updated_at)  # New timestamp
```

## Event System

The event system allows you to hook into model lifecycle events.

### Available Events

```python
from rhosocial.activerecord.interface import ModelEvent

class Article(ActiveRecord):
    def __init__(self, **data):
        super().__init__(**data)
        # Register event handlers
        self.on(ModelEvent.BEFORE_SAVE, self._before_save)
        self.on(ModelEvent.AFTER_SAVE, self._after_save)
        self.on(ModelEvent.BEFORE_DELETE, self._before_delete)
        self.on(ModelEvent.AFTER_DELETE, self._after_delete)
        self.on(ModelEvent.BEFORE_VALIDATE, self._before_validate)
        self.on(ModelEvent.AFTER_VALIDATE, self._after_validate)
    
    def _before_save(self, instance, is_new: bool, **kwargs):
        """Called before save"""
        if is_new:
            instance.slug = self.generate_slug()
    
    def _after_save(self, instance, is_new: bool, **kwargs):
        """Called after successful save"""
        self.clear_cache()
    
    def _before_delete(self, instance, **kwargs):
        """Called before delete"""
        self.backup_data()
    
    def _after_delete(self, instance, **kwargs):
        """Called after successful delete"""
        self.clear_related_cache()
```

## Custom Field Types

Support for custom field types with type conversion.

### Defining Custom Types

```python
from rhosocial.activerecord.backend import DatabaseType
from dataclasses import dataclass
from typing import Any

@dataclass
class Point:
    x: float
    y: float

class MapLocation(ActiveRecord):
    __table_name__ = 'locations'
    
    id: int
    name: str
    location: Point
    
    @classmethod
    def prepare_save_data(cls, data: Dict[str, Any], is_new: bool) -> Dict[str, Any]:
        """Convert Point to database format"""
        if 'location' in data and isinstance(data['location'], Point):
            data['location'] = f"{data['location'].x},{data['location'].y}"
        return data
    
    @classmethod
    def create_from_database(cls, row: Dict[str, Any]) -> 'MapLocation':
        """Convert database format to Point"""
        if 'location' in row and isinstance(row['location'], str):
            x, y = map(float, row['location'].split(','))
            row['location'] = Point(x, y)
        return super().create_from_database(row)
```

## Validation Rules

Complex validation using Pydantic features.

### Custom Validators

```python
from pydantic import validator, Field
from datetime import date

class Employee(ActiveRecord):
    __table_name__ = 'employees'
    
    id: int
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    birth_date: date
    hire_date: date
    salary: float = Field(ge=0)
    
    @validator('hire_date')
    def validate_hire_date(cls, v, values):
        if 'birth_date' in values:
            age_at_hire = (v - values['birth_date']).days / 365
            if age_at_hire < 18:
                raise ValueError('Must be at least 18 years old at hire date')
        return v
    
    def validate_custom(self):
        """Custom validation logic"""
        super().validate_custom()
        if self.salary < self.calculate_minimum_salary():
            raise ValueError("Salary below minimum requirement")
```

## Best Practices

1. **Combine Mixins Carefully**
   ```python
   # Good - logical combination
   class Document(TimestampMixin, SoftDeleteMixin, UUIDMixin, ActiveRecord):
       pass
   
   # Bad - conflicting features
   class Product(UUIDMixin, IntegerPKMixin, ActiveRecord):  # Conflicting primary keys
       pass
   ```

2. **Event Handler Organization**
   ```python
   class Article(ActiveRecord):
       def __init__(self, **data):
           super().__init__(**data)
           self._register_events()
       
       def _register_events(self):
           """Keep event registration organized"""
           self.on(ModelEvent.BEFORE_SAVE, self._before_save)
           self.on(ModelEvent.AFTER_SAVE, self._after_save)
       
       def _before_save(self, instance, **kwargs):
           """Keep handlers focused and simple"""
           self._update_timestamps()
           self._generate_slug()
   ```

3. **Validation Rules**
   ```python
   class Article(ActiveRecord):
       # Use Pydantic field validation when possible
       title: str = Field(min_length=1, max_length=200)
       slug: str = Field(regex=r'^[a-z0-9-]+)
       status: str = Field(pattern='^(draft|published|archived))
       
       # Use custom validators for complex logic
       @validator('slug')
       def validate_slug(cls, v, values):
           if 'title' in values and not v:
               return slugify(values['title'])
           return v
       
       # Use validate_custom for model-level validation
       def validate_custom(self):
           super().validate_custom()
           if self.is_published and not self.content:
               raise ValueError("Published articles must have content")
   ```

4. **Type Conversion**
   ```python
   class Settings(ActiveRecord):
       # Define clear conversion rules
       @classmethod
       def prepare_save_data(cls, data: Dict[str, Any], is_new: bool) -> Dict[str, Any]:
           data = super().prepare_save_data(data, is_new)
           if 'config' in data:
               data['config'] = json.dumps(data['config'])
           return data
       
       @classmethod
       def create_from_database(cls, row: Dict[str, Any]) -> 'Settings':
           if 'config' in row:
               row['config'] = json.loads(row['config'])
           return super().create_from_database(row)
   ```

5. **Feature Composition**
   ```python
   # Create focused mixins
   class AuditMixin(ActiveRecord):
       created_by: Optional[int] = None
       updated_by: Optional[int] = None
       
       def prepare_save_data(self, data: Dict[str, Any], is_new: bool) -> Dict[str, Any]:
           data = super().prepare_save_data(data, is_new)
           user_id = get_current_user_id()
           if is_new:
               data['created_by'] = user_id
           data['updated_by'] = user_id
           return data

   # Combine features logically
   class Document(
       TimestampMixin,    # Automatic timestamps
       SoftDeleteMixin,   # Soft delete support
       AuditMixin,        # User tracking
       ActiveRecord
   ):
       __table_name__ = 'documents'
       title: str
       content: str
```

## Common Pitfalls

1. **Event Handler Overload**
   ```python
   # Bad - too many responsibilities
   def _before_save(self, instance, **kwargs):
       self._update_timestamps()
       self._generate_slug()
       self._validate_business_rules()
       self._update_search_index()
       self._notify_webhooks()  # External call in event handler
   
   # Good - focused handlers
   def _before_save(self, instance, **kwargs):
       self._update_timestamps()
       self._generate_slug()
   
   def _after_save(self, instance, **kwargs):
       # Schedule async tasks for heavy operations
       self.schedule_search_index_update()
       self.schedule_webhook_notifications()
   ```

2. **Memory Management**
   ```python
   # Bad - retaining unnecessary data
   class Article(ActiveRecord):
       def __init__(self, **data):
           super().__init__(**data)
           self.revision_history = []  # Grows unbounded
   
   # Good - use database for history
   class ArticleRevision(ActiveRecord):
       article_id: int
       content: str
       created_at: datetime
   ```

3. **Type Safety**
   ```python
   # Bad - bypassing type system
   class Product(ActiveRecord):
       price: float
       
       def set_price(self, value: Any):
           self.price = value  # Might break type safety
   
   # Good - maintain type safety
   class Product(ActiveRecord):
       price: float
       
       def set_price(self, value: float):
           self.price = float(value)  # Ensures type safety
   ```

## Next Steps

- Learn about [Custom Field Types](field_types.md)
- Explore [Cache Strategies](caching.md)
- Study [Performance Optimization](performance.md)
- Review [Testing Strategies](testing.md)