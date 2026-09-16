# Type Adapters

## Overview

Type adapters handle the conversion between SQLite data types and Python types. SQLite uses a dynamic type system (type affinity), and the backend manages type conversion automatically.

## Type Mapping

### Basic SQLite Type Affinity

| SQLite Type | Python Type | Notes |
|-------------|------------|-------|
| INTEGER | `int` | 1, 2, 4, 6, or 8 bytes |
| REAL | `float` | 8-byte IEEE floating point |
| TEXT | `str` | UTF-8 encoded |
| BLOB | `bytes` | Raw binary data |
| NULL | `None` | Null value |

SQLite uses type affinity rather than strict typing. A column declared as `VARCHAR` still stores any type of data — the affinity just determines how SQLite processes the value.

### Python-to-SQLite Conversion

| Python Type | SQLite Storage | Conversion |
|-------------|----------------|------------|
| `int` | INTEGER | Direct |
| `float` | REAL | Direct |
| `str` | TEXT | Direct |
| `bytes` | BLOB | Direct |
| `bool` | INTEGER | `True` → 1, `False` → 0 |
| `None` | NULL | Direct |

### SQLite-to-Python Conversion

| SQLite Type | Python Type | Conversion |
|-------------|------------|------------|
| INTEGER | `int` | Direct |
| REAL | `float` | Direct |
| TEXT | `str` | Direct |
| BLOB | `bytes` | Direct |
| INTEGER (0/1) | `bool` | When column has BOOLEAN affinity |

## Special Types

The backend provides automatic serialization and deserialization for several Python types that have no native SQLite equivalent:

### datetime and date

```python
from datetime import datetime, date

# Stored as ISO 8601 TEXT
# datetime: "2026-01-15T10:30:00.000000"
# date: "2026-01-15"

user = User(created_at=datetime.now())
user.save()  # Automatically serialized to TEXT

user = User.find_one(1)
print(user.created_at)  # Automatically deserialized to datetime
```

| Python Type | SQLite Storage | Format |
|-------------|----------------|--------|
| `datetime.datetime` | TEXT | ISO 8601 with microseconds |
| `datetime.date` | TEXT | ISO 8601 date only |

### UUID

```python
import uuid

# Stored as TEXT (36 characters)
user = User(id=uuid.uuid4())
user.save()  # "550e8400-e29b-41d4-a716-446655440000"

user = User.find_one(1)
print(type(user.id))  # <class 'uuid.UUID'>
```

### Decimal

```python
from decimal import Decimal

# Stored as TEXT for exact precision
product = Product(price=Decimal("19.99"))
product.save()

product = Product.find_one(1)
print(type(product.price))  # <class 'decimal.Decimal'>
```

### dict and list (JSON)

Requires the JSON1 extension (built-in since SQLite 3.38.0):

```python
# Stored as JSON TEXT
user = User(settings={"theme": "dark", "notifications": True})
user.save()  # '{"theme": "dark", "notifications": true}'

user = User.find_one(1)
print(type(user.settings))  # <class 'dict'>
```

| Python Type | SQLite Storage | Extension Required |
|-------------|----------------|-------------------|
| `dict` | TEXT (JSON) | JSON1 |
| `list` | TEXT (JSON) | JSON1 |

### Summary of Special Types

| Python Type | SQLite Storage | Format | Auto-Converted |
|-------------|----------------|--------|---------------|
| `datetime.datetime` | TEXT | ISO 8601 | Yes |
| `datetime.date` | TEXT | ISO 8601 | Yes |
| `uuid.UUID` | TEXT | 36-char string | Yes |
| `decimal.Decimal` | TEXT | String representation | Yes |
| `dict` | TEXT | JSON | Yes (JSON1 required) |
| `list` | TEXT | JSON | Yes (JSON1 required) |

## Custom Type Adapters

To register custom type converters for your own Python classes:

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

backend = SQLiteBackend(database=":memory:")

class MyClass:
    def __init__(self, value):
        self.value = value

class MyClassAdapter:
    @staticmethod
    def to_sql(value, dialect):
        import json
        return json.dumps({"value": value.value})

    @staticmethod
    def from_sql(value, dialect):
        import json
        data = json.loads(value)
        return MyClass(data["value"])

backend.type_registry.register(MyClass, MyClassAdapter)
```

For more details, see [Customization](../customization/README.md).

## Checking Type Support

```python
from rhosocial.activerecord.backend.dialect.protocols import JSONSupport

dialect = backend.dialect

# Check JSON support (requires JSON1 extension)
if isinstance(dialect, JSONSupport) and dialect.supports_json_type():
    # JSON type is available
    pass
```

## See Also

- [Backend Specific Features](../backend_specific_features/README.md) — SQLite-specific capabilities
- [Customization](../customization/README.md) — Custom types and adapters
- [Core: Custom Types](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/modeling/custom_types)

💡 *AI Prompt:* "How does the type system convert between Python types and SQLite types?"
