# Mixin 与复用 (Mixins)

组合优于继承。`rhosocial-activerecord` 鼓励使用 Mixin 来复用通用的字段和逻辑。

## 内置 Mixin

框架提供了一些常用的 Mixin。

> **两类 Mixin 的约定**
>
> 框架中凡是「需要字段」的行为 Mixin（时间戳、乐观锁、软删除）都拆分为**两个类**：
>
> * **语义基类**（如 `TimestampMixin`）：只提供**维护语义**（事件挂钩、SQL 条件、查询过滤等），**不声明任何字段**。它通过类属性（如 `__created_at_field__`）指向模型自己声明的字段。适用于需要**自定义字段名/列名**的场景。
> * **默认子类**（如 `DefaultTimestampMixin`）：在语义基类之上**补充约定俗成的字段**（`created_at`/`updated_at`、`version`、`deleted_at`），开箱即用。
>
> **绝大多数情况下直接使用 `Default*` 变体即可**；只有当字段名与默认约定不同（例如映射遗留数据库表）时，才使用语义基类并自行声明字段。

### IntegerPKMixin

使用自增整数作为主键（最常用的主键类型）。

```python
from rhosocial.activerecord.field import IntegerPKMixin

class User(IntegerPKMixin, ActiveRecord):
    # 自动获得: id: int (Primary Key, auto-increment)
    username: str
    pass

# 使用示例
user = User(username="alice")
user.save()
print(user.id)  # 数据库自动分配的整数 ID
```

**特点**：

- 主键字段默认为 `id`，可通过 `__primary_key__` 类属性自定义
- 新建实例时 `id` 初始化为 `None`
- 保存后数据库自动分配整数 ID

**后端兼容性**：

保存新记录时，框架通过以下方式获取自增主键：

1. **优先使用 RETURNING 子句**：如果后端支持 `RETURNING`（如 SQLite 3.35+、PostgreSQL），直接从 INSERT 语句返回结果中获取
2. **回退到 last_insert_id**：如果后端不支持 `RETURNING`，则从 `cursor.lastrowid` 获取

大多数数据库后端都支持其中一种方式，因此 `IntegerPKMixin` 可在所有主流数据库上正常工作。

> 💡 **AI提示词示例**: "IntegerPKMixin 和 UUIDMixin 有什么区别？应该如何选择主键类型？"

### UUIDMixin

使用 UUID 作为主键。

```python
from rhosocial.activerecord.field import UUIDMixin

class User(UUIDMixin, ActiveRecord):
    # 自动获得: id: uuid.UUID (Primary Key)
    pass
```

**后端兼容性**：

UUID 主键在保存前由 Python 生成，不依赖数据库的自增机制。但如果需要在 INSERT 后获取其他数据库生成的值，仍需后端支持 `RETURNING` 子句。

> 💡 **AI提示词示例**: "使用 UUID 主键时需要注意什么？哪些数据库后端支持 RETURNING 子句？"

### CompositePKMixin

支持复合（多列）主键。

```python
from rhosocial.activerecord.field import CompositePKMixin

class OrderItem(CompositePKMixin, ActiveRecord):
    __primary_key__ = ("order_id", "product_id")

    order_id: int
    product_id: int
    quantity: int
```

**特点**：

- 主键声明为列名元组 `tuple[str, ...]`
- 创建新实例时必须提供所有 PK 列的值
- 复合 PK 值不会自动生成（`__pk_auto_generated__ = False`）
- 使用 `find_one()` 时传入 dict 或 tuple：`OrderItem.find_one({"order_id": 1, "product_id": 42})` 或 `OrderItem.find_one((1, 42))`
- 使用 `find_all()` 时可传入 dict/tuple 列表进行批量查找
- 关联关系支持：`BelongsTo(foreign_key=("order_id",))` 按位置将每个外键列与对应 PK 列匹配

> 💡 **AI提示词示例**: "如何定义复合主键模型？复合主键的 find_one 如何使用？"

### TimestampMixin / DefaultTimestampMixin

自动记录创建时间和更新时间。

#### 默认用法：DefaultTimestampMixin

```python
from rhosocial.activerecord.field import DefaultTimestampMixin

class Post(DefaultTimestampMixin, ActiveRecord):
    # 自动获得:
    # created_at: datetime (UTC 时区)
    # updated_at: datetime (UTC 时区)
    pass
```

`DefaultTimestampMixin` 会自动声明 `created_at` / `updated_at` 两个 `datetime` 字段（UTC 默认工厂），并注册维护语义。

#### 自定义字段名：TimestampMixin

