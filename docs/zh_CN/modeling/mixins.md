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
    # created_at: datetime (UTC 时区)
    # updated_at: datetime (UTC 时区)
    pass
```

#### 时间戳生成策略

`TimestampMixin` 使用 **Python 端生成时间戳** 的策略，而非依赖数据库的 `CURRENT_TIMESTAMP` 函数。

**设计原因**：

1. **格式一致性**：插入和更新操作使用相同的 UTC datetime 格式（ISO 8601），避免数据格式不一致。
   
   如果使用数据库的 `CURRENT_TIMESTAMP`：
   - 插入时：Python 生成 UTC datetime（如 `2024-01-15T10:30:00+00:00`）
   - 更新时：数据库生成时间戳（格式可能因数据库而异）
   - 结果：同一字段出现两种不同的格式

2. **跨数据库兼容**：不同数据库对 `CURRENT_TIMESTAMP` 的处理方式不同：
   - SQLite：返回本地时间字符串
   - PostgreSQL：返回带时区的时间戳
   - MySQL：返回服务器时区时间
   
   使用 Python 生成可确保所有数据库后端行为一致。

3. **可预测性**：在保存前即可获取时间戳值，便于业务逻辑处理。

**实现细节**：

- 所有时间戳使用 UTC 时区的 `datetime` 对象
- `_update_timestamps` 方法在 `BEFORE_SAVE` 事件中被调用
- 新记录：设置 `created_at` 和 `updated_at`
- 更新记录：仅更新 `updated_at`，`created_at` 保持不变

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
from rhosocial.activerecord.model import ActiveRecord

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
