# Defining Models

This section covers how to define ActiveRecord models in your application. Models are the foundation of your application's data layer, representing database tables and providing methods for data manipulation.

## Overview

In rhosocial ActiveRecord, models are defined as classes that inherit from the `ActiveRecord` base class. Each model corresponds to a database table, and each instance of a model corresponds to a row in that table. Models leverage Pydantic for data validation and type safety.

## Contents

- [Table Schema Definition](table_schema_definition.md) - How to define your table structure
- [Model Relationships](model_relationships.md) - How to define and use model relationships
- [Field Validation Rules](field_validation_rules.md) - Adding validation to your model fields
- [Lifecycle Hooks](lifecycle_hooks.md) - Using events to customize model behavior
- [Inheritance and Polymorphism](inheritance_and_polymorphism.md) - Creating model hierarchies
- [Composition Patterns and Mixins](composition_patterns_and_mixins.md) - Reusing functionality across models

## Basic Model Definition

Here's a simple example of a model definition:

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime
from typing import Optional

class User(ActiveRecord):
    __table_name__ = 'users'  # Optional: defaults to class name in snake_case
    
    id: int  # Primary key (default field name is 'id')
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True  # Field with default value
    bio: Optional[str] = None  # Optional field
```

## Key Components

### Table Name

By default, the table name is derived from the class name in snake_case (e.g., `UserProfile` becomes `user_profile`). You can override this by setting the `__table_name__` class attribute.

### Primary Key

By default, the primary key field is named `id`. You can customize this by setting the `__primary_key__` class attribute:

```python
class CustomModel(ActiveRecord):
    __primary_key__ = 'custom_id'
    
    custom_id: int
    # other fields...
```

### Field Types

rhosocial ActiveRecord leverages Pydantic's type system, supporting all standard Python types and Pydantic's specialized types. Common field types include:

- Basic types: `int`, `float`, `str`, `bool`
- Date/time types: `datetime`, `date`, `time`
- Complex types: `dict`, `list`
- Optional fields: `Optional[Type]`
- Custom types: Any Pydantic-compatible type

### Field Constraints

You can add constraints to fields using Pydantic's field functions:

```python
from pydantic import Field

class Product(ActiveRecord):
    id: int
    name: str = Field(..., min_length=3, max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=1000)
```

## Next Steps

Explore the detailed documentation for each aspect of model definition to learn how to create robust, type-safe models for your application.