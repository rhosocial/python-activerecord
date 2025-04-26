# 组合模式和混入

本文档解释了如何在ActiveRecord模型中使用组合模式和混入。这些技术允许您在不依赖继承层次结构的情况下跨模型重用功能。

## 概述

组合是一种设计模式，其中复杂对象由更小的、可重用的组件构建而成。在rhosocial ActiveRecord中，组合通常使用混入实现 - 混入是提供特定功能的类，可以"混入"到其他类中。

混入相比传统继承提供了几个优势：

- 它们允许更灵活的代码重用
- 它们避免了单一继承的限制
- 它们使从多个来源组合功能变得更容易
- 它们保持模型层次结构扁平且可维护

## 使用预定义混入

rhosocial ActiveRecord带有几个预定义的混入，提供常见功能：

### TimestampMixin

添加对created_at和updated_at字段的自动时间戳管理：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin

class Article(TimestampMixin, ActiveRecord):
    id: int
    title: str
    content: str
    # created_at和updated_at会自动添加和管理
```

### SoftDeleteMixin

实现软删除功能，允许将记录标记为已删除而不实际从数据库中删除它们：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import SoftDeleteMixin

class Document(SoftDeleteMixin, ActiveRecord):
    id: int
    title: str
    content: str
    # deleted_at会自动添加和管理
    
# 使用方法：
doc = Document.find(1)
doc.delete()  # 标记为已删除但保留在数据库中

# 查询方法：
Document.query()  # 返回仅未删除的记录
Document.query_with_deleted()  # 返回所有记录
Document.query_only_deleted()  # 仅返回已删除的记录
```

### OptimisticLockMixin

使用版本号实现乐观锁定，防止并发更新：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import OptimisticLockMixin

class Account(OptimisticLockMixin, ActiveRecord):
    id: int
    balance: float
    # version字段会自动添加和管理
```

### UUIDMixin

添加UUID主键支持，为新记录自动生成UUID：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import UUIDMixin

class Order(UUIDMixin, ActiveRecord):
    # id将自动设置为UUID
    customer_name: str
    total_amount: float
```

### IntegerPKMixin

提供整数主键支持，自动处理新记录的空值：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin

class Product(IntegerPKMixin, ActiveRecord):
    # id将自动管理
    name: str
    price: float
```

## 创建自定义混入

您可以创建自己的混入来封装可重用功能：

### 基本混入结构

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.interface import ModelEvent
from typing import ClassVar, Optional

class AuditableMixin(ActiveRecord):
    """添加审计功能的混入。"""
    
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    
    # 存储当前用户ID的类变量
    __current_user_id__: ClassVar[Optional[int]] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        
        # 注册事件处理程序
        self.on(ModelEvent.BEFORE_CREATE, self._set_created_by)
        self.on(ModelEvent.BEFORE_UPDATE, self._set_updated_by)
    
    def _set_created_by(self, event):
        """将created_by字段设置为当前用户ID。"""
        if self.__class__.__current_user_id__ is not None:
            self.created_by = self.__class__.__current_user_id__
    
    def _set_updated_by(self, event):
        """将updated_by字段设置为当前用户ID。"""
        if self.__class__.__current_user_id__ is not None:
            self.updated_by = self.__class__.__current_user_id__
    
    @classmethod
    def set_current_user(cls, user_id: Optional[int]):
        """设置用于审计的当前用户ID。"""
        cls.__current_user_id__ = user_id
```

### 使用自定义混入

```python
class Invoice(AuditableMixin, TimestampMixin, ActiveRecord):
    id: int
    amount: float
    description: str
    # 继承created_at, updated_at, created_by, updated_by

# 设置审计的当前用户
Invoice.set_current_user(user_id=123)

# 创建新发票（将有created_by=123）
invoice = Invoice(amount=100.0, description="月度服务")
invoice.save()
```

## 组合模式

### 特征类混入

特征是提供单一功能的小型、专注的混入：

```python
class TaggableMixin(ActiveRecord):
    """添加标签功能的混入。"""
    
    _tags: str = ""  # 存储在数据库中的逗号分隔标签
    
    def add_tag(self, tag: str):
        """向此记录添加标签。"""
        tags = self.tags
        if tag not in tags:
            tags.append(tag)
            self._tags = ",".join(tags)
    
    def remove_tag(self, tag: str):
        """从此记录中删除标签。"""
        tags = self.tags
        if tag in tags:
            tags.remove(tag)
            self._tags = ",".join(tags)
    
    @property
    def tags(self) -> list:
        """获取标签列表。"""
        return self._tags.split(",") if self._tags else []
```

### 行为混入

行为混入向模型添加特定行为：

