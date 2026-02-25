# JSON 序列化 (JSON Serialization)

由于 rhosocial-activerecord 模型直接继承自 Pydantic V2 的 `BaseModel`，因此你可以直接使用 Pydantic 强大的序列化功能。

## 基本用法

### 转换为字典

使用 `model_dump()` 方法将模型实例转换为字典。

```python
user = User.find(1)
data = user.model_dump()
# {'id': 1, 'username': 'john', 'created_at': datetime(...)}
```

### 转换为 JSON 字符串

使用 `model_dump_json()` 方法直接生成 JSON 字符串。

```python
json_str = user.model_dump_json()
# '{"id": 1, "username": "john", "created_at": "2023-01-01T12:00:00"}'
```

## 排除和包含字段

你可以精确控制序列化输出。

```python
# 排除敏感字段
public_data = user.model_dump(exclude={'password', 'secret_key'})

# 仅包含特定字段
summary = user.model_dump(include={'id', 'username'})
```

## 处理关联数据

默认情况下，`model_dump` 不会自动加载或包含关联数据（因为它们是方法调用）。如果你需要序列化关联数据，需要手动处理或定义 computed properties。

### 方法 1: 手动构建

```python
user_data = user.model_dump()
user_data['posts'] = [p.model_dump() for p in user.posts()]
```

### 方法 2: 使用 Pydantic 的 `computed_field` (推荐)

如果你希望某些关联数据总是被序列化，可以使用 Pydantic 的 `@computed_field`。

```python
from pydantic import computed_field

class User(ActiveRecord):
    # ... 字段定义 ...

    @computed_field
    def post_count(self) -> int:
        return self.posts().count()
```

## 自定义编码器

对于特殊类型，你可以配置 Pydantic 的序列化行为。

```python
class User(ActiveRecord):
    # ...
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.timestamp()
        }
    }
```
