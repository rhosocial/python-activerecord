# 自定义类型 (Custom Types)

有时我们需要存储数据库原生不支持的复杂类型，例如将 Python 列表存储为 JSON 字符串。

## 使用 `UseAdapter`

我们可以定义一个适配器类，实现 `to_database` 和 `from_database` 方法。

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

## 适配器触发时机

自定义类型适配器在查询执行流程中的特定步骤被触发，具体参考 [ActiveQuery 查询生命周期](../querying/active_query.md#查询生命周期与执行流程)：

1.  **在 `all()` 和 `one()` 方法中生效**：当使用 `all()` 或 `one()` 方法执行查询时，会在结果处理阶段（ORM处理步骤）调用 `create_from_database()` 方法，此时会触发自定义类型适配器的 `from_database()` 方法，将数据库中的原始数据转换为Python对象。

2.  **在 `aggregate()` 方法中不起效**：当使用 `aggregate()` 方法执行查询时，只会返回原始字典列表，不会进行模型实例化过程，因此不会触发自定义类型适配器。在这种情况下，你将直接获得数据库驱动返回的原始内容（如JSON字符串）。

## 重要注意事项

1.  **自动处理转换**：自定义类型适配器会在模型实例保存到数据库和从数据库查询时自动处理转换过程。这个转换过程是顺序执行的，即一个接一个地应用适配器。

2.  **优先使用数据库原生类型**：由于转换过程需要额外的处理时间和计算资源，建议尽可能使用数据库自带的原生类型，而不是创建特别复杂的自定义转换流程。对于复杂数据结构，考虑是否可以拆分为多个简单字段或使用数据库的JSON类型。

3.  **确保转换可逆性**：你必须自行确保转换方案一定是可逆的，即 `to_database(from_database(value)) == value`。不可逆的转换可能导致数据丢失或不一致。

4.  **性能考虑**：复杂的自定义类型转换可能会影响查询和保存的性能，特别是在处理大量数据时。在生产环境中使用前，请进行充分的性能测试。
