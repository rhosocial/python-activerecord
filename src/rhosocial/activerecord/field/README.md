<!-- src/rhosocial/activerecord/field/README.md -->
# Field Mixins

A collection of model field mixins that provide common attributes and behaviors for ActiveRecord models.

## Overview

This module provides several mixins that can be used to add common functionality to your models:

- `IntegerPKMixin`: Adds support for integer primary keys
- `UUIDMixin`: Adds UUID primary key support
- `CompositePKMixin`: Adds composite (multi-column) primary key support
- `DefaultTimestampMixin`: Automatically manages `created_at` and `updated_at` timestamps
- `DefaultOptimisticLockMixin`: Implements optimistic locking using a `version` field
- `DefaultSoftDeleteMixin` / `DefaultAsyncSoftDeleteMixin`: Provide soft delete functionality with a `deleted_at` field

> **Two-class convention**: behavior mixins that need a field are split into a *semantics base*
> (e.g. `TimestampMixin` — declares no fields, points at a model-declared field via a class
> attribute) and a *default subclass* (e.g. `DefaultTimestampMixin` — adds the conventional field).
> Use the `Default*` variant unless you need a custom field/column name (e.g. legacy tables); in
> that case use the semantics base and declare your own field.

## Usage

### Basic Usage

Import and use the mixins in your model classes:

```python
from rhosocial.activerecord.field import DefaultTimestampMixin, DefaultSoftDeleteMixin

class User(DefaultTimestampMixin, DefaultSoftDeleteMixin):
    name: str
    email: str
```

### Available Mixins

#### IntegerPKMixin
Provides integer primary key support. The primary key will be automatically set to None if not provided in the constructor.

```python
from rhosocial.activerecord.field import IntegerPKMixin

class Product(IntegerPKMixin):
    id: int  # This will be managed by the mixin
    name: str
```

#### UUIDMixin
Adds UUID primary key support with automatic UUID generation for new records.

```python
from rhosocial.activerecord.field import UUIDMixin

class Order(UUIDMixin):
    # id will be automatically set as UUID
    customer_name: str
    total_amount: float
```

#### DefaultTimestampMixin
Automatically manages `created_at` and `updated_at` timestamps. Updates timestamps on record creation and updates.

```python
from rhosocial.activerecord.field import DefaultTimestampMixin

class Article(DefaultTimestampMixin):
    title: str
    content: str
    # created_at and updated_at are automatically added and managed
```

To use different field/column names, inherit the semantics base `TimestampMixin` and point it at
your own fields via `__created_at_field__` / `__updated_at_field__`:

```python
from rhosocial.activerecord.field import TimestampMixin
from pydantic import Field
from datetime import datetime, timezone

class LegacyArticle(TimestampMixin):
    __created_at_field__ = "creation_date"
    __updated_at_field__ = "last_modified"

    creation_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str
    content: str
```

#### DefaultOptimisticLockMixin
Implements optimistic locking using version numbers to prevent concurrent updates.

```python
from rhosocial.activerecord.field import DefaultOptimisticLockMixin

class Account(DefaultOptimisticLockMixin):
    balance: float
    # version field is automatically managed
```

To use a custom version field, inherit `OptimisticLockMixin` and point it at your field via
`__version_field__`:

```python
from rhosocial.activerecord.field import OptimisticLockMixin
from pydantic import Field

class Account(OptimisticLockMixin):
    __version_field__ = "row_version"
    row_version: int = Field(default=1, ge=1)
    balance: float
```

#### DefaultSoftDeleteMixin
Implements soft delete functionality, allowing records to be marked as deleted without actually removing them from the database.

```python
from rhosocial.activerecord.field import DefaultSoftDeleteMixin

class Document(DefaultSoftDeleteMixin):
    title: str
    content: str

# Query methods:
Document.query()  # Returns only non-deleted records
Document.query_with_deleted()  # Returns all records
Document.query_only_deleted()  # Returns only deleted records
```

To use a custom soft-delete field, inherit `SoftDeleteMixin` (or `AsyncSoftDeleteMixin` for async
models) and point it at your field via `__deleted_at_field__`:

```python
from rhosocial.activerecord.field import SoftDeleteMixin
from datetime import datetime
from typing import Optional
from pydantic import Field

class Document(SoftDeleteMixin):
    __deleted_at_field__ = "deleted"
    deleted: Optional[datetime] = Field(default=None)
    title: str
    content: str
```

#### CompositePKMixin
Adds composite (multi-column) primary key support. Subclasses declare `__primary_key__` as a
tuple of column names and should set `__pk_auto_generated__ = False`.

```python
from rhosocial.activerecord.field import CompositePKMixin

class OrderItem(CompositePKMixin):
    __primary_key__ = ("order_id", "product_id")
    order_id: int
    product_id: int
    quantity: int
```

## Customization

### Creating Custom Mixins

You can create your own mixins by extending `IActiveRecord`. Here's a basic template:

```python
from ..interface import IActiveRecord

class CustomMixin(IActiveRecord):
    def __init__(self, **data):
        super().__init__(**data)
        # Your initialization code here

    def your_custom_method(self):
        # Your custom functionality here
        pass
```

### Extending Existing Mixins

You can extend existing mixins to add or modify functionality. Prefer the `Default*` variants as a
base so you inherit both the conventional fields and the semantics:

```python
from rhosocial.activerecord.field import DefaultTimestampMixin

class CustomTimestampMixin(DefaultTimestampMixin):
    def __init__(self, **data):
        super().__init__(**data)
        # Add your custom initialization

    def _set_updated_at(self, instance, data=None, **kwargs):
        # Override or extend the timestamp update behavior
        super()._set_updated_at(instance, data, **kwargs)
        # Add your custom logic
```

## Best Practices

1. **Mixin Order**: When using multiple mixins, consider the order of inheritance. Mixins that need to override methods should come first.

2. **Event Handling**: Use the event system (`on()` method) to hook into model lifecycle events rather than overriding methods directly.

3. **Super Calls**: Always call `super().__init__()` in your mixin's `__init__` method to ensure proper initialization chain.

4. **Type Hints**: Use proper type hints to maintain code clarity and enable better IDE support.

5. **Documentation**: Document your custom mixins with docstrings and type hints to maintain code clarity.