```python
from datetime import datetime, timedelta

class ExpirableMixin(ActiveRecord):
    """添加过期行为的混入。"""
    
    expires_at: Optional[datetime] = None
    
    def set_expiration(self, days: int):
        """将过期日期设置为从现在起的天数。"""
        self.expires_at = datetime.now() + timedelta(days=days)
    
    def is_expired(self) -> bool:
        """检查记录是否已过期。"""
        return self.expires_at is not None and datetime.now() > self.expires_at
    
    @classmethod
    def query_active(cls):
        """仅查询未过期的记录。"""
        return cls.query().where(
            (cls.expires_at == None) | (cls.expires_at > datetime.now())
        )
```

### 验证器混入

验证器混入添加自定义验证逻辑：

```python
from pydantic import validator

class EmailValidationMixin(ActiveRecord):
    """添加电子邮件验证的混入。"""
    
    email: str
    
    @validator('email')
    def validate_email(cls, v):
        """验证电子邮件格式。"""
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
            raise ValueError('无效的电子邮件格式')
        return v.lower()  # 规范化为小写
```

### 查询范围混入

查询范围混入添加可重用的查询方法：

```python
from datetime import datetime

class TimeScopeMixin(ActiveRecord):
    """添加基于时间的查询范围的混入。"""
    
    created_at: datetime
    
    @classmethod
    def created_today(cls):
        """查询今天创建的记录。"""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        return cls.query().where(
            (cls.created_at >= today.isoformat()) & 
            (cls.created_at < tomorrow.isoformat())
        )
    
    @classmethod
    def created_this_week(cls):
        """查询本周创建的记录。"""
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=7)
        return cls.query().where(
            (cls.created_at >= start_of_week.isoformat()) & 
            (cls.created_at < end_of_week.isoformat())
        )
```

## 组合多个混入

您可以组合多个混入来构建复杂功能：

```python
class Article(
    TaggableMixin,        # 添加标签功能
    ExpirableMixin,        # 添加过期行为
    TimeScopeMixin,        # 添加基于时间的查询范围
    SoftDeleteMixin,       # 添加软删除功能
    TimestampMixin,        # 添加时间戳管理
    IntegerPKMixin,        # 添加整数主键支持
    ActiveRecord
):
    title: str
    content: str
    author_id: int
    
    # 现在这个模型拥有所有来自混入的功能
```

## 混入顺序考虑

由于方法解析顺序（MRO），混入的顺序在Python中很重要。当调用方法时，Python会按特定顺序在类及其父类中搜索它。

```python
# 这个顺序：
class User(AuditableMixin, TimestampMixin, ActiveRecord):
    pass

# 与这个顺序不同：
class User(TimestampMixin, AuditableMixin, ActiveRecord):
    pass
```

如果两个混入定义了相同的方法或挂钩到相同的事件，列出的第一个将优先。

### 混入顺序的最佳实践

1. 将更具体的混入放在更一般的混入之前
2. 将覆盖其他混入方法的混入放在列表前面
3. 始终将ActiveRecord放在继承列表的最后

## 委托模式

另一种组合模式是委托，其中模型将某些操作委托给关联对象：

```python
class ShoppingCart(ActiveRecord):
    id: int
    user_id: int
    
    def items(self):
        """获取购物车项目。"""
        from .cart_item import CartItem
        return CartItem.query().where(cart_id=self.id).all()
    
    @property
    def total(self) -> float:
        """通过委托给购物车项目计算总计。"""
        return sum(item.subtotal for item in self.items())
    
    def add_product(self, product_id: int, quantity: int = 1):
        """向购物车添加产品。"""
        from .cart_item import CartItem
        from .product import Product
        
        # 检查产品是否已在购物车中
        existing_item = CartItem.query().where(
            cart_id=self.id, product_id=product_id
        ).first()
        
        if existing_item:
            # 更新数量
            existing_item.quantity += quantity
            existing_item.save()
            return existing_item
        else:
            # 创建新的购物车项目
            product = Product.find(product_id)
            item = CartItem(
                cart_id=self.id,
                product_id=product_id,
                price=product.price,
                quantity=quantity
            )
            item.save()
            return item
```

## 最佳实践

1. **保持混入专注**：每个混入应该有单一责任。

2. **记录混入需求**：清楚地记录混入期望在使用它的类中存在的任何字段或方法。

3. **避免混入冲突**：当组合可能覆盖相同方法或挂钩到相同事件的混入时要小心。

4. **使用组合而非继承**：在可能的情况下，优先使用组合（has-a关系）而非继承（is-a关系）。

5. **独立测试混入**：为您的混入编写单元测试，确保它们在隔离状态下正常工作。

6. **考虑命名空间污染**：通过混入向模型添加太多方法或属性时要小心。

7. **使用描述性名称**：命名您的混入以清楚地表明其目的（例如，`TaggableMixin`，`AuditableMixin`）。

## 结论

组合模式和混入提供了在ActiveRecord模型中重用功能的强大方法。通过将常见行为分解为小型、专注的混入，您可以创建更可维护和灵活的代码。这种方法允许您从简单的构建块组合复杂模型，遵循组合优于继承的原则。