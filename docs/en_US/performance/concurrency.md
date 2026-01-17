# Concurrency Control

In Web applications, it is common for two users to edit the same article simultaneously. Without locking, the later submission will overwrite the earlier one.

## Optimistic Locking

`OptimisticLockMixin` solves this problem by adding a `version` field.

```python
from rhosocial.activerecord.field import OptimisticLockMixin

class Post(OptimisticLockMixin, ActiveRecord):
    title: str
```

**How it works**:
1.  When reading data, fetch the current `version` (e.g., 1).
2.  When updating, the SQL adds a condition `WHERE id = ... AND version = 1`.
3.  If the number of updated rows is 0, it means the `version` has changed in the meantime (modified by someone else), and a `StaleObjectError` is raised.

```python
try:
    post.title = "New Title"
    post.save()
except StaleObjectError:
    print("Data has been modified, please refresh and try again")
```
