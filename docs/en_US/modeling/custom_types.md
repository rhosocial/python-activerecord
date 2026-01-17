# Custom Types

Sometimes we need to store complex types that are not natively supported by the database, such as storing a Python list as a JSON string.

## Using `UseAdapter`

We can define an adapter class that implements the `serialize` and `deserialize` methods.

```python
import json
from typing import List, Annotated, Any
from rhosocial.activerecord import TypeAdapter, UseAdapter

class JsonListAdapter(TypeAdapter[List[str], str]):
    def serialize(self, value: List[str]) -> str:
        return json.dumps(value)

    def deserialize(self, value: Any) -> List[str]:
        if isinstance(value, str):
            return json.loads(value)
        return value

class Post(ActiveRecord):
    # Stored as TEXT in DB, represented as List[str] in Python
    tags_cache: Annotated[List[str], UseAdapter(JsonListAdapter)] = []
```

This way, when you access `post.tags_cache`, it is automatically a list; when saving to the database, it automatically becomes a JSON string.
