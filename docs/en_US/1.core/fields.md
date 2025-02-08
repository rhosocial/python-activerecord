# Fields

Fields define the structure and behavior of model attributes. RhoSocial ActiveRecord uses Python type hints and Pydantic for field definitions, providing both type safety and validation.

## Basic Field Types

### Numeric Types

```python
from rhosocial.activerecord import ActiveRecord
from decimal import Decimal

class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: int                     # Integer primary key
    price: Decimal             # Decimal for currency
    stock: int                 # Integer quantity
    weight: float              # Floating point number
    rating: float              # Decimal number (0-5)
```

### String Types

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str              # Variable length string
    password_hash: str         # Fixed length string
    bio: str                   # Text field
    status: str               # Short string enum
```

### Date and Time Types

```python
from datetime import datetime, date, time

class Event(ActiveRecord):
    __table_name__ = 'events'
    
    id: int
    title: str
    date: date                # Date only
    start_time: time          # Time only
    end_time: time
    created_at: datetime      # Date and time
    updated_at: datetime
```

### Boolean Type

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    is_active: bool           # Boolean field
    is_admin: bool
    email_verified: bool
```

### Optional Fields

```python
from typing import Optional

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    phone: Optional[str] = None      # Nullable field
    deleted_at: Optional[datetime] = None
```

## Complex Field Types

### Enum Fields

```python
from enum import Enum, auto

class OrderStatus(Enum):
    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    CANCELLED = auto()

class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    status: OrderStatus      # Enum field
```

### JSON Fields

```python
from typing import Dict, Any, List

class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: int
    name: str
    attributes: Dict[str, Any]    # JSON field
    tags: List[str]               # Array field
```

### Custom Types

```python
from pydantic import EmailStr
from uuid import UUID

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: UUID                     # UUID primary key
    email: EmailStr              # Email field
```

## Field Options

### Default Values

```python
from datetime import datetime, timezone

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    title: str
    content: str
    views: int = 0              # Default integer
    status: str = 'draft'       # Default string
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
```

### Field Configuration

```python
from pydantic import Field

class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: int
    name: str = Field(min_length=3, max_length=100)
    price: Decimal = Field(ge=0)
    stock: int = Field(ge=0)
    description: str = Field(default='')
```

## Field Validation

### Basic Validation

```python
from pydantic import validator

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    age: int
    
    @validator('username')
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError('Username too short')
        return v.lower()
    
    @validator('age')
    def validate_age(cls, v: int) -> int:
        if v < 0:
            raise ValueError('Age cannot be negative')
        return v
```

### Complex Validation

```python
from pydantic import validator
from typing import List

class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    items: List[Dict[str, Any]]
    total: Decimal
    
    @validator('items')
    def validate_items(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not v:
            raise ValueError('Order must have at least one item')
        
        for item in v:
            if 'quantity' not in item:
                raise ValueError('Each item must have a quantity')
            if item['quantity'] <= 0:
                raise ValueError('Quantity must be positive')
        
        return v
    
    @validator('total')
    def validate_total(cls, v: Decimal, values: Dict[str, Any]) -> Decimal:
        if 'items' in values:
            expected_total = sum(
                item['price'] * item['quantity'] 
                for item in values['items']
            )
            if v != expected_total:
                raise ValueError('Total does not match items')
        return v
```

## Field Type Mapping

The library automatically maps Python types to database types:

| Python Type | SQLite    | MySQL     | PostgreSQL |
|------------|-----------|-----------|------------|
| int        | INTEGER   | INT       | INTEGER    |
| float      | REAL      | FLOAT     | REAL       |
| Decimal    | REAL      | DECIMAL   | DECIMAL    |
| str        | TEXT      | VARCHAR   | TEXT       |
| datetime   | TEXT      | DATETIME  | TIMESTAMP  |
| date       | TEXT      | DATE      | DATE       |
| time       | TEXT      | TIME      | TIME       |
| bool       | INTEGER   | TINYINT   | BOOLEAN    |
| UUID       | TEXT      | CHAR(36)  | UUID       |
| Dict       | TEXT      | JSON      | JSONB      |
| List       | TEXT      | JSON      | JSONB      |

## Next Steps

1. Learn about [Field Mixins](field_mixins.md)
2. Explore [Field Validation](field_validation.md)
3. Study [Custom Fields](custom_fields.md)
4. Understand [Relationships](relationships.md)