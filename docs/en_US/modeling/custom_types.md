# Custom Types

Sometimes we need to store complex types that are not natively supported by the database, such as storing a Python list as a JSON string.

## Using `UseAdapter`

We can define an adapter class that implements the `to_database` and `from_database` methods.

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

## Adapter Trigger Timing

Custom type adapters are triggered at specific steps in the query execution flow, as referenced in [ActiveQuery Lifecycle](../querying/active_query.md#query-lifecycle-and-execution-flow):

1.  **Effective in `all()` and `one()` methods**: When using `all()` or `one()` methods to execute queries, custom type adapters are triggered during the result processing phase (ORM processing step) when calling the `create_from_database()` method. At this point, the `from_database()` method of the custom type adapter is invoked to convert raw database data into Python objects.

2.  **Not effective in `aggregate()` method**: When using the `aggregate()` method to execute queries, only raw dictionary lists are returned without the model instantiation process, so custom type adapters are not triggered. In this case, you will directly get the raw content returned by the database driver (such as JSON strings).

## Important Notes

1.  **Automatic Conversion Handling**: Custom type adapters automatically handle the conversion process when model instances are saved to and retrieved from the database. This conversion process is executed sequentially, applying adapters one by one.

2.  **Prefer Native Database Types**: Since the conversion process requires additional processing time and computational resources, it is recommended to use native database types whenever possible rather than creating particularly complex custom conversion processes. For complex data structures, consider whether they can be split into multiple simple fields or use the database's JSON type.

3.  **Ensure Reversible Conversions**: You must ensure that the conversion scheme is reversible, meaning `to_database(from_database(value)) == value`. Irreversible conversions may lead to data loss or inconsistency.

4.  **Performance Considerations**: Complex custom type conversions may impact query and save performance, especially when processing large amounts of data. Conduct thorough performance testing before using in production environments.
