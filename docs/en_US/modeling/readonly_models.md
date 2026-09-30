# Read-Only Models

Some relations must never be written: a query runs against a replica, a report reads a
data warehouse, an audit trail is append-only. `ReadOnlyMixin` declares that, and the
framework enforces it on every write path it owns.

> 💡 **AI Prompt:** "I want a model class that connects to our analytics database and
> raises an error if anyone accidentally tries to write to it. How do I do that?"

---

## 1. Declaring a Read-Only Model

Mix `ReadOnlyMixin` into any model:

```python
from typing import Optional
from rhosocial.activerecord.field import ReadOnlyMixin
from rhosocial.activerecord.model import ActiveRecord

class UserAnalytics(ReadOnlyMixin, ActiveRecord):
    """Read-only view of the users table on the analytics replica."""
    __table_name__ = "users"
    id: Optional[int] = None
    name: str
    email: str
```

That is the whole declaration. `__read_only__` is set to `True` and the framework refuses
writes before preparing any SQL:

```python
# ✅ Reads work normally
analysts = UserAnalytics.query().where(UserAnalytics.c.name == "Alice").all()
count = UserAnalytics.query().count()

# ❌ Refused -- no statement is ever sent
UserAnalytics(name="Alice", email="alice@example.com").save()
# ReadOnlyError: save is not allowed on read-only model 'UserAnalytics'. ...
```

`ReadOnlyError` subclasses `DatabaseError`, so existing `except DatabaseError` handlers
catch it too.

### What is blocked

| Blocked | Available |
| --- | --- |
| `save()`, `delete()` | `query()`, `all()`, `one()`, `where()`, `order_by()`, `group_by()` |
| `bulk_create()`, `bulk_update()`, `bulk_delete()` | `count()`, `exists()`, `aggregate()`, `avg()`, `sum_()`, `max_()`, `min_()` |
| `update_all()`, `delete_all()` | `with_()` eager loading, relations, `find_all()` |

Reads are untouched. So are the fields the model declares — `ReadOnlyMixin` is
*semantics only*, following the same convention as `SoftDeleteMixin` and `TimestampMixin`.

### Escaping the gate

Set `__read_only__ = False` to write anyway:

```python
class Maintenance(ReadOnlyMixin, ActiveRecord):
    __table_name__ = "users"
    __read_only__ = False   # escape hatch, for scripts that must write
```

---

## 2. Why the Decision Lives in the Model

`ReadOnlyMixin` implements `IReadOnlyBehavior`, one of four behaviour interfaces in
`interface/update.py` alongside `IUpdateBehavior`, `IDeleteBehavior` and
`IDataPreparationBehavior`:

```python
class ReadOnlyMixin(IReadOnlyBehavior):
    __read_only__: ClassVar[bool] = True

    @classmethod
    def read_only(cls) -> bool:
        return bool(getattr(cls, "__read_only__", False))
```

The framework asks `read_only()` and acts on the **returned value**, not on the type:

```python
@classmethod
def refuse_read_only(cls, operation: str) -> None:
    read_only = getattr(cls, "read_only", None)
    if callable(read_only) and read_only():
        raise ReadOnlyError(cls.__name__, operation)
```

Membership in `IReadOnlyBehavior` only says a `read_only` method exists — a model can
satisfy the interface and still be writable. Testing the type instead of the value would
refuse those models, so it is deliberately not done. The same reasoning makes `read_only()`
return `bool` rather than `None`: a `None` return invites `is None` being used as a type
test.

**The feature is opt-in.** A model that does not mix the interface in does not even answer
`read_only()`, so existing behaviour is unchanged — there is no cost for models that never
asked for this.

**One implementation serves sync and async.** `read_only()` is a zero-I/O classmethod, and
the `field/` convention is that an async twin is needed only when a method issues SQL
(`SoftDeleteMixin` has one for `restore()`). `AsyncActiveRecord` models mix in the same
`ReadOnlyMixin`.

Any class can implement `IReadOnlyBehavior` alone — a plain dataclass, a non-ActiveRecord
domain object — and get the same declaration.

---

## 3. Connecting to a Read Replica

Configure the read-only model against a separate backend:

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

# Primary database -- writable models
User.configure(SQLiteConnectionConfig(database="primary.db"), SQLiteBackend)

# Analytics replica -- read-only models
UserAnalytics.configure(SQLiteConnectionConfig(database="analytics.db"), SQLiteBackend)
```

---

## 4. Combining with the Shared Field Mixin Pattern

Define fields once and share them between the writable model and its read-only
counterpart:

```python
from pydantic import BaseModel

class UserFields(BaseModel):
    id: Optional[int] = None
    name: str
    email: str

class User(UserFields, ActiveRecord):
    __table_name__ = "users"

class UserAnalytics(ReadOnlyMixin, UserFields, ActiveRecord):
    __table_name__ = "users"

User.configure(primary_config, SQLiteBackend)
UserAnalytics.configure(analytics_config, SQLiteBackend)
```

Field definitions live in one place. Both models stay in sync when fields change.

---

## 5. Keyless Models Are a Separate Axis

Read-only and "has a primary key" are independent. A read replica usually keeps its keys,
and a keyless relation can still be writable:

```python
class AuditLog(ActiveRecord):          # keyless, but writable (append-only table)
    __primary_key__ = None
    event: str

class EventView(ReadOnlyMixin, ActiveRecord):
    __primary_key__ = None             # keyless *and* read-only
    event: str
```

See [Keyless Models](keyless_models.md) for what `__primary_key__ = None` means and which
APPs it rules out.

---

## 6. Limits Worth Knowing

**This guards the framework's write paths, not the database.** `backend.expression` is
publicly exported, so anyone can build and execute an UPDATE by hand:

```python
from rhosocial.activerecord.backend.expression import UpdateExpression

UpdateExpression(dialect, table="users", data={"name": "x"}, where=...).to_sql()
```

The real guarantee is database credentials — grant the account `SELECT` only. Use the
mixin to prevent accidents, and privileges to enforce policy.

**Combining with a write-behaviour mixin is rejected.** `SoftDeleteMixin`,
`TimestampMixin` and `OptimisticLockMixin` register `BEFORE_INSERT` / `BEFORE_UPDATE` /
`BEFORE_DELETE` handlers, which could never run on a read-only model because every write is
refused first. That combination raises `TypeError` when the class is defined:

```python
class Broken(ReadOnlyMixin, SoftDeleteMixin, ActiveRecord):
    ...  # TypeError: Broken is read-only but also implements IDeleteBehavior ...
```

The check runs from `__init_subclass__`, so it fires at class-definition time rather than
on first instantiation.

---

## Checklist

- [ ] `ReadOnlyMixin` mixed in; no `save()` / `delete()` overrides hand-written
- [ ] Tests assert `ReadOnlyError`, not a generic exception
- [ ] Backend configured against a replica if that is the intent
- [ ] Database account granted read-only privileges — the mixin is not the boundary
- [ ] No write-behaviour mixin combined with read-only

---

## Runnable Example

See [`docs/examples/chapter_03_modeling/readonly_models.py`](../../examples/chapter_03_modeling/readonly_models.py)
for a self-contained script.

---

## See Also

- [Keyless Models](keyless_models.md) — `__primary_key__ = None` and what it rules out
- [Views as Queries](views_as_queries.md) — expressing a database view without a model
- [Mixins](mixins.md) — the other built-in mixins
- [Batch Processing](batch_processing.md) — efficiently reading large datasets
