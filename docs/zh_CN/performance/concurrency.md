# 并发控制 (Concurrency)

在 Web 应用中，两个用户同时编辑同一篇文章是很常见的。如果没有锁，后提交的修改会覆盖先提交的。

## 乐观锁 (Optimistic Locking)

`OptimisticLockMixin` 通过增加一个 `version` 字段来解决此问题。

```python
from rhosocial.activerecord.field import OptimisticLockMixin

class Post(OptimisticLockMixin, ActiveRecord):
    title: str
```

**工作原理**:
1.  读取数据时，获取当前 `version` (如 1)。
2.  更新时，SQL 附加条件 `WHERE id = ... AND version = 1`。
3.  如果更新行数为 0，说明期间 `version` 已变（被别人改了），抛出 `StaleObjectError`。

```python
try:
    post.title = "New Title"
    post.save()
except StaleObjectError:
    print("数据已被修改，请刷新重试")
```
