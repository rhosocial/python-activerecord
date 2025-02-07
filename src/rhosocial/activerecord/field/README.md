# Field Mixins

A collection of model field mixins that provide common attributes and behaviors for ActiveRecord models.

## Overview

This module provides several mixins that can be used to add common functionality to your models:

- `IntegerPKMixin`: Adds support for integer primary keys
- `TimestampMixin`: Automatically manages created_at and updated_at timestamps
- `OptimisticLockMixin`: Implements optimistic locking using version numbers
- `SoftDeleteMixin`: Provides soft delete functionality
- `UUIDMixin`: Adds UUID primary key support

## Usage

### Basic Usage

Import and use the mixins in your model classes:

```python
from rhosocial.activerecord.field import TimestampMixin, SoftDeleteMixin

class User(TimestampMixin, SoftDeleteMixin):
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

#### TimestampMixin
Automatically manages `created_at` and `updated_at` timestamps. Updates timestamps on record creation and updates.

```python
from rhosocial.activerecord.field import TimestampMixin

class Article(TimestampMixin):
    title: str
    content: str
    # created_at and updated_at are automatically added and managed
```

#### OptimisticLockMixin
Implements optimistic locking using version numbers to prevent concurrent updates.

```python
from rhosocial.activerecord.field import OptimisticLockMixin

class Account(OptimisticLockMixin):
    balance: float
    # version field is automatically managed
```

#### SoftDeleteMixin
Implements soft delete functionality, allowing records to be marked as deleted without actually removing them from the database.

```python
from rhosocial.activerecord.field import SoftDeleteMixin

class Document(SoftDeleteMixin):
    title: str
    content: str

# Query methods:
Document.query()  # Returns only non-deleted records
Document.query_with_deleted()  # Returns all records
Document.query_only_deleted()  # Returns only deleted records
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

You can extend existing mixins to add or modify functionality:

```python
from rhosocial.activerecord.field import TimestampMixin

class CustomTimestampMixin(TimestampMixin):
    def __init__(self, **data):
        super().__init__(**data)
        # Add your custom initialization

    def _update_timestamps(self, instance, is_new: bool, **kwargs):
        # Override or extend the timestamp update behavior
        super()._update_timestamps(instance, is_new, **kwargs)
        # Add your custom logic
```

## Best Practices

1. **Mixin Order**: When using multiple mixins, consider the order of inheritance. Mixins that need to override methods should come first.

2. **Event Handling**: Use the event system (`on()` method) to hook into model lifecycle events rather than overriding methods directly.

3. **Super Calls**: Always call `super().__init__()` in your mixin's `__init__` method to ensure proper initialization chain.

4. **Type Hints**: Use proper type hints to maintain code clarity and enable better IDE support.

5. **Documentation**: Document your custom mixins with docstrings and type hints to maintain code clarity.