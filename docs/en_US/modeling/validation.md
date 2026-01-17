# Validation & Hooks

Ensuring data integrity is a key responsibility of the model.

## Data Validation (Pydantic)

Since models are Pydantic `BaseModel`s, you can use all Pydantic validation features.

### Field Validation

```python
from pydantic import Field, field_validator
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    email: str
    age: int = Field(..., ge=0, le=150)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v.lower()
```

### Model-Level Validation

```python
from pydantic import model_validator

class Range(ActiveRecord):
    start: int
    end: int
    
    @model_validator(mode='after')
    def check_range(self):
        if self.start > self.end:
            raise ValueError('start must be <= end')
        return self
```

## Lifecycle Hooks

You can inject custom logic before or after a model is saved, updated, or deleted.

Supported hook methods:

*   `before_save()` / `after_save()`
*   `before_create()` / `after_create()`
*   `before_update()` / `after_update()`
*   `before_delete()` / `after_delete()`

### Example: Auto-Calculation

```python
class Order(ActiveRecord):
    items: list[dict]
    total_price: float = 0.0
    
    def before_save(self):
        # Calculate total price before saving
        self.total_price = sum(item['price'] * item['quantity'] for item in self.items)
        super().before_save() # Remember to call super
```

### Example: Side Effects

```python
class User(ActiveRecord):
    def after_create(self):
        # Send welcome email after user creation
        send_welcome_email(self.email)
        super().after_create()
```

> **Note**: Hook methods should be kept lightweight. If you perform time-consuming I/O operations in hooks, consider using an asynchronous task queue.
