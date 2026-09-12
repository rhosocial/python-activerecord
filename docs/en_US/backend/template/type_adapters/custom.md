# Custom Type Adapters

## Overview

When the built-in type adapters do not meet your needs, you can create custom adapters to handle specialized data types. This is useful for storing complex objects, domain-specific types, or any data that requires custom serialization.

## Creating Custom Adapters

### Pydantic Field Validators

The simplest approach for custom type conversion is using Pydantic's `field_validator`:

```python
from pydantic import field_validator
from rhosocial.activerecord.model import ActiveRecord


class Address:
    def __init__(self, street: str, city: str, zip_code: str):
        self.street = street
        self.city = city
        self.zip_code = zip_code

    def to_json(self) -> str:
        import json
        return json.dumps({
            'street': self.street,
            'city': self.city,
            'zip_code': self.zip_code,
        })

    @classmethod
    def from_json(cls, data: str) -> 'Address':
        import json
        d = json.loads(data)
        return cls(d['street'], d['city'], d['zip_code'])


class User(ActiveRecord):
    address: str

    @field_validator('address', mode='before')
    @classmethod
    def serialize_address(cls, v):
        if isinstance(v, Address):
            return v.to_json()
        return v

    @field_validator('address', mode='after')
    @classmethod
    def deserialize_address(cls, v):
        if isinstance(v, str):
            return Address.from_json(v)
        return v
```

### SQLTypeAdapter (Advanced)

For more control over the conversion process, you can subclass `SQLTypeAdapter`:

<!-- Document the SQLTypeAdapter pattern if available in the backend. Example:

```python
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter


class AddressAdapter(SQLTypeAdapter):
    def to_database(self, value):
        """Convert Python object to database value."""
        if isinstance(value, Address):
            return value.to_json()
        return value

    def from_database(self, value):
        """Convert database value to Python object."""
        if isinstance(value, str):
            return Address.from_json(value)
        return value


# Register the adapter
from rhosocial.activerecord.backend.impl.{backend} import {Backend}Backend
{Backend}Backend.register_adapter(Address, AddressAdapter())
```

-->

## Adapter Priority

When multiple adapters can handle the same type, the most specific adapter wins:

1. Registered custom adapters (highest priority)
2. Built-in type adapters
3. Default conversion (lowest priority)

## See Also

- [Type Mapping](mapping.md) — built-in type mappings
- [Core: Custom Types](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/custom_types)

💡 *AI Prompt:* "How do I store a Python dataclass in a {database} column?"
