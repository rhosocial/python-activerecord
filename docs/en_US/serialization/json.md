# JSON Serialization

Since rhosocial-activerecord models inherit directly from Pydantic V2's `BaseModel`, you can leverage Pydantic's powerful serialization capabilities out of the box.

## Basic Usage

### Converting to Dictionary

Use the `model_dump()` method to convert a model instance to a dictionary.

```python
user = User.find(1)
data = user.model_dump()
# {'id': 1, 'username': 'john', 'created_at': datetime(...)}
```

### Converting to JSON String

Use the `model_dump_json()` method to generate a JSON string directly.

```python
json_str = user.model_dump_json()
# '{"id": 1, "username": "john", "created_at": "2023-01-01T12:00:00"}'
```

## Excluding and Including Fields

You can precisely control the serialization output.

```python
# Exclude sensitive fields
public_data = user.model_dump(exclude={'password', 'secret_key'})

# Include only specific fields
summary = user.model_dump(include={'id', 'username'})
```

## Handling Related Data

By default, `model_dump` does not automatically load or include related data (as they are method calls). If you need to serialize related data, you need to handle it manually or define computed properties.

### Method 1: Manual Construction

```python
user_data = user.model_dump()
user_data['posts'] = [p.model_dump() for p in user.posts()]
```

### Method 2: Using Pydantic's `computed_field` (Recommended)

If you want certain related data to always be serialized, you can use Pydantic's `@computed_field`.

```python
from pydantic import computed_field

class User(ActiveRecord):
    # ... field definitions ...

    @computed_field
    def post_count(self) -> int:
        return self.posts().count()
```

## Custom Encoders

For special types, you can configure Pydantic's serialization behavior.

```python
class User(ActiveRecord):
    # ...
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.timestamp()
        }
    }
```
