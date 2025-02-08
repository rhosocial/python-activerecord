# Custom Fields

This guide explains how to create and use custom field types in RhoSocial ActiveRecord models.

## Creating Custom Field Types

### Basic Custom Field

```python
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema
from typing import Annotated, Any

class PhoneNumber:
    def __init__(self, number: str):
        self.number = self._normalize(number)
    
    def _normalize(self, number: str) -> str:
        # Remove all non-digits
        digits = ''.join(c for c in number if c.isdigit())
        if len(digits) != 10:
            raise ValueError("Phone number must be 10 digits")
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    
    def __str__(self) -> str:
        return self.number
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetJsonSchemaHandler
    ) -> CoreSchema:
        return {
            'type': 'str',
            'deserialize': lambda x: cls(x),
            'serialize': str
        }

# Usage in model
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    phone: PhoneNumber

# Example
user = User(
    name="John Doe",
    phone="1234567890"  # Stored as "(123) 456-7890"
)
```

### JSON Field Type

```python
from typing import TypeVar, Generic, Dict, Any
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class JSONField(Generic[T]):
    def __init__(self, schema_class: Type[T]):
        self.schema_class = schema_class
    
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetJsonSchemaHandler
    ) -> CoreSchema:
        return {
            'type': 'json',
            'deserialize': lambda x: cls.schema_class.parse_obj(x),
            'serialize': lambda x: x.dict()
        }

# Usage with e-commerce address
class Address(BaseModel):
    street: str
    city: str
    state: str
    zip_code: str
    country: str

class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    user_id: int
    shipping_address: JSONField[Address]
    billing_address: JSONField[Address]

# Example
order = Order(
    user_id=1,
    shipping_address={
        "street": "123 Main St",
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62701",
        "country": "USA"
    }
)
```

### Custom Array Field

```python
from typing import List, TypeVar, Generic

T = TypeVar('T')

class ArrayField(Generic[T]):
    def __init__(self, item_type: Type[T]):
        self.item_type = item_type
    
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetJsonSchemaHandler
    ) -> CoreSchema:
        return {
            'type': 'list',
            'items': {
                'type': cls.item_type.__name__.lower()
            },
            'deserialize': lambda x: [cls.item_type(i) for i in x],
            'serialize': list
        }

# Usage in social media post
class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    content: str
    tags: ArrayField[str]
    mentioned_users: ArrayField[int]

# Example
post = Post(
    content="Great meetup!",
    tags=["tech", "python", "web"],
    mentioned_users=[1, 2, 3]
)
```

## Complex Custom Fields

### Money Field

```python
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass

@dataclass
class Money:
    amount: Decimal
    currency: str = 'USD'
    
    def __init__(self, amount: Union[Decimal, str, float], currency: str = 'USD'):
        self.amount = Decimal(str(amount)).quantize(Decimal('0.01'))
        self.currency = currency.upper()
    
    def __str__(self) -> str:
        return f"{self.currency} {self.amount:,.2f}"
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetJsonSchemaHandler
    ) -> CoreSchema:
        return {
            'type': 'dict',
            'deserialize': lambda x: cls(**x),
            'serialize': lambda x: {'amount': str(x.amount), 'currency': x.currency}
        }

# Usage in e-commerce
class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: int
    name: str
    price: Money
    shipping_cost: Optional[Money]

# Example
product = Product(
    name="Premium Widget",
    price=Money("29.99", "USD"),
    shipping_cost=Money("5.00", "USD")
)
```

### GeoPoint Field

```python
from dataclasses import dataclass
from math import radians, sin, cos, sqrt, atan2

@dataclass
class GeoPoint:
    latitude: float
    longitude: float
    
    def __init__(self, latitude: float, longitude: float):
        if not -90 <= latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        self.latitude = latitude
        self.longitude = longitude
    
    def distance_to(self, other: 'GeoPoint') -> float:
        """Calculate distance in kilometers"""
        R = 6371  # Earth's radius in km
        
        lat1, lon1 = map(radians, [self.latitude, self.longitude])
        lat2, lon2 = map(radians, [other.latitude, other.longitude])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetJsonSchemaHandler
    ) -> CoreSchema:
        return {
            'type': 'dict',
            'deserialize': lambda x: cls(**x),
            'serialize': lambda x: {'latitude': x.latitude, 'longitude': x.longitude}
        }

# Usage in models
class Store(ActiveRecord):
    __table_name__ = 'stores'
    
    id: int
    name: str
    location: GeoPoint
    delivery_radius: float  # kilometers

    def is_in_delivery_range(self, point: GeoPoint) -> bool:
        return self.location.distance_to(point) <= self.delivery_radius

# Example
store = Store(
    name="Downtown Store",
    location=GeoPoint(40.7128, -74.0060),  # New York
    delivery_radius=5.0
)
```

## Database Integration

### Type Mapping

Define how custom fields map to database types:

```python
from rhosocial.activerecord.backend.dialect import DatabaseType, TypeMapping

# Register custom type mappings
CUSTOM_TYPE_MAPPINGS = {
    PhoneNumber: TypeMapping(DatabaseType.VARCHAR, length=15),
    Money: TypeMapping(DatabaseType.JSON),
    GeoPoint: TypeMapping(DatabaseType.JSON),
    ArrayField: TypeMapping(DatabaseType.JSON)
}
```

### Value Conversion

Implement value conversion for database storage:

```python
class CustomValueMapper:
    @staticmethod
    def to_database(value: Any, db_type: DatabaseType) -> Any:
        if isinstance(value, PhoneNumber):
            return str(value)
        if isinstance(value, (Money, GeoPoint)):
            return json.dumps(value.__dict__)
        return value
    
    @staticmethod
    def from_database(value: Any, db_type: DatabaseType) -> Any:
        if db_type == DatabaseType.VARCHAR and isinstance(value, str):
            return PhoneNumber(value)
        if db_type == DatabaseType.JSON:
            data = json.loads(value)
            if 'amount' in data and 'currency' in data:
                return Money(**data)
            if 'latitude' in data and 'longitude' in data:
                return GeoPoint(**data)
        return value
```

## Next Steps

1. Explore [Relationships](relationships.md)
2. Learn about [Basic Operations](basic_operations.md)
3. Study [Querying](querying.md)