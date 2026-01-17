# Custom Types

Sometimes we need to store complex types that are not natively supported by the database, such as storing a Python list as a JSON string.

## Using `UseAdapter`

We can define an adapter class that implements the `serialize` and `deserialize` methods.

```python
import json
from typing import List, Annotated, Any, Dict, Type, Optional, Set
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter
from rhosocial.activerecord.base import UseAdapter

class JsonListAdapter(SQLTypeAdapter):
    def to_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        return json.dumps(value)

    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        if isinstance(value, str):
            return json.loads(value)
        return value

    @property
    def supported_types(self) -> Dict[Type, Set[Type]]:
        return {list: {str}}

class Post(ActiveRecord):
    # Stored as TEXT in DB, represented as List[str] in Python
    tags_cache: Annotated[List[str], UseAdapter(JsonListAdapter(), str)] = []
```

This way, when you access `post.tags_cache`, it is automatically a list; when saving to the database, it automatically becomes a JSON string.
