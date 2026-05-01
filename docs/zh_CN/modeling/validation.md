# 验证与生命周期钩子 (Validation & Hooks)

确保数据的完整性是模型的重要职责。

## 数据验证 (Pydantic)

由于模型是 Pydantic 的 `BaseModel`，你可以使用所有的 Pydantic 验证功能。

### 字段验证

```python
from pydantic import Field, field_validator
from rhosocial.activerecord.model import ActiveRecord

class User(ActiveRecord):
    email: str
    age: int = Field(..., ge=0, le=150)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v.lower()
```

### 使用 Annotated (可复用验证)

Pydantic V2 推荐使用 `Annotated` 来定义可复用的验证规则：

```python
from typing import Annotated
from pydantic import Field

# 定义可复用的类型
PositiveFloat = Annotated[float, Field(gt=0, description="必须为正数")]
Username = Annotated[str, Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")]

class Product(ActiveRecord):
    price: PositiveFloat
    discount: Annotated[float, Field(ge=0, le=1)] = 0.0

class Account(ActiveRecord):
    username: Username
```

### 模型级验证

```python
from pydantic import model_validator

class Range(ActiveRecord):
    start: int
    end: int

    @model_validator(mode='after')
    def check_range(self):
        if self.start > self.end:
            raise ValueError('start must be <= end')
        return self
```

### ConfigDict 常用配置

`model_config` 可以配置全局行为：

```python
class StrictUser(ActiveRecord):
    model_config = {
        "str_strip_whitespace": True,  # 自动去除字符串首尾空格
        "frozen": False,                # 不可变模式
        "extra": "forbid",              # 禁止额外字段 (forbid/ignore/allow)
        "validate_default": True,       # 对默认值也进行验证
    }

    username: str
    email: str
```

**配置说明**：

| 配置项 | 说明 |
|--------|------|
| `str_strip_whitespace` | 自动去除字符串首尾空格 |
| `frozen` | 不可变模式，创建后不能修改 |
| `extra` | `forbid` 禁止额外字段，`ignore` 忽略额外字段，`allow` 允许额外字段 |
| `validate_default` | 对默认值也进行验证 |

### 严格模式

默认情况下，Pydantic 会自动进行类型转换。启用严格模式后，禁止隐式转换：

```python
from pydantic import ConfigDict

class StrictUser(ActiveRecord):
    model_config = ConfigDict(strict=True)

    user_id: int

# 严格模式：禁止隐式转换
StrictUser(user_id=42)      # OK
# StrictUser(user_id="42")  # ValidationError: 输入必须是 int 类型
```

## Pydantic TypeAdapter 与 SQLTypeAdapter 的区别

本项目提供了**两种不同的 TypeAdapter**，分别用于不同的场景：

### Pydantic TypeAdapter

用于通用类型验证，不需要定义完整的 Model：

```python
from pydantic import TypeAdapter
from typing import List

# 验证任意类型，不需要定义 Model
adapter = TypeAdapter(List[int])
result = adapter.validate_python([1, 2, "3"])  # → [1, 2, 3]
json_result = adapter.validate_json("[1, 2, 3]")
```

### SQLTypeAdapter (项目特有)

本项目的 `SQLTypeAdapter` 用于数据库类型转换，处理 Python 对象与数据库值之间的转换：

```python
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter, BaseSQLTypeAdapter

class JsonAdapter(BaseSQLTypeAdapter):
    """将 Python dict/list 存储为 JSON 字符串"""

    def _do_to_database(self, value, target_type, options=None):
        import json
        return json.dumps(value)

    def _do_from_database(self, value, target_type, options=None):
        import json
        if isinstance(value, str):
            return json.loads(value)
        return value
```

详细用法请参考 [自定义类型](./custom_types.md)。

## 生命周期钩子 (Lifecycle Hooks)

你可以在模型保存、更新或删除的前后插入自定义逻辑。

支持的钩子方法：

*   `before_save()` / `after_save()`
*   `before_create()` / `after_create()`
*   `before_update()` / `after_update()`
*   `before_delete()` / `after_delete()`

### 示例：自动计算字段

```python
class Order(ActiveRecord):
    items: list[dict]
    total_price: float = 0.0
    
    def before_save(self):
        # 在保存前自动计算总价
        self.total_price = sum(item['price'] * item['quantity'] for item in self.items)
        super().before_save() # 记得调用父类方法
```

### 示例：关联操作

```python
class User(ActiveRecord):
    def after_create(self):
        # 用户创建后发送欢迎邮件
        send_welcome_email(self.email)
        super().after_create()
```

> **注意**: 钩子方法应该尽量保持轻量。如果在钩子中执行耗时的 I/O 操作，建议使用异步任务队列。

## 验证触发时机

Pydantic 验证流程在查询执行流程中的特定步骤被触发，具体参考 [ActiveQuery 查询生命周期](../querying/active_query.md#查询生命周期与执行流程)：

1.  **在 `all()` 和 `one()` 方法中生效**：当使用 `all()` 或 `one()` 方法执行查询时，会在结果处理阶段（ORM处理步骤）调用 `create_from_database()` 方法，此时会触发 Pydantic 验证流程，对从数据库查询到的数据进行验证。

2.  **在 `aggregate()` 方法中不起效**：当使用 `aggregate()` 方法执行查询时，只会返回原始字典列表，不会进行模型实例化过程，因此不会触发 Pydantic 验证流程。在这种情况下，你将直接获得数据库驱动返回的原始内容，而不会经过任何验证。
