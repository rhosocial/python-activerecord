# JSON 序列化 (JSON Serialization)

由于 rhosocial-activerecord 模型直接继承自 Pydantic V2 的 `BaseModel`，因此你可以直接使用 Pydantic 强大的序列化功能。

## 基本用法

### 转换为字典

使用 `model_dump()` 方法将模型实例转换为字典。

```python
user = User.find_one(1)
data = user.model_dump()
# {'id': 1, 'username': 'john', 'created_at': datetime(...)}
```

### 转换为 JSON 字符串

使用 `model_dump_json()` 方法直接生成 JSON 字符串。

```python
json_str = user.model_dump_json()
# '{"id": 1, "username": "john", "created_at": "2023-01-01T12:00:00"}'
```

### 排除 None 值

使用 `exclude_none=True` 排除值为 `None` 的字段：

```python
user = User.find_one(1)
# 排除 None 值
data = user.model_dump(exclude_none=True)
# {'id': 1, 'username': 'john', 'created_at': datetime(...)}  # bio 字段被排除
```

### 使用别名输出

使用 `by_alias=True` 使用字段别名输出：

```python
from pydantic import Field

class User(ActiveRecord):
    user_id: int = Field(alias="userId")
    user_name: str = Field(alias="userName")

user = User.find_one(1)
data = user.model_dump(by_alias=True)
# {'userId': 1, 'userName': 'john'}
```

## 排除和包含字段

你可以精确控制序列化输出。

```python
user = User.find_one(1)

# 排除敏感字段
public_data = user.model_dump(exclude={'password', 'secret_key'})

# 仅包含特定字段
summary = user.model_dump(include={'id', 'username'})
```

### 组合使用

可以组合多种选项：

```python
data = user.model_dump(
    include={'id', 'username', 'email'},
    exclude_none=True,
    exclude={'secret_key'}
)
```

## 从 JSON 解析

### 从 dict 解析

```python
user = User.model_validate({"id": 1, "username": "john", "email": "john@example.com"})
```

### 从 JSON 字符串解析

使用 `model_validate_json()` 直接解析 JSON 字符串（比 `model_validate(json.loads(...))` 更快）：

```python
json_str = '{"id": 1, "username": "john", "email": "john@example.com"}'
user = User.model_validate_json(json_str)
```

## 处理关联数据

默认情况下，`model_dump` 不会自动加载或包含关联数据（因为它们是方法调用）。如果你需要序列化关联数据，需要手动处理或定义 computed properties。

### 方法 1: 手动构建

```python
user = User.find_one(1)
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

## 自定义编码器 (Pydantic V2)

在 Pydantic V2 中，自定义编码器使用 `field_serializer` 和 `model_serializer`：

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

或者使用 `model_serializer` 进行全字段转换：

```python
from pydantic import model_serializer

class User(ActiveRecord):
    username: str
    email: str

    @model_serializer(mode='wrap')
    def serialize(self, handler):
        data = handler(self)
        # 添加额外字段
        data['display_name'] = f"{self.username} <{self.email}>"
        return data
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
