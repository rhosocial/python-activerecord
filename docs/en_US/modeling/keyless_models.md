# Keyless Models

A relation does not always have a unique single-row key. An insert-only audit
log, an aggregate projection, or a table whose identity is supplied only by the
query that reads it are real shapes. `__primary_key__ = None` declares that
shape explicitly.

> **AI Prompt:** "I need to map a table that has no primary key. Queries and
> inserts should work, but `find_one(id)` should tell me clearly that there is
> no id to find."

---

## 1. Declaring a Keyless Model

```python
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord

class AuditLog(ActiveRecord):
    __table_name__ = "audit_log"
    __primary_key__ = None

    event: str
    level: str
```

`__primary_key__ = None` is not a missing configuration; it is an accepted
declaration. The model answers through one decision point:

```python
AuditLog.addressable()        # False
AuditLog.primary_key_columns()  # ()
AuditLog.primary_key_fields()   # ()
```

The empty tuples matter: callers can iterate the result unconditionally and
never receive `(None,)`.

---

## 2. What Keeps Working

Identity is only one way to read. These all continue to work:

```python
AuditLog(event="a").save()                                  # INSERT
AuditLog.query().all()
AuditLog.query().where(AuditLog.c.level == "warn").one()
AuditLog.query().order_by(AuditLog.c.event).limit(10).all()
AuditLog.query().count()
AuditLog.query().select(AuditLog.c.level).aggregate()
AuditLog.find_all({"level": "warn"})
AuditLog.find_one({"event": "a"})
```

`is_new_record` also has an honest answer. With no key there is no identity to
inspect, so provenance decides: a row loaded from the database is not new,
anything constructed in Python is.

```python
AuditLog(event="x").is_new_record             # True
loaded = AuditLog.query().where(...).one()
loaded.is_new_record                          # False
```

---

## 3. What Is Refused

Identity-based access needs a key. These raise `UnaddressableRecordError`
instead of leaking `TypeError: attribute name must be string, not 'NoneType'`:

| Operation | Raised error |
| --- | --- |
| `find_one(pk_value)` | `UnaddressableRecordError` |
| `find_all([pk1, pk2])` | `UnaddressableRecordError` |
| `refresh()` | `UnaddressableRecordError` |
| `_get_pk_value()` | `UnaddressableRecordError` |
| `_build_pk_where_predicate(...)` | `UnaddressableRecordError` |

The error names the model and the operation and suggests the alternative:

```python
from rhosocial.activerecord.backend.errors import UnaddressableRecordError

try:
    AuditLog.find_one(1)
except UnaddressableRecordError as exc:
    print(exc.model_name, exc.operation)  # AuditLog find_one
```

Use `where(...).one()` when a row is well defined by some other criterion:

```python
record = AuditLog.query().where(AuditLog.c.event == "only").one()
```

Only **bare-key** conditions are refused. A dict or predicate condition is not
an identity lookup and still runs:

```python
AuditLog.find_one({"event": "a"})
AuditLog.find_one(AuditLog.c.event == "a")
```

`UnaddressableRecordError` is a `DatabaseError`.

---

## 4. Keyless and Read-Only Are Orthogonal

The two dimensions do not interact:

```python
class KeylessWritable(ActiveRecord):
    __primary_key__ = None
    ...

class ReadOnlyWithKey(ActiveRecord, ReadOnlyMixin):
    __table_name__ = "records"
    ...

class KeylessReadOnly(ActiveRecord, ReadOnlyMixin):
    __primary_key__ = None
    ...
```

- `KeylessWritable.addressable()` is `False`; writes still work.
- `ReadOnlyWithKey.addressable()` is `True`; writes are refused.
- `KeylessReadOnly` is both; writes are refused and identity access is
  unavailable.

---

## 5. Checklist

- [ ] `__primary_key__ = None` declared deliberately, not left as an accident
- [ ] Identity operations replaced with `where(...).one()`
- [ ] Inserts and reads covered by tests
- [ ] Composite keys left as tuples; `None` is not a composite key

---

## See Also

- [Read-Only Models](readonly_models.md) -- refusing writes through the model API
- [DDLSource Declarations](ddl_source.md) -- `object_type()` and DDL metadata
- [Active Query](../querying/active_query.md) -- predicates, ordering, aggregation
