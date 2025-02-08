# Field Validation

RhoSocial ActiveRecord provides comprehensive field validation through Pydantic's validation system and custom validation hooks.

## Basic Validation

### Type Validation

Basic type validation is automatic through Python type hints:

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    age: int
    joined_at: datetime

# Type validation happens automatically
user = User(
    username=123,      # TypeError: username must be string
    age="twenty",      # TypeError: age must be integer
    joined_at="now"    # TypeError: joined_at must be datetime
)
```

### Field Constraints

Use Pydantic's Field for basic constraints:

```python
from pydantic import Field
from decimal import Decimal

class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: int
    name: str = Field(min_length=3, max_length=100)
    price: Decimal = Field(ge=0, le=9999.99)
    stock: int = Field(ge=0)
    description: str = Field(default='', max_length=1000)

# Validation occurs on save
product = Product(
    name="A",             # ValueError: name too short
    price=Decimal(-10),   # ValueError: price must be >= 0
    stock=-5              # ValueError: stock must be >= 0
)
```

## Custom Validators

### Single Field Validators

```python
from pydantic import validator
import re

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    password: str
    
    @validator('username')
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username must be alphanumeric')
        return v.lower()
    
    @validator('email')
    def validate_email(cls, v: str) -> str:
        if not '@' in v:
            raise ValueError('Invalid email format')
        return v.lower()
    
    @validator('password')
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password too short')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain number')
        return v
```

### Cross-Field Validation

```python
class Event(ActiveRecord):
    __table_name__ = 'events'
    
    id: int
    title: str
    start_date: datetime
    end_date: datetime
    max_attendees: int
    current_attendees: int
    
    @validator('end_date')
    def validate_dates(cls, v: datetime, values: dict) -> datetime:
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('End date must be after start date')
        return v
    
    @validator('current_attendees')
    def validate_attendees(cls, v: int, values: dict) -> int:
        if 'max_attendees' in values and v > values['max_attendees']:
            raise ValueError('Cannot exceed maximum attendees')
        return v
```

## Example: E-commerce Order Validation

```python
class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    items: List[Dict[str, Any]]
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    status: str
    
    @validator('items')
    def validate_items(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not v:
            raise ValueError('Order must have at least one item')
        
        for item in v:
            required_fields = {'product_id', 'quantity', 'price'}
            if not all(field in item for field in required_fields):
                raise ValueError(f'Missing required fields: {required_fields}')
            
            if item['quantity'] <= 0:
                raise ValueError('Quantity must be positive')
            
            if item['price'] <= 0:
                raise ValueError('Price must be positive')
        
        return v
    
    @validator('total')
    def validate_total(cls, v: Decimal, values: dict) -> Decimal:
        if 'subtotal' in values and 'tax' in values:
            expected_total = values['subtotal'] + values['tax']
            if abs(v - expected_total) > Decimal('0.01'):
                raise ValueError('Total does not match subtotal + tax')
        return v
```

## Example: Social Media Post Validation

```python
class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    content: str
    type: str
    media_urls: Optional[List[str]]
    mentions: Optional[List[str]]
    
    @validator('content')
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Content cannot be empty')
        if len(v) > 1000:
            raise ValueError('Content too long')
        return v
    
    @validator('type')
    def validate_type(cls, v: str) -> str:
        valid_types = {'text', 'image', 'video', 'link'}
        if v not in valid_types:
            raise ValueError(f'Invalid post type: {v}')
        return v
    
    @validator('media_urls')
    def validate_media(cls, v: Optional[List[str]], values: dict) -> Optional[List[str]]:
        if values.get('type') in {'image', 'video'} and not v:
            raise ValueError(f'{values["type"]} post requires media URLs')
        return v
```

## Model-Level Validation

Use model events for complex validation:

```python
from rhosocial.activerecord.interface import ModelEvent

class Order(ActiveRecord):
    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_SAVE, self._validate_order)
    
    def _validate_order(self, instance: 'Order', is_new: bool):
        # Complex business logic validation
        if self.status == 'completed' and not self.items:
            raise ValueError('Cannot complete order without items')
        if self.status == 'shipped' and not self.shipping_address:
            raise ValueError('Cannot ship order without address')
```

## Next Steps

1. Learn about [Custom Fields](custom_fields.md)
2. Explore [Relationships](relationships.md)
3. Study [Model Events](model_events.md)