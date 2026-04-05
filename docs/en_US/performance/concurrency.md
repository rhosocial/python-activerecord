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

## Pessimistic Locking

Pessimistic locking prevents concurrent modifications by locking rows during queries. `rhosocial-activerecord` provides the `for_update()` method for pessimistic locking.

### Basic Usage

```python
# Transfer scenario: Lock user rows to prevent concurrent modification
def transfer(from_id: int, to_id: int, amount: float):
    with Account.transaction():
        # Lock in fixed order to avoid deadlocks
        first_id, second_id = min(from_id, to_id), max(from_id, to_id)

        first = Account.query().where(Account.c.id == first_id).for_update().one()
        second = Account.query().where(Account.c.id == second_id).for_update().one()

        debit, credit = (first, second) if from_id < to_id else (second, first)
        debit.balance -= amount
        credit.balance += amount

        debit.save()
        credit.save()
```

### Backend Support

| Backend | Support | Notes |
|---------|---------|-------|
| MySQL | ✅ Full support | InnoDB row-level locks |
| PostgreSQL | ✅ Full support | MVCC + row-level locks |
| SQLite | ❌ Not supported | Uses file-level locks |

> **Note**: The table above is for reference only. Backend capabilities may vary depending on version or configuration. Please use the `supports_for_update()` method to dynamically detect backend capabilities.

### Capability Detection

When writing cross-database compatible code, use `supports_for_update()` to detect backend capabilities:

```python
dialect = Account.backend().dialect

if dialect.supports_for_update():
    # MySQL/PostgreSQL: Use FOR UPDATE
    account = Account.query().where(Account.c.id == 1).for_update().one()
else:
    # SQLite: Rely on file locks or use data partitioning strategy
    account = Account.find_one(1)
```

### Design Principles

`rhosocial-activerecord` follows the "don't make choices for users" principle for `FOR UPDATE` support:

1. **Default Deny**: `SQLDialectBase.supports_for_update()` returns `False` by default
2. **Explicit Enable**: Only backends that explicitly support it (MySQL, PostgreSQL) return `True`
3. **Dual-Layer Defense**:
   - ActiveQuery layer: Detects when `for_update()` is called, raises error if unsupported
   - Dialect layer: Checks again during SQL generation as a safety net
4. **User Adapts**: Users choose alternative approaches after checking `supports_for_update()`

### Deadlock Prevention

When using pessimistic locking, pay attention to deadlock prevention:

1. **Fixed Lock Order**: Always lock resources in primary key ascending order
2. **Short Transactions**: Only do necessary operations within transactions
3. **Data Partitioning**: Assign data to different Workers by ID range

```python
# ✅ Correct: Lock in primary key ascending order
first_id, second_id = min(from_id, to_id), max(from_id, to_id)
first = Account.query().where(Account.c.id == first_id).for_update().one()
second = Account.query().where(Account.c.id == second_id).for_update().one()

# ❌ Wrong: Different Workers may lock in opposite orders
account1 = Account.query().where(Account.c.id == from_id).for_update().one()
account2 = Account.query().where(Account.c.id == to_id).for_update().one()
```

### Optimistic vs Pessimistic Locking Choice

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| Few conflicts | Optimistic | No lock overhead, higher throughput |
| Frequent conflicts | Pessimistic | Avoid frequent retries |
| Strong consistency needed | Pessimistic | Data guaranteed unchanged during lock |
| Cross-database compatibility | Optimistic | Supported by all backends |
