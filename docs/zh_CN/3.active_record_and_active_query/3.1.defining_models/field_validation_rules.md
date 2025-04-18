# 字段验证规则

本文档解释了如何在ActiveRecord模型中定义和使用字段验证规则。验证规则确保您的数据在保存到数据库之前满足特定标准。

## 概述

rhosocial ActiveRecord利用Pydantic强大的验证系统提供全面的字段验证。这允许您直接在模型定义中定义约束和验证规则。

## 基本验证

最基本的验证形式来自Python的类型系统。通过为模型字段指定类型，您自动获得类型验证：

```python
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    id: int
    name: str
    price: float
    in_stock: bool
```

在这个例子中：
- `id`必须是整数
- `name`必须是字符串
- `price`必须是浮点数
- `in_stock`必须是布尔值

如果您尝试分配错误类型的值，将引发验证错误。

## 使用Pydantic的Field

对于更高级的验证，您可以使用Pydantic的`Field`函数添加约束：

```python
from pydantic import Field
from rhosocial.activerecord import ActiveRecord
from typing import Optional

class Product(ActiveRecord):
    id: int
    name: str = Field(..., min_length=3, max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=1000)
    sku: str = Field(..., pattern=r'^[A-Z]{2}\d{6}$')
```

在这个例子中：
- `name`必须在3到100个字符之间
- `price`必须大于0
- `description`是可选的，但如果提供，最多只能有1000个字符
- `sku`必须匹配模式：两个大写字母后跟6位数字

## 常见验证约束

### 字符串验证

```python
# 长度约束
name: str = Field(..., min_length=2, max_length=50)

# 模式匹配（正则表达式）
zip_code: str = Field(..., pattern=r'^\d{5}(-\d{4})?$')

# 预定义格式
email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
```

### 数值验证

```python
# 范围约束
age: int = Field(..., ge=0, le=120)  # 大于等于0，小于等于120

# 正数
price: float = Field(..., gt=0)  # 大于0

# 倍数
quantity: int = Field(..., multiple_of=5)  # 必须是5的倍数
```

### 集合验证

```python
from typing import List, Dict

# 具有最小/最大项目的列表
tags: List[str] = Field(..., min_items=1, max_items=10)

# 具有特定键的字典
metadata: Dict[str, str] = Field(...)
```

### 枚举验证

```python
from enum import Enum

class Status(str, Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class Order(ActiveRecord):
    id: int
    status: Status = Status.PENDING
```

## 自定义验证器

对于更复杂的验证逻辑，您可以使用Pydantic的验证器装饰器定义自定义验证器：

```python
from pydantic import validator
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    id: int
    username: str
    password: str
    password_confirm: str
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('用户名必须是字母数字')
        return v
    
    @validator('password_confirm')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('密码不匹配')
        return v
```

## 条件验证

您可以使用自定义验证器实现条件验证：

```python
from pydantic import validator
from rhosocial.activerecord import ActiveRecord
from typing import Optional

class Subscription(ActiveRecord):
    id: int
    type: str  # 'free'或'premium'
    payment_method: Optional[str] = None
    
    @validator('payment_method')
    def payment_required_for_premium(cls, v, values):
        if values.get('type') == 'premium' and not v:
            raise ValueError('高级订阅需要支付方式')
        return v
```

## 根验证器

对于涉及多个字段的验证，您可以使用根验证器：

```python
from pydantic import root_validator
from rhosocial.activerecord import ActiveRecord

class Order(ActiveRecord):
    id: int
    subtotal: float
    discount: float = 0
    total: float
    
    @root_validator
    def calculate_total(cls, values):
        if 'subtotal' in values and 'discount' in values:
            values['total'] = values['subtotal'] - values['discount']
            if values['total'] < 0:
                raise ValueError('总计不能为负数')
        return values
```

## 模型操作期间的验证

在以下操作期间自动执行验证：

1. **模型实例化**：当您创建新的模型实例时
2. **赋值**：当您为模型属性赋值时
3. **保存操作**：在保存到数据库之前

```python
# 实例化期间的验证
try:
    user = User(username="John123", password="secret", password_confirm="different")
except ValidationError as e:
    print(e)  # 将显示"密码不匹配"

# 赋值期间的验证
user = User(username="John123", password="secret", password_confirm="secret")
try:
    user.username = "John@123"  # 包含非字母数字字符
except ValidationError as e:
    print(e)  # 将显示"用户名必须是字母数字"

# 保存期间的验证
user = User(username="John123", password="secret", password_confirm="secret")
user.password_confirm = "different"
try:
    user.save()
except ValidationError as e:
    print(e)  # 将显示"密码不匹配"
```

## 处理验证错误

验证错误作为Pydantic的`ValidationError`引发。您可以捕获并处理这些错误以提供用户友好的反馈：

```python
from pydantic import ValidationError

try:
    product = Product(name="A", price=-10, sku="AB123")
except ValidationError as e:
    # 提取错误详情
    error_details = e.errors()
    
    # 格式化用户友好消息
    for error in error_details:
        field = error['loc'][0]  # 字段名称
        msg = error['msg']       # 错误消息
        print(f"{field}错误：{msg}")
```

## 最佳实践

1. **使用类型提示**：始终为模型字段指定类型以启用基本类型验证。

2. **在模型级别验证**：将验证逻辑放在模型中，而不是控制器或视图中。

3. **保持验证器简单**：每个验证器应该检查验证的一个特定方面。

4. **提供清晰的错误消息**：自定义验证器应该引发具有清晰、用户友好消息的错误。

5. **对受限选择使用枚举**：当字段只能有特定值时，使用Python的Enum类。

6. **测试您的验证器**：为您的验证逻辑编写单元测试，特别是对于复杂的自定义验证器。

## 结论

字段验证是维护应用程序数据完整性的关键部分。rhosocial ActiveRecord与Pydantic的集成提供了一种强大的声明式方式，直接在模型定义中定义验证规则。