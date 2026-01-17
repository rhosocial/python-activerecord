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
