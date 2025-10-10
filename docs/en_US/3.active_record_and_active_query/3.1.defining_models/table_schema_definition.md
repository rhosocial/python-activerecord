# Table Schema Definition

This document explains how to define the table schema for your ActiveRecord models. The table schema defines the structure of your database table, including field names, types, and constraints.

## Basic Schema Definition

In rhosocial ActiveRecord, the table schema is defined through the model class definition. Each attribute of the class represents a column in the database table.

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime
from typing import Optional

class User(ActiveRecord):
    id: int
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
```

In this example:
- `id`, `username`, `email`, `created_at`, and `updated_at` are required fields
- `is_active` has a default value of `True`

## Table Name Configuration

By default, the table name is derived from the class name in snake_case format. For example, a class named `UserProfile` would map to a table named `user_profile`.

You can explicitly set the table name using the `__table_name__` class attribute:

```python
class User(ActiveRecord):
    __table_name__ = 'app_users'  # Maps to the 'app_users' table
    
    id: int
    username: str
    # other fields...
```

## Primary Key Configuration

By default, ActiveRecord assumes the primary key field is named `id`. You can customize this by setting the `__primary_key__` class attribute:

```python
class Product(ActiveRecord):
    __primary_key__ = 'product_id'  # Use 'product_id' as the primary key
    
    product_id: int
    name: str
    # other fields...
```

## Field Types and Database Mapping

rhosocial ActiveRecord leverages Pydantic's type system and maps Python types to appropriate database column types. Here's how common Python types map to database types:

| Python Type | SQLite | MySQL | PostgreSQL |
|-------------|--------|-------|------------|
| `int` | INTEGER | INT | INTEGER |
| `float` | REAL | DOUBLE | DOUBLE PRECISION |
| `str` | TEXT | VARCHAR | VARCHAR |
| `bool` | INTEGER | TINYINT | BOOLEAN |
| `datetime` | TEXT | DATETIME | TIMESTAMP |
| `date` | TEXT | DATE | DATE |
| `bytes` | BLOB | BLOB | BYTEA |
| `dict`, `list` | TEXT (JSON) | JSON | JSONB |
| `UUID` | TEXT | CHAR(36) | UUID |

## Field Constraints

You can add constraints to your fields using Pydantic's `Field` function:

```python
from pydantic import Field

class Product(ActiveRecord):
    id: int
    name: str = Field(..., min_length=3, max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=1000)
    category: str = Field(..., pattern=r'^[A-Z][a-z]+$')
```

Common constraints include:
- `min_length`/`max_length`: For string length validation
- `gt`/`ge`/`lt`/`le`: For numeric value validation (greater than, greater or equal, less than, less or equal)
- `regex`/`pattern`: For string pattern validation
- `default`: Default value if not provided

## Optional Fields

You can mark fields as optional using Python's `typing.Optional` type hint:

```python
from typing import Optional

class User(ActiveRecord):
    id: int
    username: str
    email: str
    bio: Optional[str] = None  # Optional field with default None
```

## Default Values

You can specify default values for fields:

```python
class User(ActiveRecord):
    id: int
    username: str
    is_active: bool = True  # Default to True
    login_count: int = 0  # Default to 0
```

## Computed Fields

You can define computed properties that aren't stored in the database but are calculated when accessed:

```python
class Order(ActiveRecord):
    id: int
    subtotal: float
    tax_rate: float = 0.1
    
    @property
    def total(self) -> float:
        """Calculate the total including tax."""
        return self.subtotal * (1 + self.tax_rate)
```

## Field Documentation

It's good practice to document your fields using docstrings or Pydantic's `Field` description:

```python
from pydantic import Field

class User(ActiveRecord):
    id: int
    username: str = Field(
        ...,
        description="The user's unique username for login"
    )
    email: str = Field(
        ...,
        description="The user's email address for notifications"
    )
```

## Schema Validation

When you create or update a model instance, Pydantic automatically validates the data against your schema definition. If validation fails, a `ValidationError` is raised with details about the validation issues.

## Advanced Schema Features (❌ NOT IMPLEMENTED)

### Indexes

You can define indexes on your model using the `__indexes__` class attribute:

```python
class User(ActiveRecord):
    __indexes__ = [
        ('username',),  # Single column index
        ('first_name', 'last_name'),  # Composite index
        {'columns': ('email',), 'unique': True}  # Unique index
    ]
    
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
```

### Custom Column Types

For more control over the exact database column type, you can use the `Field` function with the `sa_column_type` parameter:

```python
from pydantic import Field

class Product(ActiveRecord):
    id: int
    name: str
    description: str = Field(
        ...,
        sa_column_type="TEXT"  # Force TEXT type in database
    )
```

## Conclusion

Defining your table schema through rhosocial ActiveRecord models provides a clean, type-safe way to structure your database. The combination of Python type hints and Pydantic validation ensures your data maintains integrity throughout your application.