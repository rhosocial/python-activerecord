# 自定义类型 (Custom Types)

有时我们需要存储数据库原生不支持的复杂类型，例如将 Python 列表存储为 JSON 字符串。

## 使用 `UseAdapter`

我们可以定义一个适配器类，实现 `serialize` 和 `deserialize` 方法。

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
    # 数据库中存储为 TEXT，Python 中表现为 List[str]
    tags_cache: Annotated[List[str], UseAdapter(JsonListAdapter(), str)] = []
```

这样，当你访问 `post.tags_cache` 时，它自动是一个列表；保存到数据库时，它自动变成 JSON 字符串。
