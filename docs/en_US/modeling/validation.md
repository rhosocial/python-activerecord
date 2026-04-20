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

### Using Annotated (Reusable Validators)

Pydantic V2 recommends using `Annotated` for defining reusable validation rules:

```python
from typing import Annotated
from pydantic import Field

# Define reusable types
PositiveFloat = Annotated[float, Field(gt=0, description="Must be positive")]
Username = Annotated[str, Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")]

class Product(ActiveRecord):
    price: PositiveFloat
    discount: Annotated[float, Field(ge=0, le=1)] = 0.0

class Account(ActiveRecord):
    username: Username
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

### ConfigDict Common Configurations

`model_config` can configure global behavior:

```python
class StrictUser(ActiveRecord):
    model_config = {
        "str_strip_whitespace": True,  # Auto-strip whitespace from strings
        "frozen": False,               # Immutable mode
        "extra": "forbid",              # Forbid extra fields (forbid/ignore/allow)
        "validate_default": True,      # Validate default values too
    }

    username: str
    email: str
```

**Configuration Options**:

| Option | Description |
|--------|-------------|
| `str_strip_whitespace` | Auto-strip whitespace from strings |
| `frozen` | Immutable mode - cannot modify after creation |
| `extra` | `forbid` reject extra fields, `ignore` ignore, `allow` allow |
| `validate_default` | Validate default values as well |

### Strict Mode

By default, Pydantic automatically performs type coercion. Enable strict mode to disable implicit conversion:

```python
from pydantic import ConfigDict

class StrictUser(ActiveRecord):
    model_config = ConfigDict(strict=True)

    user_id: int

# Strict mode: No implicit conversion allowed
StrictUser(user_id=42)      # OK
# StrictUser(user_id="42")  # ValidationError: Input must be int
```

## Pydantic TypeAdapter vs SQLTypeAdapter

This project provides **two different TypeAdapters** for different scenarios:

### Pydantic TypeAdapter

Used for general type validation without needing a complete Model definition:

```python
from pydantic import TypeAdapter
from typing import List

# Validate any type, no need to define a Model
adapter = TypeAdapter(List[int])
result = adapter.validate_python([1, 2, "3"])  # → [1, 2, 3]
json_result = adapter.validate_json("[1, 2, 3]")
```

### SQLTypeAdapter (Project-Specific)

The project's `SQLTypeAdapter` is used for database type conversion, handling conversion between Python objects and database values:

```python
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter, BaseSQLTypeAdapter

class JsonAdapter(BaseSQLTypeAdapter):
    """Store Python dict/list as JSON string"""

    def _do_to_database(self, value, target_type, options=None):
        import json
        return json.dumps(value)

    def _do_from_database(self, value, target_type, options=None):
        import json
        if isinstance(value, str):
            return json.loads(value)
        return value
```

For more details, see [Custom Types](./custom_types.md).

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

## Validation Trigger Timing

Pydantic validation is triggered at specific steps in the query execution flow, as referenced in [ActiveQuery Lifecycle](../querying/active_query.md#query-lifecycle-and-execution-flow):

1.  **Effective in `all()` and `one()` methods**: When using `all()` or `one()` methods to execute queries, Pydantic validation is triggered during the result processing phase (ORM processing step) when calling the `create_from_database()` method. At this point, the data queried from the database is validated.

2.  **Not effective in `aggregate()` method**: When using the `aggregate()` method to execute queries, only raw dictionary lists are returned without the model instantiation process, so Pydantic validation is not triggered. In this case, you will directly get the raw content returned by the database driver without any validation.
