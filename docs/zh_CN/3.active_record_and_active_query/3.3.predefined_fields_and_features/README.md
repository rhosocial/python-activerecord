# 预定义字段和特性

rhosocial ActiveRecord提供了几种预定义字段和特性，您可以轻松地将它们合并到您的模型中。这些特性以混入(Mixin)的形式实现，可以添加到您的模型类中，提供通用功能，而无需自己重新实现。

## 概述

rhosocial ActiveRecord中的预定义字段和特性包括：

- 主键配置
- 用于跟踪创建和更新时间的时间戳字段
- 用于逻辑删除的软删除机制
- 用于并发管理的版本控制和乐观锁
- 用于事务隔离的悲观锁策略
- 用于扩展模型功能的自定义字段

这些特性设计为可组合的，允许您根据应用程序的需求混合和匹配它们。

## 内容

- [主键配置](primary_key_configuration.md)
- [时间戳字段](timestamp_fields.md)
- [软删除机制](soft_delete_mechanism.md)
- [版本控制和乐观锁](version_control_and_optimistic_locking.md)
- [悲观锁策略](pessimistic_locking_strategies.md)
- [自定义字段](custom_fields.md)

## 使用预定义特性

要使用这些预定义特性，只需在模型类定义中包含适当的混入：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin, SoftDeleteMixin, IntegerPKMixin

class User(IntegerPKMixin, TimestampMixin, SoftDeleteMixin, ActiveRecord):
    __tablename__ = 'users'
    
    name: str
    email: str
```

在此示例中，`User`模型包括：
- 通过`IntegerPKMixin`提供整数主键支持
- 通过`TimestampMixin`提供自动时间戳管理
- 通过`SoftDeleteMixin`提供软删除功能

## 混入顺序

使用多个混入时，继承顺序可能很重要。作为一般规则：

1. 将更具体的混入放在更一般的混入之前
2. 如果两个混入修改相同的方法，列出的第一个将优先
3. 始终将`ActiveRecord`作为最后一个基类

例如，如果您有一个扩展标准`TimestampMixin`的自定义时间戳混入，您将在继承列表中将其放在`TimestampMixin`之前：

```python
class CustomTimestampMixin(TimestampMixin):
    # 自定义时间戳行为
    pass

class Article(CustomTimestampMixin, TimestampMixin, ActiveRecord):
    # 文章模型定义
    pass
```

## 下一步

通过上面内容部分中的链接详细探索每个预定义特性。