当模型使用不同的字段名（例如映射遗留数据库）时，使用语义基类 `TimestampMixin`，自行声明字段，并通过 `__created_at_field__` / `__updated_at_field__` 告知框架：

```python
from rhosocial.activerecord.field import TimestampMixin
from pydantic import Field
from datetime import datetime, timezone

class LegacyPost(TimestampMixin, ActiveRecord):
    # 语义基类不声明字段，这里由模型自行声明，并指向它们
    __created_at_field__ = "creation_date"
    __updated_at_field__ = "last_modified"

    creation_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str
```

> **注意**：`TimestampMixin` 要求所指向的字段必须存在，否则在实例化时立即抛出 `TypeError`（fail-fast），避免静默失效。

#### 时间戳生成策略

时间戳混入使用 **Python 端生成时间戳** 的策略，而非依赖数据库的 `CURRENT_TIMESTAMP` 函数。

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
- 插入操作（`BEFORE_INSERT`）同时设置 `created_at` 和 `updated_at`
- 更新操作（`BEFORE_UPDATE`）仅更新 `updated_at`，`created_at` 保持不变

### SoftDeleteMixin / DefaultSoftDeleteMixin

标记删除而不是物理删除。

#### 默认用法：DefaultSoftDeleteMixin

```python
from rhosocial.activerecord.field import DefaultSoftDeleteMixin

class Comment(DefaultSoftDeleteMixin, ActiveRecord):
    # 自动获得: deleted_at: Optional[datetime] (默认 None)
    pass

# 查询时会自动过滤已删除的记录
active_comments = Comment.all()

# 恢复
comment = Comment.find_one(1)
comment.restore()

# 物理删除
comment.delete(hard=True)
```

#### 自定义字段名：SoftDeleteMixin

```python
from rhosocial.activerecord.field import SoftDeleteMixin
from datetime import datetime
from typing import Optional
from pydantic import Field

class LegacyComment(SoftDeleteMixin, ActiveRecord):
    __deleted_at_field__ = "deleted"

    deleted: Optional[datetime] = Field(default=None)
    content: str
```

**查询方法**：

- `query()` — 只返回未删除的记录（`DefaultSoftDeleteMixin` 会自动过滤）
- `query_with_deleted()` — 返回全部记录
- `query_only_deleted()` — 只返回已删除的记录

> **异步模型**：异步模型请使用 `AsyncSoftDeleteMixin` / `DefaultAsyncSoftDeleteMixin`，以保证同步/异步执行模型不混用。

### OptimisticLockMixin / DefaultOptimisticLockMixin

处理并发更新冲突。

#### 默认用法：DefaultOptimisticLockMixin

```python
from rhosocial.activerecord.field import DefaultOptimisticLockMixin

class Post(DefaultOptimisticLockMixin, ActiveRecord):
    # 自动获得: version: int (NOT NULL, ge=1, 默认 1)
    title: str
    pass

# 使用示例
post = Post.find_one(1)
post.title = "New Title"
post.save()  # 如果期间有其他更新，会抛出 DatabaseError
```

#### 自定义字段名：OptimisticLockMixin

```python
from rhosocial.activerecord.field import OptimisticLockMixin
from typing import Annotated
from pydantic import Field
from rhosocial.activerecord.base.fields import UseColumn, UseConstraint
from rhosocial.activerecord.backend.expression.statements.ddl_table import ColumnConstraintType

class Article(OptimisticLockMixin, ActiveRecord):
    __version_field__ = "row_version"
    __version_increment_by__ = 2   # 可选，默认 1

    row_version: Annotated[
        int, UseColumn("row_ver"), UseConstraint(ColumnConstraintType.NOT_NULL)
    ] = Field(default=1, ge=1)
    title: str
```

**乐观锁工作原理**：

- INSERT 时将版本值规范化为 1，无论用户传入什么
- UPDATE 的 WHERE 子句使用 `_version_snapshot`（最后一次提交到数据库的值），因此内存中的篡改无法破坏锁条件
- UPDATE 的 SET 子句是列算术表达式（`col = col + 步长`），在合并脏字段数据之后应用，覆盖任何用户赋值
- 用户手动赋值且与快照不一致时，会在 `BEFORE_UPDATE` 阶段直接抛出 `DatabaseError`

**自定义字段名时**：

- `__version_field__`：指向模型声明的版本字段（Python 字段名）
- `__version_increment_by__`：每次 UPDATE 的递增步长（可选，默认 1）
- 版本列的列名遵循 `UseColumn` 标准解析

> 💡 **AI提示词示例**: "如何处理多人同时编辑同一篇文章的情况？乐观锁的工作原理是什么？"

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
