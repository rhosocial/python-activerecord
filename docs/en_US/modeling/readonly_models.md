# Read-Only Models

In data analytics, reporting, and read-replica scenarios, you often want model
classes that **can query but must never write**. `ReadOnlyMixin` makes that a
declaration rather than a set of overridden methods: every framework write path
refuses the operation before any SQL is issued.

> **AI Prompt:** "I want a model class that connects to our analytics database
> and raises an error if anyone accidentally tries to write to it. How do I do
> that?"

---

## 1. Why Read-Only Models

| Use Case | Description |
| --- | --- |
| **Read replica** | Queries run on a replica; writes go to the primary only |
| **Analytics / BI** | Reports query a data warehouse that must not be modified |
| **Multi-tenant audit** | One tenant's model may read another tenant's data but never write |
| **Historical snapshots** | Immutable archive tables -- reads allowed, no mutations |
| **View-backed models** | The model maps a view or materialized view, not a writable table |

---

## 2. Declaring a Read-Only Model

Mix `ReadOnlyMixin` into a normal model:

```python
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import ReadOnlyMixin

class UserAnalytics(ActiveRecord, ReadOnlyMixin):
    """Read-only view of the users table on the analytics replica."""
    __table_name__ = "users"
    id: Optional[int] = None
    name: str
    email: str
    created_at: Optional[str] = None
```

The mixin declares no fields. It sets `__read_only__ = True` and supplies the
single decision point the framework asks:

```python
UserAnalytics.read_only()  # True
```

A model without the mixin does not answer `read_only()` at all, so the feature
stays opt-in.

---

## 3. What Is Refused

All framework write paths call `refuse_read_only()` before building a
statement:

| Path | Sync / async |
| --- | --- |
| `save()`, `delete()` | both |
| `_insert_internal()`, `_update_internal()` | both |
| `bulk_create()`, `bulk_update()`, `bulk_delete()` | both |
| `query().update_all()`, `query().delete_all()` | both |

A refused write raises `ReadOnlyError`:

```python
from rhosocial.activerecord.backend.errors import ReadOnlyError

user = UserAnalytics(name="Alice", email="alice@example.com")
try:
    user.save()
except ReadOnlyError as exc:
    print(exc.model_name, exc.operation)  # UserAnalytics save
```

`ReadOnlyError` is a `DatabaseError`, so existing `except DatabaseError`
handlers keep working. The error carries `model_name` and `operation`.

Reads are never refused:

```python
UserAnalytics.query().where(UserAnalytics.c.created_at >= "2024-01-01").all()
UserAnalytics.query().count()
UserAnalytics.find_one({"email": "alice@example.com"})
```

> **Guarantee boundary.** This guards the framework's own write paths. The
> expression layer is public, so hand-built UPDATE/DELETE statements can still
> be executed. The real guarantee is database credentials; the mixin prevents
> accidents.

---

## 4. Opting Out and Custom Behaviour

An explicit `__read_only__ = False` turns the gate back off:

```python
class SometimesWritable(ActiveRecord, ReadOnlyMixin):
    __table_name__ = "records"
    __read_only__ = False
```

The gate reads the **value** returned by `read_only()`, not the type of the
receiver. A model may implement `IReadOnlyBehavior` while remaining writable:

```python
from rhosocial.activerecord.interface import IReadOnlyBehavior

class PolicyDriven(ActiveRecord, IReadOnlyBehavior):
    @classmethod
    def read_only(cls) -> bool:
        return False  # a real decision, not a type test

PolicyDriven.refuse_read_only("save")  # allowed
```

This is why `isinstance(model, IReadOnlyBehavior)` is not the gate: it only says
that a `read_only` method exists.

---

## 5. View and Materialized-View Declarations

A read-only model often maps a database object that is not a table. Declare the
object kind on the DDL source:

```python
from rhosocial.activerecord.base import ObjectDeclaration

class UserAnalytics(ActiveRecord, ReadOnlyMixin):
    __table_name__ = "user_analytics_view"
    id: Optional[int] = None
    name: str

    @classmethod
    def object_type(cls) -> ObjectDeclaration:
        return ObjectDeclaration.VIEW
```

`ObjectDeclaration` has `TABLE` (the default), `VIEW`, and
`MATERIALIZED_VIEW`. This is a declaration only: the DDL layer chooses which
statement to build, and dialect capability gates decide whether that statement
is expressible. Whether a database actually holds a view of that name is a
question for introspection, not model metadata.

---

## 6. Conflict With Write-Event Mixins

`SoftDeleteMixin` registers a `BEFORE_DELETE` handler that issues an UPDATE;
`TimestampMixin` and `OptimisticLockMixin` register `BEFORE_UPDATE` handlers.
On a read-only model those handlers can never run, because every write is
refused first. The combination is rejected when the class is defined:

```python
class Conflict(ActiveRecord, ReadOnlyMixin, TimestampMixin):
    ...
# TypeError: Conflict is read-only but also implements
# IUpdateBehavior (e.g. TimestampMixin, OptimisticLockMixin).
```

Detection is by interface (`IUpdateBehavior` / `IDeleteBehavior`), so a
third-party behaviour mixin is caught too. Set `__read_only__ = False` if the
model is genuinely writable.

---

## 7. Read-Only Is Orthogonal to the Primary Key

A read-only table may have an auto-generated key; a keyless table may be
writable. `ReadOnlyMixin` imposes no opinion on either. See
[Keyless Models](keyless_models.md) for `__primary_key__ = None`.

---

## 8. Checklist

- [ ] `ReadOnlyMixin` mixed into the model
- [ ] `ReadOnlyError` is caught (or allowed to surface) in write paths
- [ ] Read-only model configured against a replica / analytics backend, not the primary
- [ ] Field definitions shared via a `BaseModel` mixin when duplicated
- [ ] Computed metrics expressed as `@property`, not stored columns
- [ ] `object_type()` overridden when the model maps a view

---

## Runnable Example

See [`docs/examples/chapter_03_modeling/readonly_models.py`](../../../examples/chapter_03_modeling/readonly_models.py)
for a self-contained script.

## See Also

- [Keyless Models](keyless_models.md) -- `__primary_key__ = None` and identity-free access
- [Multiple Independent Connections](best_practices.md#8-multiple-independent-connections) -- separating connections with subclass vs. mixin patterns
- [Mixins](mixins.md) -- built-in mixins and patterns for composing model behaviour
