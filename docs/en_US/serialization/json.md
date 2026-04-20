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

### Excluding None Values

Use `exclude_none=True` to exclude fields with `None` values:

```python
user = User.find(1)
# Exclude None values
data = user.model_dump(exclude_none=True)
# {'id': 1, 'username': 'john', 'created_at': datetime(...)}  # bio field excluded
```

### Using Aliases for Output

Use `by_alias=True` to use field aliases for output:

```python
from pydantic import Field

class User(ActiveRecord):
    user_id: int = Field(alias="userId")
    user_name: str = Field(alias="userName")

user = User.find(1)
data = user.model_dump(by_alias=True)
# {'userId': 1, 'userName': 'john'}
```

## Excluding and Including Fields

You can precisely control the serialization output.

```python
user = User.find(1)

# Exclude sensitive fields
public_data = user.model_dump(exclude={'password', 'secret_key'})

# Include only specific fields
summary = user.model_dump(include={'id', 'username'})
```

### Combining Options

You can combine multiple options:

```python
data = user.model_dump(
    include={'id', 'username', 'email'},
    exclude_none=True,
    exclude={'secret_key'}
)
```

## Parsing from JSON

### Parsing from Dict

```python
user = User.model_validate({"id": 1, "username": "john", "email": "john@example.com"})
```

### Parsing from JSON String

Use `model_validate_json()` to parse JSON strings directly (faster than `model_validate(json.loads(...))`):

```python
json_str = '{"id": 1, "username": "john", "email": "john@example.com"}'
user = User.model_validate_json(json_str)
```

## Handling Related Data

By default, `model_dump` does not automatically load or include related data (as they are method calls). If you need to serialize related data, you need to handle it manually or define computed properties.

### Method 1: Manual Construction

```python
user = User.find(1)
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

## Custom Encoders (Pydantic V2)

In Pydantic V2, custom encoders use `field_serializer` and `model_serializer`:

```python
from pydantic import field_serializer, field_deserializer
from datetime import datetime

class User(ActiveRecord):
    username: str
    created_at: datetime

    @field_serializer('created_at')
    def serialize_datetime(self, v: datetime) -> str:
        return v.strftime('%Y-%m-%d %H:%M:%S')

    @field_deserializer('created_at')
    def deserialize_datetime(self, v: str) -> datetime:
        return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
```

Or use `model_serializer` for whole-model transformation:

```python
from pydantic import model_serializer

class User(ActiveRecord):
    username: str
    email: str

    @model_serializer(mode='wrap')
    def serialize(self, handler):
        data = handler(self)
        # Add extra field
        data['display_name'] = f"{self.username} <{self.email}>"
        return data
```
