# 时间戳字段

时间戳字段对于跟踪记录的创建和更新时间至关重要。rhosocial ActiveRecord提供了`TimestampMixin`来自动管理这些字段。

## 概述

`TimestampMixin`为您的模型添加了两个日期时间字段：

- `created_at`：记录首次创建的时间
- `updated_at`：记录最后更新的时间

这些字段由混入自动维护，它通过挂钩到模型的生命周期事件来适当地更新时间戳。

## 基本用法

要向模型添加时间戳功能，只需在类定义中包含`TimestampMixin`：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin

class Article(TimestampMixin, ActiveRecord):
    __table_name__ = 'articles'
    
    title: str
    content: str
```

使用此设置，`created_at`和`updated_at`字段将被自动管理：

```python
# 创建新文章
article = Article(title="Hello World", content="这是我的第一篇文章")
article.save()

# 时间戳自动设置
print(article.created_at)  # 创建时的当前日期时间
print(article.updated_at)  # 初始时与created_at相同

# 更新文章
article.content = "更新的内容"
article.save()

# updated_at自动更新，created_at保持不变
print(article.updated_at)  # 更新时的当前日期时间
```

## 工作原理

`TimestampMixin`的工作原理是：

1. 定义`created_at`和`updated_at`字段，默认值设置为当前时间
2. 为`BEFORE_SAVE`事件注册处理程序
3. 在事件处理程序中，根据记录是新的还是现有的来更新时间戳

以下是实现的简化视图：

```python
class TimestampMixin(IActiveRecord):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone))

    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_SAVE, self._update_timestamps)

    def _update_timestamps(self, instance, is_new: bool, **kwargs):
        now = datetime.now(timezone)
        if is_new:
            instance.created_at = now
        instance.updated_at = now
```

## 时区处理

默认情况下，`TimestampMixin`使用本地时区作为时间戳值。您可以通过设置`__timezone__`类属性来自定义此行为：

```python
import pytz
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin

class Article(TimestampMixin, ActiveRecord):
    __table_name__ = 'articles'
    __timezone__ = pytz.timezone('UTC')  # 对时间戳使用UTC
    
    title: str
    content: str
```

## 自定义时间戳行为

您可以通过扩展`TimestampMixin`并重写`_update_timestamps`方法来自定义时间戳行为：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin

class CustomTimestampMixin(TimestampMixin):
    last_viewed_at: datetime = None
    
    def _update_timestamps(self, instance, is_new: bool, **kwargs):
        # 首先调用父实现
        super()._update_timestamps(instance, is_new, **kwargs)
        
        # 添加自定义行为
        if not is_new and kwargs.get('is_view', False):
            instance.last_viewed_at = datetime.now(self.__timezone__)

class Article(CustomTimestampMixin, ActiveRecord):
    __table_name__ = 'articles'
    
    title: str
    content: str
    
    def view(self):
        # 更新last_viewed_at的自定义方法
        self.save(is_view=True)
```

## 数据库考虑因素

不同的数据库处理日期时间字段的方式不同：

- **SQLite**：将时间戳存储为ISO8601字符串
- **MySQL/MariaDB**：使用`DATETIME`或`TIMESTAMP`类型
- **PostgreSQL**：使用`TIMESTAMP`或`TIMESTAMP WITH TIME ZONE`类型

rhosocial ActiveRecord为您处理这些差异，确保跨数据库后端的一致行为。

## 最佳实践

1. **始终包含时间戳**：在所有模型中包含时间戳字段是一个好习惯，用于审计和调试目的
2. **使用UTC**：对于跨多个时区的应用程序，考虑对所有时间戳使用UTC
3. **考虑额外的审计字段**：对于更全面的审计，考虑添加`created_by`和`updated_by`等字段

## 下一步

现在您了解了时间戳字段，您可能想探索：

- [软删除机制](soft_delete_mechanism.md) - 用于实现逻辑删除
- [版本控制和乐观锁](version_control_and_optimistic_locking.md) - 用于管理并发更新