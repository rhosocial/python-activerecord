# Field Validation Rules

This document explains how to define and use field validation rules in your ActiveRecord models. Validation rules ensure that your data meets specific criteria before it's saved to the database.

## Overview

rhosocial ActiveRecord leverages Pydantic's powerful validation system to provide comprehensive field validation. This allows you to define constraints and validation rules directly in your model definition.

## Basic Validation

The most basic form of validation comes from Python's type system. By specifying types for your model fields, you automatically get type validation:

```python
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    id: int
    name: str
    price: float
    in_stock: bool
```

In this example:
- `id` must be an integer
- `name` must be a string
- `price` must be a floating-point number
- `in_stock` must be a boolean

If you try to assign a value of the wrong type, a validation error will be raised.

## Using Pydantic's Field

For more advanced validation, you can use Pydantic's `Field` function to add constraints:

```python
from pydantic import Field
from rhosocial.activerecord import ActiveRecord
from typing import Optional

class Product(ActiveRecord):
    id: int
    name: str = Field(..., min_length=3, max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=1000)
    sku: str = Field(..., pattern=r'^[A-Z]{2}\d{6}$')
```

In this example:
- `name` must be between 3 and 100 characters long
- `price` must be greater than 0
- `description` is optional but if provided, must be at most 1000 characters
- `sku` must match the pattern: two uppercase letters followed by 6 digits

## Common Validation Constraints

### String Validation

```python
# Length constraints
name: str = Field(..., min_length=2, max_length=50)

# Pattern matching (regex)
zip_code: str = Field(..., pattern=r'^\d{5}(-\d{4})?$')

# Predefined formats
email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
```

### Numeric Validation

```python
# Range constraints
age: int = Field(..., ge=0, le=120)  # greater than or equal to 0, less than or equal to 120

# Positive numbers
price: float = Field(..., gt=0)  # greater than 0

# Multiple of
quantity: int = Field(..., multiple_of=5)  # must be a multiple of 5
```

### Collection Validation

```python
from typing import List, Dict

# List with min/max items
tags: List[str] = Field(..., min_items=1, max_items=10)

# Dictionary with specific keys
metadata: Dict[str, str] = Field(...)
```

### Enum Validation

```python
from enum import Enum

class Status(str, Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class Order(ActiveRecord):
    id: int
    status: Status = Status.PENDING
```

## Custom Validators

For more complex validation logic, you can define custom validators using Pydantic's validator decorators:

```python
from pydantic import validator
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    id: int
    username: str
    password: str
    password_confirm: str
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v
    
    @validator('password_confirm')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
```

## Conditional Validation

You can implement conditional validation using custom validators:

```python
from pydantic import validator
from rhosocial.activerecord import ActiveRecord
from typing import Optional

class Subscription(ActiveRecord):
    id: int
    type: str  # 'free' or 'premium'
    payment_method: Optional[str] = None
    
    @validator('payment_method')
    def payment_required_for_premium(cls, v, values):
        if values.get('type') == 'premium' and not v:
            raise ValueError('Payment method is required for premium subscriptions')
        return v
```

## Root Validators

For validation that involves multiple fields, you can use root validators:

```python
from pydantic import root_validator
from rhosocial.activerecord import ActiveRecord

class Order(ActiveRecord):
    id: int
    subtotal: float
    discount: float = 0
    total: float
    
    @root_validator
    def calculate_total(cls, values):
        if 'subtotal' in values and 'discount' in values:
            values['total'] = values['subtotal'] - values['discount']
            if values['total'] < 0:
                raise ValueError('Total cannot be negative')
        return values
```

## Validation During Model Operations

Validation is automatically performed during these operations:

1. **Model Instantiation**: When you create a new model instance
2. **Assignment**: When you assign values to model attributes
3. **Save Operations**: Before saving to the database

```python
# Validation during instantiation
try:
    user = User(username="John123", password="secret", password_confirm="different")
except ValidationError as e:
    print(e)  # Will show "Passwords do not match"

# Validation during assignment
user = User(username="John123", password="secret", password_confirm="secret")
try:
    user.username = "John@123"  # Contains non-alphanumeric character
except ValidationError as e:
    print(e)  # Will show "Username must be alphanumeric"

# Validation during save
user = User(username="John123", password="secret", password_confirm="secret")
user.password_confirm = "different"
try:
    user.save()
except ValidationError as e:
    print(e)  # Will show "Passwords do not match"
```

## Handling Validation Errors

Validation errors are raised as Pydantic's `ValidationError`. You can catch and handle these errors to provide user-friendly feedback:

```python
from pydantic import ValidationError

try:
    product = Product(name="A", price=-10, sku="AB123")
except ValidationError as e:
    # Extract error details
    error_details = e.errors()
    
    # Format user-friendly messages
    for error in error_details:
        field = error['loc'][0]  # The field name
        msg = error['msg']       # The error message
        print(f"Error in {field}: {msg}")
```

## Best Practices

1. **Use Type Hints**: Always specify types for your model fields to enable basic type validation.

2. **Validate at the Model Level**: Put validation logic in your models rather than in controllers or views.

3. **Keep Validators Simple**: Each validator should check one specific aspect of validation.

4. **Provide Clear Error Messages**: Custom validators should raise errors with clear, user-friendly messages.

5. **Use Enums for Constrained Choices**: When a field can only have specific values, use Python's Enum class.

6. **Test Your Validators**: Write unit tests for your validation logic, especially for complex custom validators.

## Conclusion

Field validation is a critical part of maintaining data integrity in your application. rhosocial ActiveRecord's integration with Pydantic provides a powerful, declarative way to define validation rules directly in your model definitions.