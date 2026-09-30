# Keyless Models

A relation does not always have a unique single-row key. An insert-only audit log has
none. An aggregate projection has none — "the row for customer 42" may not exist at all.
`__primary_key__ = None` declares that, and the framework has a defined answer for it.

---

## 1. Declaring a Keyless Model

```python
from rhosocial.activerecord.model import ActiveRecord

class AuditLog(ActiveRecord):
    __table_name__ = "audit_log"
    __primary_key__ = None      # no single-row identity
    event: str
    level: str
```

```python
AuditLog.addressable()            # False
AuditLog.primary_key_columns()    # ()  -- empty, never (None,)
AuditLog.primary_key_fields()     # ()
AuditLog.is_composite_pk()        # False
```

`primary_key_columns()` returns an **empty tuple**, not `(None,)`, so callers can iterate
it unconditionally.

`addressable()` is the single decision point, named to match the other predicates the
framework asks a model about (`read_only()`). It answers one question: *can a single row be
addressed by primary key?*

---

## 2. What Stops Working

Everything that needs identity:

| Unavailable | Instead |
| --- | --- |
| `find_one(pk)` | `query().where(...).one()` |
| `find_all([pk, pk])` | `query().where(Model.c.id.in_([...]))` |
| `refresh()` | re-query explicitly |
| update or delete by key | `where(...)` plus `update_all()` / `delete_all()` |
| primary-key relation caching | leave caching off, or cache under your own key |

Each raises `UnaddressableRecordError` naming the model and the operation:

```python
AuditLog.find_one(5)
# UnaddressableRecordError: find_one needs a primary key, but 'AuditLog' declares
# __primary_key__ = None and so has no single-row identity. Select with
# AuditLog.query().where(...).one() instead, or declare a primary key if the
# relation really has one.
```

`UnaddressableRecordError` subclasses `DatabaseError`.

---

## 3. What Keeps Working

Most of the API, because most of it never needed identity:

```python
AuditLog(event="login", level="info").save()               # ✅ inserts
AuditLog.query().all()                                      # ✅
AuditLog.query().where(AuditLog.c.level == "info").all()    # ✅
AuditLog.query().order_by(AuditLog.c.event).limit(10).all()  # ✅
AuditLog.query().count()                                    # ✅
AuditLog.query().where(...).exists()                        # ✅
AuditLog.query().select(AuditLog.c.level).aggregate()       # ✅ grouping, averaging
AuditLog.find_all({"level": "warn"})                        # ✅ dict conditions
AuditLog.find_one(AuditLog.c.level == "warn")               # ✅ predicate conditions
```

Relations keep working too. Preloading a `belongs_to` uses the *target's* key; `has_many`
uses the *parent's*. A keyless model on either side is fine — what it cannot do is key
its own relation cache.

> **Note:** `ActiveQuery` has no `first()`, `last()` or `pluck()`. Use `limit(1).all()`,
> a reversed `order_by`, or `.select(...).aggregate()`.

---

## 4. `is_new_record` Without a Key

With a key, `is_new_record` asks whether the key is set. Without one there is no identity
to inspect, so provenance decides instead:

```python
AuditLog(event="x").is_new_record          # True  -- constructed in Python

loaded = AuditLog.query().where(...).one()
loaded.is_new_record                       # False -- came from the database
```

That keeps `save()` dispatching sensibly: a constructed keyless record inserts, and a
row read back from the database is recognised as already persisted.

Post-insert key retrieval is skipped for keyless models — there is nothing for the
database to generate, so there is nothing to read back.

---

## 5. Independent of Read-Only

The two axes are orthogonal, in both directions:

```python
class AuditLog(ActiveRecord):                    # keyless, writable
    __primary_key__ = None

class EventSummary(ReadOnlyMixin, ActiveRecord): # keyless and read-only
    __primary_key__ = None

class UserReplica(ReadOnlyMixin, ActiveRecord):  # read-only, but addressable
    __table_name__ = "users"
```

A materialized-view model will need both.

---

## 6. Choosing Between a Keyless Model and a View

If the shape you want is "one row per X, with columns derived from other tables", that is
usually a *query*, not a table. See [Views as Queries](views_as_queries.md) — an
encapsulated `ActiveQuery` is the more direct expression, and it needs no model.

Reach for a keyless *model* when you want typed instances, relations, or eager loading
over the result.

---

## Checklist

- [ ] `__primary_key__ = None` only where the relation genuinely has no unique key
- [ ] Callers use `where(...).one()` rather than `find_one(pk)`
- [ ] Relation caching left disabled for the model, or keyed explicitly
- [ ] Tests assert `UnaddressableRecordError`, not a bare `TypeError`

---

## See Also

- [Read-Only Models](readonly_models.md) — refusing writes
- [Views as Queries](views_as_queries.md) — when a query beats a table
- [Derived Fields](derived_fields.md) — computed columns in the SELECT list
