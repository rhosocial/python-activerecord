# Mixin 与复用 (Mixins)

组合优于继承。`rhosocial-activerecord` 鼓励使用 Mixin 来复用通用的字段和逻辑。

## 内置 Mixin

框架提供了一些常用的 Mixin：

### UUIDMixin

使用 UUID 作为主键。

```python
from rhosocial.activerecord.field import UUIDMixin

class User(UUIDMixin, ActiveRecord):
    # 自动获得: id: uuid.UUID (Primary Key)
    pass
```

### TimestampMixin

自动记录创建时间和更新时间。

```python
from rhosocial.activerecord.field import TimestampMixin

class Post(TimestampMixin, ActiveRecord):
    # 自动获得:
    # created_at: int (默认毫秒级时间戳，可配置)
    # updated_at: int
    pass
```

### SoftDeleteMixin (软删除)

标记删除而不是物理删除。

```python
from rhosocial.activerecord.field import SoftDeleteMixin

class Comment(SoftDeleteMixin, ActiveRecord):
    # 自动获得: deleted_at: Optional[int]
    pass

# 查询时会自动过滤已删除的记录
active_comments = Comment.all()

# 物理删除
comment.delete(hard=True)
```

## 自定义 Mixin

你可以轻松创建自己的 Mixin。Mixin 只是一个继承自 `ActiveRecord` (或其基类) 的类。

### 示例：ContentMixin

假设多个模型（文章、评论、笔记）都有 `content` 和 `summary` 字段。

```python
from pydantic import Field
from rhosocial.activerecord import ActiveRecord

class ContentMixin(ActiveRecord):
    content: str
    
    # 可以在 Mixin 中定义方法和属性
    @property
    def word_count(self) -> int:
        return len(self.content.split())
        
    def summary(self, length=100) -> str:
        return self.content[:length] + "..." if len(self.content) > length else self.content

class Post(ContentMixin, ActiveRecord):
    title: str

class Comment(ContentMixin, ActiveRecord):
    user_id: str
```

通过这种方式，你可以保持代码的 DRY (Don't Repeat Yourself) 原则。
