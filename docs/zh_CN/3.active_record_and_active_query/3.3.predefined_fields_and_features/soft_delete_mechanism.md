# 软删除机制

软删除是一种模式，其中记录被标记为已删除，而不是从数据库中物理删除。rhosocial ActiveRecord提供了`SoftDeleteMixin`来在您的模型中实现这种模式。

## 概述

`SoftDeleteMixin`为您的模型添加了一个`deleted_at`时间戳字段。当记录被"删除"时，该字段被设置为当前时间戳，而不是从数据库中删除记录。这允许您：

- 维护所有记录的历史记录，包括已删除的记录
- 实现"垃圾箱"或"回收站"功能
- 恢复意外删除的记录
- 在相关记录中维护引用完整性

## 基本用法

要向模型添加软删除功能，请在类定义中包含`SoftDeleteMixin`：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import SoftDeleteMixin

class Article(SoftDeleteMixin, ActiveRecord):
    __table_name__ = 'articles'
    
    title: str
    content: str
```

使用此设置，在文章上调用`delete()`将把它标记为已删除，而不是删除它：

```python
# 创建一个新文章
article = Article(title="Hello World", content="这是我的第一篇文章")
article.save()

# 软删除文章
article.delete()

# 文章现在被标记为已删除
print(article.deleted_at)  # 删除时的当前日期时间

# 记录仍然存在于数据库中，但默认查询不会返回它
```

## 查询软删除记录

`SoftDeleteMixin`修改了默认查询行为，以排除软删除的记录。它提供了用于处理已删除记录的其他方法：

```python
# 默认查询 - 仅返回未删除的记录
articles = Article.query().all()

# 包括已删除的记录
all_articles = Article.query_with_deleted().all()

# 仅查询已删除的记录
deleted_articles = Article.query_only_deleted().all()
```

## 恢复软删除记录

您可以使用`restore()`方法恢复软删除的记录：

```python
# 查找已删除的文章
deleted_article = Article.query_only_deleted().first()

# 恢复文章
deleted_article.restore()

# 文章现在已恢复（deleted_at设置为None）
print(deleted_article.deleted_at)  # None
```

## 工作原理

`SoftDeleteMixin`通过以下方式工作：

1. 向您的模型添加一个可为空的`deleted_at`时间戳字段
2. 为`BEFORE_DELETE`事件注册处理程序以设置时间戳
3. 覆盖默认查询方法以过滤掉已删除的记录
4. 提供用于处理已删除记录的其他查询方法
5. 实现`restore()`方法以取消删除记录

以下是实现的简化视图：

```python
class SoftDeleteMixin(IActiveRecord):
    deleted_at: Optional[datetime] = Field(default=None)

    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_DELETE, self._mark_as_deleted)

    def _mark_as_deleted(self, instance, **kwargs):
        instance.deleted_at = datetime.now(tzlocal.get_localzone())

    def prepare_delete(self):
        return {'deleted_at': self.deleted_at}

    @classmethod
    def query(cls):
        return super().query().where("deleted_at IS NULL")

    @classmethod
    def query_with_deleted(cls):
        return super().query()

    @classmethod
    def query_only_deleted(cls):
        return super().query().where("deleted_at IS NOT NULL")

    def restore(self):
        # 将deleted_at设置为None并保存的实现
```

## 与其他混入结合

`SoftDeleteMixin`与其他混入（如`TimestampMixin`）配合良好：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin, SoftDeleteMixin

class Article(TimestampMixin, SoftDeleteMixin, ActiveRecord):
    __table_name__ = 'articles'
    
    title: str
    content: str
```

使用此设置，您将拥有：
- `created_at`：记录创建时间
- `updated_at`：记录最后更新时间
- `deleted_at`：记录软删除时间（如果未删除，则为`None`）

## 批量操作

软删除也适用于批量操作：

```python
# 软删除多篇文章
Article.delete_all({"author_id": 123})

# 所有匹配的文章现在都被标记为已删除，而不是物理删除
```

## 数据库考虑因素

软删除向数据库表添加了一个额外的列并修改了查询行为。请考虑以下几点：

- **索引**：您可能希望在`deleted_at`列上添加索引以提高性能
- **唯一约束**：如果您有唯一约束，它们可能需要包括`deleted_at`以允许"已删除"的重复项
- **级联删除**：您需要在应用程序代码中处理级联软删除

## 最佳实践

1. **保持一致**：在相关模型中一致使用软删除
2. **考虑硬删除选项**：对于某些数据（如个人信息），您可能需要真正的硬删除选项以符合合规要求
3. **定期清理**：考虑实现一个过程来永久删除非常旧的软删除记录
4. **UI清晰度**：向用户清楚地表明他们正在查看包括或排除已删除记录的数据

## 下一步

现在您了解了软删除，您可能想要探索：

- [版本控制和乐观锁](version_control_and_optimistic_locking.md) - 用于管理并发更新
- [悲观锁策略](pessimistic_locking_strategies.md) - 用于更强的并发控制