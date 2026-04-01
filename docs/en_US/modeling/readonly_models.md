# Read-Only Analytics Models

In data analytics, reporting, and read-replica scenarios, you often want model classes
that **can query but must never write**.  This guide shows how to define, configure, and
use read-only models safely.

> 💡 **AI Prompt:** "I want a model class that connects to our analytics database and
> raises an error if anyone accidentally tries to write to it.  How do I do that?"

---

## 1. Why Read-Only Models

| Use Case | Description |
| --- | --- |
| **Read replica** | Queries run on a replica; writes go to the primary only |
| **Analytics / BI** | Reports query a data warehouse that must not be modified |
| **Multi-tenant audit** | One tenant's model may read another tenant's data but never write |
| **Historical snapshots** | Immutable archive tables -- reads allowed, no mutations |

---

## 2. Declaring a Read-Only Model

Add a `__readonly__` class attribute and override `save()` and `delete()` to raise an
error immediately:

```python
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord

class ReadOnlyMixin:
    """Mix into any ActiveRecord subclass to make it read-only."""

    __readonly__: bool = True

    def save(self, *args, **kwargs):
        raise TypeError(
            f"{type(self).__name__} is a read-only model and cannot be saved. "
            "Use the corresponding writable model class instead."
        )

    def delete(self, *args, **kwargs):
        raise TypeError(
            f"{type(self).__name__} is a read-only model and cannot be deleted."
        )

    @classmethod
    def bulk_create(cls, *args, **kwargs):
        raise TypeError(f"{cls.__name__} is a read-only model.")
```

Apply it to any model:

```python
class UserAnalytics(ReadOnlyMixin, ActiveRecord):
    """Read-only view of the users table on the analytics replica."""
    __table_name__ = "users"
    id: Optional[int] = None
    name: str
    email: str
    created_at: Optional[str] = None
```

---

## 3. Connecting to a Read Replica

Configure the read-only model against a separate backend -- typically a read replica or
analytics database:

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

# Primary database -- writable models
primary_config = SQLiteConnectionConfig(database="primary.db")
User.configure(primary_config, SQLiteBackend)

# Analytics replica -- read-only models
analytics_config = SQLiteConnectionConfig(database="analytics_replica.db")
UserAnalytics.configure(analytics_config, SQLiteBackend)
```

Queries run against the replica; any accidental write raises `TypeError` before reaching
the database:

```python
# ✅ Safe: read operations work normally
analysts = UserAnalytics.query().where(UserAnalytics.c.created_at >= "2024-01-01").all()

# ✅ Safe: aggregations
count = UserAnalytics.query().count()

# ❌ Blocked immediately -- no database call is made
user = UserAnalytics(name="Alice", email="alice@example.com")
user.save()  # Raises: TypeError: UserAnalytics is a read-only model and cannot be saved.
```

---

## 4. Combining with the Shared Field Mixin Pattern

The most maintainable approach is to combine `ReadOnlyMixin` with the [shared field
mixin](best_practices.md#8-multiple-independent-connections) pattern: define fields
once, share them between the writable model and its read-only analytics counterpart.

```python
from pydantic import BaseModel

# Shared field definition
class UserFields(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    created_at: Optional[str] = None

# Writable business model -- primary database
class User(UserFields, ActiveRecord):
    __table_name__ = "users"

# Read-only analytics model -- analytics replica
class UserAnalytics(ReadOnlyMixin, UserFields, ActiveRecord):
    __table_name__ = "users"

# Configure independently
User.configure(primary_config, SQLiteBackend)
UserAnalytics.configure(analytics_config, SQLiteBackend)
```

Field definitions live in one place (`UserFields`).  Both models stay in sync
automatically when fields are added or changed.

---

## 5. Derived / Computed Fields

Analytics models often need metrics derived from stored data.  Use `@property` for
values that should not be persisted:

```python
from datetime import datetime

class UserAnalytics(ReadOnlyMixin, UserFields, ActiveRecord):
    __table_name__ = "users"
    signup_days_ago: Optional[int] = None  # populated by DB query / annotation

    @property
    def is_new_user(self) -> bool:
        """True if the user signed up within the last 30 days."""
        return (self.signup_days_ago or 0) <= 30

    @property
    def tier(self) -> str:
        """Classify users by signup age."""
        days = self.signup_days_ago or 0
        if days <= 30:
            return "new"
        if days <= 365:
            return "regular"
        return "veteran"
```

`@property` fields are computed in Python and never stored in the database, making them
safe to add without schema changes.

---

## 6. Read-Only Model Checklist

- [ ] `ReadOnlyMixin` (or equivalent) overrides `save()`, `delete()`, and `bulk_create()`
- [ ] Read-only model configured against a replica / analytics backend, not the primary
- [ ] Field definitions shared via a `BaseModel` mixin to avoid duplication
- [ ] Computed metrics expressed as `@property`, not stored columns
- [ ] Unit tests verify that `save()` and `delete()` raise `TypeError`

---

## Runnable Example

See [`docs/examples/chapter_03_modeling/readonly_models.py`](../../../examples/chapter_03_modeling/readonly_models.py)
for a self-contained script that demonstrates all four patterns above.

---

## See Also

- [Multiple Independent Connections](best_practices.md#8-multiple-independent-connections) — separating connections with subclass vs. mixin patterns
- [Batch Processing](batch_processing.md) — efficiently reading large datasets from analytics databases
- [Mixins](mixins.md) — built-in mixins and patterns for composing model behaviour
