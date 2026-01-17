<!-- TRANSLATION PENDING -->

# 自定义类型 (Custom Types)

有时我们需要存储数据库原生不支持的复杂类型，例如将 Python 列表存储为 JSON 字符串。

## 使用 `UseAdapter`

我们可以定义一个适配器类，实现 `serialize` 和 `deserialize` 方法。

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
    # 数据库中存储为 TEXT，Python 中表现为 List[str]
    tags_cache: Annotated[List[str], UseAdapter(JsonListAdapter)] = []
```

这样，当你访问 `post.tags_cache` 时，它自动是一个列表；保存到数据库时，它自动变成 JSON 字符串。
