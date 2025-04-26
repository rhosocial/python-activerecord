# Pessimistic Locking Strategies

Pessimistic locking is a concurrency control method that prevents conflicts by locking records at the database level before they are read or modified. rhosocial ActiveRecord provides transaction-level support for implementing pessimistic locking strategies.

## Overview

Unlike optimistic locking, which checks for conflicts only at save time, pessimistic locking acquires locks on database rows to prevent other transactions from modifying them. This approach is called "pessimistic" because it assumes conflicts are likely and takes preventive measures.

rhosocial ActiveRecord supports pessimistic locking through its transaction API and database-specific locking capabilities.

## Basic Usage

To use pessimistic locking, you typically work within a transaction and specify the lock type when querying records:

```python
from rhosocial.activerecord import ActiveRecord

class Account(ActiveRecord):
    __tablename__ = 'accounts'
    
    name: str
    balance: float

# Using a transaction with pessimistic locking
with Account.transaction():
    # Lock the record for update
    account = Account.query().where("id = ?", 1).lock_for_update().first()
    
    # Now the record is locked until the transaction completes
    account.balance += 100.0
    account.save()
    
    # The lock is released when the transaction ends
```

## Lock Types

rhosocial ActiveRecord supports different types of locks depending on the database backend:

### FOR UPDATE Lock

The `FOR UPDATE` lock is the most common type of pessimistic lock. It prevents other transactions from modifying the locked rows until the current transaction completes:

```python
# Lock records for update
accounts = Account.query().where("balance > ?", 1000).lock_for_update().all()
```

### SHARE Lock

The `SHARE` lock allows other transactions to read the locked rows but prevents them from modifying the rows until the current transaction completes:

```python
# Lock records for shared access
accounts = Account.query().where("balance > ?", 1000).lock_in_share_mode().all()
```

## Handling Lock Timeouts and Deadlocks

When using pessimistic locking, you need to handle potential lock timeouts and deadlocks:

```python
from rhosocial.activerecord.backend import DeadlockError, LockError

try:
    with Account.transaction():
        account = Account.query().where("id = ?", 1).lock_for_update().first()
        account.balance += 100.0
        account.save()
except DeadlockError as e:
    # Handle deadlock situation
    print(f"Deadlock detected: {e}")
    # Retry the operation or notify the user
except LockError as e:
    # Handle lock timeout
    print(f"Lock acquisition failed: {e}")
    # Retry the operation or notify the user
```

## Database-Specific Considerations

Pessimistic locking behavior can vary between database systems:

### MySQL

MySQL supports both `FOR UPDATE` and `SHARE` locks. By default, InnoDB uses row-level locking:

```python
# MySQL-specific example
with Account.transaction():
    # Lock for update with nowait option (MySQL 8.0+)
    account = Account.query().where("id = ?", 1).lock_for_update(nowait=True).first()
    # Process the account...
```

### PostgreSQL

PostgreSQL provides additional locking options like `NOWAIT` and `SKIP LOCKED`:

```python
# PostgreSQL-specific example
with Account.transaction():
    # Lock for update with nowait option
    try:
        account = Account.query().where("id = ?", 1).lock_for_update(nowait=True).first()
        # Process the account...
    except LockError:
        # Handle the case where the lock couldn't be acquired immediately
        pass
```

### SQLite

SQLite has limited support for row-level locking. It uses database-level locking by default:

```python
# SQLite-specific example
with Account.transaction():
    # Basic locking in SQLite
    account = Account.query().where("id = ?", 1).first()
    # Process the account...
```

## Transaction Isolation Levels

The effectiveness of pessimistic locking depends on the transaction isolation level. rhosocial ActiveRecord supports different isolation levels:

```python
from rhosocial.activerecord.backend import IsolationLevel

# Set isolation level for the transaction
with Account.backend().transaction_manager.transaction(isolation_level=IsolationLevel.SERIALIZABLE):
    account = Account.query().where("id = ?", 1).lock_for_update().first()
    # Process the account...
```

Common isolation levels include:

- `READ UNCOMMITTED`: Lowest isolation level, allows dirty reads
- `READ COMMITTED`: Prevents dirty reads, but allows non-repeatable reads
- `REPEATABLE READ`: Prevents dirty and non-repeatable reads, but allows phantom reads
- `SERIALIZABLE`: Highest isolation level, prevents all concurrency anomalies

## Best Practices

1. **Keep Transactions Short**: Long-running transactions with locks can significantly impact system performance.

2. **Handle Deadlocks**: Always implement deadlock detection and recovery strategies.

3. **Consider Lock Scope**: Lock only the records you need to modify to minimize contention.

4. **Use Timeouts**: Set appropriate lock timeouts to prevent indefinite waiting.

5. **Fallback Strategy**: Have a fallback strategy when locks cannot be acquired, such as retrying or using optimistic locking.

## Combining Locking Strategies

In some cases, you might want to combine pessimistic and optimistic locking:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import OptimisticLockMixin
from rhosocial.activerecord.backend import DatabaseError

class Account(OptimisticLockMixin, ActiveRecord):
    __tablename__ = 'accounts'
    
    name: str
    balance: float

try:
    with Account.transaction():
        # Use pessimistic locking for initial access
        account = Account.query().where("id = ?", 1).lock_for_update().first()
        
        # Perform some long calculation or external API call
        # that might take time
        
        # Optimistic locking will verify no changes occurred
        # during the calculation
        account.balance += 100.0
        account.save()
except DatabaseError as e:
    # Handle optimistic lock failure
    pass
```

## Next Steps

Now that you understand pessimistic locking, you might want to explore:

- [Version Control and Optimistic Locking](version_control_and_optimistic_locking.md) - For lighter-weight concurrency control
- [Transaction Basics](../3.2.crud_operations/transaction_basics.md) - For more details on transaction management
- [Custom Fields](custom_fields.md) - For extending model capabilities