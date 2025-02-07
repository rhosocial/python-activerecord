# Model Definition

## Basic Structure

An ActiveRecord model is a Python class that inherits from `ActiveRecord` and uses Pydantic's field type system:

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime
from typing import Optional
from pydantic import Field, EmailStr

class User(ActiveRecord):
    """User model definition"""
    
    # Required table name
    __table_name__ = 'users'
    
    # Optional primary key name (defaults to 'id')
    __primary_key__ = 'id'
    
    # Field definitions
    id: int
    name: str = Field(min_length=2, max_length=50)
    email: EmailStr
    age: Optional[int] = Field(ge=0, lt=150)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

## Field Types

### Basic Types

```python
class Product(ActiveRecord):
    __table_name__ = 'products'
    
    # Numeric types
    id: int                  # INTEGER
    price: float            # FLOAT/REAL
    quantity: int           # INTEGER
    weight: Decimal         # DECIMAL
    
    # String types
    name: str              # VARCHAR/TEXT
    description: str       # TEXT
    sku: str = Field(max_length=50)  # VARCHAR(50)
    
    # Boolean
    is_active: bool       # BOOLEAN/INTEGER
    
    # Date and Time
    created_at: datetime  # DATETIME/TIMESTAMP
    updated_at: datetime
    sale_date: date      # DATE
    sale_time: time      # TIME
```

### Advanced Types

```python
from uuid import UUID
from typing import Dict, List, Set, Any
from enum import Enum

class ProductType(str, Enum):
    PHYSICAL = 'physical'
    DIGITAL = 'digital'
    SERVICE = 'service'

class AdvancedProduct(ActiveRecord):
    __table_name__ = 'advanced_products'
    
    # UUID fields
    id: UUID = Field(default_factory=uuid.uuid4)
    
    # JSON fields
    metadata: Dict[str, Any]     # Stored as JSON
    tags: List[str]             # JSON array
    categories: Set[str]        # JSON array
    
    # Enum fields
    product_type: ProductType
    
    # Binary data
    image_data: bytes          # BLOB/BINARY
```

### Optional Fields

```python
class Article(ActiveRecord):
    __table_name__ = 'articles'
    
    id: int
    title: str
    content: str
    # Optional fields use Optional[] or None default
    excerpt: Optional[str] = None
    published_at: Optional[datetime] = None
    author_id: Optional[int] = None
```

## Field Validation

### Built-in Validations

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    # String validations
    name: str = Field(
        min_length=2,
        max_length=50,
        pattern='^[a-zA-Z ]+$'
    )
    
    # Numeric validations
    age: int = Field(ge=0, le=150)
    score: float = Field(gt=0, lt=100)
    
    # Email validation
    email: EmailStr
    
    # URL validation
    website: HttpUrl
    
    # Custom constraints
    role: str = Field(pattern='^(user|admin|editor)$')
```

### Custom Validation

```python
from pydantic import validator
from datetime import date

class Employee(ActiveRecord):
    __table_name__ = 'employees'
    
    id: int
    name: str
    birth_date: date
    hire_date: date
    
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
        if self.hire_date < date(2000, 1, 1):
            raise ValueError('Hire date too old')
```

## Table Configuration

### Table Name

```python
class Order(ActiveRecord):
    # Static table name
    __table_name__ = 'orders'
    
    @classmethod
    def table_name(cls) -> str:
        # Dynamic table name (e.g., for sharding)
        shard = cls.get_shard()
        return f'orders_{shard}'
```

### Primary Key

```python
class CustomPK(ActiveRecord):
    # Custom primary key field
    __primary_key__ = 'uid'
    
    uid: UUID = Field(default_factory=uuid.uuid4)
    
    @classmethod
    def primary_key(cls) -> str:
        # Dynamic primary key
        return cls.__primary_key__
```

## Model Mixins

### Common Field Mixins

```python
from rhosocial.activerecord.field import (
    TimestampMixin,
    SoftDeleteMixin,
    UUIDMixin
)

class Post(TimestampMixin, SoftDeleteMixin, ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    title: str
    content: str
    # Inherits created_at, updated_at from TimestampMixin
    # Inherits deleted_at from SoftDeleteMixin
```

### Custom Mixins

```python
class AuditMixin(ActiveRecord):
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    
    def prepare_save_data(self, data: Dict[str, Any], is_new: bool) -> Dict[str, Any]:
        data = super().prepare_save_data(data, is_new)
        current_user_id = self.get_current_user_id()
        if is_new:
            data['created_by'] = current_user_id
        data['updated_by'] = current_user_id
        return data
```

## Event Handling

```python
from rhosocial.activerecord.interface import ModelEvent
from typing import Any

class AuditedModel(ActiveRecord):
    def __init__(self, **data):
        super().__init__(**data)
        # Register event handlers
        self.on(ModelEvent.BEFORE_SAVE, self._before_save)
        self.on(ModelEvent.AFTER_SAVE, self._after_save)
        self.on(ModelEvent.BEFORE_DELETE, self._before_delete)
    
    def _before_save(self, instance: 'AuditedModel', **kwargs: Any) -> None:
        """Called before save"""
        instance.updated_at = datetime.now()
    
    def _after_save(self, instance: 'AuditedModel', **kwargs: Any) -> None:
        """Called after save"""
        self.log_audit_trail(instance)
    
    def _before_delete(self, instance: 'AuditedModel', **kwargs: Any) -> None:
        """Called before delete"""
        self.validate_deletion(instance)
```

## Advanced Features

### Dynamic Fields

```python
from typing import ClassVar

class DynamicModel(ActiveRecord):
    # Class-level configuration
    _settings: ClassVar[Dict[str, Any]] = {
        'cache_enabled': True,
        'cache_ttl': 3600
    }
    
    @property
    def display_name(self) -> str:
        """Dynamic property"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_address(self) -> str:
        parts = [self.street, self.city]
        if self.state:
            parts.append(self.state)
        parts.append(self.country)
        return ', '.join(parts)
```

### Type Conversion

```python
from typing import Dict, Any
import json

class ConfigModel(ActiveRecord):
    settings: Dict[str, Any]
    
    def prepare_save_data(self, data: Dict[str, Any], is_new: bool) -> Dict[str, Any]:
        """Custom type conversion for database storage"""
        data = super().prepare_save_data(data, is_new)
        if 'settings' in data:
            data['settings'] = json.dumps(data['settings'])
        return data
    
    @classmethod
    def create_from_database(cls, row: Dict[str, Any]) -> 'ConfigModel':
        """Custom type conversion from database"""
        if 'settings' in row and isinstance(row['settings'], str):
            row['settings'] = json.loads(row['settings'])
        return super().create_from_database(row)
```

## Next Steps

- Learn about [Relationships](relationships.md)
- Explore [Query Building](querying.md)
- Understand [Transactions](transactions.md)
- See [Field Mixins](field_mixins.md)